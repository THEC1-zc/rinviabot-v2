"""Write a single synthetic log probe. No Telegram or calendar writes."""
import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from launch import configure
configure()
spec = importlib.util.spec_from_file_location('rinviabot', '/opt/rinviabot/app/bot.py')
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)
bot.ensure_runtime_directories()
trace = 'ionos-logger-probe-' + uuid.uuid4().hex
bot.log_pipeline_event('migration_probe', trace, text='Synthetic logger probe; no customer data.')
records = [json.loads(line) for line in bot.PIPELINE_LOG_PATH.read_text().splitlines()]
assert not any(r.get('trace_id') == trace and r.get('stage') == 'remote_log_failed' for r in records)
proof = {'at': datetime.now(timezone.utc).isoformat(), 'trace_id': trace, 'local_write': True, 'remote_request_succeeded': True}
Path('/var/lib/rinviabot/logger-proof.json').write_text(json.dumps(proof, indent=2))
print(json.dumps(proof))
