import os
import logging
from datetime import datetime, timedelta
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import anthropic
from dateutil import parser
import pytz
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

# Client Anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Google Calendar scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    """
    Autentica con Service Account e restituisce il servizio Google Calendar
    """
    try:
        if not GOOGLE_SERVICE_ACCOUNT_JSON:
            logger.error("GOOGLE_SERVICE_ACCOUNT_JSON non configurato!")
            return None
        
        # Carica credenziali Service Account da variabile d'ambiente
        service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("✅ Servizio Google Calendar inizializzato")
        return service
        
    except Exception as e:
        logger.error(f"Errore inizializzazione Google Calendar: {e}")
        return None

def parse_message_with_ai(message_text):
    """
    Usa Claude per interpretare il messaggio e estrarre informazioni
    """
    if not client:
        logger.error("Client Anthropic non configurato")
        return None
        
    try:
        prompt = f"""Sei un assistente AI specializzato nell'analisi di messaggi di avvocati penalisti italiani. Devi essere INTELLIGENTE, FLESSIBILE e TOLLERANTE agli errori.

DATA ODIERNA: {datetime.now(pytz.timezone('Europe/Rome')).strftime('%d/%m/%Y %A')}
ANNO CORRENTE: {datetime.now(pytz.timezone('Europe/Rome')).year}

═══════════════════════════════════════════════════════════════
📋 LISTE RIFERIMENTO
═══════════════════════════════════════════════════════════════

GIUDICI (correggi errori battitura):
Carlomagno, Di Iorio, Farinella, Fuccio, Fuccio Sanza, Cardinali, Cirillo, Puliafito, Beccia, Mannara, De Santis, Sodani, Petrocelli, Ferrante, Collegio, Filocamo, Ferretti, Sorrentino, Barzellotti, Palmaccio, Vigorito, Vitelli, Nardone, Ragusa, Cerasoli, Roda, Ciabattari, GDP, Lombardi, Russo, Collegio A, Collegio B, Collegio C, GUP, GIP, Corte d'Appello

AVVOCATI (NON sono giudici):
Burgada, Candeloro, Fortino, Sciullo, Puggioni, Messina, Bruni, Martellino, Di Giovanni

ABBREVIAZIONI COMUNI:
- "predib" / "preliminare" → "udienza preliminare dibattimento"
- "disc" / "discuss" / "discussione" → "discussione"
- "es. imp" / "esame imp" → "esame imputato"
- "testi pm" → "testimoni PM"
- "testi difesa" → "testimoni difesa"
- "got" / "gup" / "gip" → includi in note
- "rinvio" → rinvio udienza
- "sentenza" → sentenza (NON udienza!)
- "ndp" → non doversi procedere

═══════════════════════════════════════════════════════════════
🧠 LOGICA INTELLIGENTE
═══════════════════════════════════════════════════════════════

1. **TOLLERANZA ERRORI BATTITURA:**
   - "Farinela" → Correggi a "Farinella" (SEGNA correzione)
   - "Sodanoi" → "Sodani"
   - "Fuccuo" → "Fuccio"
   - "Becciaa" → "Beccia"
   - Usa fuzzy matching per nomi simili (max 2 lettere differenza)

2. **DATE INTELLIGENTI:**
   - "15/3" → Prova anno corrente, se passato usa prossimo
   - "domani" → calcola data domani
   - "dopodomani" → calcola +2 giorni
   - "lunedì prossimo" → calcola prossimo lunedì
   - "poi h 14" → stessa data, ora diversa
   - "successivamente" → inferisci data logica

3. **ORE FLESSIBILI:**
   - "alle 10" / "h 10" / "ore 10" → 10:00
   - "h 10.30" / "h 10,30" → 10:30
   - "di mattina" (se ora manca) → 09:00
   - "pomeriggio" (se ora manca) → 14:00
   - "poi h 14" → stessa data evento precedente

4. **RG VARIANTI:**
   - "4264/2020 rgnr" → RG: 4264/2020 rgnr
   - "4264/2020" → RG: 4264/2020 rgnr
   - "proc 4264/2020" → RG: 4264/2020
   - "rg 4264/20" → RG: 4264/2020

5. **NOMI MULTIPLI:**
   - "Rossi + Bianchi" → Nome: "Rossi + Bianchi"
   - "Rossi, Bianchi e Verdi" → Nome: "Rossi, Bianchi, Verdi"
   - "D'Angelo Cristian" → UN nome (non separare)

6. **PARSING FLESSIBILE:**
   - Ordine libero: "Sodani Rossi 15/3" = "15/3 Rossi Sodani"
   - Estrai tutto: caso, giudice, data, ora, RG, note
   - Contesto: "rinvio per impedimento" → aggiungi a note

═══════════════════════════════════════════════════════════════
📤 FORMATO RISPOSTA
═══════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
🤖 LOGICA CORREZIONE ERRORI
═══════════════════════════════════════════════════════════════

IMPORTANTE: Chiedi conferma SOLO se NON sei sicuro!

**CORREZIONI AUTOMATICHE (sicurezza >90%):**
Procedi con status "ok" e crea evento direttamente:
- "Farinela" → "Farinella" (1 lettera differenza, nome noto)
- "Sodanoi" → "Sodani" (1-2 lettere, ovvio)
- "Fuccuo" → "Fuccio" (evidente typo)
- "Becciaa" → "Beccia" (doppia lettera)
- "15/3" → "15/03/2026" (aggiunta anno standard)

**RICHIEDI CONFERMA (sicurezza <90%):**
Usa status "conferma_richiesta":
- "Marino" → "Mariani"? o "Marino"? (ambiguo)
- "Rossi" + giudice non nella lista → Conferma interpretazione
- Data ambigua: "3/4" → 03/04 o 04/03?
- Più interpretazioni plausibili

REGOLA D'ORO: 
- Se correzione è OVVIA → status "ok" (procedi)
- Se hai DUBBI → status "conferma_richiesta"

═══════════════════════════════════════════════════════════════
📤 FORMATO RISPOSTA
═══════════════════════════════════════════════════════════════

MESSAGGIO DA ANALIZZARE:
{message_text}

RISPOSTA SE TUTTO OK (anche con correzioni ovvie):
{{
    "status": "ok",
    "eventi": [
        {{
            "nome_caso": "Nome parte/imputato",
            "giudice": "Nome giudice",
            "data": "DD/MM/YYYY",
            "ora": "HH:MM",
            "rg": "XXXX/YYYY rgnr (o null)",
            "tipo_evento": "predib/discussione/esame/etc",
            "note_estratte": "dettagli procedurali",
            "messaggio_integrale": "{message_text}"
        }}
    ]
}}

SE NON SEI SICURO (correzione ambigua o dubbi):
{{
    "status": "conferma_richiesta",
    "motivo": "Spiegazione dubbio",
    "correzioni_applicate": [
        {{"da": "originale", "a": "corretto", "tipo": "campo", "sicurezza": "70%"}}
    ],
    "eventi": [{{...evento con dati interpretati...}}],
    "messaggio": "Non sono sicuro: 'X' → 'Y'?"
}}

SE DATA PASSATA ESPLICITA:
{{
    "status": "errore",
    "tipo": "data_passata",
    "data_inserita": "15/01/2024",
    "correzioni_proposte": [
        {{"id": "a", "data": "15/01/{datetime.now(pytz.timezone('Europe/Rome')).year}", "descrizione": "Anno corrente"}},
        {{"id": "b", "data": "15/01/{datetime.now(pytz.timezone('Europe/Rome')).year + 1}", "descrizione": "Anno prossimo"}}
    ],
    "messaggio": "La data è nel passato. Intendevi:"
}}

SE AMBIGUO/INCERTO (>30% dubbio):
{{
    "status": "chiarimento",
    "problema": "Descrizione dubbio",
    "dati_estratti": {{...dati parziali...}},
    "incertezze": ["giudice potrebbe essere X o Y", "data non chiara"],
    "opzioni": [
        {{"id": "a", "descrizione": "Interpretazione 1", "evento_proposto": {{...}}}},
        {{"id": "b", "descrizione": "Interpretazione 2", "evento_proposto": {{...}}}},
        {{"id": "manuale", "descrizione": "Inserimento manuale"}}
    ],
    "domanda": "Quale opzione? Rispondi 'a', 'b', o 'manuale'"
}}

═══════════════════════════════════════════════════════════════
📚 ESEMPI
═══════════════════════════════════════════════════════════════

Input: "Rossi Farinela 15/3 h 10"
Output: status=ok, correzioni=[{{"giudice": "Farinela"→"Farinella"}}], evento con Farinella

Input: "Bianchi 20/3 alle 10, poi h 14 disc"
Output: 2 eventi, stessa data 20/03, ore 10:00 e 14:00

Input: "Verdi + Neri 4264/20 predib domani h 9"
Output: nome="Verdi + Neri", RG="4264/2020 rgnr", data=domani, tipo="udienza preliminare dibattimento"

Input: "D'Angelo Cristian Sodanoi 15/01/2024 pomeriggio"
Output: correzioni=[giudice: Sodanoi→Sodani], errore data_passata con opzioni

Rispondi SOLO JSON valido, no markdown."""

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
        
        titolo = f"🤖 {parsed_data.get('nome_caso', 'Udienza')}"
        if parsed_data.get('rg'):
            titolo += f" - RG {parsed_data['rg']}"
        
        return {
            'title': titolo,
            'start_time': dt,
            'location': parsed_data.get('giudice', ''),
            'description': parsed_data.get('messaggio_integrale', ''),
            'parsed_data': parsed_data
        }
        
    except Exception as e:
        logger.error(f"Errore formattazione evento: {e}")
        return None

def create_google_calendar_event(event_data):
    """
    Crea evento su Google Calendar
    """
    try:
        service = get_google_calendar_service()
        if not service:
            logger.error("Servizio Google Calendar non disponibile")
            return None
        
        # Prepara evento
        start_dt = event_data['start_time']
        end_dt = start_dt + timedelta(hours=1)  # Durata 1 ora
        
        event = {
            'summary': event_data['title'],
            'location': event_data.get('location', ''),
            'description': event_data.get('description', ''),
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Europe/Rome',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [],  # Nessun avviso
            },
        }
        
        # Crea evento
        created_event = service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event
        ).execute()
        
        logger.info(f"Evento creato: {created_event.get('htmlLink')}")
        return created_event
        
    except Exception as e:
        logger.error(f"Errore creazione evento Google Calendar: {e}")
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
    
    # Gestisce ERRORI (date passate con correzioni proposte)
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'errore':
        tipo_errore = parsed_data.get('tipo', '')
        
        if tipo_errore == 'data_passata':
            data_inserita = parsed_data.get('data_inserita', '')
            correzioni = parsed_data.get('correzioni_proposte', [])
            messaggio_base = parsed_data.get('messaggio', 'Data nel passato')
            
            messaggio_errore = f"❌ {messaggio_base}\n\n"
            messaggio_errore += f"📅 Data inserita: **{data_inserita}**\n\n"
            messaggio_errore += "💡 Intendevi:\n"
            
            for corr in correzioni:
                corr_id = corr.get('id', '')
                corr_data = corr.get('data', '')
                corr_desc = corr.get('descrizione', '')
                messaggio_errore += f"   {corr_id.upper()}) {corr_data} ({corr_desc})\n"
            
            messaggio_errore += "\n❓ Rispondi con la lettera dell'opzione corretta (es: 'a' o 'b')"
            
            await update.message.reply_text(messaggio_errore)
            # TODO: Gestire risposta utente
            return
        else:
            messaggio_errore = parsed_data.get('messaggio', 'Errore sconosciuto')
            await update.message.reply_text(f"❌ {messaggio_errore}")
            return
    
    # Gestisce CHIARIMENTI con opzioni
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'chiarimento':
        problema = parsed_data.get('problema', '')
        opzioni = parsed_data.get('opzioni', [])
        domanda = parsed_data.get('domanda', '')
        
        messaggio_chiarimento = f"❓ {problema}\n\n"
        
        for opz in opzioni:
            opt_id = opz.get('id', '')
            descrizione = opz.get('descrizione', '')
            
            if opt_id == 'manuale':
                messaggio_chiarimento += f"🔤 **{opt_id.upper()}**: {descrizione}\n"
            else:
                evento = opz.get('evento_proposto', {})
                messaggio_chiarimento += f"✅ **Opzione {opt_id.upper()}**: {descrizione}\n"
                if evento:
                    messaggio_chiarimento += f"   📋 {evento.get('nome_caso', 'N/A')} - {evento.get('data', 'N/A')} {evento.get('ora', 'N/A')}\n"
            messaggio_chiarimento += "\n"
        
        messaggio_chiarimento += f"💬 {domanda}"
        
        await update.message.reply_text(messaggio_chiarimento)
        # TODO: Implementare gestione risposta utente (richiede stato conversazione)
        return
    
    # Gestisce CONFERMA RICHIESTA (correzioni effettuate)
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'conferma_richiesta':
        motivo = parsed_data.get('motivo', '')
        correzioni_applicate = parsed_data.get('correzioni_applicate', [])
        eventi = parsed_data.get('eventi', [])
        messaggio_ai = parsed_data.get('messaggio', '')
        
        messaggio_conferma = "⚠️ **CORREZIONE AUTOMATICA RILEVATA**\n\n"
        
        for corr in correzioni_applicate:
            da = corr.get('da', '')
            a = corr.get('a', '')
            tipo = corr.get('tipo', 'campo')
            messaggio_conferma += f"   📝 {tipo.title()}: '{da}' → **'{a}'**\n"
        
        messaggio_conferma += f"\n{messaggio_ai}\n\n"
        messaggio_conferma += "📋 **ANTEPRIMA EVENTO:**\n"
        
        for i, evento in enumerate(eventi, 1):
            messaggio_conferma += f"\n**Evento {i}:**\n"
            messaggio_conferma += f"   📋 Nome: 🤖 {evento.get('nome_caso', 'N/A')}\n"
            messaggio_conferma += f"   📍 Luogo: {evento.get('giudice', 'N/A')}\n"
            messaggio_conferma += f"   📅 Data: {evento.get('data', 'N/A')}\n"
            messaggio_conferma += f"   🕐 Ora: {evento.get('ora', 'N/A')}\n"
            if evento.get('rg'):
                messaggio_conferma += f"   📁 RG: {evento.get('rg')}\n"
        
        messaggio_conferma += "\n\n❓ **Vuoi creare l'evento con questi dati corretti?**\n"
        messaggio_conferma += "💬 Rispondi:\n"
        messaggio_conferma += "   ✅ **'sì'** o **'s'** per confermare\n"
        messaggio_conferma += "   ❌ **'no'** o **'n'** per annullare"
        
        await update.message.reply_text(messaggio_conferma)
        # STOP QUI: attendiamo conferma utente prima di creare evento
        # TODO: Implementare gestione risposta "sì/no" utente
        logger.info("Conferma richiesta per correzione, attendo risposta utente")
        return
    
    # Gestisce eventi OK SENZA correzioni (creazione diretta)
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'ok':
        eventi = parsed_data.get('eventi', [])
    elif isinstance(parsed_data, list):
        eventi = parsed_data
    else:
        eventi = [parsed_data] if isinstance(parsed_data, dict) else []
    
    if not eventi:
        await update.message.reply_text("⚠️ Nessun evento trovato nel messaggio.")
        return
    
    # Crea eventi DIRETTAMENTE su Google Calendar (no correzioni, no conferma)
    risposte = []
    eventi_creati = 0
    
    for i, evento in enumerate(eventi, 1):
        if not evento.get('data') or not evento.get('ora'):
            risposte.append(f"⚠️ Evento {i}: Dati incompleti (manca data o ora)")
            continue
        
        # Formatta evento per calendario
        event_data = format_calendar_event(evento)
        if not event_data:
            risposte.append(f"⚠️ Evento {i}: Errore formattazione")
            continue
        
        # Crea evento su Google Calendar
        created = create_google_calendar_event(event_data)
        
        nome_evento = event_data['title']
        
        if created:
            eventi_creati += 1
            risposta = f"""✅ Evento {i} CREATO su Google Calendar:
📋 Nome: {nome_evento}
📍 Luogo: {evento.get('giudice', 'N/A')}
📅 Data: {evento.get('data', 'N/A')}
🕐 Ora: {evento.get('ora', 'N/A')}
📁 RG: {evento.get('rg', 'N/A')}
🔗 Link: {created.get('htmlLink', 'N/A')}"""
        else:
            risposta = f"""⚠️ Evento {i} NON creato (errore Calendar API):
📋 Nome: {nome_evento}
📍 Luogo: {evento.get('giudice', 'N/A')}
📅 Data: {evento.get('data', 'N/A')}
🕐 Ora: {evento.get('ora', 'N/A')}
📁 RG: {evento.get('rg', 'N/A')}"""
        
        risposte.append(risposta)
    
    messaggio_finale = "\n\n".join(risposte)
    messaggio_finale += f"\n\n📝 Messaggio integrale salvato in note."
    messaggio_finale += f"\n✅ {eventi_creati}/{len(eventi)} eventi creati su Google Calendar"
    
    await update.message.reply_text(messaggio_finale)
    logger.info(f"{eventi_creati}/{len(eventi)} evento/i creato/i su Google Calendar")

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
