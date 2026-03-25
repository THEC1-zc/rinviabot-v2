import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from hashlib import sha256
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED
import re
from typing import Any, Optional
from urllib import request as urllib_request
from urllib import error as urllib_error
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
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
LOG_DIR = Path(os.getenv('RINVIABOT_LOG_DIR', 'logs'))
PIPELINE_LOG_PATH = LOG_DIR / 'pipeline' / 'jsonl' / 'pipeline.jsonl'
TELEGRAM_RAW_LOG_PATH = LOG_DIR / 'telegram' / 'raw' / 'messages.jsonl'
CHAT_EXPORT_DIR = Path('exports') / 'chat'
REMOTE_LOG_ENDPOINT = os.getenv('REMOTE_LOG_ENDPOINT', '').strip()
REMOTE_LOG_TOKEN = os.getenv('REMOTE_LOG_TOKEN', '').strip()

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

KNOWN_LAWYERS = {
    'frattasi', 'd’angerio', "d'angerio", 'righetti', 'fabio viscarelli',
    'saginario mirko', 'messina', 'burgada', 'candeloro', 'monteleone',
    'moffa', 'bruni', 'corazzelli', 'fortino', 'poddesu', 'crescioni',
    'pecchi', 'mottola', 'vincenzo corazzelli', 'michele petracca'
}

COURT_LOCATION_KEYWORDS = {
    'tribunale', "corte d'appello", 'corte di appello', 'corte appello',
    'collegio', 'sez', 'sezione', 'gdp', 'gup', 'gip', 'got'
}

REFERENCE_PATTERNS = [
    r'\br\.?g\.?\s*[:.]?\s*[\w/-]+',
    r'\brgnr\s*[:.]?\s*[\w/-]+',
    r'\brg\s+dib\s*[:.]?\s*[\w/-]+',
    r'\bprocedimento\s+n\.?\s*[\w/-]+',
]
RECURRING_ACTIVITIES = {
    'discussione',
    'esame imputato',
    'esame testi',
    'esame teste',
    'testi pm',
    'testi difesa',
    'stessi incombenti',
    'incombenti',
    'tpm',
    'fine tpm',
    'impedimento',
    'sentito',
    'teste po',
    'acquisito',
    '507',
    'perizia',
    'incidente esecuzione',
    'obbligo pg',
    'udienza preliminare',
    'apertura dibattimento',
    'citazione',
    'diffidati',
    'residui testi pm',
}
PENDING_EXPIRY_HOURS = 12
MASK_FIELD_ORDER = ['parte', 'giudice', 'domiciliatario', 'rinvio', 'successo', 'altro']
MASK_FIELD_LABELS = {
    'parte': 'Parte',
    'giudice': 'Giudice',
    'domiciliatario': 'Domiciliatario',
    'rinvio': 'Rinvio',
    'successo': 'Successo',
    'altro': 'Altro',
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


def ensure_runtime_directories() -> None:
    for path in (
        LOG_DIR / 'telegram' / 'raw',
        LOG_DIR / 'telegram' / 'structured',
        LOG_DIR / 'pipeline' / 'jsonl',
        Path('replays') / 'inputs',
        Path('replays') / 'expected',
        Path('replays') / 'outputs',
        CHAT_EXPORT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


def safe_json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_json_value(item) for item in value]
    return str(value)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_runtime_directories()
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(safe_json_value(payload), ensure_ascii=False) + '\n')


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Riga JSONL non valida ignorata in {path}")
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def normalize_chat_id(value: Any) -> str:
    return str(value) if value is not None else ''


def sanitize_export_component(value: Any) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9_.-]+', '-', str(value or 'chat'))
    return cleaned.strip('-') or 'chat'


def format_export_ts(value: Optional[str]) -> str:
    if not value:
        return 'N/A'
    try:
        dt = parser.isoparse(value)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(ROME_TZ).strftime('%d/%m/%Y %H:%M:%S %Z')
    except (ValueError, TypeError):
        return value


def sort_key_for_ts(value: Optional[str]) -> tuple[int, str]:
    if not value:
        return (1, '')
    return (0, value)


def build_chat_export(chat_id: Any) -> dict[str, Any]:
    normalized_chat_id = normalize_chat_id(chat_id)
    raw_records = read_jsonl(TELEGRAM_RAW_LOG_PATH)
    pipeline_records = read_jsonl(PIPELINE_LOG_PATH)
    conversations: dict[str, dict[str, Any]] = {}
    trace_ids_for_chat: set[str] = set()

    for record in raw_records:
        if normalize_chat_id(record.get('chat_id')) != normalized_chat_id:
            continue

        trace_id = str(record.get('trace_id') or '')
        if not trace_id:
            continue

        trace_ids_for_chat.add(trace_id)
        conversation = conversations.setdefault(trace_id, {
            'trace_id': trace_id,
            'started_at': record.get('ts'),
            'chat_id': record.get('chat_id'),
            'user_message': None,
            'replies': [],
            'events': [],
        })
        conversation['started_at'] = min(
            [value for value in (conversation.get('started_at'), record.get('ts')) if value],
            key=lambda item: sort_key_for_ts(item),
            default=record.get('ts'),
        )
        conversation['user_message'] = {
            'ts': record.get('ts'),
            'message_id': record.get('message_id'),
            'user_id': record.get('user_id'),
            'username': record.get('username'),
            'text': record.get('text', ''),
        }

    for record in pipeline_records:
        trace_id = str(record.get('trace_id') or '')
        if not trace_id:
            continue
        if normalize_chat_id(record.get('chat_id')) == normalized_chat_id:
            trace_ids_for_chat.add(trace_id)

    for record in pipeline_records:
        trace_id = str(record.get('trace_id') or '')
        if trace_id not in trace_ids_for_chat:
            continue

        conversation = conversations.setdefault(trace_id, {
            'trace_id': trace_id,
            'started_at': record.get('ts'),
            'chat_id': record.get('chat_id'),
            'user_message': None,
            'replies': [],
            'events': [],
        })
        if record.get('ts') and (
            not conversation.get('started_at') or sort_key_for_ts(record.get('ts')) < sort_key_for_ts(conversation.get('started_at'))
        ):
            conversation['started_at'] = record.get('ts')
        if conversation.get('chat_id') is None and record.get('chat_id') is not None:
            conversation['chat_id'] = record.get('chat_id')

        if record.get('stage') == 'telegram_received' and not conversation.get('user_message'):
            conversation['user_message'] = {
                'ts': record.get('ts'),
                'message_id': record.get('message_id'),
                'user_id': record.get('user_id'),
                'username': record.get('username'),
                'text': record.get('text', ''),
            }

        if record.get('stage') == 'telegram_reply_sent':
            conversation['replies'].append({
                'ts': record.get('ts'),
                'category': record.get('data', {}).get('reply_category'),
                'text': record.get('data', {}).get('reply_text', ''),
            })

        conversation['events'].append({
            'ts': record.get('ts'),
            'stage': record.get('stage'),
            'message_id': record.get('message_id'),
            'user_id': record.get('user_id'),
            'username': record.get('username'),
            'text': record.get('text'),
            'data': safe_json_value(record.get('data', {})),
        })

    ordered_conversations = sorted(
        conversations.values(),
        key=lambda item: sort_key_for_ts(item.get('started_at')),
    )

    for conversation in ordered_conversations:
        conversation['replies'].sort(key=lambda item: sort_key_for_ts(item.get('ts')))
        conversation['events'].sort(key=lambda item: sort_key_for_ts(item.get('ts')))

    return {
        'generated_at': utc_now_iso(),
        'chat_id': normalized_chat_id,
        'total_conversations': len(ordered_conversations),
        'total_replies': sum(len(item.get('replies', [])) for item in ordered_conversations),
        'conversations': ordered_conversations,
    }


def render_chat_export_markdown(export_data: dict[str, Any]) -> str:
    lines = [
        '# Export chat RinviaBot',
        '',
        f"- Chat ID: `{export_data['chat_id']}`",
        f"- Generato il: `{format_export_ts(export_data.get('generated_at'))}`",
        f"- Conversazioni: `{export_data.get('total_conversations', 0)}`",
        f"- Risposte bot: `{export_data.get('total_replies', 0)}`",
        '',
    ]

    for index, conversation in enumerate(export_data.get('conversations', []), start=1):
        user_message = conversation.get('user_message') or {}
        lines.extend([
            f"## {index}. {conversation.get('trace_id', 'trace-sconosciuta')}",
            '',
            f"- Timestamp: `{format_export_ts(conversation.get('started_at'))}`",
            f"- Username: `{user_message.get('username') or 'N/A'}`",
            f"- User ID: `{user_message.get('user_id') or 'N/A'}`",
            f"- Message ID: `{user_message.get('message_id') or 'N/A'}`",
            '',
            '### Messaggio utente',
            '',
            user_message.get('text') or '_Messaggio non disponibile_',
            '',
            '### Risposte del bot',
            '',
        ])

        replies = conversation.get('replies', [])
        if replies:
            for reply in replies:
                lines.extend([
                    f"- `{format_export_ts(reply.get('ts'))}` [{reply.get('category') or 'reply'}]",
                    '',
                    reply.get('text') or '_Risposta vuota_',
                    '',
                ])
        else:
            lines.extend([
                '_Nessuna risposta trovata nei log_',
                '',
            ])

        lines.extend([
            '### Eventi pipeline',
            '',
        ])
        for event in conversation.get('events', []):
            lines.append(
                f"- `{format_export_ts(event.get('ts'))}` `{event.get('stage')}`"
            )
        lines.append('')

    return '\n'.join(lines).strip() + '\n'


def write_chat_export_files(export_data: dict[str, Any]) -> dict[str, Path]:
    ensure_runtime_directories()
    stamp = datetime.now(ROME_TZ).strftime('%Y%m%d-%H%M%S')
    base_name = f"{sanitize_export_component(export_data.get('chat_id'))}-{stamp}"
    json_path = CHAT_EXPORT_DIR / f"{base_name}.json"
    md_path = CHAT_EXPORT_DIR / f"{base_name}.md"
    zip_path = CHAT_EXPORT_DIR / f"{base_name}.zip"

    json_path.write_text(
        json.dumps(safe_json_value(export_data), ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    md_path.write_text(render_chat_export_markdown(export_data), encoding='utf-8')

    with ZipFile(zip_path, 'w', compression=ZIP_DEFLATED) as archive:
        archive.write(json_path, arcname=json_path.name)
        archive.write(md_path, arcname=md_path.name)

    return {
        'json': json_path,
        'markdown': md_path,
        'zip': zip_path,
    }


def hash_text(value: str) -> str:
    return sha256((value or '').encode('utf-8')).hexdigest()


def build_trace_id(update: Optional[Update]) -> str:
    if update and update.effective_chat and update.effective_message:
        return f"tg-{update.effective_chat.id}-{update.effective_message.message_id}"
    return f"tg-{uuid4().hex}"


def send_remote_log(payload: dict[str, Any]) -> None:
    if not REMOTE_LOG_ENDPOINT or not REMOTE_LOG_TOKEN:
        return

    req = urllib_request.Request(
        REMOTE_LOG_ENDPOINT,
        data=json.dumps(safe_json_value(payload), ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {REMOTE_LOG_TOKEN}',
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(req, timeout=2.0) as response:
            if response.status >= 400:
                raise RuntimeError(f"Remote log endpoint returned status {response.status}")
    except (urllib_error.URLError, RuntimeError, TimeoutError) as exc:
        logger.warning(f"Remote logging failed: {exc}")
        append_jsonl(PIPELINE_LOG_PATH, {
            'ts': utc_now_iso(),
            'trace_id': payload.get('trace_id', 'remote-log'),
            'stage': 'remote_log_failed',
            'data': {
                'target': REMOTE_LOG_ENDPOINT,
                'failed_stage': payload.get('stage'),
                'error': str(exc),
            },
        })


def log_pipeline_event(
    stage: str,
    trace_id: str,
    *,
    chat_id: Any = None,
    message_id: Any = None,
    user_id: Any = None,
    username: Any = None,
    text: Optional[str] = None,
    source: str = 'rinviabot-render',
    **data: Any,
) -> None:
    payload = {
        'ts': utc_now_iso(),
        'trace_id': trace_id,
        'stage': stage,
        'chat_id': chat_id,
        'message_id': message_id,
        'user_id': user_id,
        'username': username,
        'text': text,
        'source': source,
        'data': data,
    }
    append_jsonl(PIPELINE_LOG_PATH, payload)
    send_remote_log(payload)


def log_telegram_raw_message(update: Update, trace_id: str, message_text: str) -> None:
    append_jsonl(TELEGRAM_RAW_LOG_PATH, {
        'ts': utc_now_iso(),
        'trace_id': trace_id,
        'chat_id': update.effective_chat.id if update.effective_chat else None,
        'message_id': update.effective_message.message_id if update.effective_message else None,
        'user_id': update.effective_user.id if update.effective_user else None,
        'username': update.effective_user.username if update.effective_user else None,
        'text': message_text,
    })


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
        return ''

    lowered = raw.lower()
    if any(keyword in lowered for keyword in COURT_LOCATION_KEYWORDS):
        if lowered.startswith('collegio pres'):
            match = re.search(r'collegio\s+pres\.?\s+(.+)$', raw, flags=re.IGNORECASE)
            if match:
                return normalize_judge_name(match.group(1))
        return ''
    if re.search(r'\bavv\.?\b', lowered):
        return ''
    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in REFERENCE_PATTERNS):
        return ''
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


def normalize_location_name(value: str, original_message: str = '') -> str:
    raw = normalize_whitespace(value)
    source = raw or normalize_whitespace(original_message)
    lowered = source.lower()

    if not source:
        return 'Tribunale Civitavecchia'

    if re.search(r'collegio\s+pres\.?\s+', source, flags=re.IGNORECASE):
        return 'Collegio'
    if re.search(r'\bcorte\s+d[’\']appello\b|\bcorte\s+di\s+appello\b', lowered):
        match = re.search(r'(corte\s+d[’\']appello(?:\s+di\s+[A-Za-zÀ-ÿ]+)?)', source, flags=re.IGNORECASE)
        return normalize_whitespace(match.group(1).title() if match else "Corte d'Appello")
    if re.search(r'\btribunale(?:\s+di)?\s+[A-Za-zÀ-ÿ]+', source, flags=re.IGNORECASE):
        city_match = re.search(r'\btribunale(?:\s+di)?\s+([A-Za-zÀ-ÿ]+)', source, flags=re.IGNORECASE)
        base = f"Tribunale di {city_match.group(1).title()}" if city_match else 'Tribunale Civitavecchia'
        sez_match = re.search(r'\bsez(?:ione)?\.?\s*([IVXLC0-9]+)', source, flags=re.IGNORECASE)
        if sez_match:
            return f"{base}, Sez. {sez_match.group(1).upper()}"
        return base
    if lowered.startswith('collegio'):
        return 'Collegio'
    if lowered in {'gdp', 'gup', 'gip', 'got'}:
        return lowered.upper()
    return raw or 'Tribunale Civitavecchia'


def looks_like_location(value: str) -> bool:
    lowered = normalize_whitespace(value).lower()
    return bool(lowered) and any(keyword in lowered for keyword in COURT_LOCATION_KEYWORDS)


def looks_like_reference(value: str) -> bool:
    lowered = normalize_whitespace(value).lower()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in REFERENCE_PATTERNS)


def looks_like_lawyer(value: str) -> bool:
    lowered = normalize_whitespace(value).lower()
    if not lowered:
        return False
    if re.search(r'\bavv\.?\b|\bdifens', lowered):
        return True
    return lowered in KNOWN_LAWYERS


def has_judicial_context(message_text: str) -> bool:
    lowered = normalize_message_text(message_text).lower()
    if any(keyword in lowered for keyword in NON_HEARING_KEYWORDS):
        return True
    if any(keyword in lowered for keyword in HEARING_HINTS):
        return True
    if any(keyword in lowered for keyword in COURT_LOCATION_KEYWORDS):
        return True
    if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in REFERENCE_PATTERNS):
        return True
    return bool(extract_dates_from_text(lowered) and extract_times_from_text(lowered))


def extract_reference_segments(message_text: str) -> list[str]:
    normalized = normalize_message_text(message_text)
    found: list[str] = []
    for pattern in REFERENCE_PATTERNS:
        for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
            value = normalize_whitespace(match.group(0))
            if value and value not in found:
                found.append(value)
    return found


def extract_recurring_activities(message_text: str) -> list[str]:
    lowered = normalize_message_text(message_text).lower()
    found: list[str] = []
    for activity in sorted(RECURRING_ACTIVITIES, key=len, reverse=True):
        if activity in lowered and activity not in found:
            found.append(activity)
    return found


def extract_primary_party_candidate(message_text: str) -> str:
    normalized = normalize_message_text(message_text)
    if not normalized:
        return ''
    first_line = normalized.split('\n', 1)[0]
    first_line = re.split(r'[:,-]', first_line, maxsplit=1)[0]
    tokens = re.findall(r"[A-Za-zÀ-ÿ'’.-]+", first_line)
    if not tokens:
        return ''
    if len(tokens) >= 2 and tokens[0].lower() not in COURT_LOCATION_KEYWORDS and tokens[1].lower() not in COURT_LOCATION_KEYWORDS:
        return normalize_whitespace(' '.join(tokens[:2]))
    return normalize_whitespace(tokens[0])


def normalize_event_notes(note_value: str, original_message: str) -> str:
    note = normalize_whitespace(note_value)
    original = normalize_whitespace(original_message)
    extras: list[str] = []
    references = extract_reference_segments(original_message)
    activities = extract_recurring_activities(original_message)

    if note:
        extras.append(note)
    for reference in references:
        if reference not in extras:
            extras.append(reference)
    if activities:
        extras.append(f"Attivita': {', '.join(activities)}")
    if original:
        if not any(original in item for item in extras):
            extras.append(f"Messaggio originale: {original}")

    return ' | '.join(extras)


def get_pending_store(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict[str, Any]]:
    return context.bot_data.setdefault('pending_clarifications', {})


def build_pending_key(chat_id: Any, user_id: Any) -> str:
    return f"{chat_id}:{user_id}"


def set_pending_clarification(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    trace_id: str,
    chat_id: Any,
    user_id: Any,
    original_message: str,
    parsed_data: dict[str, Any],
    reason: str,
    pending_type: str = 'generic_confirmation',
) -> None:
    store = get_pending_store(context)
    now = datetime.now(ROME_TZ)
    store[build_pending_key(chat_id, user_id)] = {
        'trace_id': trace_id,
        'chat_id': chat_id,
        'user_id': user_id,
        'original_message': original_message,
        'parsed_data': safe_json_value(parsed_data),
        'reason': reason,
        'pending_type': pending_type,
        'created_at': now.isoformat(),
        'expires_at': (now + timedelta(hours=PENDING_EXPIRY_HOURS)).isoformat(),
        'mode': 'awaiting_action',
    }


def get_pending_clarification(context: ContextTypes.DEFAULT_TYPE, chat_id: Any, user_id: Any) -> Optional[dict[str, Any]]:
    store = get_pending_store(context)
    pending = store.get(build_pending_key(chat_id, user_id))
    if not pending:
        return None
    expires_at = pending.get('expires_at')
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now(ROME_TZ):
                store.pop(build_pending_key(chat_id, user_id), None)
                return None
        except Exception:
            pass
    return pending


def clear_pending_clarification(context: ContextTypes.DEFAULT_TYPE, chat_id: Any, user_id: Any) -> None:
    get_pending_store(context).pop(build_pending_key(chat_id, user_id), None)


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Conferma", callback_data='clarify:confirm'),
            InlineKeyboardButton("🔁 Riscrivi", callback_data='clarify:rewrite'),
        ],
        [
            InlineKeyboardButton("❌ Non creare", callback_data='clarify:cancel'),
        ],
    ])


def get_mask_store(context: ContextTypes.DEFAULT_TYPE) -> dict[str, dict[str, Any]]:
    return context.bot_data.setdefault('input_masks', {})


def get_mask_form(context: ContextTypes.DEFAULT_TYPE, chat_id: Any, user_id: Any) -> Optional[dict[str, Any]]:
    return get_mask_store(context).get(build_pending_key(chat_id, user_id))


def set_mask_form(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    trace_id: str,
    chat_id: Any,
    user_id: Any,
    username: Any,
) -> dict[str, Any]:
    form = {
        'trace_id': trace_id,
        'chat_id': chat_id,
        'user_id': user_id,
        'username': username,
        'created_at': datetime.now(ROME_TZ).isoformat(),
        'mode': 'idle',
        'active_field': None,
        'fields': {field: '' for field in MASK_FIELD_ORDER},
    }
    get_mask_store(context)[build_pending_key(chat_id, user_id)] = form
    return form


def clear_mask_form(context: ContextTypes.DEFAULT_TYPE, chat_id: Any, user_id: Any) -> None:
    get_mask_store(context).pop(build_pending_key(chat_id, user_id), None)


def build_mask_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Parte/Giudice/Domic.", callback_data='mask:field:pgd'),
            InlineKeyboardButton("Rinvio", callback_data='mask:field:rinvio'),
        ],
        [
            InlineKeyboardButton("Successo", callback_data='mask:field:successo'),
            InlineKeyboardButton("Altro", callback_data='mask:field:altro'),
        ],
        [
            InlineKeyboardButton("✅ Crea evento", callback_data='mask:create'),
            InlineKeyboardButton("❌ Annulla", callback_data='mask:cancel'),
        ],
    ])


def render_mask_summary(fields: dict[str, Any]) -> str:
    lines = ["Scheda udienza (/1)", ""]
    for field in MASK_FIELD_ORDER:
        label = MASK_FIELD_LABELS[field]
        value = normalize_whitespace(str(fields.get(field, '') or ''))
        lines.append(f"{label}: {value or '-'}")
    lines.extend([
        "",
        "Campi principali: Parte/Giudice/Domiciliatario e Rinvio.",
        "Successo e Altro sono opzionali.",
    ])
    return '\n'.join(lines)


def build_mask_structured_text(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in MASK_FIELD_ORDER:
        value = normalize_whitespace(str(fields.get(field, '') or ''))
        if value:
            parts.append(f"{MASK_FIELD_LABELS[field].upper()}: {value}")
    return '\n'.join(parts)


def split_compact_mask_values(message_text: str) -> list[str]:
    text = normalize_message_text(message_text)
    if not text:
        return []
    if '|' in text:
        return [normalize_whitespace(part) for part in text.split('|') if normalize_whitespace(part)]
    if ';' in text:
        return [normalize_whitespace(part) for part in text.split(';') if normalize_whitespace(part)]
    return [normalize_whitespace(part) for part in re.split(r'\s{2,}', text) if normalize_whitespace(part)]


def apply_compact_identity_fields(fields: dict[str, Any], message_text: str) -> None:
    values = split_compact_mask_values(message_text)
    if not values:
        return
    if len(values) == 1:
        tokens = values[0].split()
        if len(tokens) == 2:
            fields['parte'] = values[0]
            return
    mapping = ['parte', 'giudice', 'domiciliatario']
    for field, value in zip(mapping, values[:3]):
        fields[field] = value


def extract_remainder_after_datetime(value: str) -> str:
    text = normalize_message_text(value)
    match = re.search(
        r'^(.*?\b\d{1,2}[\/.\-]\d{1,2}(?:[\/.\-]\d{2,4})?(?:\s*(?:h|ore|alle)?\s*\d{1,2}(?::|[.,])?\d{0,2})?)(.*)$',
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ''
    return normalize_whitespace(match.group(2))


def build_event_from_mask(fields: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    rinvio_value = normalize_whitespace(str(fields.get('rinvio', '') or ''))
    if not rinvio_value:
        return None, "Per creare l'evento dalla maschera mi serve almeno il campo Rinvio con data e ora."

    data = normalize_event_date(rinvio_value)
    ora = normalize_event_time(rinvio_value)
    if not data or not ora:
        return None, "Nel campo Rinvio non riesco a leggere bene data e ora."

    parte = normalize_whitespace(str(fields.get('parte', '') or ''))
    giudice = normalize_judge_name(str(fields.get('giudice', '') or ''))
    altro = normalize_whitespace(str(fields.get('altro', '') or ''))
    luogo = normalize_location_name(altro, altro) if altro else ''

    note_segments: list[str] = []
    domiciliatario = normalize_whitespace(str(fields.get('domiciliatario', '') or ''))
    successo = normalize_whitespace(str(fields.get('successo', '') or ''))
    if domiciliatario:
        note_segments.append(f"Domiciliatario: {domiciliatario}")
    if successo:
        note_segments.append(f"Successo: {successo}")
    if altro:
        note_segments.append(f"Altro: {altro}")

    original = build_mask_structured_text(fields)
    note = normalize_event_notes(' | '.join(note_segments), original)

    return {
        'parte': parte or 'Udienza',
        'giudice': giudice,
        'luogo': luogo,
        'data': data,
        'ora': ora,
        'note': note,
    }, None


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
        eventi = parsed_data.get('eventi', [])
        normalized['eventi'] = eventi if isinstance(eventi, list) else []
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
        giudice_raw = str(evento.get('giudice', '') or '')
        luogo_raw = str(evento.get('luogo', '') or evento.get('location', '') or '')
        giudice = normalize_judge_name(giudice_raw)
        luogo = normalize_location_name(luogo_raw, original_message)
        data = normalize_event_date(str(evento.get('data', '')))
        ora = normalize_event_time(str(evento.get('ora', '')))
        note = normalize_event_notes(str(evento.get('note', '') or original_message), original_message)

        collegio_match = re.search(r'collegio\s+pres\.?\s+([A-Za-zÀ-ÿ\'’.-]+)', original_message, flags=re.IGNORECASE)
        if collegio_match:
            luogo = 'Collegio'
            if not giudice or looks_like_location(giudice):
                giudice = normalize_judge_name(collegio_match.group(1))

        if not luogo_raw and looks_like_location(giudice_raw):
            luogo = normalize_location_name(giudice_raw, original_message)
            giudice = normalize_judge_name(giudice_raw)

        if looks_like_location(parte) or looks_like_reference(parte):
            parte = extract_primary_party_candidate(original_message)
        if looks_like_lawyer(parte):
            parte = ''

        if not parte and note:
            maybe_parte = re.split(r'[:\n,]', original_message or note, maxsplit=1)[0].strip()
            parte = normalize_whitespace(maybe_parte)
        if looks_like_location(parte) or looks_like_reference(parte) or looks_like_lawyer(parte):
            parte = ''

        if not parte or not data or not ora:
            continue

        eventi.append({
            'parte': parte,
            'giudice': giudice,
            'luogo': luogo,
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


def should_require_confirmation(parsed_data: dict[str, Any], analysis: dict[str, Any], original_message: str) -> Optional[str]:
    if parsed_data.get('tipo') != 'rinvio':
        return None

    confidence = parsed_data.get('confidence')
    warnings = parsed_data.get('warnings', [])
    eventi = parsed_data.get('eventi', [])
    normalized_message = normalize_message_text(original_message)
    lowered_message = normalized_message.lower()

    if not has_judicial_context(original_message):
        return "Il messaggio non sembra contenere elementi sufficientemente affidabili per un evento di udienza."

    if isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
        return f"Confidenza troppo bassa ({confidence:.2f}) per creare l'evento in automatico."

    if isinstance(warnings, list) and warnings:
        return "Ho alcuni punti di incertezza che è meglio confermare prima della creazione."

    if analysis.get('block_count', 0) > 1 and len(eventi) != analysis.get('block_count'):
        return "Il messaggio sembra contenere più blocchi o più rinvii, ma non sono riuscito a separarli con sufficiente affidabilità."

    for evento in eventi:
        parte = normalize_whitespace(str(evento.get('parte', '')))
        giudice = normalize_whitespace(str(evento.get('giudice', '')))
        luogo = normalize_whitespace(str(evento.get('luogo', '')))
        if len(parte) < 2:
            return "Non sono sicuro di aver identificato correttamente la parte."
        if looks_like_location(parte):
            return "La parte sembra in realta' un tribunale, una corte o un contesto di udienza."
        if looks_like_reference(parte):
            return "La parte sembra in realta' un riferimento di ruolo o di procedimento."
        if looks_like_lawyer(parte):
            return "La parte sembra in realta' un avvocato o un difensore."
        if re.search(r'\bavv\.?\b', giudice.lower()):
            return "Il nome del giudice sembra in realtà un avvocato o un riferimento difensivo."
        if looks_like_lawyer(giudice):
            return "Il nome del giudice sembra in realtà un avvocato o un domiciliatario."
        if giudice and looks_like_location(giudice):
            return "Il giudice sembra in realta' un luogo o un ufficio giudiziario."
        if looks_like_reference(luogo):
            return "Il luogo sembra contenere solo riferimenti di ruolo o procedimento."
        if looks_like_lawyer(luogo):
            return "Il luogo sembra in realta' un avvocato o un domiciliatario."

        if re.search(r'collegio\s+pres\.?\s+', lowered_message):
            if luogo != 'Collegio':
                return "Ho rilevato un contesto di collegio, ma il luogo non risulta coerente."
            if not giudice:
                return "Ho rilevato un collegio con presidente indicato, ma il giudice non e' stato estratto bene."

        if re.search(r'\btribunale(?:\s+di)?\s+[A-Za-zÀ-ÿ]+', normalized_message, flags=re.IGNORECASE):
            if not luogo or not looks_like_location(luogo):
                return "Nel messaggio compare un tribunale, ma il luogo non e' stato ricostruito in modo coerente."

        if re.search(r"\bcorte\s+d[’']appello\b|\bcorte\s+di\s+appello\b", lowered_message):
            if not luogo or 'corte' not in luogo.lower():
                return "Nel messaggio compare una corte d'appello, ma il luogo non e' stato ricostruito correttamente."

        first_candidate = extract_primary_party_candidate(original_message)
        if first_candidate and giudice.lower() == first_candidate.lower() and (
            re.search(r'\btribunale\b|\bsez\b|\brg\b|\bprocedimento\b', lowered_message)
        ):
            return "Il primo cognome sembra la parte, ma e' finito nel campo giudice."

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
            'luogo': first_event.get('luogo', ''),
            'data': first_event.get('data', ''),
            'ora': first_event.get('ora', ''),
        },
        'eventi': eventi if isinstance(eventi, list) else [],
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

def parse_message_with_ai(message_text: str, trace_id: Optional[str] = None):
    """Usa Claude per interpretare il messaggio mantenendo lettura completa e validazione finale."""
    if not client:
        logger.error("Client Anthropic non configurato")
        return None

    try:
        analysis = build_message_analysis(message_text)
        normalized_message = analysis['normalized_message']
        today = datetime.now(ROME_TZ)
        prompt_version = 'v1-intelligent-reader'
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
- Nei messaggi di Fabio, il primo cognome o il primo token nominale e' quasi sempre la parte/imputato assistito.
- Non trasformare il primo cognome in giudice solo perche' nel messaggio non compare un giudice esplicito.
- Se dopo il primo cognome compaiono riferimenti come "tribunale", citta', "sez", "rg", numeri di ruolo, data e ora, interpreta normalmente il primo cognome come parte e il resto come contesto dell'udienza.
- "Tribunale", citta', sezione, ruolo e RG non sono la parte e non devono sostituire il nome dell'evento.
- "Tribunale di Civitavecchia" o qualunque "Tribunale di <citta'>" deve sempre diventare luogo, mai giudice.
- "Corte d'Appello" e varianti devono sempre diventare luogo, mai giudice.
- "Collegio Pres. Tizio" significa luogo = "Collegio" e giudice = "Tizio".
- "RG", "R.G.", "RGNR", "RG DIB", "procedimento n." e riferimenti simili non sono mai luogo e vanno nelle note insieme al messaggio originale.
- "avv", "avv." e difensori nominati non sono il giudice.
- Il giudice puo' essere noto oppure dedotto dal contesto; se manca davvero lascialo vuoto invece di inventarlo.
- Se manca il giudice ma c'e' il tribunale, il tribunale va in luogo.
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

Casi importanti:
- Se il messaggio e' del tipo "GUBIOTTI TRIBUNALE ROMA 26.03.2026 h 11.15 sez V 001966/23 RG", allora:
  - "GUBIOTTI" e' la parte
  - "Tribunale Roma" e "sez V" sono location/contesto
  - il giudice puo' anche mancare del tutto
  - non invertire parte e tribunale

Formato JSON obbligatorio.
Se è rinvio:
{{
  "tipo": "rinvio",
  "confidence": 0.0,
  "eventi": [
    {{
      "parte": "",
      "giudice": "",
      "luogo": "",
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

        if trace_id:
            log_pipeline_event(
                'message_analysis_built',
                trace_id,
                normalized_message=normalized_message,
                block_count=analysis.get('block_count'),
                date_candidates=analysis.get('date_candidates'),
                time_candidates=analysis.get('time_candidates'),
                hearing_hints=analysis.get('has_hearing_hints'),
                non_hearing_keywords=analysis.get('has_non_hearing_keywords'),
            )
            log_pipeline_event(
                'claude_request_prepared',
                trace_id,
                prompt_version=prompt_version,
                prompt_hash=hash_text(prompt),
                message_hash=hash_text(message_text),
                normalized_message=normalized_message,
            )

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        if trace_id:
            log_pipeline_event(
                'claude_response_received',
                trace_id,
                raw_response=response_text,
                raw_response_hash=hash_text(response_text),
            )
        parsed_data = extract_json_object(response_text)
        if not parsed_data:
            logger.error(f"Risposta AI non parseabile: {response_text}")
            if trace_id:
                log_pipeline_event(
                    'pipeline_failed',
                    trace_id,
                    stage='claude_response_received',
                    error='Risposta AI non parseabile',
                    raw_response=response_text,
                )
            return None

        parsed_data = validate_and_normalize_parsed_data(parsed_data, normalized_message)
        confirmation_reason = should_require_confirmation(parsed_data, analysis, normalized_message)
        if trace_id:
            log_pipeline_event(
                'parsed_data_normalized',
                trace_id,
                parsed_data=parsed_data,
                tipo=parsed_data.get('tipo'),
                confidence=parsed_data.get('confidence'),
                warnings=parsed_data.get('warnings', []),
            )
            log_pipeline_event(
                'confirmation_decision',
                trace_id,
                confirmation_required=bool(confirmation_reason),
                reason=confirmation_reason,
                tipo=parsed_data.get('tipo'),
            )
        if confirmation_reason:
            parsed_data = build_confirmation_from_events(parsed_data, confirmation_reason)
        logger.info(f"AI parsed data: {parsed_data}")
        return parsed_data

    except Exception as e:
        logger.error(f"Errore parsing AI: {e}")
        if trace_id:
            log_pipeline_event(
                'pipeline_failed',
                trace_id,
                stage='parse_message_with_ai',
                error=str(e),
            )
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
            'location': evento.get('luogo') or evento.get('giudice') or 'Tribunale Civitavecchia',
            'description': evento.get('note', ''),
            'evento': evento
        }
        
    except Exception as e:
        logger.error(f"Errore formattazione evento: {e}")
        return None

def create_google_calendar_event(event_data, trace_id: Optional[str] = None):
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
        if trace_id:
            log_pipeline_event(
                'calendar_event_formatted',
                trace_id,
                title=event.get('summary'),
                location=event.get('location'),
                start=event.get('start'),
                end=event.get('end'),
                description_length=len(event.get('description', '')),
            )
        
        created_event = service.events().insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event
        ).execute()
        
        logger.info(f"Evento creato: {created_event.get('htmlLink')}")
        if trace_id:
            log_pipeline_event(
                'calendar_event_created',
                trace_id,
                success=True,
                calendar_id=GOOGLE_CALENDAR_ID,
                event_id=created_event.get('id'),
                html_link=created_event.get('htmlLink'),
            )
        return created_event
        
    except Exception as e:
        logger.error(f"Errore creazione evento Google Calendar: {e}")
        if trace_id:
            log_pipeline_event(
                'calendar_event_created',
                trace_id,
                success=False,
                calendar_id=GOOGLE_CALENDAR_ID,
                error=str(e),
            )
        return None


async def reply_and_log(update: Update, trace_id: str, reply_text: str, reply_category: str, **extra: Any) -> None:
    await update.message.reply_text(reply_text)
    log_pipeline_event(
        'telegram_reply_sent',
        trace_id,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id if update.effective_user else None,
        username=update.effective_user.username if update.effective_user else None,
        reply_category=reply_category,
        reply_text=reply_text,
        **extra,
    )


async def reply_with_keyboard_and_log(
    update: Update,
    trace_id: str,
    reply_text: str,
    reply_category: str,
    reply_markup: InlineKeyboardMarkup,
    **extra: Any,
) -> None:
    await update.message.reply_text(reply_text, reply_markup=reply_markup)
    log_pipeline_event(
        'telegram_reply_sent',
        trace_id,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id if update.effective_user else None,
        username=update.effective_user.username if update.effective_user else None,
        reply_category=reply_category,
        reply_text=reply_text,
        has_inline_keyboard=True,
        **extra,
    )


def build_reanalysis_prompt(original_message: str, followup_text: str, previous_parsed_data: dict[str, Any]) -> str:
    return f"""Sei il lettore intelligente dei messaggi di Fabio, avvocato penalista italiano.

Hai gia' analizzato un messaggio, ma Fabio lo ha riscritto per chiarire meglio il caso.

Messaggio originale:
{original_message}

Interpretazione precedente:
{json.dumps(previous_parsed_data, ensure_ascii=False)}

Nuova riscrittura di Fabio:
{followup_text}

Produci solo JSON valido nello stesso formato del parser principale.
Se il caso e' un rinvio, includi anche:
- parte
- giudice
- luogo
- data
- ora
- note

Non inventare dati mancanti."""


def parse_message_with_ai_rewrite(
    original_message: str,
    followup_text: str,
    previous_parsed_data: dict[str, Any],
    trace_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    if not client:
        logger.error("Client Anthropic non configurato")
        return None

    try:
        prompt = build_reanalysis_prompt(original_message, followup_text, previous_parsed_data)
        if trace_id:
            log_pipeline_event(
                'clarification_reanalysis_requested',
                trace_id,
                original_message=original_message,
                followup_text=followup_text,
                previous_parsed_data=previous_parsed_data,
            )
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        parsed_data = extract_json_object(response_text)
        if not parsed_data:
            return None
        parsed_data = validate_and_normalize_parsed_data(parsed_data, normalize_message_text(followup_text))
        return parsed_data
    except Exception as exc:
        logger.error(f"Errore rilettura dubbio: {exc}")
        if trace_id:
            log_pipeline_event('pipeline_failed', trace_id, stage='clarification_reanalysis', error=str(exc))
        return None


async def user_can_export_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.effective_chat or not update.effective_user:
        return False

    if update.effective_chat.type == 'private':
        return True

    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    except Exception as exc:
        logger.warning(f"Impossibile verificare i permessi export chat: {exc}")
        return False

    return getattr(member, 'status', '') in {'administrator', 'creator'}


async def handle_export_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message:
        return

    trace_id = build_trace_id(update)
    allowed = await user_can_export_chat(update, context)
    if not allowed:
        await update.message.reply_text("⚠️ Solo la chat privata o un admin del gruppo puo' esportare la cronologia.")
        log_pipeline_event(
            'chat_export_denied',
            trace_id,
            chat_id=update.effective_chat.id if update.effective_chat else None,
            message_id=update.effective_message.message_id if update.effective_message else None,
            user_id=update.effective_user.id if update.effective_user else None,
            username=update.effective_user.username if update.effective_user else None,
            text=update.message.text,
        )
        return

    export_data = build_chat_export(update.effective_chat.id)
    if not export_data.get('conversations'):
        await update.message.reply_text("ℹ️ Non ho trovato messaggi esportabili nei log locali per questa chat.")
        log_pipeline_event(
            'chat_export_empty',
            trace_id,
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id if update.effective_message else None,
            user_id=update.effective_user.id if update.effective_user else None,
            username=update.effective_user.username if update.effective_user else None,
            text=update.message.text,
        )
        return

    export_files = write_chat_export_files(export_data)
    caption = (
        f"Export completo chat {update.effective_chat.id}\n"
        f"Conversazioni: {export_data['total_conversations']} | "
        f"Risposte bot: {export_data['total_replies']}"
    )

    with export_files['zip'].open('rb') as document:
        await update.message.reply_document(
            document=document,
            filename=export_files['zip'].name,
            caption=caption,
        )

    log_pipeline_event(
        'chat_export_generated',
        trace_id,
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id if update.effective_user else None,
        username=update.effective_user.username if update.effective_user else None,
        text=update.message.text,
        export_zip=str(export_files['zip']),
        export_json=str(export_files['json']),
        export_markdown=str(export_files['markdown']),
        total_conversations=export_data['total_conversations'],
        total_replies=export_data['total_replies'],
    )


async def handle_mask_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user or not update.message:
        return

    trace_id = build_trace_id(update)
    form = set_mask_form(
        context,
        trace_id=trace_id,
        chat_id=update.effective_chat.id,
        user_id=update.effective_user.id,
        username=update.effective_user.username,
    )
    summary = render_mask_summary(form['fields'])
    log_pipeline_event(
        'mask_started',
        trace_id,
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        text=update.message.text,
    )
    await update.message.reply_text(summary, reply_markup=build_mask_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce i messaggi in arrivo"""
    message_text = update.message.text
    
    if not message_text:
        return
    
    trace_id = build_trace_id(update)
    logger.info(f"Nuovo messaggio ricevuto trace_id={trace_id}")
    log_telegram_raw_message(update, trace_id, message_text)
    log_pipeline_event(
        'telegram_received',
        trace_id,
        chat_id=update.effective_chat.id if update.effective_chat else None,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id if update.effective_user else None,
        username=update.effective_user.username if update.effective_user else None,
        text=message_text,
    )

    mask_form = get_mask_form(
        context,
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )
    if mask_form and mask_form.get('mode') == 'awaiting_field':
        active_field = str(mask_form.get('active_field') or '')
        if active_field in MASK_FIELD_ORDER or active_field == 'pgd':
            if active_field == 'pgd':
                apply_compact_identity_fields(mask_form['fields'], message_text)
            elif active_field == 'rinvio':
                normalized_value = normalize_whitespace(message_text)
                mask_form['fields']['rinvio'] = normalized_value
                remainder = extract_remainder_after_datetime(normalized_value)
                if remainder and not mask_form['fields'].get('successo'):
                    mask_form['fields']['successo'] = remainder
            else:
                mask_form['fields'][active_field] = normalize_whitespace(message_text)
            mask_form['mode'] = 'idle'
            mask_form['active_field'] = None
            log_pipeline_event(
                'mask_field_updated',
                mask_form.get('trace_id') or trace_id,
                chat_id=update.effective_chat.id if update.effective_chat else None,
                message_id=update.effective_message.message_id if update.effective_message else None,
                user_id=update.effective_user.id if update.effective_user else None,
                username=update.effective_user.username if update.effective_user else None,
                field=active_field,
                value=message_text,
            )
            await update.message.reply_text(
                render_mask_summary(mask_form['fields']),
                reply_markup=build_mask_keyboard(),
            )
            return

    pending = get_pending_clarification(
        context,
        update.effective_chat.id if update.effective_chat else None,
        update.effective_user.id if update.effective_user else None,
    )
    if pending and pending.get('mode') == 'awaiting_rewrite':
        log_pipeline_event(
            'clarification_text_received',
            trace_id,
            chat_id=update.effective_chat.id if update.effective_chat else None,
            message_id=update.effective_message.message_id if update.effective_message else None,
            user_id=update.effective_user.id if update.effective_user else None,
            username=update.effective_user.username if update.effective_user else None,
            text=message_text,
            pending_trace_id=pending.get('trace_id'),
        )
        await update.message.chat.send_action(action="typing")
        reparsed = parse_message_with_ai_rewrite(
            pending.get('original_message', ''),
            message_text,
            pending.get('parsed_data', {}),
            trace_id=trace_id,
        )
        clear_pending_clarification(
            context,
            update.effective_chat.id if update.effective_chat else None,
            update.effective_user.id if update.effective_user else None,
        )
        if not reparsed:
            await reply_and_log(update, trace_id, "⚠️ Non sono riuscito a rileggere la riscrittura. Prova a riscrivere il messaggio in modo piu' lineare.", 'clarification_rewrite_failed')
            return
        parsed_data = reparsed
    else:
        await update.message.chat.send_action(action="typing")
        parsed_data = parse_message_with_ai(message_text, trace_id=trace_id)
    
    if not parsed_data:
        await reply_and_log(update, trace_id, "⚠️ Non sono riuscito a interpretare il messaggio.", 'parse_failed')
        return
    
    tipo = parsed_data.get('tipo', '')
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE TIPI NON-RINVIO
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'sentenza':
        await reply_and_log(update, trace_id, "📋 È una sentenza", 'sentenza')
        return
    
    if tipo == 'riserva':
        await reply_and_log(update, trace_id, "⏸️ È una riserva", 'riserva')
        return
    
    if tipo == 'trattenuta':
        await reply_and_log(update, trace_id, "⚖️ È una trattenuta", 'trattenuta')
        return
    
    if tipo == 'nota':
        await reply_and_log(update, trace_id, "📝 È una nota procedurale", 'nota')
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE CONFERMA RICHIESTA
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'conferma':
        dubbio = parsed_data.get('dubbio', '')
        interpretazione = parsed_data.get('interpretazione', {})
        domanda = parsed_data.get('domanda', 'Va bene così?')
        
        msg = f"❓ Ho un dubbio\n\n"
        msg += f"📋 {dubbio}\n\n"
        msg += f"La mia interpretazione:\n"
        msg += f"   👤 Parte: {interpretazione.get('parte', 'N/A')}\n"
        msg += f"   ⚖️ Giudice: {interpretazione.get('giudice', 'N/A')}\n"
        msg += f"   📍 Luogo: {interpretazione.get('luogo', 'N/A')}\n"
        msg += f"   📅 Data: {interpretazione.get('data', 'N/A')}\n"
        msg += f"   🕐 Ora: {interpretazione.get('ora', 'N/A')}\n\n"
        msg += f"💬 {domanda}"
        set_pending_clarification(
            context,
            trace_id=trace_id,
            chat_id=update.effective_chat.id if update.effective_chat else None,
            user_id=update.effective_user.id if update.effective_user else None,
            original_message=message_text,
            parsed_data=parsed_data,
            reason=dubbio,
        )
        log_pipeline_event(
            'clarification_opened',
            trace_id,
            chat_id=update.effective_chat.id if update.effective_chat else None,
            message_id=update.effective_message.message_id if update.effective_message else None,
            user_id=update.effective_user.id if update.effective_user else None,
            username=update.effective_user.username if update.effective_user else None,
            text=message_text,
            reason=dubbio,
            interpretation=interpretazione,
        )
        await reply_with_keyboard_and_log(
            update,
            trace_id,
            msg,
            'conferma',
            build_confirmation_keyboard(),
            tipo=tipo,
            interpretazione=interpretazione,
        )
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE DATA PASSATA
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'data_passata':
        data_letta = parsed_data.get('data_letta', '')
        opzioni = parsed_data.get('opzioni', [])
        domanda = parsed_data.get('domanda', '')
        
        msg = f"❌ Data nel passato\n\n"
        msg += f"📅 Ho letto: {data_letta}\n\n"
        msg += f"💡 Intendevi:\n"
        for opt in opzioni:
            msg += f"   {opt['id'].upper()}) {opt['data']}\n"
        msg += f"\n💬 Rispondi con 'a' o 'b'"
        
        await reply_and_log(update, trace_id, msg, 'data_passata', tipo=tipo, data_letta=data_letta, opzioni=opzioni)
        return
    
    # ═══════════════════════════════════════════════════════════
    # GESTIONE RINVII (creazione eventi)
    # ═══════════════════════════════════════════════════════════
    
    if tipo == 'rinvio':
        eventi = parsed_data.get('eventi', [])
        correzioni = parsed_data.get('correzioni', [])
        
        if not eventi:
            await reply_and_log(update, trace_id, "⚠️ Nessun evento trovato.", 'rinvio_empty', tipo=tipo)
            return
        
        risposte = []
        eventi_creati = 0
        
        # Mostra correzioni se presenti
        if correzioni:
            msg_corr = "🔧 Correzioni automatiche:\n"
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
            
            created = create_google_calendar_event(event_data, trace_id=trace_id)
            
            if created:
                eventi_creati += 1
                resp = f"✅ Evento creato\n"
                resp += f"   👤 {evento.get('parte', 'N/A')}\n"
                resp += f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
                resp += f"   📍 {evento.get('luogo', 'N/A')}\n"
                resp += f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}\n"
                resp += f"   🔗 {created.get('htmlLink', '')}"
            else:
                resp = f"⚠️ Errore creazione\n"
                resp += f"   👤 {evento.get('parte', 'N/A')}\n"
                resp += f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
                resp += f"   📍 {evento.get('luogo', 'N/A')}\n"
                resp += f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}"
            
            risposte.append(resp)
        
        # Messaggio finale
        messaggio_finale = "\n\n".join(risposte)
        if len(eventi) > 1:
            messaggio_finale += f"\n\n📊 {eventi_creati}/{len(eventi)} eventi creati"
        
        await reply_and_log(
            update,
            trace_id,
            messaggio_finale,
            'rinvio_result',
            tipo=tipo,
            eventi_totali=len(eventi),
            eventi_creati=eventi_creati,
        )
        logger.info(f"{eventi_creati}/{len(eventi)} evento/i creato/i")
        return
    
    # Fallback
    await reply_and_log(update, trace_id, "⚠️ Non ho capito il tipo di messaggio.", 'fallback', tipo=tipo)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestisce errori"""
    logger.error(f"Errore: {context.error}")
    trace_id = build_trace_id(update)
    log_pipeline_event(
        'pipeline_failed',
        trace_id,
        stage='error_handler',
        error=str(context.error),
    )
    if update and update.message:
        await update.message.reply_text("❌ Si è verificato un errore. Riprova.")


async def handle_clarification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_chat or not update.effective_user:
        return

    await query.answer()
    action = (query.data or '').replace('clarify:', '', 1)
    pending = get_pending_clarification(context, update.effective_chat.id, update.effective_user.id)
    if not pending:
        await query.edit_message_text("ℹ️ Questo dubbio non è piu' attivo. Rimandami il messaggio se vuoi riprovare.")
        return

    trace_id = pending.get('trace_id') or build_trace_id(update)
    log_pipeline_event(
        'clarification_button_clicked',
        trace_id,
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        action=action,
    )

    if action == 'cancel':
        clear_pending_clarification(context, update.effective_chat.id, update.effective_user.id)
        await query.edit_message_text("❌ Va bene, non creo alcun evento per questo messaggio.")
        log_pipeline_event('clarification_cancelled', trace_id, chat_id=update.effective_chat.id, user_id=update.effective_user.id)
        return

    if action == 'rewrite':
        pending['mode'] = 'awaiting_rewrite'
        await query.edit_message_text(
            "🔁 Riscrivi il messaggio in forma piu' chiara. Lo rileggero' tenendo conto del dubbio appena aperto."
        )
        return

    if action == 'confirm':
        parsed_data = pending.get('parsed_data') or {}
        eventi = parsed_data.get('eventi', [])
        if not eventi:
            clear_pending_clarification(context, update.effective_chat.id, update.effective_user.id)
            await query.edit_message_text("⚠️ Non trovo eventi utilizzabili nel dubbio salvato.")
            return

        risposte = []
        eventi_creati = 0
        for evento in eventi:
            event_data = format_calendar_event(evento)
            if not event_data:
                risposte.append("⚠️ Errore formattazione evento.")
                continue
            created = create_google_calendar_event(event_data, trace_id=trace_id)
            if created:
                eventi_creati += 1
                resp = f"✅ Evento creato\n"
                resp += f"   👤 {evento.get('parte', 'N/A')}\n"
                resp += f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
                resp += f"   📍 {evento.get('luogo', 'N/A')}\n"
                resp += f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}\n"
                resp += f"   🔗 {created.get('htmlLink', '')}"
            else:
                resp = "⚠️ Errore nella creazione dell'evento."
            risposte.append(resp)

        clear_pending_clarification(context, update.effective_chat.id, update.effective_user.id)
        await query.edit_message_text("\n\n".join(risposte))
        log_pipeline_event(
            'clarification_resolved',
            trace_id,
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            action='confirm',
            eventi_creati=eventi_creati,
            eventi_totali=len(eventi),
        )
        return

    await query.edit_message_text("ℹ️ Azione non riconosciuta.")


async def handle_mask_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_chat or not update.effective_user:
        return

    await query.answer()
    form = get_mask_form(context, update.effective_chat.id, update.effective_user.id)
    if not form:
        await query.edit_message_text("ℹ️ La maschera non e' piu' attiva. Rimanda /1 per riaprirla.")
        return

    trace_id = form.get('trace_id') or build_trace_id(update)
    action = query.data or ''
    log_pipeline_event(
        'mask_button_clicked',
        trace_id,
        chat_id=update.effective_chat.id,
        message_id=update.effective_message.message_id if update.effective_message else None,
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        action=action,
    )

    if action == 'mask:cancel':
        clear_mask_form(context, update.effective_chat.id, update.effective_user.id)
        await query.edit_message_text("❌ Maschera annullata.")
        log_pipeline_event('mask_cancelled', trace_id, chat_id=update.effective_chat.id, user_id=update.effective_user.id)
        return

    if action.startswith('mask:field:'):
        field = action.split(':', 2)[2]
        if field not in MASK_FIELD_ORDER and field != 'pgd':
            await query.edit_message_text("ℹ️ Campo non riconosciuto.")
            return
        form['mode'] = 'awaiting_field'
        form['active_field'] = field
        if field == 'pgd':
            text = (
                "✏️ Inserisci fino a 3 blocchi in questo ordine:\n"
                "Parte  Giudice  Domiciliatario\n\n"
                "Esempi:\n"
                "- `Gubiotti  Farinella  Candeloro`\n"
                "- `Gubiotti  Farinella`\n"
                "- `Gubiotti`\n\n"
                "Usa preferibilmente spazi doppi tra i blocchi. Se usi un solo spazio il bot provera' comunque a capirti.\n\n"
                "Se inserisci solo due blocchi, usero' i primi due campi e basta."
            )
        elif field == 'rinvio':
            text = (
                "✏️ Inserisci il rinvio nel formato:\n"
                "Data Ora Cosa succedera'\n\n"
                "Esempio:\n"
                "- `30/03/2026 h 11.15 discussione`\n\n"
                "Leggero' data e ora nel campo Rinvio e, se presente, il resto andra' in Successo."
            )
        else:
            text = f"✏️ Scrivi il valore per {MASK_FIELD_LABELS[field]}."
        await query.edit_message_text(text)
        return

    if action == 'mask:create':
        evento, error_message = build_event_from_mask(form.get('fields', {}))
        if error_message:
            await query.edit_message_text(
                f"⚠️ {error_message}\n\n{render_mask_summary(form.get('fields', {}))}",
                reply_markup=build_mask_keyboard(),
            )
            return

        event_data = format_calendar_event(evento or {})
        if not event_data:
            await query.edit_message_text(
                f"⚠️ Non riesco a formattare l'evento dalla maschera.\n\n{render_mask_summary(form.get('fields', {}))}",
                reply_markup=build_mask_keyboard(),
            )
            return

        created = create_google_calendar_event(event_data, trace_id=trace_id)
        if not created:
            await query.edit_message_text(
                f"⚠️ Errore nella creazione dell'evento da maschera.\n\n{render_mask_summary(form.get('fields', {}))}",
                reply_markup=build_mask_keyboard(),
            )
            return

        clear_mask_form(context, update.effective_chat.id, update.effective_user.id)
        response = (
            "✅ Evento creato da maschera\n"
            f"   👤 {evento.get('parte', 'N/A')}\n"
            f"   ⚖️ {evento.get('giudice', 'N/A')}\n"
            f"   📍 {evento.get('luogo', 'N/A') or 'N/A'}\n"
            f"   📅 {evento.get('data', 'N/A')} 🕐 {evento.get('ora', 'N/A')}\n"
            f"   🔗 {created.get('htmlLink', '')}"
        )
        await query.edit_message_text(response)
        log_pipeline_event(
            'mask_event_created',
            trace_id,
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
            evento=evento,
            html_link=created.get('htmlLink'),
        )
        return

    await query.edit_message_text("ℹ️ Azione maschera non riconosciuta.")

def main():
    """Funzione principale"""
    ensure_runtime_directories()
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN non configurato!")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY non configurato!")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('1', handle_mask_start))
    application.add_handler(CommandHandler('export_chat', handle_export_chat))
    application.add_handler(CallbackQueryHandler(handle_mask_callback, pattern=r'^mask:'))
    application.add_handler(CallbackQueryHandler(handle_clarification_callback, pattern=r'^clarify:'))
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
