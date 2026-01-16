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
        prompt = f"""Sei un assistente specializzato nell'analisi di messaggi di avvocati italiani riguardanti udienze penali.

MESSAGGIO:
{message_text}

GIUDICI CONOSCIUTI (NON sono parti in causa):
Carlomagno, Di Iorio, Farinella, Fuccio, Fuccio Sanza, Cardinali, Cirillo, Puliafito, Beccia, Mannara, De Santis, Sodani, Petrocelli, Ferrante, Collegio, Filocamo, Ferretti, Sorrentino, Barzellotti, Palmaccio, Vigorito, Vitelli, Nardone, Ragusa, Cerasoli, Roda, Ciabattari, GDP, Lombardi, Russo
OPPURE città di tribunali (es: Tivoli, Milano, Roma)

AVVOCATI CONOSCIUTI (NON sono parti in causa):
Burgada, Candeloro, Fortino, Sciullo, Puggioni, Messina, Bruni, Martellino, Di Giovanni
Riconosci anche pattern "avv [Nome]" o "avvocato [Nome]"

COMPITO:
1. IDENTIFICA TUTTE LE DATE con orari nel messaggio
2. Per OGNI data, crea un evento separato
3. Le PARTI sono nomi che NON sono giudici/avvocati
4. Se il messaggio è AMBIGUO o hai DUBBI, rispondi con: {{"chiarimento_richiesto": "spiega il dubbio"}}

FORMATO OUTPUT:
Se chiaro, rispondi con array JSON:
[
  {{
    "nome_caso": "nome parte/imputato (NO giudici, NO avvocati)",
    "rg": "numero RG se presente (es: '4264/2020 rgnr'). null se assente",
    "data": "DD/MM/YYYY",
    "ora": "HH:MM (converti 'h 10.30'→'10:30', 'ore 14'→'14:00')",
    "giudice": "nome giudice dalla lista OPPURE città tribunale. null se assente",
    "messaggio_integrale": "{message_text}"
  }}
]

Se date multiple, crea ELEMENTO SEPARATO per ciascuna.
Se dubbio/ambiguo, rispondi: {{"chiarimento_richiesto": "descrivi problema"}}

ESEMPI:
Input: "Serafini: 4264/2020 rgnr - Sodani - 20/09/2026 h 10.30 testi diffidati"
Output: [{{"nome_caso": "Serafini", "rg": "4264/2020 rgnr", "data": "20/09/2026", "ora": "10:30", "giudice": "Sodani", "messaggio_integrale": "..."}}]

Input: "Rossi: 15/3/26 h 10 predib, poi 20/4/26 h 11 discussione"
Output: [{{"nome_caso": "Rossi", "data": "15/03/2026", "ora": "10:00", ...}}, {{"nome_caso": "Rossi", "data": "20/04/2026", "ora": "11:00", ...}}]

Rispondi SOLO JSON, no markdown.

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
        if parsed_data.get('giudice'):
            descrizione_parts.append(f"Giudice: {parsed_data['giudice']}")
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
    
    # Controlla se serve chiarimento
    if isinstance(parsed_data, dict) and parsed_data.get('chiarimento_richiesto'):
        await update.message.reply_text(f"❓ Ho bisogno di chiarimenti:\n\n{parsed_data['chiarimento_richiesto']}")
        return
    
    # Gestisce array di eventi (supporta date multiple)
    eventi = parsed_data if isinstance(parsed_data, list) else [parsed_data]
    
    if not eventi:
        await update.message.reply_text("⚠️ Nessun evento trovato nel messaggio.")
        return
    
    # Prepara risposta per ogni evento
    risposte = []
    for i, evento in enumerate(eventi, 1):
        if not evento.get('data') or not evento.get('ora'):
            risposte.append(f"⚠️ Evento {i}: Dati incompleti (manca data o ora)")
            continue
        
        # Aggiungi emoticon Claude al nome caso
        nome_evento = f"🤖 {evento.get('nome_caso', 'Udienza')}"
        
        risposta = f"""✅ Evento {i}:
📋 Nome: {nome_evento}
📍 Luogo: {evento.get('giudice', 'N/A')}
📅 Data: {evento.get('data', 'N/A')}
🕐 Ora: {evento.get('ora', 'N/A')}
📁 RG: {evento.get('rg', 'N/A')}"""
        
        risposte.append(risposta)
    
    messaggio_finale = "\n\n".join(risposte)
    messaggio_finale += "\n\n📝 Messaggio integrale salvato in note."
    messaggio_finale += "\n✅ Pronto per Google Calendar (integration coming soon)"
    
    await update.message.reply_text(messaggio_finale)
    logger.info(f"{len(eventi)} evento/i processato/i")

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
