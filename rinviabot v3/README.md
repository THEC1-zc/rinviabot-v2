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

## 📚 Prossimi passi

- [ ] Integrazione Google Calendar completa
- [ ] Dashboard web per statistiche
- [ ] Supporto reminder automatici
- [ ] Export PDF calendario mensile

## 🐛 Bug o domande?

Apri una Issue su GitHub!

## 📄 Licenza

MIT - Usa liberamente!
