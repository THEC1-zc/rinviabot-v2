"""Subscription-first extraction. Child CLIs receive no service/API credentials."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

ALLOWED_TYPES = {'rinvio', 'conferma', 'data_passata', 'sentenza', 'riserva', 'trattenuta', 'nota'}
MAX_OUTPUT = 128_000


def validated_text(raw):
    if not isinstance(raw, str) or len(raw.encode()) > MAX_OUTPUT:
        raise ValueError('invalid_output_size')
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    data = json.loads(text)
    if not isinstance(data, dict) or data.get('tipo') not in ALLOWED_TYPES:
        raise ValueError('invalid_response_contract')
    if 'eventi' in data and (not isinstance(data['eventi'], list) or any(not isinstance(e, dict) for e in data['eventi'])):
        raise ValueError('invalid_events')
    if data['tipo'] == 'rinvio' and not data.get('eventi'):
        raise ValueError('empty_rinvio')
    return json.dumps(data, ensure_ascii=False)


def child_env(provider):
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'TZ', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if k in os.environ}
    root = Path(os.environ.get('RINVIABOT_LLM_RUNTIME', '/run/rinviabot'))
    env['HOME'] = str(root / 'agy-home' if provider == 'argon' else root / 'codex-home')
    env['CODEX_HOME'] = str(root / 'codex-home')
    env['AGY_CLI_DISABLE_AUTO_UPDATE'] = '1'
    return env


def run_process(command, prompt, env, timeout):
    cwd = Path(os.environ.get('RINVIABOT_LLM_WORKDIR', '/var/lib/rinviabot/llm-work'))
    cwd.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=output, stderr=errors,
                                text=True, cwd=cwd, env=env, start_new_session=True)
        try:
            proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise RuntimeError('provider_timeout') from None
        if proc.returncode:
            raise RuntimeError('provider_process_failed')
        if output.tell() > MAX_OUTPUT:
            raise RuntimeError('provider_output_too_large')
        output.seek(0)
        return output.read().decode('utf-8')


def codex(prompt):
    with tempfile.TemporaryDirectory(prefix='rinviabot-answer-') as tmp:
        answer = Path(tmp) / 'answer.json'
        command = [os.environ.get('RINVIABOT_CODEX_BIN', '/opt/rinviabot/toolchain/node_modules/.bin/codex'), 'exec',
                   '--model', 'gpt-6.1-sol', '-c', 'model_reasoning_effort="low"',
                   '--ephemeral', '--skip-git-repo-check', '--sandbox', 'read-only',
                   '-c', 'features.shell_tool=false', '-c', 'features.unified_exec=false',
                   '-c', 'features.apps=false', '-c', 'features.browser_use=false',
                   '-c', 'features.hooks=false', '-c', 'web_search="disabled"',
                   '--output-last-message', str(answer), '-']
        run_process(command, prompt, child_env('codex'), int(os.environ.get('RINVIABOT_CODEX_TIMEOUT', '75')))
        if not answer.is_file() or answer.stat().st_size > MAX_OUTPUT:
            raise RuntimeError('codex_output_unavailable')
        return validated_text(answer.read_text())


def argon(prompt):
    command = [os.environ.get('RINVIABOT_AGY_BIN', '/usr/local/bin/agy'), '-p', prompt,
               '--model', os.environ.get('RINVIABOT_ARGON_MODEL', 'gemini-4-argon-low'),
               '--effort', 'low', '--mode', 'plan', '--sandbox', '--disable-slash-commands',
               '--output-format', 'json', '--print-timeout', '75s']
    raw = run_process(command, prompt, child_env('argon'), int(os.environ.get('RINVIABOT_ARGON_TIMEOUT', '80')))
    envelope = json.loads(raw)
    if isinstance(envelope, dict) and (envelope.get('is_error') or envelope.get('status') not in (None, 'SUCCESS', 'success')):
        raise RuntimeError('argon_error')
    if isinstance(envelope, dict) and 'tipo' in envelope:
        return validated_text(json.dumps(envelope))
    result = (envelope.get('response') or envelope.get('result')) if isinstance(envelope, dict) else None
    if isinstance(result, str):
        return validated_text(result)
    raise ValueError('argon_output_unavailable')


def complete_json(prompt, *, api_client=None, audit=None):
    if not isinstance(prompt, str) or not prompt or len(prompt.encode()) > 96_000:
        raise ValueError('invalid_prompt')
    root = Path(__file__).parent
    rules = (root / 'reading/SKILL.md').read_text()
    references = json.loads((root / 'reference/people.json').read_text())
    profiles = [{k:p[k] for k in ('name','surname','role','office')} for p in references['magistrates']]
    prompt = (rules + '\n\nRiferimenti di nomi e ruoli (non prova di identità):\n' +
              json.dumps({'magistrati': profiles, 'colleghi': references['colleague_names_from_studio']}, ensure_ascii=False) + '\n\n' + prompt)
    prompt = ('Estrai esclusivamente dai dati forniti. Non usare strumenti, file, web o comandi. '
              'Restituisci SOLO il JSON richiesto, senza markdown.\n\n' + prompt)
    def emit(provider, status, elapsed):
        if audit:
            try: audit(provider, status, elapsed)
            except Exception: pass

    for provider, call in [('codex', codex), ('argon', argon), ('claude_api', None)]:
        started = time.monotonic()
        try:
            if provider == 'claude_api':
                if api_client is None:
                    raise RuntimeError('api_fallback_not_configured')
                message = api_client.messages.create(model=os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
                                                     max_tokens=2200, messages=[{'role': 'user', 'content': prompt}])
                response = validated_text(message.content[0].text)
            else:
                response = call(prompt)
            emit(provider, 'success', round(time.monotonic() - started, 3))
            return response
        except Exception as exc:
            # Exception text can contain provider payloads: retain category only.
            emit(provider, 'failed:' + type(exc).__name__, round(time.monotonic() - started, 3))
    raise RuntimeError('all_llm_providers_failed')
