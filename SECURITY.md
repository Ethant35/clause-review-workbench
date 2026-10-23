# Security

Author: Ethan

Run on loopback for one trusted local user. No authentication or user isolation is provided. Any local process with access to the service can read or delete data. Do not expose this service to untrusted users or a public network.

The v1.2.0 readiness evidence covers a single-user local macOS workflow. It does not establish multi-user or network security, broad legal accuracy, or qualification of optional AI for legal analysis.

Controls include content-sniffed upload parsing; a 10 MiB file limit; 200 PDF pages; 30 MB DOCX expanded size; 300,000 extracted characters; 5,000 blocks; bounded parsing subprocesses; bounded regex matching; UUID storage paths; SQL parameterization; safe React text rendering; a restrictive Content Security Policy on the production server; trusted local Host checks; and rejection of cross-site writes. The API bounds request bodies and active work; body-read timeout returns 408, oversize requests return 413, and admission rejection returns 503 with `Retry-After: 2`. These are per-process availability limits, not defenses against a malicious same-user process. Malformed formats, macro documents, XML entity attacks, unsupported DOCX features, and image-only or partially textless PDFs are rejected. Original files should still be opened only in patched document viewers.

Uploaded filenames are sanitized for display and never used as disk paths. Report filenames use generated IDs. Markdown escapes HTML. Source excerpts remain untrusted data and are never rendered through `innerHTML`. API docs are disabled in the deployment surface; ordinary request access logging is disabled by the supported launcher. Bounded local diagnostics retain only timestamp, event, request ID, entry point, status, route template, and duration. The JSONL log is mode 0600, rotates at 1,000,000 bytes, and keeps two backups. It does not include source text, request bodies, filenames, or provider response bodies. Storage errors return content-free guidance to the [local recovery guide](docs/recovery.md).

AI output is untrusted. It cannot execute tools or alter policy. Quotes, block references, and rule IDs must validate. Interpretations remain uncertain. Prompt injection can still distort model reasoning; attorney review remains required. AI provider errors do not remove offline results.

Report vulnerabilities privately using GitHub's repository security reporting if available, or contact the repository owner without posting contracts, credentials, or exploit data in a public issue. Dependency lockfiles support repeatable installs; keep runtimes and dependencies patched. Use the safe launcher only after explicitly installing the frozen runtime environment (`uv sync --frozen --python 3.12 --no-dev`) and building the frontend. GitHub Actions are intentionally disabled by project-owner instruction; all release checks run locally.
