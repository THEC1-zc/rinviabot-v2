# Target Architecture

## Product goal

RinviaBot must behave like an extremely intelligent legal assistant inside Telegram:

- Fabio sends short, messy, real-world legal notes
- the system understands intent and extracts the right structured meaning
- if the message describes a future hearing/postponement, it creates the correct calendar event
- if the message is not a hearing, it responds correctly without creating an event
- if the message is ambiguous, it asks a focused clarification question
- every decision must be observable, replayable, and improvable over time

## Why redesign now

We do not have reliable exports of past Telegram chat history.

So the right strategy is:

- instrument the future pipeline well
- capture complete evidence from now on
- make each new message usable for audit, replay, and improvement

This architecture is optimized for future learning from real usage.

## Architecture principles

1. One message, one trace
- every incoming Telegram message gets a `trace_id`
- the full lifecycle is logged end-to-end

2. Separate intelligence from execution
- AI interprets
- validation decides whether execution is allowed
- calendar creation happens only after passing hard checks

3. Safe by default
- ambiguous messages should not silently create wrong events
- unnecessary clarifications should also be minimized

4. Replay-first engineering
- important messages should be reproducible as test/replay fixtures
- every regression should be testable

5. Codex-readable system
- logs, prompts, structured outputs, and replay inputs must be stored in stable formats
- future audits must be evidence-based

## Target pipeline

```text
Telegram inbound message
  -> Ingress logging
  -> Preprocessing and normalization
  -> AI interpretation
  -> JSON extraction / schema validation
  -> Deterministic normalization
  -> Risk evaluation
  -> Decision:
       - non-hearing reply
       - clarification flow
       - calendar event creation
  -> Outbound Telegram reply
  -> Structured logging
  -> Replay fixture optional
```

## Target modules

### 1. Ingress layer

Responsibility:

- receive Telegram message
- assign `trace_id`
- capture raw message safely
- hand off to orchestrator

Current location:

- `handle_message()` in `bot.py`

Future direction:

- keep Telegram-specific concerns here only
- move business logic out of the handler

### 2. Preprocessing layer

Responsibility:

- normalize whitespace
- normalize separators
- detect possible dates/times
- detect message blocks
- generate technical hints for AI and validators

Current functions:

- `normalize_whitespace()`
- `normalize_message_text()`
- `split_message_blocks()`
- `extract_dates_from_text()`
- `extract_times_from_text()`
- `build_message_analysis()`

Future direction:

- keep this deterministic
- expand only with rules that are easy to test

### 3. AI interpretation layer

Responsibility:

- interpret the full meaning of the message
- classify message type
- propose structured output

Current location:

- `parse_message_with_ai()`

Future direction:

- isolate prompt building from API calling
- version prompts explicitly
- log prompt version/hash on every call
- force a stronger JSON contract

### 4. Validation and normalization layer

Responsibility:

- sanitize AI output
- normalize dates/times/judges
- reject malformed outputs
- determine if confidence is high enough

Current functions:

- `extract_json_object()`
- `normalize_judge_name()`
- `normalize_event_date()`
- `normalize_event_time()`
- `infer_tipo_from_text()`
- `validate_and_normalize_parsed_data()`
- `should_require_confirmation()`
- `build_confirmation_from_events()`

Future direction:

- make this the main safety barrier
- keep rules deterministic and auditable
- never let raw AI output reach calendar creation directly

### 5. Conversation-state layer

Responsibility:

- remember pending clarifications
- map user answers like `si`, `no`, `a`, `b`, or free-text correction
- resume the right pending flow

Current status:

- missing

Why it matters:

- clarification currently exists only as text
- there is no stateful continuation

Future direction:

- add lightweight persistence for pending clarifications
- minimum key:
  - chat id
  - message id
  - trace id
  - pending type
  - proposed interpretation
  - expiration time

### 6. Calendar execution layer

Responsibility:

- convert validated hearing event into Google Calendar payload
- execute creation
- log success/failure deterministically

Current functions:

- `format_calendar_event()`
- `create_google_calendar_event()`

Future direction:

- make payload formatting auditable
- add duplicate-protection strategy later
- capture API request outcome in logs every time

### 7. Observability layer

Responsibility:

- create machine-readable evidence for future audits
- support incident analysis and replay

Current assets:

- `LOGGING_PLAN.md`
- new JSONL logging in `bot.py`

Target output:

- `logs/telegram/raw/messages.jsonl`
- `logs/pipeline/jsonl/pipeline.jsonl`

Future direction:

- add structured clarification logs
- optionally add daily summary generation

### 8. Replay and regression layer

Responsibility:

- turn real messages into reusable fixtures
- compare current behavior against expected behavior
- protect improvements from regressions

Current structure:

- `replays/inputs/`
- `replays/expected/`
- `replays/outputs/`

Future direction:

- manually curate important real-world messages
- store expected structured outputs
- add a replay runner

## Target decision model

Every message should end in exactly one of these outcomes:

1. `non_hearing_reply`
- sentence / reserve / note / similar

2. `clarification_required`
- message is potentially actionable but unsafe to execute

3. `calendar_event_created`
- validated hearing event created successfully

4. `calendar_event_failed`
- validated hearing event could not be created because of downstream error

5. `parse_failed`
- interpretation was not reliable enough to proceed

This outcome model should become explicit in logs and eventually in code.

## Target clarification model

Clarification messages should become structured and operational, not just descriptive.

Target clarification format:

- what I understood
- what is uncertain
- what action I need from Fabio
- how Fabio can answer quickly

Example shape:

```text
Ho bisogno di una conferma prima di creare l'evento.

Lettura proposta:
- Parte: Rossi
- Giudice: Sodani
- Data: 15/03/2026
- Ora: 10:00

Punto incerto:
- Il giudice potrebbe essere un difensore, non il magistrato

Rispondi con una di queste opzioni:
- SI
- NO
- CORREZIONE: <testo libero>
```

Future enhancement:

- Telegram inline buttons if useful

## Data model to grow toward

Suggested internal entities:

- `RawTelegramMessage`
- `MessageAnalysis`
- `AiInterpretation`
- `NormalizedDecision`
- `PendingClarification`
- `CalendarEventDraft`
- `PipelineOutcome`

Even if we keep one Python file for now, thinking in these entities will reduce confusion.

## Suggested implementation phases

### Phase 1: observability baseline

- done or started:
  - structured logs
  - stable directories
  - Codex audit prompt
  - logging plan

### Phase 2: architecture split

- extract pure helper functions into clearer sections or modules
- separate:
  - ingress
  - AI call
  - validators
  - Telegram reply rendering
  - calendar execution

### Phase 3: clarification state

- introduce pending clarification persistence
- support reply continuation

### Phase 4: replay harness

- save representative live cases as fixtures
- build repeatable replay checks

### Phase 5: prompt and rules hardening

- redesign prompt
- redesign clarification output format
- expand deterministic safety rules

## What Codex should have available

To improve the system over time, Codex should always be able to access:

- source code
- `MAP.md`
- `TARGET_ARCHITECTURE.md`
- `LOGGING_PLAN.md`
- `CODEX_AUDIT_PROMPT.md`
- structured future logs
- curated replay fixtures from real messages

That is the minimum operational memory of the system.
