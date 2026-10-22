"""Load systemd's decrypted in-memory credential and run the unchanged bot."""
import json
import logging
import os
from pathlib import Path
import runpy


def configure():
    config = json.loads((Path(os.environ['CREDENTIALS_DIRECTORY']) / 'rinviabot.json').read_text())
    for key, value in config.items():
        os.environ[key] = value
    # Keep the Render URL in the encrypted original, but use outbound polling here.
    os.environ.pop('WEBHOOK_URL', None)
    os.environ['RINVIABOT_LOG_DIR'] = '/var/lib/rinviabot/logs'
    os.environ['RINVIABOT_SOURCE'] = 'rinviabot-ionos'
    secrets = [config.get(k, '') for k in ('TELEGRAM_BOT_TOKEN', 'ANTHROPIC_API_KEY', 'REMOTE_LOG_TOKEN', 'WORKDB_API_KEY')]

    class RedactedFormatter(logging.Formatter):
        def format(self, record):
            value = super().format(record)
            for secret in secrets:
                if secret:
                    value = value.replace(secret, '[REDACTED]')
            return value

    handler = logging.StreamHandler()
    handler.setFormatter(RedactedFormatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in ('httpx', 'httpcore', 'googleapiclient.discovery_cache'):
        logging.getLogger(name).setLevel(logging.WARNING)
    return config


if __name__ == '__main__':
    configure()
    runpy.run_path('/opt/rinviabot/app/bot.py', run_name='__main__')
