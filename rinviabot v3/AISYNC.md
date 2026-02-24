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

- Build: `0.3.3`
- Updated at: `2026-02-23`
- Updated by: `Codex`

## Changelog (newest first)

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
