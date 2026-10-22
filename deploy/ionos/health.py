"""Read-only provider checks; never calls getUpdates or changes the webhook."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
from launch import configure
from telegram import Bot
from google.oauth2 import service_account
from googleapiclient.discovery import build

config = configure()
result = {'at': datetime.now(timezone.utc).isoformat()}

async def main():
    async with Bot(config['TELEGRAM_BOT_TOKEN']) as bot:
        me = await bot.get_me()
        wh = await bot.get_webhook_info()
        result['telegram'] = {'bot': me.username, 'webhook_empty': not bool(wh.url), 'pending': wh.pending_update_count}
        assert me.username == 'rinviav2bot' and not wh.url

asyncio.run(main())
creds = service_account.Credentials.from_service_account_info(json.loads(config['GOOGLE_SERVICE_ACCOUNT_JSON']), scopes=['https://www.googleapis.com/auth/calendar.readonly'])
service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
service.events().list(calendarId=config['GOOGLE_CALENDAR_ID'], maxResults=1, fields='kind').execute()
result['calendar_read'] = True
from urllib.parse import urlsplit, urlunsplit
u = urlsplit(config['REMOTE_LOG_ENDPOINT'])
health_url = urlunsplit((u.scheme, u.netloc, '/health', '', ''))
with urllib.request.urlopen(urllib.request.Request(health_url, headers={'User-Agent': 'Rinviabot/1.0'}), timeout=15) as response:
    logger_health = json.load(response)
assert logger_health.get('ok')
result['remote_logger_health'] = True
req = urllib.request.Request('https://api.anthropic.com/v1/models', headers={'x-api-key': config['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'})
with urllib.request.urlopen(req, timeout=20) as response:
    data = json.load(response)
result['anthropic_model_available'] = any(m['id'] == config['ANTHROPIC_MODEL'] for m in data['data'])
assert result['anthropic_model_available']
Path('/var/lib/rinviabot/health-proof.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
