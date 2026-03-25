# RinviaBot v2 🤖⚖️

Bot Telegram con AI intelligente per automatizzare la gestione dei rinvii delle udienze.

## 🎯 Cosa fa

- ✅ Legge automaticamente i messaggi dal gruppo Telegram
- ✅ Usa Claude AI per interpretare messaggi complessi
- ✅ Estrae: data, ora, caso, RG, tribunale, note
- ✅ Crea eventi in Google Calendar (coming soon)
- ✅ Completamente automatico

## 📋 Requisiti

- Account Telegram (bot token)
- API Key Anthropic Claude
- Account Render.com (hosting gratuito)
- Google Calendar (optional, coming soon)

## 🚀 Deploy su Render.com

### 1. Prepara le variabili d'ambiente

Avrai bisogno di:
- `TELEGRAM_BOT_TOKEN` - Token del bot da @BotFather
- `ANTHROPIC_API_KEY` - API key da console.anthropic.com
- `WEBHOOK_URL` - URL del tuo servizio Render (lo ottieni dopo il deploy)

### 2. Deploy

1. Vai su [Render.com](https://render.com)
2. Collega questo repository GitHub
3. Crea nuovo "Web Service"
4. Configura le variabili d'ambiente
5. Deploy!

### 3. Configura Webhook

Dopo il primo deploy, Render ti dà un URL tipo:
```
https://rinviabot-v2.onrender.com
```

Aggiungi questa variabile:
```
WEBHOOK_URL=https://rinviabot-v2.onrender.com
```

E fai re-deploy.

## 📝 Uso

1. Crea gruppo Telegram privato
2. Aggiungi il bot al gruppo
3. Rendi il bot admin
4. Scrivi messaggi tipo:

```
Serafini: 4264/2020 rgnr - 20/09/2026 h 10.30 
testi Folcarelli diffidati
```

5. Il bot risponde con conferma e crea l'evento!

## 💰 Costi

- Hosting Render.com: **GRATIS** (750 ore/mese)
- Claude API: **~1-2€/mese** (5$ durano 6+ mesi)
- Telegram Bot: **GRATIS**
- Google Calendar: **GRATIS**

**Totale: ~1-2€/mese**

## 🔧 Sviluppo locale

```bash
# Clone
git clone https://github.com/tuousername/rinviabot-v2.git
cd rinviabot-v2

# Installa dipendenze
pip install -r requirements.txt

# Configura variabili (crea file .env)
TELEGRAM_BOT_TOKEN=il_tuo_token
ANTHROPIC_API_KEY=la_tua_key

# Run
python bot.py
```

## 📊 Logging operativo per Codex

Il bot ora prepara una struttura standard per raccogliere log utili a debug, audit e replay:

```text
logs/
  telegram/raw/
  telegram/structured/
  pipeline/jsonl/
replays/
  inputs/
  expected/
  outputs/
exports/
  chat/
```

File principali generati a runtime:

- `logs/telegram/raw/messages.jsonl`
- `logs/pipeline/jsonl/pipeline.jsonl`

Ogni messaggio Telegram riceve un `trace_id` stabile, in modo da seguire tutto il percorso:

`telegram_received -> message_analysis_built -> claude_response_received -> parsed_data_normalized -> confirmation_decision -> calendar_event_* -> telegram_reply_sent`

Se vuoi salvare i log in un'altra cartella:

```bash
export RINVIABOT_LOG_DIR=/percorso/personalizzato/logs
python bot.py
```

Per l'audit storico e i replay con Codex, usa anche:

- `CODEX_AUDIT_PROMPT.md`
- `LOGGING_PLAN.md`
- `MAP.md`

### Export totale chat

E' disponibile il comando Telegram:

```text
/export_chat
```

Comportamento:

- in chat privata puo' essere eseguito direttamente
- nei gruppi puo' eseguirlo solo un admin
- genera un archivio `.zip` in `exports/chat/` con:
  - export `JSON` completo
  - trascrizione `Markdown` leggibile

L'export viene ricostruito a partire dai file locali:

- `logs/telegram/raw/messages.jsonl`
- `logs/pipeline/jsonl/pipeline.jsonl`

### Export storico Telegram via userbot

Se ti serve esportare la chat pregressa, un bot Telegram standard non basta: serve un client MTProto autenticato con il tuo account.

Nel repo c'e' lo script:

```text
scripts/export_telegram_history.py
```

Setup:

```bash
pip install -r requirements.txt
export TELEGRAM_API_ID=123456
export TELEGRAM_API_HASH=la_tua_api_hash
```

Primo export:

```bash
python3 scripts/export_telegram_history.py --chat "https://t.me/nome_chat_o_link" --append-raw-log
```

Note:

- al primo avvio Telegram chiedera' login, codice OTP ed eventualmente password 2FA
- la sessione locale viene salvata in `.telegram-userbot/` ed e' ignorata da git
- gli export completi finiscono in `exports/telegram-history/`
- con `--append-raw-log` i messaggi storici vengono aggiunti anche a `logs/telegram/raw/messages.jsonl`

Da quel momento lo storico entra nel formato del repo e il bot puo' continuare con l'auto-log dei nuovi messaggi.

### Auto-log futuro

Per i nuovi messaggi non serve il userbot: il bot principale registra gia' i dati runtime in:

- `logs/telegram/raw/messages.jsonl`
- `logs/pipeline/jsonl/pipeline.jsonl`

Quindi, una volta ridistribuito il bot con questa versione del codice, il logging futuro parte automaticamente. Se vuoi anche una copia remota persistente, configura inoltre:

- `REMOTE_LOG_ENDPOINT`
- `REMOTE_LOG_TOKEN`

come descritto in `CLOUDFLARE_LOGGING_SETUP.md`.

Se invece vuoi aggiornare il nostro log del repo anche con i nuovi messaggi visibili direttamente dal tuo account Telegram, puoi usare il listener MTProto:

```text
scripts/telegram_live_log.py
```

Esempio su una chat specifica:

```bash
export TELEGRAM_API_ID=123456
export TELEGRAM_API_HASH=la_tua_api_hash
python3 scripts/telegram_live_log.py --chat -5011341129
```

Comportamento:

- resta in ascolto dei nuovi messaggi
- scrive in append su `logs/telegram/raw/messages.jsonl`
- riusa la sessione locale in `.telegram-userbot/`
- puo' filtrare una o piu' chat ripetendo `--chat`

Quindi si': il log e' nel repo, e con questo listener puo' aggiornarsi automaticamente anche senza passare dal bot principale.

Per il sync manuale delle chat storiche che stiamo monitorando stabilmente (`-5011341129` e `-1003792884377`), puoi usare il launcher locale:

```bash
./scripts/run_sync_known_telegram_chats.sh
```

Il launcher:

- chiede `TELEGRAM_API_ID` e `TELEGRAM_API_HASH` se non sono gia' esportati
- aggiorna gli export completi in `exports/telegram-history/`
- aggiunge solo i messaggi nuovi a `logs/telegram/raw/messages.jsonl`

## 📚 Prossimi passi

- [ ] Integrazione Google Calendar completa
- [ ] Dashboard web per statistiche
- [ ] Supporto reminder automatici
- [ ] Export PDF calendario mensile

## 🐛 Bug o domande?

Apri una Issue su GitHub!

## 📄 Licenza

MIT - Usa liberamente!
