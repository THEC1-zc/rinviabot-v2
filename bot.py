import os
import logging
from datetime import datetime, timedelta
import re
from typing import Any, Optional
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
ROME_TZ = pytz.timezone('Europe/Rome')

KNOWN_JUDGES = {
    'carlomagno': 'Carlomagno',
    'di iorio': 'Di Iorio',
    'farinella': 'Farinella',
    'fuccio': 'Fuccio',
    'fuccio sanza': 'Fuccio Sanza',
    'cardinali': 'Cardinali',
    'cirillo': 'Cirillo',
    'puliafito': 'Puliafito',
    'beccia': 'Beccia',
    'mannara': 'Mannara',
    'de santis': 'De Santis',
    'sodani': 'Sodani',
    'petrocelli': 'Petrocelli',
    'ferrante': 'Ferrante',
    'filocamo': 'Filocamo',
    'ferretti': 'Ferretti',
    'sorrentino': 'Sorrentino',
    'barzellotti': 'Barzellotti',
    'palmaccio': 'Palmaccio',
    'vigorito': 'Vigorito',
    'vitelli': 'Vitelli',
    'nardone': 'Nardone',
    'ragusa': 'Ragusa',
    'cerasoli': 'Cerasoli',
    'roda': 'Roda',
    'ciabattari': 'Ciabattari',
    'lombardi': 'Lombardi',
    'russo': 'Russo',
    'maellaro': 'Maellaro',
    'nappi': 'Nappi',
    'petti': 'Petti',
    'coniglio': 'Coniglio',
    'croci': 'Croci',
    'bocola': 'Bocola',
    'ciampelli': 'Ciampelli',
    'arcieri': 'Arcieri',
    'karpinska': 'Karpinska',
    'gdp': 'GDP',
    'gup': 'GUP',
    'gip': 'GIP',
    'got': 'GOT',
    'collegio': 'Collegio',
    'collegio a': 'Collegio A',
    'collegio b': 'Collegio B',
    'collegio c': 'Collegio C',
    "corte d'appello": "Corte d'Appello",
}

JUDGE_TYPO_MAP = {
    'farinela': 'Farinella',
    'sodanoi': 'Sodani',
    'fuccuo': 'Fuccio',
    'petrucelli': 'Petrocelli',
    'di ioro': 'Di Iorio',
    'puliafitto': 'Puliafito',
    'maelaro': 'Maellaro',
}

NON_HEARING_KEYWORDS = {
    'sentenza', 'condanna', 'assolto', 'assolta', 'assoluzione', 'prescritto',
    'prescrizione', '530', '131bis', 'n.d.p.', 'ndp', 'pena', 'mesi', 'anni',
    'riserva', 'riservato', 'riservata', 'trattenuta', 'trattenuto'
}

HEARING_HINTS = {
    'rinvio', 'udienza', 'esame', 'testi', 'discussione', 'impedimento',
    'predib', 'dibattimento', 'stessi incombenti', 'incombenti', 'h ', 'ore ',
    'alle ', 'al ', 'del '
}
LOW_CONFIDENCE_THRESHOLD = 0.72


def normalize_whitespace(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def normalize_message_text(message_text: str) -> str:
    text = message_text or ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[—–]{3,}', '\n----\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    def fix_numeric_token(match: re.Match[str]) -> str:
        token = match.group(0)
        return (token
            .replace('O', '0')
            .replace('o', '0')
            .replace('I', '1')
            .replace('l', '1')
            .replace('S', '5')
            .replace('B', '8'))

    text = re.sub(r'(?<!\w)[0-9OlISB][0-9OlISB\s/.,:-]*[0-9OlISB](?!\w)', fix_numeric_token, text)
    return text.strip()


def split_message_blocks(message_text: str) -> list[str]:
    normalized = normalize_message_text(message_text)
    parts = re.split(r'\n\s*----\s*\n|\n{2,}', normalized)
    return [normalize_whitespace(part) for part in parts if normalize_whitespace(part)]


def extract_dates_from_text(message_text: str) -> list[str]:
    return re.findall(r'\b\d{1,2}[\/.\-]\d{1,2}(?:[\/.\-]\d{2,4})?\b', message_text or '')


def extract_times_from_text(message_text: str) -> list[str]:
    return re.findall(r'(?:\bh\s*|\bore\s*|\balle\s*)?\d{1,2}(?::|[.,])\d{2}|\b(?:h\s*|ore\s*|alle\s*)\d{1,2}\b', message_text or '', flags=re.IGNORECASE)


def build_message_analysis(message_text: str) -> dict[str, Any]:
    normalized = normalize_message_text(message_text)
    blocks = split_message_blocks(message_text)
    lowered = normalized.lower()
    dates = extract_dates_from_text(normalized)
    times = extract_times_from_text(normalized)

    return {
        'normalized_message': normalized,
        'message_blocks': blocks,
        'block_count': len(blocks),
        'date_candidates': dates,
        'time_candidates': times,
        'has_multiple_dates': len(set(dates)) > 1,
        'has_non_hearing_keywords': [kw for kw in NON_HEARING_KEYWORDS if kw in lowered],
        'has_hearing_hints': [kw for kw in HEARING_HINTS if kw in lowered],
        'first_token': normalize_whitespace(re.split(r'[:\n, ]', normalized, maxsplit=1)[0]) if normalized else '',
    }


def extract_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    cleaned = (raw_text or '').strip()
    cleaned = cleaned.replace('```json', '').replace('```', '').strip()

    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except Exception:
        pass

    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def normalize_judge_name(value: str) -> str:
    raw = normalize_whitespace(value)
    if not raw:
        return 'Tribunale Civitavecchia'

    lowered = raw.lower()
    if lowered in JUDGE_TYPO_MAP:
        return JUDGE_TYPO_MAP[lowered]
    if lowered in KNOWN_JUDGES:
        return KNOWN_JUDGES[lowered]

    compact = re.sub(r'\s+', ' ', lowered)
    if compact in JUDGE_TYPO_MAP:
        return JUDGE_TYPO_MAP[compact]
    if compact in KNOWN_JUDGES:
        return KNOWN_JUDGES[compact]

    return raw


def normalize_event_date(date_value: str) -> Optional[str]:
    raw = normalize_whitespace(date_value)
    if not raw:
        return None

    try:
        dt = parser.parse(raw, dayfirst=True, default=datetime.now(ROME_TZ).replace(hour=9, minute=0, second=0, microsecond=0))
        if dt.year < 100:
            dt = dt.replace(year=2000 + dt.year)
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return None


def normalize_event_time(time_value: str) -> Optional[str]:
    raw = normalize_whitespace(time_value)
    if not raw:
        return '09:00'

    try:
        dt = parser.parse(raw, default=datetime.now(ROME_TZ).replace(hour=9, minute=0, second=0, microsecond=0))
        return dt.strftime('%H:%M')
    except Exception:
        return None


def infer_tipo_from_text(message_text: str) -> str:
    lowered = (message_text or '').lower()
    if any(keyword in lowered for keyword in ('riserva', 'riservato', 'riservata')):
        return 'riserva'
    if any(keyword in lowered for keyword in ('trattenuta', 'trattenuto')):
        return 'trattenuta'
    if any(keyword in lowered for keyword in ('condanna', 'assolto', 'assolta', 'assoluzione', '530', 'prescritto', '131bis', 'ndp', 'n.d.p.')):
        return 'sentenza'
    if re.search(r'\b\d{1,2}[\/.\-]\d{1,2}(?:[\/.\-]\d{2,4})?\b', lowered) and any(hint in lowered for hint in HEARING_HINTS):
        return 'rinvio'
    if any(hint in lowered for hint in HEARING_HINTS):
        return 'rinvio'
    return 'nota'


def validate_and_normalize_parsed_data(parsed_data: dict[str, Any], original_message: str) -> dict[str, Any]:
    tipo = str(parsed_data.get('tipo', '')).strip().lower()
    if tipo not in {'rinvio', 'sentenza', 'riserva', 'trattenuta', 'nota', 'conferma', 'data_passata'}:
        tipo = infer_tipo_from_text(original_message)

    normalized: dict[str, Any] = {'tipo': tipo}

    if tipo in {'sentenza', 'riserva', 'trattenuta', 'nota'}:
        default_messages = {
            'sentenza': '📋 È una sentenza',
            'riserva': '⏸️ È una riserva',
            'trattenuta': '⚖️ È una trattenuta',
            'nota': '📝 È una nota procedurale',
        }
        normalized['messaggio'] = parsed_data.get('messaggio') or default_messages[tipo]
        return normalized

    if tipo == 'conferma':
        normalized['dubbio'] = normalize_whitespace(str(parsed_data.get('dubbio', '')))
        normalized['interpretazione'] = parsed_data.get('interpretazione', {}) if isinstance(parsed_data.get('interpretazione'), dict) else {}
        normalized['domanda'] = normalize_whitespace(str(parsed_data.get('domanda', 'Va bene così?')))
        return normalized

    if tipo == 'data_passata':
        opzioni = parsed_data.get('opzioni', [])
        normalized['data_letta'] = normalize_whitespace(str(parsed_data.get('data_letta', '')))
        normalized['opzioni'] = opzioni if isinstance(opzioni, list) else []
        normalized['domanda'] = normalize_whitespace(str(parsed_data.get('domanda', 'La data è nel passato. Quale intendevi?')))
        return normalized

    eventi_raw = parsed_data.get('eventi', [])
    if isinstance(eventi_raw, dict):
        eventi_raw = [eventi_raw]
    if not isinstance(eventi_raw, list):
        eventi_raw = []

    correzioni = parsed_data.get('correzioni', [])
    warnings = parsed_data.get('warnings', [])
    confidence = parsed_data.get('confidence')

    eventi = []
    for evento in eventi_raw:
        if not isinstance(evento, dict):
            continue

        parte = normalize_whitespace(str(evento.get('parte', '')))
        giudice = normalize_judge_name(str(evento.get('giudice', '') or 'Tribunale Civitavecchia'))
        data = normalize_event_date(str(evento.get('data', '')))
        ora = normalize_event_time(str(evento.get('ora', '')))
        note = normalize_whitespace(str(evento.get('note', '') or original_message))

        if not parte and note:
            maybe_parte = re.split(r'[:\n,]', note, maxsplit=1)[0].strip()
            parte = normalize_whitespace(maybe_parte)

        if not parte or not data or not ora:
            continue

        eventi.append({
            'parte': parte,
            'giudice': giudice,
            'data': data,
            'ora': ora,
            'note': note,
        })

    if not eventi:
        fallback_tipo = infer_tipo_from_text(original_message)
        if fallback_tipo != 'rinvio':
            return validate_and_normalize_parsed_data({'tipo': fallback_tipo}, original_message)

        return {
            'tipo': 'conferma',
            'dubbio': 'Ho capito che probabilmente si tratta di un rinvio, ma non sono riuscito a ricostruire tutti i dati con sufficiente affidabilità.',
            'interpretazione': {},
            'domanda': 'Puoi riscriverlo indicando almeno parte, data e ora?'
        }

    normalized['eventi'] = eventi
    normalized['correzioni'] = correzioni if isinstance(correzioni, list) else []
    normalized['warnings'] = warnings if isinstance(warnings, list) else []
    if isinstance(confidence, (int, float)):
        normalized['confidence'] = float(confidence)
    return normalized


def should_require_confirmation(parsed_data: dict[str, Any], analysis: dict[str, Any]) -> Optional[str]:
    if parsed_data.get('tipo') != 'rinvio':
        return None

    confidence = parsed_data.get('confidence')
    warnings = parsed_data.get('warnings', [])
    eventi = parsed_data.get('eventi', [])

    if isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
        return f"Confidenza troppo bassa ({confidence:.2f}) per creare l'evento in automatico."

    if isinstance(warnings, list) and warnings:
        return "Ho alcuni punti di incertezza che è meglio confermare prima della creazione."

    if analysis.get('block_count', 0) > 1 and len(eventi) != analysis.get('block_count'):
        return "Il messaggio sembra contenere più blocchi o più rinvii, ma non sono riuscito a separarli con sufficiente affidabilità."

    for evento in eventi:
        parte = normalize_whitespace(str(evento.get('parte', '')))
        giudice = normalize_whitespace(str(evento.get('giudice', '')))
        if len(parte) < 2:
            return "Non sono sicuro di aver identificato correttamente la parte."
        if re.search(r'\bavv\.?\b', giudice.lower()):
            return "Il nome del giudice sembra in realtà un avvocato o un riferimento difensivo."

    return None


def build_confirmation_from_events(parsed_data: dict[str, Any], reason: str) -> dict[str, Any]:
    first_event = {}
    eventi = parsed_data.get('eventi', [])
    if isinstance(eventi, list) and eventi:
        first = eventi[0]
        if isinstance(first, dict):
            first_event = first

    return {
        'tipo': 'conferma',
        'dubbio': reason,
        'interpretazione': {
            'parte': first_event.get('parte', ''),
            'giudice': first_event.get('giudice', ''),
            'data': first_event.get('data', ''),
            'ora': first_event.get('ora', ''),
        },
        'domanda': 'Confermi questa lettura prima che crei l’evento?'
    }

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
    """Usa Claude per interpretare il messaggio mantenendo lettura completa e validazione finale."""
    if not client:
        logger.error("Client Anthropic non configurato")
        return None

    try:
        analysis = build_message_analysis(message_text)
        normalized_message = analysis['normalized_message']
        today = datetime.now(ROME_TZ)
        prompt = f"""Sei il lettore intelligente dei messaggi di Fabio, avvocato penalista italiano.

Leggi il messaggio in modo completo e naturale: non applicare regole meccaniche se il senso complessivo suggerisce una lettura migliore.
Le istruzioni servono come aiuto, non devono impedirti di capire davvero il testo.

Data corrente: {today.strftime('%d/%m/%Y')}
Anno corrente: {today.year}

Obiettivo:
1. Capire se il messaggio parla di un rinvio/udienza futura oppure di altro.
2. Se è un rinvio, estrarre uno o più eventi con la migliore interpretazione possibile.
3. Correggere typo evidenti di date, ore e nomi dei giudici.
4. Conservare i cognomi delle parti il più possibile come scritti.
5. Chiedere conferma solo quando il rischio di creare un evento sbagliato è concreto.

Linee guida:
- Considera tutto il messaggio prima di decidere.
- "avv", "avv." e difensori nominati non sono il giudice.
- Il giudice può essere noto oppure dedotto dal contesto; se manca davvero usa "Tribunale Civitavecchia".
- Se ci sono separatori come "----" oppure più date chiaramente distinte, estrai più eventi.
- Se una data manca dell'anno, inferiscilo in modo sensato.
- Se un anno esplicito porta nel passato e sembra sospetto, usa "data_passata".
- Se il messaggio sembra una sentenza, riserva, trattenuta o nota procedurale, non inventare eventi.
- Se hai dubbi reali, usa "conferma" invece di forzare un evento.
- Usa anche l'analisi tecnica qui sotto come indizio, ma se il significato complessivo del messaggio suggerisce qualcosa di meglio, segui il significato.

Giudici noti utili:
Carlomagno, Di Iorio, Farinella, Fuccio, Fuccio Sanza, Cardinali, Cirillo, Puliafito, Beccia, Mannara, De Santis, Sodani, Petrocelli, Ferrante, Filocamo, Ferretti, Sorrentino, Barzellotti, Palmaccio, Vigorito, Vitelli, Nardone, Ragusa, Cerasoli, Roda, Ciabattari, Lombardi, Russo, Maellaro, Nappi, Petti, Coniglio, Croci, Bocola, Ciampelli, Arcieri, Karpinska, GDP, GUP, GIP, GOT, Collegio, Collegio A, Collegio B, Collegio C, Corte d'Appello.

Correzioni typo frequenti dei giudici:
Farinela->Farinella, Sodanoi->Sodani, Fuccuo->Fuccio, Petrucelli->Petrocelli, Di Ioro->Di Iorio, Puliafitto->Puliafito, Maelaro->Maellaro.

Formato JSON obbligatorio.
Se è rinvio:
{{
  "tipo": "rinvio",
  "confidence": 0.0,
  "eventi": [
    {{
      "parte": "",
      "giudice": "",
      "data": "DD/MM/YYYY",
      "ora": "HH:MM",
      "note": ""
    }}
  ],
  "correzioni": [],
  "warnings": []
}}

Se non è rinvio:
{{"tipo":"sentenza|riserva|trattenuta|nota","messaggio":"..."}}

Se serve conferma:
{{
  "tipo":"conferma",
  "dubbio":"",
  "interpretazione":{{"parte":"","giudice":"","data":"","ora":""}},
  "domanda":""
}}

Se la data è nel passato:
{{
  "tipo":"data_passata",
  "data_letta":"",
  "opzioni":[{{"id":"a","data":""}},{{"id":"b","data":""}}],
  "domanda":""
}}

Messaggio originale:
{message_text}

Messaggio normalizzato:
{normalized_message}

Analisi tecnica preliminare:
{json.dumps(analysis, ensure_ascii=False)}

Rispondi solo con JSON valido."""

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        parsed_data = extract_json_object(response_text)
        if not parsed_data:
            logger.error(f"Risposta AI non parseabile: {response_text}")
            return None

        parsed_data = validate_and_normalize_parsed_data(parsed_data, normalized_message)
        confirmation_reason = should_require_confirmation(parsed_data, analysis)
        if confirmation_reason:
            parsed_data = build_confirmation_from_events(parsed_data, confirmation_reason)
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
