# Codex Audit Prompt

Use this prompt when you want Codex to audit, debug, and improve the RinviaBot Telegram -> Claude -> Calendar pipeline using real repository evidence.

## Goal

The end goal of this project is:

- a Telegram chat that reads Fabio's messages with very high intelligence
- understands whether the message is a hearing postponement, sentence, reserve, procedural note, or ambiguous case
- creates correct Google Calendar events when appropriate
- asks for clarification only when truly necessary
- behaves consistently and safely in production

Codex should work from real evidence, not assumptions.

## Prompt

```text
You are auditing and improving RinviaBot, a Telegram -> Claude -> Google Calendar automation pipeline.

The real product goal is:
- Fabio sends short natural-language legal notes in Telegram
- the system reads them intelligently
- if the message represents a future hearing/postponement, it creates the correct calendar event
- if the message is not a hearing, it responds correctly without creating an event
- if the message is ambiguous, it asks for clarification in a controlled and user-friendly way

You are working inside the repository itself.

Primary source files:
- bot.py
- MAP.md
- AISYNC.md
- repository logs / exported chat history / structured replay inputs, if present

Your task is to perform an evidence-based engineering audit and stabilization review of the whole pipeline.

Rules:
- Do not guess.
- Use repository data, logs, exported chat history, and code as evidence.
- If logs or chat exports are missing, say exactly what is missing and what cannot be proven without them.
- Treat observed behavior and stored history as more important than intention in comments or README.
- Distinguish clearly between:
  - confirmed bugs
  - likely issues
  - improvement opportunities
- Prefer deterministic fixes over heuristic-only fixes.
- Use exact file references and line numbers for code findings.
- Use exact examples from logs or chat history whenever possible.

System to reconstruct:
Telegram message
-> preprocessing / normalization
-> Claude prompt input
-> Claude raw output
-> bot-side parsing / normalization / validation
-> ambiguity handling
-> calendar event formatting
-> Google Calendar API creation
-> Telegram user reply

What to analyze:

1. Discovery
- Find all relevant evidence in the repo:
  - bot logic
  - prompt logic
  - parsing/normalization logic
  - ambiguity handling
  - calendar formatting / API logic
  - Telegram reply formatting
  - logs
  - exported chat history
  - replay fixtures or historical examples
- Summarize what evidence exists and how reliable it is.

2. System reconstruction
- Rebuild the real end-to-end data flow from user message to final outcome.
- Show how free text becomes structured event data.
- Identify each transformation stage and its safeguards.

3. Failure detection
Using code + logs + historical messages, identify:
- wrong date extraction
- wrong time extraction
- wrong party/judge/title extraction
- wrong classification between hearing and non-hearing
- missing events
- duplicate events
- malformed Telegram clarification messages
- malformed or unsafe calendar payloads
- ambiguity not handled
- ambiguity handled too aggressively
- relative date or locale issues
- multi-event message failures
- parse failures caused by unstable Claude output

4. Pattern analysis
- Group recurring failures into clusters.
- Estimate frequency if data allows it.
- Show representative examples.

5. Root cause analysis
For each confirmed issue, determine whether the main cause is:
- prompt design
- Claude output instability
- parsing / normalization logic
- bot-side conversation state
- formatting / UX of clarification messages
- calendar formatting logic
- missing validation layer
- inadequate logs / observability

6. Improvement design
Propose concrete improvements for:
- prompt structure
- Claude JSON contract
- validation before calendar creation
- ambiguity / clarification flow
- Telegram reply UX
- observability and logging
- replay testing and regression checks

7. Replay simulation
If replayable historical inputs exist:
- run or simulate representative messages through current logic
- compare actual vs expected behavior
- show how improved logic would change outcomes

Output format:

A. Evidence Inventory
- available datasets
- missing datasets
- confidence level

B. System Map
- concise end-to-end explanation
- key code entrypoints

C. Findings
- ordered by severity
- each finding must include:
  - title
  - severity
  - evidence
  - affected component
  - user impact

D. Root Causes
- one subsection per finding

E. Fix Plan
- quick wins
- medium refactors
- structural improvements

F. Optional Implementation
- if feasible, propose or apply code changes tied directly to findings

When relevant, prioritize this product principle:
The system should create calendar events only when the interpretation is reliable, but it should also avoid unnecessary clarification requests. The desired behavior is "extremely intelligent but operationally safe."
```

## How to use it

Best used when the repository contains:

- exported Telegram chat history
- structured logs of message parsing and event creation
- source code of the active bot

If logs are not yet present in usable form, pair this prompt with `LOGGING_PLAN.md`.
