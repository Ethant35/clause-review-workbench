# Security

Author: Ethan

Run on loopback for one trusted local user. No authentication or user isolation is provided. Any local process with access to the service can read or delete data. Do not expose this service to untrusted users or a public network.

Controls include content-sniffed upload parsing; 10 MiB file limit; 200 PDF pages; 30 MB DOCX expanded size; 300,000 extracted characters; 5,000 blocks; bounded parsing subprocesses; bounded regex matching; UUID storage paths; SQL parameterization; safe React text rendering; a restrictive Content Security Policy on the production server; trusted local Host checks; and rejection of cross-site writes. Malformed formats, macro documents, XML entity attacks, unsupported DOCX features, and image-only or partially textless PDFs are rejected. Original files should still be opened only in patched document viewers.

Uploaded filenames are sanitized for display and never used as disk paths. Report filenames use generated IDs. Markdown escapes HTML. Source excerpts remain untrusted data and are never rendered through `innerHTML`. API docs are disabled in the deployment surface. Ordinary request access logging is disabled by documented launch commands; errors do not include contracts or provider response bodies.

AI output is untrusted. It cannot execute tools or alter policy. Quotes, block references, and rule IDs must validate. Interpretations remain uncertain. Prompt injection can still distort model reasoning; attorney review remains required. AI provider errors do not remove offline results.

Report vulnerabilities privately using GitHub's repository security reporting if available, or contact the repository owner without posting contracts, credentials, or exploit data in a public issue. Dependency lockfiles support repeatable installs; keep runtimes and dependencies patched. GitHub Actions are intentionally disabled by project-owner instruction; all release checks run locally.
