# Workbench implementation contract

All endpoints are under `/api`. Application JSON errors use `{detail:string}`. Request validation returns a generic 422 detail string without echoing submitted values. The same-origin frontend dev proxy sends `/api` to `127.0.0.1:8765`. There is no authentication or user isolation; use only as a trusted single-user loopback service. The backend checks Host and same-origin writes. Never use external assets. This contract describes implementation behavior, not legal-analysis qualification.

GET /api/health -> {status:"ok", ai_configured:bool, retention_days:int, max_upload_bytes:int, extraction_revision:int, review_revision:int}
GET /documents?limit=100&offset=0 -> Document[]; limit is 1–100, offset >=0. Results sort newest first, with ID as a stable tie-breaker. The response has no total-count field; request later pages until an empty page.
POST /documents multipart field file -> DocumentDetail
GET /documents/{id} -> DocumentDetail
DELETE /documents/{id} -> {deleted:true}
GET /documents/{id}/original -> original file (attachment, PDF may link #page=N)
Document={id,name,format,created_at,state:"ready",sha256}
DocumentDetail adds {text,blocks:Block[],warnings:string[]}
Block={id,text,start,end,page:int|null,kind:"paragraph"|"heading",location:string}. Offsets are Python Unicode code points, [start,end) in extracted text; block exact substrings. Browser should show block.text directly, not slice with JS UTF16 offsets. Source text is untrusted, render as text.
GET /documents/{id}/reviews?summary=false&limit=100&offset=0 -> Review[]; limit is 1–100, offset >=0, newest first. `summary=true` returns paginated metadata without issues, checks, playbook snapshot, AI audit, or AI error. The summary response is intended for history lists; fetch the full review separately.
POST /documents/{id}/reviews JSON {playbook_id} -> Review
GET /reviews/{id} -> Review
Review={id,document_id,playbook_id,playbook_name,created_at,issues:Issue[],checks:Check[],ai_status:string,ai_error:string|null,playbook_snapshot:object}
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
