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
    """Autentica con Service Account e restituisce il servizio Google Calendar"""
    try:
        if not GOOGLE_SERVICE_ACCOUNT_JSON:
            logger.error("GOOGLE_SERVICE_ACCOUNT_JSON non configurato!")
            return None
        
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
    """Usa Claude per interpretare il messaggio con AI intraprendente"""
    if not client:
        logger.error("Client Anthropic non configurato")
        return None
        
    try:
        prompt = f"""Sei l'assistente AI di Fabio, un avvocato penalista italiano. Fabio ti manda appunti veloci presi durante le udienze. Devi interpretarli ATTIVAMENTE e AUTONOMAMENTE.

DATA ODIERNA: {datetime.now(pytz.timezone('Europe/Rome')).strftime('%d/%m/%Y %A')}
ANNO CORRENTE: {datetime.now(pytz.timezone('Europe/Rome')).year}

═══════════════════════════════════════════════════════════════
🧠 PRIMA DI TUTTO: CHE TIPO DI MESSAGGIO È?
═══════════════════════════════════════════════════════════════

**RINVIO** (crea evento calendario):
- Contiene una DATA FUTURA
- Parole chiave: "rinvio al", "udienza del", "al [data]", "h [ora]", "ore [ora]"
- Esempio: "Rossi Sodani rinvio al 15/3/26 h 10"

**SENTENZA** (NO evento, rispondi "È una sentenza"):
- Parole: "condanna", "assolto", "530", "assoluzione", "prescritto", "ndp", "131bis"
- Contiene pena: "mesi X", "anni X", "€ XXX"
- Esempio: "Bianchi: 530 assolto! Giorni 90"

**RISERVA** (NO evento, rispondi "È una riserva"):
- Parole: "riserva", "riservato", "riservata"
- Esempio: "Vitale: riserva"

**TRATTENUTA** (NO evento, rispondi "È una trattenuta"):
- Parole: "trattenuta", "trattenuto"
- Esempio: "calicchio: gdp cerasoli: trattenuta"

**NOTA PROCEDURALE** (NO evento, rispondi "È una nota procedurale"):
- Info senza data futura né sentenza
- Esempio: "Avv. Gentili per canale 3201788775"

═══════════════════════════════════════════════════════════════
📝 STILE DI SCRITTURA DI FABIO
═══════════════════════════════════════════════════════════════

Fabio scrive appunti veloci con questo PATTERN tipico:
**[PARTE] [GIUDICE] [cosa è successo] [DATA] [ORA] [prossimi incombenti]**

Varianti comuni:
- "Rossi: avv. Bianchi: Sodani: rinvio al 15/3/26 h 10 per esame testi"
- "Gamlouche di iorio impedimento 22/10/25 h 11"
- "Bova puliafito 3/6/25 h 9.30 per discussione"
- "Giuliano: di iorio, avv Lucia pepe, aperto dibattimento, rinvio al 18/9/24 h 10"

**REGOLE CHIAVE:**
1. La PRIMA PAROLA è quasi sempre la PARTE (imputato/caso)
2. "avv. X" o "avv X" = AVVOCATO (difensore), MAI il giudice
3. Il GIUDICE è un cognome dalla lista O un cognome che appare nel contesto giusto
4. La DATA viene dopo "rinvio al", "al", "udienza del" o da sola
5. L'ORA viene dopo "h", "ore", "alle"

═══════════════════════════════════════════════════════════════
⚖️ RICONOSCIMENTO GIUDICE
═══════════════════════════════════════════════════════════════

**GIUDICI NOTI (Tribunale Civitavecchia e altri):**
Carlomagno, Di Iorio, Farinella, Fuccio, Fuccio Sanza, Cardinali, Cirillo, 
Puliafito, Beccia, Mannara, De Santis, Sodani, Petrocelli, Ferrante, 
Filocamo, Ferretti, Sorrentino, Barzellotti, Palmaccio, Vigorito, Vitelli, 
Nardone, Ragusa, Cerasoli, Roda, Ciabattari, Lombardi, Russo, Maellaro,
Nappi, Petti, Coniglio, Croci, Bocola, Ciampelli, Arcieri, Karpinska,
GDP, GUP, GIP, GOT, Collegio, Collegio A, Collegio B, Collegio C, Corte d'Appello

**AVVOCATI (NON sono giudici) - preceduti da "avv" o "avv.":**
Burgada, Candeloro, Fortino, Sciullo, Puggioni, Messina, Bruni, Martellino, 
Di Giovanni, Montaruli, Panfilo, Fazzari, Gentili, Patrizi, Napolitano,
Archilei, Lenzi, Fucci, Viola, Ascone, D'Orso, Milita, Vincenzi, Caliendo...

**LOGICA RICONOSCIMENTO:**
1. Se preceduto da "avv" o "avv." → È un AVVOCATO, non giudice
2. Se nella lista giudici noti → È il GIUDICE
3. Se cognome italiano/straniero nel contesto giusto → Probabilmente GIUDICE
4. Se città (Roma, Milano, Grosseto, Taranto) → È la LOCATION, non il giudice
5. Se nessun giudice riconosciuto → Usa "Tribunale Civitavecchia"

**CORREZIONE TYPO GIUDICI (automatica):**
- "Farinela" → "Farinella"
- "Sodanoi" → "Sodani"  
- "Fuccuo" → "Fuccio"
- "Petrucelli" → "Petrocelli"
- "Di Ioro" → "Di Iorio"
- "Puliafitto" → "Puliafito"
- "Maelaro" → "Maellaro"

═══════════════════════════════════════════════════════════════
📅 PARSING DATE - ULTRA TOLLERANTE
═══════════════════════════════════════════════════════════════

**FORMATI ACCETTATI (qualsiasi spaziatura):**
- "15/3/26" "15/03/2026" "15/3/2026" "15 / 3 / 26"
- "15.3.26" "15. 3. 2026" "15-3-26"
- "15 marzo 2026" "15marzo26" "15 mar 26"
- "al 15/3" "rinvio al 15/3/26" "udienza del 15/3"

**ERRORI BATTITURA NUMERI:**
- "O" (lettera) → "0": "15/O3/26" → "15/03/26"
- "l" o "I" → "1": "l5/03/26" → "15/03/26"
- "S" → "5", "B" → "8"
- Spazi nel numero: "1 5/03" → "15/03"

**LOGICA ANNO:**
- Se manca anno → anno corrente (o prossimo se data è passata)
- "26" → "2026", "25" → "2025"
- Se anno completo nel passato (es. "15/01/2024") → CHIEDI CONFERMA

**ORE:**
- "h 10" "h10" "ore 10" "alle 10" "10:00" → 10:00
- "h 10.30" "h 10,30" "10.30" → 10:30
- "h 9.30" → 09:30
- Se manca ora → default 09:00

═══════════════════════════════════════════════════════════════
👤 PARTI E COGNOMI
═══════════════════════════════════════════════════════════════

La PARTE è quasi sempre la PRIMA parola del messaggio.
Accetta QUALSIASI cognome (italiano, straniero, composto):

- Italiani: Rossi, De Luca, D'Angelo, Della Ragione
- Stranieri: Kowalczyk, Müller, Al-Hassan, O'Brien, N'Diaye, Nguyen
- Composti: "Rossi + Bianchi", "Fuccio Sanza"

**NON correggere mai i cognomi delle parti!**

═══════════════════════════════════════════════════════════════
📋 MESSAGGI MULTIPLI
═══════════════════════════════════════════════════════════════

Se il messaggio contiene "———" o "——-" o "----" → sono PIÙ EVENTI separati.
Se ci sono più date diverse → sono PIÙ EVENTI.
Crea un evento per ciascuno.

═══════════════════════════════════════════════════════════════
🤖 COMPORTAMENTO AI: SII INTRAPRENDENTE!
═══════════════════════════════════════════════════════════════

**AGISCI AUTONOMAMENTE (90% dei casi):**
- Correggi typo evidenti senza chiedere
- Deduci il giudice dal contesto
- Completa l'anno mancante
- Interpreta abbreviazioni ("predib", "disc", "tpm")
- Se giudice non riconosciuto ma sembra un cognome → usalo
- Se città menzionata → usala come contesto

**CHIEDI CONFERMA SOLO SE:**
- Data nel passato con anno esplicito (es. "15/01/2024")
- Data veramente ambigua (es. "3/4" potrebbe essere 3 aprile o 4 marzo)
- Messaggio incomprensibile
- Non riesci a capire se è rinvio o sentenza

**RISPONDI BREVEMENTE SE NON È UN RINVIO:**
- Sentenza → "📋 È una sentenza"
- Riserva → "⏸️ È una riserva"
- Trattenuta → "⚖️ È una trattenuta"
- Nota → "📝 È una nota procedurale"

═══════════════════════════════════════════════════════════════
📤 FORMATO RISPOSTA JSON
═══════════════════════════════════════════════════════════════

MESSAGGIO DA ANALIZZARE:
{message_text}

**SE È UN RINVIO (o più rinvii):**
{{
    "tipo": "rinvio",
    "eventi": [
        {{
            "parte": "Cognome parte/imputato",
            "giudice": "Nome giudice (o Tribunale Civitavecchia)",
            "data": "DD/MM/YYYY",
            "ora": "HH:MM",
            "note": "Messaggio integrale originale"
        }}
    ],
    "correzioni": [
        {{"campo": "giudice", "da": "Farinela", "a": "Farinella"}}
    ]
}}

**SE È UNA SENTENZA:**
{{
    "tipo": "sentenza",
    "messaggio": "📋 È una sentenza"
}}

**SE È UNA RISERVA:**
{{
    "tipo": "riserva", 
    "messaggio": "⏸️ È una riserva"
}}

**SE È UNA TRATTENUTA:**
{{
    "tipo": "trattenuta",
    "messaggio": "⚖️ È una trattenuta"  
}}

**SE È UNA NOTA:**
{{
    "tipo": "nota",
    "messaggio": "📝 È una nota procedurale"
}}

**SE HAI DUBBI (chiedi conferma):**
{{
    "tipo": "conferma",
    "dubbio": "Spiegazione del dubbio",
    "interpretazione": {{
        "parte": "...",
        "giudice": "...",
        "data": "...",
        "ora": "..."
    }},
    "domanda": "Va bene così? (sì/no)"
}}

**SE DATA PASSATA:**
{{
    "tipo": "data_passata",
    "data_letta": "15/01/2024",
    "opzioni": [
        {{"id": "a", "data": "15/01/2025"}},
        {{"id": "b", "data": "15/01/2026"}}
    ],
    "domanda": "La data è nel passato. Intendevi: a) 15/01/2025 o b) 15/01/2026?"
}}

═══════════════════════════════════════════════════════════════
📚 ESEMPI REALI DAI MESSAGGI DI FABIO
═══════════════════════════════════════════════════════════════

**Esempio 1 - Rinvio semplice:**
Input: "Rossi Sodani rinvio al 15/3/26 h 10 per esame testi"
Output: tipo=rinvio, parte=Rossi, giudice=Sodani, data=15/03/2026, ora=10:00

**Esempio 2 - Con avvocato (non è il giudice!):**
Input: "Giuliano: di iorio, avv Lucia pepe, rinvio al 18/9/24 h 10"
Output: tipo=rinvio, parte=Giuliano, giudice=Di Iorio, data=18/09/2024, ora=10:00

**Esempio 3 - Sentenza:**
Input: "De caro: beccia: 530 assolto fatto non sussiste, motivi contestuali"
Output: tipo=sentenza, messaggio="📋 È una sentenza"

**Esempio 4 - Riserva:**
Input: "Vitale: riserva"
Output: tipo=riserva, messaggio="⏸️ È una riserva"

**Esempio 5 - Trattenuta:**
Input: "calicchio: gdp cerasoli: trattenuta"
Output: tipo=trattenuta, messaggio="⚖️ È una trattenuta"

**Esempio 6 - Messaggio multiplo (2 eventi):**
Input: "Pomponi: di iorio rinvio al 25/6/25 ore 11
————
Iannace: Fuccio sanza' stessi incombenti al 18/6/25 h 9.30"
Output: tipo=rinvio, eventi=[{{parte=Pomponi, giudice=Di Iorio, data=25/06/2025, ora=11:00}}, {{parte=Iannace, giudice=Fuccio Sanza, data=18/06/2025, ora=09:30}}]

**Esempio 7 - Typo giudice (correggi automaticamente):**
Input: "Bianchi Farinela 15/3 h 9"
Output: tipo=rinvio, parte=Bianchi, giudice=Farinella, correzioni=[giudice: Farinela→Farinella]

**Esempio 8 - Giudice non in lista (usa comunque):**
Input: "Müller Bortolini 20/03 h 9"
Output: tipo=rinvio, parte=Müller, giudice=Bortolini (non chiedere conferma, usalo!)

**Esempio 9 - Nessun giudice riconoscibile:**
Input: "Kowalczyk 15/3/26 h 10 per discussione"
Output: tipo=rinvio, parte=Kowalczyk, giudice=Tribunale Civitavecchia

**Esempio 10 - Città come contesto:**
Input: "Airi: grosseto, rinvio al 13/10/23 h 12.30"
Output: tipo=rinvio, parte=Airi, giudice=Grosseto (usa la città!)

**Esempio 11 - Data con errore battitura:**
Input: "Rossi Sodani l5/O3 h 9"
Output: tipo=rinvio, parte=Rossi, giudice=Sodani, data=15/03/{datetime.now(pytz.timezone('Europe/Rome')).year}, ora=09:00, correzioni=[data: l5/O3→15/03]

Rispondi SOLO JSON valido, no markdown, no commenti."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
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

def format_calendar_event(evento):
    """Formatta i dati per creare l'evento calendario"""
    if not evento or not evento.get('data') or not evento.get('ora'):
        return None
    
    try:
        data_str = evento['data']
        ora_str = evento['ora']
        
        # Pulisci da eventuali note
        data_str = re.sub(r'\s*\(.*?\)\s*', '', data_str).strip()
        ora_str = re.sub(r'\s*\(.*?\)\s*', '', ora_str).strip()
        
        datetime_str = f"{data_str} {ora_str}"
        dt = parser.parse(datetime_str, dayfirst=True)
        
        tz = pytz.timezone('Europe/Rome')
        dt = tz.localize(dt)
        
        # Titolo: 🤖 + Parte
        titolo = f"🤖 {evento.get('parte', 'Udienza')}"
        
        return {
            'title': titolo,
            'start_time': dt,
            'location': evento.get('giudice', 'Tribunale Civitavecchia'),
            'description': evento.get('note', ''),
            'evento': evento
        }
        
    except Exception as e:
        logger.error(f"Errore formattazione evento: {e}")
        return None

def create_google_calendar_event(event_data):
    """Crea evento su Google Calendar"""
    try:
        service = get_google_calendar_service()
        if not service:
            logger.error("Servizio Google Calendar non disponibile")
            return None
        
        start_dt = event_data['start_time']
        end_dt = start_dt + timedelta(hours=1)
        
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
                'overrides': [],
            },
        }
        
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
    """Gestisce i messaggi in arrivo"""
    message_text = update.message.text
    
    if not message_text:
        return
    
    logger.info(f"Nuovo messaggio ricevuto")
    
    await update.message.chat.send_action(action="typing")
    
    parsed_data = parse_message_with_ai(message_text)
    
    if not parsed_data:
        await update.message.reply_text("⚠️ Non sono riuscito a interpretare il messaggio.")
        return
    
    tipo = parsed_data.get('tipo', '')
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE TIPI NON-RINVIO
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'sentenza':
        await update.message.reply_text("📋 È una sentenza")
        return
    
    if tipo == 'riserva':
        await update.message.reply_text("⏸️ È una riserva")
        return
    
    if tipo == 'trattenuta':
        await update.message.reply_text("⚖️ È una trattenuta")
        return
    
    if tipo == 'nota':
        await update.message.reply_text("📝 È una nota procedurale")
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE CONFERMA RICHIESTA
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'conferma':
        dubbio = parsed_data.get('dubbio', '')
        interpretazione = parsed_data.get('interpretazione', {})
        domanda = parsed_data.get('domanda', 'Va bene così?')
        
        msg = f"❓ **Ho un dubbio**\n\n"
        msg += f"📋 {dubbio}\n\n"
        msg += f"**La mia interpretazione:**\n"
        msg += f"   👤 Parte: {interpretazione.get('parte', 'N/A')}\n"
        msg += f"   ⚖️ Giudice: {interpretazione.get('giudice', 'N/A')}\n"
        msg += f"   📅 Data: {interpretazione.get('data', 'N/A')}\n"
        msg += f"   🕐 Ora: {interpretazione.get('ora', 'N/A')}\n\n"
        msg += f"💬 {domanda}"
        
        await update.message.reply_text(msg)
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE DATA PASSATA
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'data_passata':
        data_letta = parsed_data.get('data_letta', '')
        opzioni = parsed_data.get('opzioni', [])
        domanda = parsed_data.get('domanda', '')
        
        msg = f"❌ **Data nel passato**\n\n"
        msg += f"📅 Ho letto: {data_letta}\n\n"
        msg += f"💡 Intendevi:\n"
        for opt in opzioni:
            msg += f"   {opt['id'].upper()}) {opt['data']}\n"
        msg += f"\n💬 Rispondi con 'a' o 'b'"
        
        await update.message.reply_text(msg)
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE RINVII (creazione eventi)
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'rinvio':
        eventi = parsed_data.get('eventi', [])
        correzioni = parsed_data.get('correzioni', [])
        
        if not eventi:
            await update.message.reply_text("⚠️ Nessun evento trovato.")
            return
        
        risposte = []
        eventi_creati = 0
        
        # Mostra correzioni se presenti
        if correzioni:
            msg_corr = "🔧 **Correzioni automatiche:**\n"
            for c in correzioni:
                msg_corr += f"   • {c.get('campo', '')}: '{c.get('da', '')}' → '{c.get('a', '')}'\n"
            risposte.append(msg_corr)
        
        # Crea ogni evento
        for i, evento in enumerate(eventi, 1):
            if not evento.get('data') or not evento.get('ora'):
                risposte.append(f"⚠️ Evento {i}: dati incompleti")
                continue
            
            event_data = format_calendar_event(evento)
            if not event_data:
                risposte.append(f"⚠️ Evento {i}: errore formattazione")
                continue
            
            created = create_google_calendar_event(event_data)
            
            if created:
                eventi_creati += 1
                resp = f"✅ **Evento creato**\n"
                resp += f"   👤 {evento.get('parte', 'N/A')}\n"
                resp += f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
                resp += f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}\n"
                resp += f"   🔗 {created.get('htmlLink', '')}"
            else:
                resp = f"⚠️ **Errore creazione**\n"
                resp += f"   👤 {evento.get('parte', 'N/A')}\n"
                resp += f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
                resp += f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}"
            
            risposte.append(resp)
        
        # Messaggio finale
        messaggio_finale = "\n\n".join(risposte)
        if len(eventi) > 1:
            messaggio_finale += f"\n\n📊 **{eventi_creati}/{len(eventi)}** eventi creati"
        
        await update.message.reply_text(messaggio_finale)
        logger.info(f"{eventi_creati}/{len(eventi)} evento/i creato/i")
        return
    
    # Fallback
    await update.message.reply_text("⚠️ Non ho capito il tipo di messaggio.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce errori"""
    logger.error(f"Errore: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Si è verificato un errore. Riprova.")

def main():
    """Funzione principale"""
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
