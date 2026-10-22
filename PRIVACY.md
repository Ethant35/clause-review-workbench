# Privacy

Author: Ethan

Documents and reviews stay in local storage by default. There is no automatic analytics, telemetry, or background provider request. Offline parsing, reviews, exports, and playbook editing work without credentials. The browser uses only local assets.

`CRW_DATA_DIR` selects storage (default `.data` in the working directory). The directory and source files use restrictive permissions. SQLite is not application-encrypted; use full-disk encryption and an appropriate local account. Operating-system backups, swap, browser downloads, and exported reports may retain copies.

`CRW_RETENTION_DAYS=0` keeps documents until deletion. A positive integer deletes expired documents at startup and within approximately one minute while running. Deletion removes the original file, extracted text, and associated reviews using SQLite cascade and secure-delete. It does not guarantee forensic erasure from SSDs or backups. Playbooks remain because they are independent policy settings. Downloaded reports are not removed.

Optional AI requires server-side `OPENROUTER_API_KEY` and an explicit checkbox before each UI request. The entire extracted document blocks and selected playbook are sent to OpenRouter and the named provider. Reviewer notes are not transmitted. The original binary file is not sent. Provider retention and handling policies apply; confirm those policies and your authority to transmit the document. Declining consent makes no external request.

Authentication and pricing requests send credentials and model/provider information without document text. Review requests have bounded output tokens and a conservative price estimate; a provider/account hard spending cap is recommended for billing control. No key is placed in frontend code, reports, Git, or ordinary application logs. Do not enable HTTP body logging for confidential documents. E2E acceptance uses only repository-owned synthetic contracts.
