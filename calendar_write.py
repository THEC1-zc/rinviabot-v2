"""Deterministic Calendar writes with payload binding and live readback."""
from hashlib import sha256
import json


def insert_verified(service, calendar_id, event, key):
    event = dict(event)
    fingerprint = sha256(json.dumps(event, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    identity = 'rb' + sha256(key.encode()).hexdigest()
    event['id'] = identity
    event['extendedProperties'] = {'private': {'rinviabot_payload_sha256': fingerprint}}

    def get_existing():
        try:
            return service.events().get(calendarId=calendar_id, eventId=identity).execute()
        except Exception as exc:
            if getattr(getattr(exc, 'resp', None), 'status', None) == 404:
                return None
            raise

    found = get_existing()
    if found is None:
        try:
            service.events().insert(calendarId=calendar_id, body=event).execute()
        except Exception:
            # A timeout is not evidence of failure. Reconcile the SAME deterministic ID.
            found = get_existing()
            if found is None: raise
        if found is None: found = get_existing()
    marker = (found or {}).get('extendedProperties', {}).get('private', {}).get('rinviabot_payload_sha256')
    if not found or marker != fingerprint or found.get('status') == 'cancelled':
        raise RuntimeError('calendar_identity_conflict')
    for field in ('summary', 'description', 'location', 'start', 'end'):
        if field in ('summary', 'description', 'location'):
            if found.get(field, '') != event.get(field, ''): raise RuntimeError('calendar_readback_conflict')
        else:
            # The API may canonicalize timezone offsets: compare actual instants.
            from datetime import datetime
            if datetime.fromisoformat(found[field]['dateTime']) != datetime.fromisoformat(event[field]['dateTime']):
                raise RuntimeError('calendar_readback_conflict')
    if found.get('reminders', {}).get('useDefault') != event.get('reminders', {}).get('useDefault'):
        raise RuntimeError('calendar_readback_conflict')
    return found
