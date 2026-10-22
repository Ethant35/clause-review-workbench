# Workbench implementation contract

All endpoints /api. JSON errors {detail:string}; 422 may contain validation array. Same-origin frontend dev proxy /api to 127.0.0.1:8765. No auth on loopback single-user service; trusted Host and same-origin write checks on backend. Never use external assets.

GET /health -> {status:"ok", ai_configured:bool, retention_days:int, max_upload_bytes:int}
GET /documents -> Document[]
POST /documents multipart field file -> DocumentDetail
GET /documents/{id} -> DocumentDetail
DELETE /documents/{id} -> {deleted:true}
GET /documents/{id}/original -> original file (attachment, PDF may link #page=N)
Document={id,name,format,created_at,state:"ready",sha256}
DocumentDetail adds {text,blocks:Block[],warnings:string[]}
Block={id,text,start,end,page:int|null,kind:"paragraph"|"heading",location:string}. Offsets are Python Unicode code points, [start,end) in extracted text; block exact substrings. Browser should show block.text directly, not slice with JS UTF16 offsets. Source text is untrusted, render as text.
GET /documents/{id}/reviews -> Review[]
POST /documents/{id}/reviews JSON {playbook_id} -> Review
GET /reviews/{id} -> Review
Review={id,document_id,playbook_id,playbook_name,created_at,issues:Issue[],checks:Check[],ai_status:string,ai_error:string|null,playbook_snapshot:object}
Issue={id,rule_id,severity:"high"|"medium"|"low",category,observed_language:string|null,absence:bool,source_anchor:Block|null,explanation,preferred_position,negotiating_response,status:"unresolved"|"accepted"|"rejected",notes,confidence:"OBJECTIVE"|"NEEDS_REVIEW",origin:"deterministic"|"ai"}
Check={rule_id,category,outcome:"COMPLIANT"|"ISSUE"|"NEEDS_REVIEW"|"NOT_APPLICABLE",properties:object}
PATCH /reviews/{id}/issues/{issue_id} {status,notes} -> Issue
GET /reviews/{id}/export?format=json|markdown|docx -> download
POST /reviews/{id}/ai {consent:true,model:string,provider:string,max_output_tokens:1024,max_cost_usd:0.05} -> Review. Requires configured server OPENROUTER_API_KEY. Must have explicit unchecked consent checkbox identifying external transmission, model/provider and budget fields. Failures return HTTP error and persist ai_error/status on review; offline review remains usable. Never show API key input.
GET /playbooks -> {id,name,version,description}[]
GET /playbooks/{id} -> {id,name,version,description,yaml:string}
POST /playbooks {yaml:string} -> same
PUT /playbooks/{id} {yaml:string} -> same
POST /playbooks/{id}/duplicate -> same (new id/name)
GET /playbooks/{id}/export -> YAML attachment
UI: library upload/list/state/delete/history; open original and extracted source; select playbook/run; severity/category groups; issue filters/search; select issue shows exact source block with location and original link; status/notes save; exports; playbook manager create/duplicate/edit/import/export via YAML editor. YAML editor is sufficient editable UI, provide validation feedback. New blank playbook editor may start from selected exported YAML and explanatory help. Keyboard accessible, responsive, calm professional teal/navy palette. No fake results. Clear legal-review aid disclaimer. Show checks including compliant outcomes and properties (liability cap basis).
