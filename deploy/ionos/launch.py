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

    os.environ['RINVIABOT_STATE_DIR'] = '/var/lib/rinviabot'
    auth_path = Path(os.environ['CREDENTIALS_DIRECTORY']) / 'llm-auth.json'
    if auth_path.exists():
        auth = json.loads(auth_path.read_text())
        runtime = Path(os.environ.get('RINVIABOT_LLM_RUNTIME', '/run/rinviabot'))
        codex_home = runtime / 'codex-home'
        agy_home = runtime / 'agy-home'
        agy_config = agy_home / '.gemini' / 'antigravity-cli'
        codex_home.mkdir(parents=True, exist_ok=True, mode=0o700)
        agy_config.mkdir(parents=True, exist_ok=True, mode=0o700)
        # No QWE/STUDIO config, MCP servers, tools or history are copied.
        if not (codex_home / 'auth.json').exists():
            (codex_home / 'auth.json').write_text(auth['codex_auth'])
        (codex_home / 'auth.json').chmod(0o600)
        (codex_home / 'config.toml').write_text('model = "gpt-6.1-sol"\nmodel_reasoning_effort = "low"\nweb_search = "disabled"\n[features]\nshell_tool = false\nunified_exec = false\napps = false\nbrowser_use = false\nhooks = false\n')
        if not (agy_config / 'antigravity-oauth-token').exists():
            (agy_config / 'antigravity-oauth-token').write_text(auth['agy_token'])
        (agy_config / 'antigravity-oauth-token').chmod(0o600)
        (agy_config / 'installation_id').write_text(auth['agy_installation_id'])
        (agy_config / 'settings.json').write_text('{}')

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
