"""Live dependency check, using only synthetic data; never consumes Telegram updates."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import uuid
from datetime import datetime
from launch import configure

config = configure()
spec = importlib.util.spec_from_file_location('rinviabot', '/opt/rinviabot/app/bot.py')
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)
bot.ensure_runtime_directories()
proof = {'time': datetime.now().isoformat(), 'checks': {}}

async def telegram_check():
    async with bot.Application.builder().token(config['TELEGRAM_BOT_TOKEN']).build() as app:
        me = await app.bot.get_me()
        webhook = await app.bot.get_webhook_info()
        assert me.username == 'rinviav2bot'
        proof['checks']['telegram'] = {'username': me.username, 'pending': webhook.pending_update_count, 'webhook_present': bool(webhook.url)}

asyncio.run(telegram_check())
parsed = bot.parse_message_with_ai('CollaudoTecnico: udienza Tribunale di Civitavecchia il 15/12/2030 ore 10:30, giudice Carlomagno. Prova tecnica senza dati reali.')
assert parsed and parsed.get('tipo') in ('rinvio', 'conferma'), 'AI extraction failed'
events = parsed.get('eventi') or []
assert events and events[0].get('data') and events[0].get('ora'), 'Missing structured event'
proof['checks']['anthropic'] = {'model': config['ANTHROPIC_MODEL'], 'type': parsed['tipo'], 'events': len(events)}
service = bot.get_google_calendar_service()
assert service is not None
calendar = config['GOOGLE_CALENDAR_ID']
created_ids = []
try:
    event_data = bot.format_calendar_event({'parte': 'TEST TECNICO MIGRAZIONE ' + uuid.uuid4().hex[:8], 'data': '15/12/2030', 'ora': '10:30', 'note': 'Collaudo tecnico temporaneo; nessun dato cliente.'})
    created = bot.create_google_calendar_event(event_data)
    assert created and created.get('id')
    created_ids.append(created['id'])
    # Record the ID before any later assertion so cleanup is recoverable after failure.
    Path('/var/lib/rinviabot/preflight-test-events.json').write_text(json.dumps(created_ids))
    readback = service.events().get(calendarId=calendar, eventId=created['id']).execute()
    assert readback['summary'] == event_data['title']
    assert readback['start']['dateTime'].startswith('2030-12-15T10:30:00')
    assert readback['end']['dateTime'].startswith('2030-12-15T11:30:00')
    assert readback['reminders']['useDefault'] is False
    proof['checks']['calendar_create_read'] = True
    title = 'TEST TECNICO TURNO ' + uuid.uuid4().hex[:8]
    day = bot.ROME_TZ.localize(datetime(2030, 12, 16))
    all_day, status = bot.create_all_day_calendar_event(title, day)
    assert all_day and all_day.get('id'), 'All-day creation failed'
    created_ids.append(all_day['id'])
    Path('/var/lib/rinviabot/preflight-test-events.json').write_text(json.dumps(created_ids))
    check = service.events().get(calendarId=calendar, eventId=all_day['id']).execute()
    assert check['start']['date'] == '2030-12-16'
    proof['checks']['calendar_all_day'] = True
finally:
    for event_id in created_ids:
        service.events().delete(calendarId=calendar, eventId=event_id).execute()
        # Google can return a cancelled tombstone instead of 410: verify via list too.
    remaining = service.events().list(calendarId=calendar, timeMin='2030-12-15T00:00:00Z', timeMax='2030-12-17T00:00:00Z', showDeleted=False).execute().get('items', [])
    assert not any(x['id'] in created_ids for x in remaining), 'Test cleanup not verified'
    proof['checks']['test_events_removed'] = True
Path('/var/lib/rinviabot/preflight-proof.json').write_text(json.dumps(proof, indent=2))
print(json.dumps(proof, indent=2))
