# Architecture

Author: Ethan

Clause Review Workbench is a single-user, local contract review aid. It does not provide legal advice or replace attorney review. A React/TypeScript browser client talks to a FastAPI service on loopback. SQLite stores document metadata, extracted blocks, playbooks, immutable playbook snapshots, and reviews. Original bytes are stored separately under random UUID names, with a SHA-256 digest.

## Extraction and evidence

File signatures and content select DOCX, PDF, or UTF-8 text parsing. DOCX body paragraphs, including table cells, retain their order. PDF text blocks retain page numbers. Text anchors retain line numbers. The canonical extracted text joins blocks with two newlines. Anchors contain block ID, exact text, start/end Unicode code-point offsets, and source location. These offsets describe extracted text, not original ZIP/PDF bytes. Every issue quote is checked against a stored block and canonical text before persistence. Missing-provision findings have null quote and anchor, an explicit absence flag, and NEEDS_REVIEW confidence.

Binary extraction runs in a disposable subprocess with a 15-second wall limit, 10 CPU seconds, and Linux address-space limit. Uploads, ZIP expansion, PDF pages, text size, and block counts are bounded. DOCX tracked changes, text boxes, notes, embedded imports, macros, content controls, fields/drawings, directly marked hidden text, and PDFs with raster images or textless pages are rejected. DOCX headers/footers are excluded with a visible warning. PDF visual reading order and text encodings can still be imperfect; inspect originals.

## Analysis

Layer A uses the selected versioned YAML conditions. Presence patterns locate candidate blocks. Recognized negation, unresolved cross-references, open-ended qualifications, and mixed liability/indemnity scope first trigger conservative abstention. Remaining unacceptable matches produce objective pattern findings; every acceptable group must match a candidate block before COMPLIANT is returned. Other identified language becomes NEEDS_REVIEW. A second inconsistent clause prevents a clean result. Common number words and typography are normalized only for matching; quotations remain unchanged. Explicit liability-cap properties identify a fee basis and period separately from cap exceptions. These are narrow string-pattern facts, not conclusions about enforceability.

Layer B is isolated in `backend/workbench/ai.py`. It is called only through an explicit-consent endpoint. OpenRouter authentication and provider endpoint prices are checked before contract transmission. One configured model and explicitly selected provider are used, with fallback disabled. Input size, output tokens, estimated dollar cost, and provider maximum prices constrain each request. No automatic retries occur. All AI findings remain NEEDS_REVIEW even when quotations match. Invalid quotes or rule IDs reject the entire response; the offline review and reviewer decisions remain available.

## Persistence and deployment

Each SQLite write is transactional. Reviewer decisions use an immediate transaction to avoid lost writes. Review history retains the playbook snapshot used at analysis time. Changes to a playbook affect later reviews only. API/UI/export guidance is derived from that saved snapshot, including alternatives and optional fallback wording. Extraction and review revisions mark the checks used. Older rows are not migrated or rewritten: read/export views add a historical warning, and new analysis requires a fresh upload. Retention runs at startup and once per minute. Deleting a document cascades to all reviews and removes its original. Exports downloaded by a user are outside server retention.

Production serves the built frontend from the backend. Development uses Vite's same-origin `/api` proxy. No remote scripts, fonts, analytics, or paid hosting are required. This is not a multi-user service: do not expose it to a network without adding authentication, authorization, transport protection, and isolation.
