import os
import logging
from datetime import datetime
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import anthropic
from dateutil import parser
import pytz
import json

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variabili d'ambiente
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Client Anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def parse_message_with_ai(message_text):
    """
    Usa Claude per interpretare il messaggio e estrarre informazioni
    """
    if not client:
        logger.error("Client Anthropic non configurato")
        return None
        
    try:
        prompt = f"""Analizza questo messaggio di un avvocato italiano riguardante un rinvio di udienza.
Estrai le seguenti informazioni in formato JSON:

Messaggio:
{message_text}

Rispondi SOLO con un oggetto JSON (senza markdown) con questi campi:
{{
    "nome_caso": "nome del caso o delle parti",
    "rg": "numero RG se presente (formato: XXXX/YYYY)",
    "data": "data udienza in formato DD/MM/YYYY",
    "ora": "ora udienza in formato HH:MM",
    "tribunale": "nome tribunale se presente",
    "note": "altre informazioni rilevanti (tipo udienza, testi, ecc)"
}}

Se un campo non è presente, usa null. La data e l'ora sono OBBLIGATORIE."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        parsed_data = json.loads(response_text)
        logger.info(f"AI parsed data: {parsed_data}")
        return parsed_data
        
    except Exception as e:
        logger.error(f"Errore parsing AI: {e}")
        return None

def format_calendar_event(parsed_data):
    """
    Formatta i dati per creare l'evento calendario
    """
    if not parsed_data or not parsed_data.get('data') or not parsed_data.get('ora'):
        return None
    
    try:
        data_str = parsed_data['data']
        ora_str = parsed_data['ora']
        datetime_str = f"{data_str} {ora_str}"
        dt = parser.parse(datetime_str, dayfirst=True)
        
        tz = pytz.timezone('Europe/Rome')
        dt = tz.localize(dt)
        
        titolo = parsed_data.get('nome_caso', 'Udienza')
        if parsed_data.get('rg'):
            titolo += f" - RG {parsed_data['rg']}"
        
        descrizione_parts = []
        if parsed_data.get('tribunale'):
            descrizione_parts.append(f"Tribunale: {parsed_data['tribunale']}")
        if parsed_data.get('note'):
            descrizione_parts.append(f"Note: {parsed_data['note']}")
        
        descrizione = "\n".join(descrizione_parts)
        
        return {
            'title': titolo,
            'start_time': dt,
            'description': descrizione,
            'parsed_data': parsed_data
        }
        
    except Exception as e:
        logger.error(f"Errore formattazione evento: {e}")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestisce i messaggi in arrivo dal gruppo
    """
    message_text = update.message.text
    
    if not message_text:
        return
    
    logger.info(f"Nuovo messaggio ricevuto")
    
    await update.message.chat.send_action(action="typing")
    
    parsed_data = parse_message_with_ai(message_text)
    
    if not parsed_data:
        await update.message.reply_text("⚠️ Non sono riuscito a interpretare il messaggio.")
        return
    
    event_data = format_calendar_event(parsed_data)
    
    if not event_data:
        await update.message.reply_text("⚠️ Dati incompleti: manca data o ora.")
        return
    
    conferma = f"""✅ Messaggio interpretato:

📋 Caso: {parsed_data.get('nome_caso', 'N/A')}
📁 RG: {parsed_data.get('rg', 'N/A')}
📅 Data: {parsed_data.get('data', 'N/A')}
🕐 Ora: {parsed_data.get('ora', 'N/A')}
🏛️ Tribunale: {parsed_data.get('tribunale', 'N/A')}
📝 Note: {parsed_data.get('note', 'N/A')}

✅ Evento pronto (Google Calendar integration coming soon)"""
    
    await update.message.reply_text(conferma)
    logger.info(f"Evento processato: {event_data['title']}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestisce errori
    """
    logger.error(f"Errore: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Si è verificato un errore. Riprova.")

def main():
    """
    Funzione principale
    """
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non configurato!")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY non configurato!")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    application.add_error_handler(error_handler)
    
    if WEBHOOK_URL:
        port = int(os.getenv('PORT', 8443))
        logger.info(f"Starting webhook on port {port}")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
        )
    else:
        logger.info("Starting polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
