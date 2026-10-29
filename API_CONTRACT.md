# Workbench implementation contract

All endpoints are under `/api`. Application JSON errors use `{detail:string}`. Request validation returns a generic 422 detail string without echoing submitted values. The same-origin frontend dev proxy sends `/api` to `127.0.0.1:8765`. There is no authentication or user isolation; use only as a trusted single-user loopback service. The backend checks Host and same-origin writes. Never use external assets. This contract describes implementation behavior, not legal-analysis qualification.

GET /api/health -> {status:"ok", ai_configured:bool, retention_days:int, max_upload_bytes:int, extraction_revision:int, review_revision:int}
GET /documents?limit=100&offset=0 -> Document[]; limit is 1–100, offset >=0. Results sort newest first, with ID as a stable tie-breaker. The response has no total-count field; request later pages until an empty page.
POST /documents multipart field file -> DocumentDetail. Text-based PDFs with raster images are accepted only when every page has extractable text and all image placement/resource checks pass. They return `state:"needs_visual_check"`, `visual_check.status:"NEEDS_VISUAL_CHECK"`, an image manifest, and a warning. OCR remains unsupported. PDFs with page-scale images, invalid positions, images fully off the page crop or more than half off the crop, or any page without extractable text return 422. Small page-edge bleed is clipped to the visible crop with its raw coordinates retained and a warning. All pages and image regions must be compared manually against extracted text; no automated completeness or image-visibility check is claimed. PDF layers and transparency can affect visibility.
GET /documents/{id} -> DocumentDetail
DELETE /documents/{id} -> {deleted:true}
GET /documents/{id}/original -> original file (attachment, PDF may link #page=N)
POST /documents/{id}/visual-check JSON `{confirm_no_missing_text:true,original_sha256,extraction_revision,manifest_sha256}` -> updated DocumentDetail. All values must match the current document and image manifest. The service verifies the stored original SHA-256 and records the UTC confirmation time. A confirmation is a manual reviewer assertion; it does not establish automated OCR or completeness. Reviews and AI requests are blocked until confirmed.
POST /documents/{id}/reprocess -> 201 DocumentDetail with a new `id` and `source_document_id` lineage. The service verifies the stored source SHA-256, extracts current rules, and creates a fresh document with no reviews or decisions copied. The old document and review history remain unchanged. Each successful call creates another new document; clients should prevent accidental duplicate submissions.
Document={id,name,format,created_at,state:"ready"|"needs_visual_check",sha256,source_document_id?:string,visual_check:{status:"NOT_REQUIRED"|"NEEDS_VISUAL_CHECK"|"CONFIRMED",manifest_sha256:string|null,...},image_manifest?:{page:int,bbox:[number,number,number,number],raw_bbox_points:[number,number,number,number],clipped:bool,width:int,height:int}[]}. `bbox` is the visible portion normalized to the page crop and bounded to [0,1]. When `clipped` is true, `raw_bbox_points` preserves the PDF placement outside that crop; content beyond the crop is not analyzed and a warning is included.
DocumentDetail adds {text,blocks:Block[],warnings:string[]}
Block={id,text,start,end,page:int|null,kind:"paragraph"|"heading",location:string}. Offsets are Python Unicode code points, [start,end) in extracted text; block exact substrings. Browser should show block.text directly, not slice with JS UTF16 offsets. Source text is untrusted, render as text.
GET /documents/{id}/reviews?summary=false&limit=100&offset=0 -> Review[]; limit is 1–100, offset >=0, newest first. `summary=true` returns paginated metadata without issues, checks, playbook snapshot, AI audit, or AI error. The summary response is intended for history lists; fetch the full review separately.
POST /documents/{id}/reviews JSON {playbook_id} -> Review
GET /reviews/{id} -> Review
Review={id,document_id,playbook_id,playbook_name,created_at,issues:Issue[],checks:Check[],ai_status:string,ai_error:string|null,playbook_snapshot:object,source_warnings:string[],source_visual_check:object}
Issue={id,rule_id,severity:"high"|"medium"|"low",category,observed_language:string|null,absence:bool,source_anchor:Block|null,explanation,preferred_position,negotiating_response,status:"unresolved"|"accepted"|"rejected",notes,confidence:"OBJECTIVE"|"NEEDS_REVIEW",origin:"deterministic"|"ai"}
Check={rule_id,category,outcome:"COMPLIANT"|"ISSUE"|"NEEDS_REVIEW"|"NOT_APPLICABLE",properties:object}
PATCH /reviews/{id}/issues/{issue_id} with any nonempty subset of `{status,notes}` -> Issue. `status` may be `accepted`, `rejected`, or `unresolved`; `notes` may be a string up to 10,000 characters. Null values and an empty object are rejected. The update is atomic.
GET /reviews/{id}/export?format=json|markdown|docx -> download
POST /reviews/{id}/ai {consent:true,model:string,provider:string,max_output_tokens:1024,max_cost_usd:0.05} -> Review. Requires configured server `OPENROUTER_API_KEY`. Must have explicit unchecked consent checkbox identifying external transmission, model/provider and budget fields. A request is persisted as `IN_PROGRESS` before transmission. If the app cannot establish the outcome after transmission may have started, it records `OUTCOME_UNKNOWN`; it does not retry automatically because a provider charge may have occurred. Other outcomes include `BLOCKED_EXTERNAL`, `ERROR`, and `VERIFIED_CITATIONS_REQUIRES_REVIEW`. Failures persist status/error on the review; offline review remains usable. Never show API key input. AI is not qualified for legal accuracy.
GET /playbooks -> {id,name,version,description}[]
GET /playbooks/{id} -> {id,name,version,description,yaml:string}
POST /playbooks {yaml:string} -> same
PUT /playbooks/{id} {yaml:string} -> same
POST /playbooks/{id}/duplicate -> same (new id/name)
GET /playbooks/{id}/export -> YAML attachment
UI: library upload/list/state/delete/history; open original and extracted source; select playbook/run; severity/category groups; issue filters/search; select issue shows exact source block with location and original link; status/notes save; exports; playbook manager create/duplicate/edit/import/export via YAML editor. YAML editor is sufficient editable UI, provide validation feedback. New blank playbook editor may start from selected exported YAML and explanatory help. Keyboard accessible, responsive, calm professional teal/navy palette. No fake results. Clear legal-review aid disclaimer. Show checks including compliant outcomes and properties (liability cap basis).

## Request, admission, and diagnostics limits

Non-upload request bodies are limited to 300,000 bytes; multipart upload requests have a body limit of 10 MiB plus 1,000,000 bytes around the 10 MiB file limit. The server stops waiting for a request body after 30 seconds and returns 408; oversize bodies return 413. Local admission limits are 16 active requests total, two concurrent uploads, two concurrent reviews, and one concurrent AI request. Rejected work returns 503 with `Retry-After: 2`. These controls are per process and do not provide multi-user isolation.

The server writes bounded local JSONL diagnostics with request ID, entry point, response status, route template, duration, and timestamp. It does not log document text, request bodies, filenames, or provider response bodies. Diagnostics rotate at 1,000,000 bytes with two backups and use mode 0600. Storage-level failures return a content-free 503 that points to the [recovery guide](docs/recovery.md).

## Common playbook settings (1.3.0)

`GET /api/playbooks/{id}/settings` returns `id`, `name`, `version`, `description`,
`revision` (SHA256 of saved YAML), and rule `id`, `category`, `description`,
`severity`, `required`, `preferred_position`, `negotiation_guidance`, and
`fallback_language` fields.

`PATCH /api/playbooks/{id}/settings` requires that revision and at least one
explicit change. Rules are partial objects keyed by unique existing IDs. Only
priority, required-clause detection and guidance fields can change here; regular
expression logic remains in advanced YAML. Null is allowed only to clear fallback
language. Unknown/duplicate rule IDs or invalid fields return 422; a stale revision
returns 409. The update is one transaction. Existing review snapshots remain intact.
The same stale revision cannot silently overwrite a later settings edit.

UI “Confirm finding” maps to stored `accepted`; “Dismiss finding” maps to
`rejected`; “Clear decision” maps to `unresolved`. These are decisions about a
finding, not approval or rejection of contract terms. Repeated confirmation is
idempotent. Source/export API enums remain backward compatible.

## Contract revisions and comparisons

`POST /api/documents?revision_of=<document_id>` accepts the same multipart upload
as the ordinary upload. It creates a separate source record with an immutable
`previous_document_id` pointer. The parent must exist through publication. No
review, note or decision is copied. Deleting the parent does not cascade to its
revisions. The existing document lists expose this pointer.

`GET /api/reviews/{after_review_id}/comparison?baseline_review_id=<before_review_id>`
returns a read-only version-1 comparison. Identical review IDs return 422. Missing
records return 404. Failed original hashes, changed saved source digests or mismatched
quoted evidence return 409. `download=true` returns the same JSON as an attachment.

Fields: `before_review_id`, `after_review_id`, `before_document`, `after_document`
(each with id/name/sha256), `same_policy`, `same_checks`, `same_extracted_text`,
`same_original`, `before_context`, `after_context`, `warnings`, `text_changes` and `rules`.
Context objects include saved policy snapshots and extraction/analysis revisions. Text-change kinds are
`insert`, `delete`, `replace`; each contains exact `before` and `after` blocks.
Rule statuses are `ADDED`, `NO_LONGER_FLAGGED`, `CHANGED`, `UNCHANGED`,
`NOT_COMPARABLE`. Each rule contains checks, issues, prior decisions and
`revisit_prior_decisions`. A change anywhere in the source or review context requires
reconsideration of recorded prior decisions. No API copies decisions.

New reviews include `source_sha256` and `source_text_sha256`. Legacy comparisons
check anchors and disclose that no historical full-text digest exists. Internal
`COMPLIANT` remains the API token for matching configured conditions; it is not
legal approval. Extraction revision 6 introduces table/row/cell and PDF bbox metadata
and broader visual-check gating. Existing records are preserved, not migrated in place.
