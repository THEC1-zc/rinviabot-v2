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
📅 PARSING DATE - ULTRA TOLLERANTE
═══════════════════════════════════════════════════════════════

**SPAZIATURE - Accetta QUALSIASI formato:**
- "12/03/2026" ✓ standard
- "12 / 03 / 2026" ✓ spazi attorno a /
- "12/ 03/2026" ✓ spazio dopo /
- "12 /03/ 2026" ✓ spazi misti
- "12.03.2026" ✓ con punti
- "12. 03. 2026" ✓ punti con spazi
- "12-03-2026" ✓ con trattini
- "12 - 03 - 2026" ✓ trattini con spazi
- "12marzo2026" ✓ senza spazi
- "12 marzo 2026" ✓ con spazi
- "12Marzo2026" ✓ maiuscola

**ERRORI BATTITURA NUMERI:**
- "O" (lettera O) → "0" (zero): "12/O3/2026" → "12/03/2026"
- "l" o "I" → "1": "l5/03/2026" → "15/03/2026"
- "S" → "5": "1S/03/2026" → "15/03/2026"
- "B" → "8": "1B/03/2026" → "18/03/2026"
- Doppi numeri: "12//03" → "12/03"
- Spazi nel numero: "1 5/03" → "15/03"

**MESI SCRITTI (case insensitive):**
- gennaio, febbraio, marzo, aprile, maggio, giugno
- luglio, agosto, settembre, ottobre, novembre, dicembre
- Abbreviazioni: gen, feb, mar, apr, mag, giu, lug, ago, set, ott, nov, dic
- Errori: "genniao" → gennaio, "febraio" → febbraio, "setembre" → settembre

**LOGICA ANNO:**
- Se manca anno: prova anno corrente, se passato usa prossimo
- "15/3" → 15/03/{datetime.now(pytz.timezone('Europe/Rome')).year} (o {datetime.now(pytz.timezone('Europe/Rome')).year + 1} se passato)
- "domani" → calcola data domani
- "dopodomani" → calcola +2 giorni
- "lunedì prossimo" → calcola prossimo lunedì

═══════════════════════════════════════════════════════════════
👤 PARSING NOMI/PARTI - COGNOMI STRANIERI
═══════════════════════════════════════════════════════════════

**ACCETTA QUALSIASI COGNOME** - Non correggere cognomi delle parti!
I cognomi delle PARTI (imputati) possono essere di qualsiasi nazionalità.
NON sono nella lista giudici, quindi NON tentare di correggerli.

**ESEMPI COGNOMI VALIDI:**
- Italiani: Rossi, De Luca, D'Angelo, Dell'Acqua
- Est Europa: Kowalczyk, Szczepański, Novák, Horváth, Popescu
- Tedeschi: Müller, Schröder, Weiß, Köhler
- Spagnoli: García, Rodríguez, González, Martínez
- Francesi: Lefèvre, Dubois, Moreau, Côté
- Portoghesi: Gonçalves, Fernandes, Conceição
- Inglesi/Irlandesi: O'Brien, McDonald, MacLeod, O'Connor
- Arabi: Al-Hassan, Ben Ahmed, El-Amin, Abdul-Rahman
- Africani: N'Diaye, Mbeki, Okonkwo, Diallo
- Asiatici: Nguyen, Zhang, Yamamoto, Park, Singh
- Turchi: Öztürk, Yılmaz, Çelik

**REGOLE NOMI:**
- Mantieni caratteri speciali: ü, ö, ä, ß, ñ, ç, è, é, ê, ë, î, ï, ô, œ, ù, û, ÿ
- Mantieni apostrofi: O'Brien, D'Angelo, N'Diaye
- Mantieni trattini: Al-Hassan, Abdul-Rahman
- Nomi composti: "Maria Rossi" = un nome, "Rossi + Bianchi" = due parti
- Prefissi nobiliari: von, van, de, del, della, di, da, le, la

**NOMI MULTIPLI:**
- "Rossi + Bianchi" → Nome: "Rossi + Bianchi"
- "Rossi, Bianchi e Verdi" → Nome: "Rossi, Bianchi, Verdi"
- "Rossi/Bianchi" → Nome: "Rossi, Bianchi"

═══════════════════════════════════════════════════════════════
⚖️ PARSING GIUDICE - FUZZY MATCHING
═══════════════════════════════════════════════════════════════

**CORREZIONI AUTOMATICHE (sicurezza ≥90%):**
Errori evidenti con 1-2 lettere di differenza:
- "Farinela" → "Farinella" (manca una L)
- "Sodanoi" → "Sodani" (O in più)
- "Fuccuo" → "Fuccio" (U invece di I)
- "Becciaa" → "Beccia" (A doppia)
- "Carolomagno" → "Carlomagno" (O in più)
- "Di Ioro" → "Di Iorio" (manca I)
- "Puliafitto" → "Puliafito" (T doppia)
- "Petrucelli" → "Petrocelli" (U invece di O)
- "Vigoritto" → "Vigorito" (T doppia)

**GIUDICE NON RICONOSCIUTO:**
Se il giudice NON è in lista e NON è simile a nessuno:
- USA "Monocratico Civitavecchia" come default
- Chiedi conferma con "Va bene così?"
- Esempio: "Bortolini" (non in lista) → giudice: "Monocratico Civitavecchia", chiedi conferma

**RICHIEDI CONFERMA (sicurezza <90%):**
Quando il nome è ambiguo o non riconosciuto:
- Nome non in lista → usa "Monocratico Civitavecchia" e chiedi conferma
- Più giudici possibili con stessa similarità
- Nome troppo diverso da tutti (>3 lettere differenza)

═══════════════════════════════════════════════════════════════
🕐 PARSING ORE - FLESSIBILE
═══════════════════════════════════════════════════════════════

**FORMATI ACCETTATI:**
- "alle 10" / "h 10" / "ore 10" / "10:00" → 10:00
- "h 10.30" / "h 10,30" / "10.30" / "10,30" → 10:30
- "h10" / "ore10" (senza spazio) → 10:00
- "10 e 30" / "10 e mezza" → 10:30
- "10h30" → 10:30

**DEFAULT SE MANCA ORA:**
- "di mattina" / "mattina" → 09:00
- "pomeriggio" → 14:00
- "tarda mattinata" → 11:00
- Se nessuna indicazione → 09:00 (default tribunale)

**ORE MULTIPLE:**
- "poi h 14" → stessa data, ora 14:00
- "e alle 15 disc" → stessa data, ora 15:00

═══════════════════════════════════════════════════════════════
📁 PARSING RG - VARIANTI
═══════════════════════════════════════════════════════════════

**FORMATI ACCETTATI:**
- "4264/2020 rgnr" → RG: 4264/2020 rgnr
- "4264/2020" → RG: 4264/2020 rgnr
- "proc 4264/2020" → RG: 4264/2020
- "rg 4264/20" → RG: 4264/2020 (espandi anno)
- "n. 4264/2020" → RG: 4264/2020
- "4264 / 2020" (con spazi) → RG: 4264/2020
- "4264-2020" (con trattino) → RG: 4264/2020

═══════════════════════════════════════════════════════════════
🤖 LOGICA CONFERMA "VA BENE COSÌ?"
═══════════════════════════════════════════════════════════════

IMPORTANTE: Usa status "conferma_richiesta" con messaggio "Va bene così?" 
SOLO quando hai DUBBI su QUALSIASI dato, non solo giudice!

**PROCEDI AUTOMATICAMENTE (status: "ok") quando:**
- Tutti i dati sono chiari e riconosciuti
- Correzioni ovvie (1-2 lettere, typo evidenti)
- Data parsata senza ambiguità
- Giudice riconosciuto con certezza ≥90%
- Nome parte qualsiasi (non correggere mai le parti!)

**CHIEDI "VA BENE COSÌ?" (status: "conferma_richiesta") quando:**

1. **GIUDICE INCERTO:**
   - Nome non in lista e non simile
   - Più match possibili con stessa probabilità
   - Correzione con >2 lettere differenza

2. **DATA AMBIGUA:**
   - "3/4" → 03/04 o 04/03? (giorno/mese ambiguo)
   - Data scritta male e più interpretazioni possibili
   - "martedì" senza data (quale martedì?)

3. **ORA INCERTA:**
   - Ora non specificata e contesto non chiaro
   - "pomeriggio tardi" (15? 16? 17?)

4. **RG AMBIGUO:**
   - Formato strano non riconosciuto
   - Più numeri che potrebbero essere RG

5. **MESSAGGIO CONFUSO:**
   - Ordine parole incomprensibile
   - Mancano dati essenziali
   - Più interpretazioni plausibili

**FORMATO CONFERMA:**
Quando chiedi conferma, mostra SEMPRE:
- Cosa hai interpretato
- Cosa ti sembra dubbio
- Domanda "Va bene così?" o opzioni

═══════════════════════════════════════════════════════════════
📤 FORMATO RISPOSTA JSON
═══════════════════════════════════════════════════════════════

MESSAGGIO DA ANALIZZARE:
{message_text}

**RISPOSTA SE TUTTO OK (anche con correzioni automatiche ovvie):**
{{
    "status": "ok",
    "correzioni_automatiche": [
        {{"campo": "giudice", "da": "Farinela", "a": "Farinella", "sicurezza": "95%"}}
    ],
    "eventi": [
        {{
            "nome_caso": "Nome parte/imputato (MANTIENI ORIGINALE)",
            "giudice": "Nome giudice (corretto se necessario)",
            "data": "DD/MM/YYYY",
            "ora": "HH:MM",
            "rg": "XXXX/YYYY rgnr (o null)",
            "tipo_evento": "predib/discussione/esame/etc",
            "note_estratte": "dettagli procedurali",
            "messaggio_integrale": "{message_text}"
        }}
    ]
}}

**RISPOSTA SE HAI DUBBI - "VA BENE COSÌ?":**
{{
    "status": "conferma_richiesta",
    "dubbi": [
        {{"campo": "giudice", "valore_letto": "Marinelli", "interpretazione": "Non in lista", "domanda": "Giudice 'Marinelli' non riconosciuto. È corretto?"}},
        {{"campo": "data", "valore_letto": "3/4", "interpretazione": "03/04 o 04/03?", "domanda": "Intendi 3 aprile o 4 marzo?"}}
    ],
    "eventi": [
        {{
            "nome_caso": "...",
            "giudice": "Marinelli (da confermare)",
            "data": "03/04/{datetime.now(pytz.timezone('Europe/Rome')).year} (da confermare)",
            "ora": "...",
            "rg": "...",
            "tipo_evento": "...",
            "note_estratte": "...",
            "messaggio_integrale": "{message_text}"
        }}
    ],
    "messaggio": "Ho dei dubbi, va bene così?"
}}

**RISPOSTA SE DATA PASSATA:**
{{
    "status": "errore",
    "tipo": "data_passata",
    "data_inserita": "15/01/2024",
    "correzioni_proposte": [
        {{"id": "a", "data": "15/01/{datetime.now(pytz.timezone('Europe/Rome')).year}", "descrizione": "Anno corrente"}},
        {{"id": "b", "data": "15/01/{datetime.now(pytz.timezone('Europe/Rome')).year + 1}", "descrizione": "Anno prossimo"}}
    ],
    "messaggio": "La data 15/01/2024 è nel passato. Intendevi:"
}}

**RISPOSTA SE INCOMPRENSIBILE:**
{{
    "status": "chiarimento",
    "problema": "Descrizione problema",
    "dati_estratti": {{"parziali": "..."}},
    "domanda": "Puoi riformulare? Non ho capito [cosa]"
}}

═══════════════════════════════════════════════════════════════
📚 ESEMPI
═══════════════════════════════════════════════════════════════

**ESEMPIO 1 - Tutto OK con correzione automatica:**
Input: "Kowalczyk Farinela 15 / 03 h 10"
Output: 
{{
    "status": "ok",
    "correzioni_automatiche": [{{"campo": "giudice", "da": "Farinela", "a": "Farinella", "sicurezza": "95%"}}],
    "eventi": [{{
        "nome_caso": "Kowalczyk",
        "giudice": "Farinella",
        "data": "15/03/{datetime.now(pytz.timezone('Europe/Rome')).year}",
        "ora": "10:00",
        ...
    }}]
}}

**ESEMPIO 2 - Giudice non riconosciuto, chiedi conferma:**
Input: "Müller Bortolini 20/03 h 9"
Output:
{{
    "status": "conferma_richiesta",
    "dubbi": [{{"campo": "giudice", "valore_letto": "Bortolini", "interpretazione": "Non in lista giudici, uso default", "domanda": "Giudice 'Bortolini' non riconosciuto. Uso 'Monocratico Civitavecchia'. Va bene?"}}],
    "eventi": [{{
        "nome_caso": "Müller",
        "giudice": "Monocratico Civitavecchia",
        ...
    }}],
    "messaggio": "Ho dei dubbi, va bene così?"
}}

**ESEMPIO 3 - Data ambigua:**
Input: "Rossi Sodani 3/4 h 10"
Output:
{{
    "status": "conferma_richiesta", 
    "dubbi": [{{"campo": "data", "valore_letto": "3/4", "interpretazione": "Ambiguo: 3 aprile o 4 marzo?", "domanda": "Intendi 03/04 (3 aprile) o 04/03 (4 marzo)?"}}],
    "eventi": [{{...}}],
    "messaggio": "Ho dei dubbi, va bene così?"
}}

**ESEMPIO 4 - Cognome straniero OK:**
Input: "Al-Hassan Di Iorio 12/05 h 11"
Output:
{{
    "status": "ok",
    "correzioni_automatiche": [],
    "eventi": [{{
        "nome_caso": "Al-Hassan",
        "giudice": "Di Iorio",
        "data": "12/05/{datetime.now(pytz.timezone('Europe/Rome')).year}",
        "ora": "11:00",
        ...
    }}]
}}

**ESEMPIO 5 - Typo data con lettera:**
Input: "Bianchi Beccia l5/O3 h 9"
Output:
{{
    "status": "ok",
    "correzioni_automatiche": [
        {{"campo": "data", "da": "l5/O3", "a": "15/03/{datetime.now(pytz.timezone('Europe/Rome')).year}", "sicurezza": "90%"}}
    ],
    "eventi": [{{
        "nome_caso": "Bianchi",
        "giudice": "Beccia",
        "data": "15/03/{datetime.now(pytz.timezone('Europe/Rome')).year}",
        "ora": "09:00",
        ...
    }}]
}}

Rispondi SOLO JSON valido, no markdown, no commenti."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
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
        
        # Pulisci data da eventuali note "(da confermare)"
        data_str = re.sub(r'\s*\(.*?\)\s*', '', data_str).strip()
        ora_str = re.sub(r'\s*\(.*?\)\s*', '', ora_str).strip()
        
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
            'location': parsed_data.get('giudice', '').replace(' (da confermare)', ''),
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
            return
        else:
            messaggio_errore = parsed_data.get('messaggio', 'Errore sconosciuto')
            await update.message.reply_text(f"❌ {messaggio_errore}")
            return
    
    # Gestisce CHIARIMENTI con opzioni
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'chiarimento':
        problema = parsed_data.get('problema', '')
        domanda = parsed_data.get('domanda', 'Puoi riformulare?')
        
        messaggio_chiarimento = f"❓ **Non ho capito bene**\n\n"
        messaggio_chiarimento += f"📋 Problema: {problema}\n\n"
        messaggio_chiarimento += f"💬 {domanda}"
        
        await update.message.reply_text(messaggio_chiarimento)
        return
    
    # Gestisce CONFERMA RICHIESTA - "VA BENE COSÌ?"
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'conferma_richiesta':
        dubbi = parsed_data.get('dubbi', [])
        eventi = parsed_data.get('eventi', [])
        messaggio_ai = parsed_data.get('messaggio', 'Ho dei dubbi')
        
        messaggio_conferma = "⚠️ **HO DEI DUBBI**\n\n"
        
        # Mostra i dubbi specifici
        for dubbio in dubbi:
            campo = dubbio.get('campo', '')
            valore = dubbio.get('valore_letto', '')
            domanda_dubbio = dubbio.get('domanda', '')
            
            emoji_campo = {
                'giudice': '⚖️',
                'data': '📅',
                'ora': '🕐',
                'rg': '📁',
                'nome': '👤'
            }.get(campo, '❓')
            
            messaggio_conferma += f"{emoji_campo} **{campo.upper()}**: {domanda_dubbio}\n"
        
        messaggio_conferma += "\n📋 **ANTEPRIMA EVENTO:**\n"
        
        for i, evento in enumerate(eventi, 1):
            if len(eventi) > 1:
                messaggio_conferma += f"\n**Evento {i}:**\n"
            messaggio_conferma += f"   👤 Parte: {evento.get('nome_caso', 'N/A')}\n"
            messaggio_conferma += f"   ⚖️ Giudice: {evento.get('giudice', 'N/A')}\n"
            messaggio_conferma += f"   📅 Data: {evento.get('data', 'N/A')}\n"
            messaggio_conferma += f"   🕐 Ora: {evento.get('ora', 'N/A')}\n"
            if evento.get('rg'):
                messaggio_conferma += f"   📁 RG: {evento.get('rg')}\n"
        
        messaggio_conferma += "\n\n❓ **Va bene così?**\n"
        messaggio_conferma += "💬 Rispondi:\n"
        messaggio_conferma += "   ✅ **'sì'** o **'s'** per confermare e creare evento\n"
        messaggio_conferma += "   ❌ **'no'** o **'n'** per annullare\n"
        messaggio_conferma += "   ✏️ Oppure riscrivi il messaggio corretto"
        
        await update.message.reply_text(messaggio_conferma)
        logger.info("Conferma 'Va bene così?' richiesta, attendo risposta utente")
        return
    
    # Gestisce eventi OK (creazione diretta)
    if isinstance(parsed_data, dict) and parsed_data.get('status') == 'ok':
        eventi = parsed_data.get('eventi', [])
        correzioni_auto = parsed_data.get('correzioni_automatiche', [])
    elif isinstance(parsed_data, list):
        eventi = parsed_data
        correzioni_auto = []
    else:
        eventi = [parsed_data] if isinstance(parsed_data, dict) else []
        correzioni_auto = []
    
    if not eventi:
        await update.message.reply_text("⚠️ Nessun evento trovato nel messaggio.")
        return
    
    # Crea eventi su Google Calendar
    risposte = []
    eventi_creati = 0
    
    # Se ci sono correzioni automatiche, mostralle in modo chiaro
    if correzioni_auto:
        msg_correzioni = "🔧 **Correzioni automatiche applicate:**\n"
        for corr in correzioni_auto:
            campo = corr.get('campo', '')
            da = corr.get('da', '')
            a = corr.get('a', '')
            sicurezza = corr.get('sicurezza', '')
            emoji_campo = {
                'giudice': '⚖️',
                'data': '📅',
                'ora': '🕐',
                'rg': '📁',
                'nome': '👤'
            }.get(campo, '📝')
            msg_correzioni += f"   {emoji_campo} {campo}: '{da}' → **'{a}'**"
            if sicurezza:
                msg_correzioni += f" ({sicurezza})"
            msg_correzioni += "\n"
        risposte.append(msg_correzioni)
    
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
            risposta = f"""✅ **Evento {i} CREATO**
👤 Parte: {evento.get('nome_caso', 'N/A')}
⚖️ Giudice: {evento.get('giudice', 'N/A')}
📅 Data: {evento.get('data', 'N/A')}
🕐 Ora: {evento.get('ora', 'N/A')}
📁 RG: {evento.get('rg', 'N/A')}
🔗 {created.get('htmlLink', '')}"""
        else:
            risposta = f"""⚠️ **Evento {i} NON creato** (errore API)
👤 Parte: {evento.get('nome_caso', 'N/A')}
⚖️ Giudice: {evento.get('giudice', 'N/A')}
📅 Data: {evento.get('data', 'N/A')}
🕐 Ora: {evento.get('ora', 'N/A')}"""
        
        risposte.append(risposta)
    
    messaggio_finale = "\n\n".join(risposte)
    messaggio_finale += f"\n\n📊 **{eventi_creati}/{len(eventi)}** eventi creati"
    
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
