# AISYNC.md

Shared sync log for all AI agents working on WORKDB and RinviaBot v3.

## Hard rules (mandatory)

1. Every code or config change MUST update this file.
2. Build number MUST follow `X.y.z` (SemVer):
   - `X` major: breaking change
   - `y` minor: new feature, backward compatible
   - `z` patch: fix/refactor/docs/config with no feature change
3. No commit is valid without:
   - build bump
   - short changelog entry
   - touched files list
4. Cross-repo sync is mandatory:
   - update `/Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md`
   - update `/Users/fabio/Documents/New project/rinviabot v3/AISYNC.md`
5. Latest entry must be on top.

## Current build

- Build: `0.4.8`
- Updated at: `2026-02-24`
- Updated by: `Codex`

## Changelog (newest first)

### 0.4.8 - 2026-02-24 - Codex
- Added global `AI Check` action to scan pratiche/clienti and create in-app notifications for missing essential data.
- Added notification de-duplication (`create_notification_once`) to avoid repeated identical alerts.
- Added chat-driven udienza update: internal chat messages can update `pratiche.udienza` (and `ore`) when pattern includes pratica/rg + date.
- Added fallback notification when chat detects rinvio but no matching pratica is found.
- Added archivia action in pratica edit form and AI-check buttons in dashboard/clienti pages.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/dashboard.html
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/clienti.html
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/pratica_form.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.7 - 2026-02-24 - Codex
- Fixed Excel import consistency: per-row `SAVEPOINT` to prevent full transaction rollback on single-row errors.
- Added duplicate guards for `clienti` (by nome normalized) and `pratiche` (by prat_n+archiviata).
- Goal: avoid doubled clienti and ensure pratiche persist correctly during bulk import.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.6 - 2026-02-24 - Codex
- Import stabilizzato: AI assist reso opzionale (default OFF) per evitare timeout su import pesanti.
- Dashboard import aggiornata con checkbox `Assist AI (piu lento)`.
- Start command Render aggiornato con timeout gunicorn esteso (`--timeout 300`).
- Fix conteggi finali import compatibili con PostgreSQL/RealDictCursor.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/dashboard.html
  - /Users/fabio/workspace/WORKDB/WORKDB/render.yaml
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.5 - 2026-02-24 - Codex
- Added persistent DB administration endpoints: `POST /admin/db/init` and `GET /admin/db/status`.
- Added `ensure_runtime_tables()` to force runtime schema init for core tables (pratiche/chat/telegram/notifications).
- Goal: enable explicit DB initialization and verification on Render PostgreSQL.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.4 - 2026-02-24 - Codex
- Reintroduced Telegram webhook endpoint in WORKDB (`POST /api/telegram/webhook`) to fix 404 on Telegram delivery.
- Added webhook secret validation (`X-Telegram-Bot-Api-Secret-Token`) and update deduplication by `update_id`.
- Added durable storage table `telegram_messages` and mirror of inbound text into internal chat timeline.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.3 - 2026-02-24 - Codex
- Chat UX fix: conferma visiva su invio messaggio (`flash success`) e auto-scroll timeline.
- Nessuna modifica al flusso dati; migliorata solo evidenza utente dopo submit.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/chat.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.3.3 - 2026-02-23 - Codex
- Step 4 Telegram integration: added outbound send support from WORKDB to Telegram.
- Added helper `telegram_send_message()` and protected API endpoint `POST /api/telegram/send`.
- Added outbound logging in `telegram_messages` and mirror line in internal chat timeline.
- Updated chat UI with Telegram send toggle and `chat_id` input.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/chat.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.3.2 - 2026-02-23 - Codex
- Step 3 Telegram integration: added inbound webhook endpoint in WORKDB (`/api/telegram/webhook`).
- Added webhook secret verification via `X-Telegram-Bot-Api-Secret-Token`.
- Added idempotent ingest with `update_id` deduplication and storage in `telegram_messages`.
- Mirrored inbound Telegram text into internal chat timeline (`source=telegram`).
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.3.1 - 2026-02-23 - Codex
- Stabilized notifications subsystem to avoid app outage when notification tables are unavailable/unready at runtime.
- Added defensive fallback in notification create/fetch helpers (non-fatal errors, empty-state fallback).
- Goal: keep WORKDB online and renderable while DB schema catches up.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.2.0 - 2026-02-23 - Codex
- Added autonomous Claude integration directly in WORKDB (`/api/ai/compile`).
- Added internal chat module in WORKDB with optional Claude response (`/chat`).
- Added internal notification engine and global header badge/dropdown (`notifications`).
- Added intervention notifications for unmatched rinvio and missing essential fields.
- Added UI assistant in pratica/cliente forms for AI-assisted field compilation.
- Added roadmap definition file and sample importer for 1 cliente + 1 pratica from archive Excel.
- Imported tester records into local DB: cliente_id=1, pratica_id=1.
- Files:
  - `/Users/fabio/workspace/WORKDB/WORKDB/app.py`
  - `/Users/fabio/workspace/WORKDB/WORKDB/templates/base.html`
  - `/Users/fabio/workspace/WORKDB/WORKDB/templates/chat.html`
  - `/Users/fabio/workspace/WORKDB/WORKDB/templates/notifiche.html`
  - `/Users/fabio/workspace/WORKDB/WORKDB/templates/pratica_form.html`
  - `/Users/fabio/workspace/WORKDB/WORKDB/templates/cliente_form.html`
  - `/Users/fabio/workspace/WORKDB/WORKDB/roadmap.md`
  - `/Users/fabio/workspace/WORKDB/WORKDB/import_sample_rows.py`
  - `/Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md`
  - `/Users/fabio/Documents/New project/rinviabot v3/AISYNC.md`

### 0.1.0 - 2026-02-23 - Codex
- Initialized shared AISYNC protocol between WORKDB and RinviaBot v3.
- Defined hard rules for mandatory updates and SemVer build tracking.
- Created sync requirement across both repositories.
- Files:
  - `/Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md`
  - `/Users/fabio/Documents/New project/rinviabot v3/AISYNC.md`

## Entry template

### X.y.z - YYYY-MM-DD - AgentName
- Summary:
- Impact:
- Files:
  - absolute/path/file1
  - absolute/path/file2
