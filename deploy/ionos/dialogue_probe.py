"""Synthetic dialogue with real subscription LLM; Calendar writes require explicit flag.

Telegram replies are captured in memory, never sent to a person or group.
"""
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid
from launch import configure
configure()
import bot
from conversations import ConversationStore
bot.client = None  # A probe must never use the paid fallback.

async def main():
    identity = uuid.uuid4().hex[:10]
    root = Path('/var/lib/rinviabot')
    context = SimpleNamespace(bot_data={'_conversation_store': ConversationStore(root / ('probe-'+identity+'.sqlite3'))})
    text = 'PersonaCollaudo'+identity+': udienza 15/12/2030 davanti a Farinella, Tribunale di Civitavecchia. Devo ancora comunicare l’orario.'
    first = await asyncio.to_thread(bot.parse_message_with_ai, text, 'probe-'+identity)
    assert first and first['tipo'] == 'conferma', 'Missing time must open a dialogue'
    pending = bot.set_pending_clarification(context, trace_id='probe-'+identity, chat_id=-1, user_id=-1,
              original_message=text, parsed_data=first, reason='Missing time')
    message = SimpleNamespace(text='alle 11', reply_text=AsyncMock(), chat=SimpleNamespace(send_action=AsyncMock()))
    update = SimpleNamespace(message=message, effective_message=message, effective_chat=SimpleNamespace(id=-1), effective_user=SimpleNamespace(id=-1, username='synthetic'))
    await bot.handle_dialog_text(update, context, pending)
    pending = bot.get_pending_clarification(context, -1, -1)
    assert pending and pending['parsed_data']['eventi'], 'Candidate missing after correction'
    event = pending['parsed_data']['eventi'][0]
    assert event['ora'] == '11:00' and event['data'] == '15/12/2030'
    assert event['parte'] in text and event['parte'].startswith('PersonaCollaudo')
    proof = {'at':datetime.now(timezone.utc).isoformat(), 'dialogue_roundtrip':True,
             'original_preserved':pending['original_message']==text, 'correction_requires_confirmation':True,
             'telegram_delivery':'simulated_no_messages_sent', 'paid_fallback_disabled_for_probe':True}
    if '--write-calendar' in sys.argv:
        service = bot.get_google_calendar_service()
        assert service is not None
        pending['write_trace'] = 'probe-write-'+identity
        bot.dialog_store(context).save(pending)
        formatted = bot.format_calendar_event(event)
        key = pending['write_trace']+':'+formatted['title']+':'+formatted['start_time'].isoformat()
        event_id = 'rb'+sha256(key.encode()).hexdigest()
        try:
            await bot.confirm_dialog(update, context, pending)
            assert bot.get_pending_clarification(context,-1,-1) is None, 'Write not verified'
            created = service.events().get(calendarId=bot.GOOGLE_CALENDAR_ID,eventId=event_id).execute()
            assert created['summary']==formatted['title']
            proof['calendar_confirmation_readback'] = True
        finally:
            try:
                service.events().delete(calendarId=bot.GOOGLE_CALENDAR_ID,eventId=event_id).execute()
            except Exception as exc:
                if getattr(getattr(exc,'resp',None),'status',None) not in (404,410):raise
            try:
                tombstone = service.events().get(calendarId=bot.GOOGLE_CALENDAR_ID,eventId=event_id).execute()
                assert tombstone.get('status')=='cancelled'
            except Exception as exc:
                if getattr(getattr(exc,'resp',None),'status',None) not in (404,410):raise
            proof['synthetic_event_removed'] = True
    (root/'dialogue-proof.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(proof,indent=2))

asyncio.run(main())
