# Logging Plan

## Goal

Codex must be able to analyze real Telegram conversations and the exact behavior of the bot across the full pipeline.

That means the repository should contain complete, structured logs for:

- inbound Telegram messages
- Claude request/response processing
- normalization/validation decisions
- ambiguity decisions
- Google Calendar payload creation
- final Telegram replies

Without that, Codex can review code, but cannot prove many behavioral bugs.

## Logging principle

Every user message should produce one traceable record across the whole pipeline.

Minimum requirement:

- one correlation ID per incoming Telegram message
- one structured log event per major stage

## Recommended log stages

For each inbound Telegram message, capture:

1. `telegram_received`
- raw message text
- chat id
- message id
- user id if available
- timestamp

2. `message_analysis_built`
- normalized message
- detected date candidates
- detected time candidates
- block count
- hearing hints
- non-hearing hints

3. `claude_request_prepared`
- prompt version or prompt hash
- compact summary of prompt inputs
- analysis metadata used

4. `claude_response_received`
- raw Claude text
- parse success / failure
- extracted JSON if parseable

5. `parsed_data_normalized`
- normalized parsed payload
- warnings
- confidence
- computed type

6. `confirmation_decision`
- whether confirmation was required
- why

7. `calendar_event_formatted`
- event title
- date/time
- location
- description length

8. `calendar_event_created`
- success/failure
- calendar id
- event id
- event link
- API error if any

9. `telegram_reply_sent`
- reply category
- reply text
- whether event was created

10. `pipeline_failed`
- exception class
- exception message
- stage

## Recommended file layout

When we implement logging, keep logs inside the repo in a stable structure:

```text
logs/
  telegram/
    raw/
    structured/
  pipeline/
    jsonl/
  replays/
    inputs/
    expected/
    outputs/
```

Suggested formats:

- `JSONL` for machine-readable logs
- `MD` summaries for human audit reports
- replay fixtures as JSON

## Minimum JSONL schema

Each line should contain fields like:

```json
{
  "ts": "2026-03-20T16:00:00Z",
  "trace_id": "tg-12345-67890",
  "stage": "telegram_received",
  "chat_id": 12345,
  "message_id": 67890,
  "text": "Rossi Sodani rinvio al 15/3/26 h 10",
  "data": {}
}
```

## Why this matters

With complete structured logs, Codex can:

- reconstruct exact failures
- compare raw input vs Claude output vs normalized event
- find recurring error clusters
- replay historical inputs
- measure whether prompt or code changes actually improve results

## Immediate next step

Before the full AI audit, implement logging in `bot.py` for:

- received message
- Claude parsed output
- normalization result
- confirmation decision
- calendar creation result
- final reply

That is the minimum viable observability layer for reliable Codex-driven debugging.
