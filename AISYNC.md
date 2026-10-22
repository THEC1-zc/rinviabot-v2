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
   - update this repository’s root `AISYNC.md`; the old Documents path is obsolete
5. Latest entry must be on top.

## Current build

- Build: `0.5.0`
- Updated at: `2026-10-22`
- Updated by: `Codex`

## Changelog (newest first)

### 0.5.0 - 2026-10-22 - Codex
- Switched extraction and clarification to subscription-first Codex `gpt-6.1-sol` low → Antigravity `gemini-4-argon-low` → existing Claude API last resort. Verified the dedicated Codex 0.159.3 path after the old global CLI rejected the model; no global CLI or shared runtime changed.
- Added encrypted isolated CLI login, runtime homes, refresh preservation, provider audit and subscription-only live probes.
- Replaced dead-end clarification handling with persistent SQLite conversations, contextual followups, explicit final confirmation, owner/revision-bound buttons, `/nuovo` and `/dubbi`. Manual masks enter the same conversation flow.
- Added intent-bound Calendar IDs, payload checks, readback and timeout reconciliation. Corrections are blocked while a write remains uncertain.
- Versioned role-aware public magistrate sources and professional-name hints derived from read-only STUDIO registries/calendar. Read 5 colleague dossiers, 21 substitution records and 589 calendar events over 6 pages; fetched all 15 truncated descriptions. No client source material entered Git and no canonical SAI2 registry was modified.
- Runtime reading rules in `reading/SKILL.md`; reusable skills `rinviabot-ionos` and `rinviabot-lettura` updated/validated.
- Validation: 35 automated tests; live Codex and Argon; integrated synthetic conversation and verified Calendar write/read/cleanup with Telegram simulated and paid fallback disabled; production health and encrypted own-login refresh snapshot succeeded. Human Telegram check requested separately; do not conflate it with the synthetic probe.
- Files: `bot.py`, `llm_runtime.py`, `conversations.py`, `calendar_write.py`, `reference_data.py`, `reference/people.json`, `reference/README.md`, `reading/SKILL.md`, `tests/test_*.py`, `deploy/ionos/{launch.py,save_auth.py,rinviabot.service,health.py,provider_probe.py,dialogue_probe.py,README.md}`, `README.md`, `AISYNC.md`.

### 0.4.13 - 2026-10-22 - Codex
- Migrated the existing Telegram bot and Google Calendar configuration from Render to isolated IONOS service `rinviabot.service`; Render suspended and retained for rollback.
- Added encrypted systemd credential launcher, resource limits, provider health, synthetic calendar preflight and logger probe.
- Fixed logging User-Agent and deployment source metadata; corrected malformed logger URL and mismatched logger token in private runtime configuration.
- Verified live Telegram input/replies, Claude extraction, calendar event read/write and synthetic cleanup, remote logger DB write, automatic service startup, and unchanged persistent QWE/STUDIO process IDs.
- Saved original Render export and corrected IONOS JSON in the central vault; no customer data or credentials added here.
- Files: `bot.py`, `README.md`, `AISYNC.md`, `deploy/ionos/launch.py`, `deploy/ionos/rinviabot.service`, `deploy/ionos/preflight.py`, `deploy/ionos/health.py`, `deploy/ionos/logging_probe.py`, `deploy/ionos/README.md`.
- Reusable operations skill: `/Users/fabio/.codex/skills/rinviabot-ionos/SKILL.md`; evidence and actual limitations in `deploy/ionos/README.md`.

### 0.4.12 - 2026-03-20 - Codex
- Consolidated the repository to a single root-level bot structure for clearer local and remote workflows.
- Moved `AISYNC.md` to the repository root and removed the duplicated nested project files.
- Added `MAP.md` as an operational map for architecture, refactor planning, and debug work.
- Ignored `.DS_Store` and removed tracked macOS metadata files from the repository structure.
- Files:
  - /Users/fabio/workspace/rinviabot v3/.gitignore
  - /Users/fabio/workspace/rinviabot v3/AISYNC.md
  - /Users/fabio/workspace/rinviabot v3/MAP.md
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/AISYNC.md
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/Procfile
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/README.md
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/bot.py
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/gitignore.txt
  - /Users/fabio/workspace/rinviabot v3/rinviabot v3/requirements.txt

### 0.4.11 - 2026-02-24 - Codex
- Added new admin page `Import Chat TXT` to process RinviaBot export chat text files.
- Upload flow updates only future udienza dates and supports dry-run mode.
- If pratica matching fails, creates notification for manual anchoring; handles ambiguous matches too.
- Added sidebar navigation link for quick access to the new page.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/base.html
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/chat_import.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.10 - 2026-02-24 - Codex
- Fixed 500 on `/pratiche` with PostgreSQL date objects by introducing Jinja filter `date10`.
- Updated templates to render date safely for both string and date/datetime values.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/pratiche.html
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/dashboard.html
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/pratica_form.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

### 0.4.9 - 2026-02-24 - Codex
- Import fix: sanitized date placeholders (`NaT`, `definito`, `rinuncia`, `null`) before DB insert.
- Date cleaning rule now returns only valid dates or `None` (never raw text for DATE columns).
- Added admin action to deduplicate clienti by name and re-link pratiche (`POST /admin/clienti/dedupe`).
- Added UI button `Deduplica Clienti` in clienti page.
- Files:
  - /Users/fabio/workspace/WORKDB/WORKDB/app.py
  - /Users/fabio/workspace/WORKDB/WORKDB/templates/clienti.html
  - /Users/fabio/workspace/WORKDB/WORKDB/AISYNC.md
  - /Users/fabio/Documents/New project/rinviabot v3/AISYNC.md

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
