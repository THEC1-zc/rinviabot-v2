# Cloudflare Logging Setup

## Obiettivo

Il bot principale continua a girare su Render e a fare il suo lavoro normale:

- ricevere messaggi Telegram
- chiamare Claude
- creare eventi Google Calendar

In parallelo, il bot invia i log tecnici a Cloudflare, dove un Worker li salva in D1.

Codex poi lavora su quei log come su un diario completo della pipeline.

## Architettura consigliata

```text
Telegram
  -> Render bot
    -> Claude API
    -> Google Calendar
    -> local JSONL logs
    -> POST best-effort to Cloudflare Worker
         -> D1

Codex
  -> legge repo locale
  -> legge/exporta log da Cloudflare D1
  -> analizza replay e pipeline
```

## Perche' questa e' la strada giusta

Non conviene far scrivere Render direttamente su D1.

La via piu' pulita e stabile e':

- Render invia HTTP a un Worker Cloudflare
- il Worker ha il binding nativo a D1
- il Worker salva

Vantaggi:

- nessuna dipendenza fragile da accesso diretto a D1 da Render
- autenticazione semplice via bearer token
- D1 resta dietro Cloudflare
- in futuro puoi aggiungere filtri, audit, export, dashboard

## Componenti da creare

Nel repo trovi gia' lo scaffold:

- `cloudflare/logger-worker/wrangler.toml.example`
- `cloudflare/logger-worker/schema.sql`
- `cloudflare/logger-worker/src/index.js`

## Dati che vogliamo salvare

Ogni messaggio deve diventare una sequenza di eventi, tutti uniti da `trace_id`.

Esempi di stage:

- `telegram_received`
- `message_analysis_built`
- `claude_request_prepared`
- `claude_response_received`
- `parsed_data_normalized`
- `confirmation_decision`
- `calendar_event_formatted`
- `calendar_event_created`
- `telegram_reply_sent`
- `pipeline_failed`

## Tabella D1

La tabella principale e':

- `pipeline_events`

Contiene:

- timestamp
- trace id
- stage
- chat/message/user ids Telegram
- preview testuale
- payload JSON completo
- sorgente

## Configurazione step-by-step

### 1. Crea un database D1

Da terminale, nella cartella del Worker:

```bash
cd cloudflare/logger-worker
npx wrangler d1 create rinviabot-logs
```

Prendi nota di:

- `database_name`
- `database_id`

### 2. Crea un Worker Cloudflare

Sempre in `cloudflare/logger-worker`, usa il file:

- `wrangler.toml.example`

Copialo in:

- `wrangler.toml`

Poi inserisci:

- nome del Worker
- `database_id`
- `account_id`

### 3. Applica lo schema SQL

```bash
npx wrangler d1 execute rinviabot-logs --file=./schema.sql --remote
```

### 4. Imposta il secret di autenticazione del Worker

```bash
npx wrangler secret put LOG_INGEST_TOKEN
```

Questo token dovra' essere lo stesso anche su Render.

### 5. Deploy del Worker

```bash
npx wrangler deploy
```

Otterrai un URL tipo:

```text
https://rinviabot-logger.<subdomain>.workers.dev
```

Nel setup attuale l'URL del Worker e':

```text
https://rinviabot-fabio.workers.dev
```

Endpoint principale:

- `POST /ingest`

Health check:

- `GET /health`

### 6. Configura Render

Nel servizio Render del bot aggiungi due environment variables:

- `REMOTE_LOG_ENDPOINT=https://rinviabot-fabio.workers.dev/ingest`
- `REMOTE_LOG_TOKEN=<lo stesso token del Worker>`

### 7. Bot behavior consigliato

Il bot deve inviare i log in modalita' best-effort:

- se il logging remoto riesce: bene
- se il logging remoto fallisce: il bot continua comunque a funzionare

Regola chiave:

- il logging remoto non deve mai bloccare creazione evento o risposta Telegram

## Payload HTTP consigliato da Render al Worker

Body JSON:

```json
{
  "ts": "2026-03-20T16:00:00Z",
  "trace_id": "tg-12345-67890",
  "stage": "telegram_received",
  "chat_id": "12345",
  "message_id": "67890",
  "user_id": "999",
  "username": "fabio",
  "text": "Rossi Sodani rinvio al 15/3/26 h 10",
  "source": "rinviabot-render",
  "data": {
    "normalized_message": "Rossi Sodani rinvio al 15/3/26 h 10"
  }
}
```

Header:

```text
Authorization: Bearer <REMOTE_LOG_TOKEN>
Content-Type: application/json
```

## Query utili future

### Ultimi eventi

```sql
SELECT ts, trace_id, stage, text_preview
FROM pipeline_events
ORDER BY id DESC
LIMIT 100;
```

### Tutta la timeline di un messaggio

```sql
SELECT ts, stage, payload_json
FROM pipeline_events
WHERE trace_id = 'tg-12345-67890'
ORDER BY id ASC;
```

### Errori recenti

```sql
SELECT ts, trace_id, stage, payload_json
FROM pipeline_events
WHERE stage = 'pipeline_failed'
ORDER BY id DESC
LIMIT 50;
```

## Integrazione con Codex

Codex non deve leggere Telegram direttamente.

Codex lavorera' su:

- `bot.py`
- `MAP.md`
- `TARGET_ARCHITECTURE.md`
- `LOGGING_PLAN.md`
- export o dump dei log da D1
- eventuali replay fixtures

## Strategia consigliata di rollout

### Fase 1

- tieni attivi i log JSONL locali gia' presenti nel bot
- deploya il Worker Cloudflare + D1

### Fase 2

- aggiungi al bot l'invio remoto best-effort
- fai qualche test run reale

### Fase 3

- verifica che ogni `trace_id` compaia correttamente in D1
- controlla almeno:
  - messaggio raw
  - risposta Claude
  - decisione finale
  - esito calendario

### Fase 4

- inizia a promuovere casi interessanti in `replays/inputs`

## Nota importante

La soluzione Cloudflare e' il ponte.

Il bot continua a vivere su Render.
Cloudflare serve come archivio centrale dei log, non come sostituto del bot.
