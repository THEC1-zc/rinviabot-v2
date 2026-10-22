"""Root-only stop hook: preserve refreshed CLI login in an encrypted credential."""
import json
import os
from pathlib import Path
import stat
import subprocess

credential = Path('/etc/rinviabot/llm-auth.cred')
root = Path('/run/rinviabot')
paths = {'codex_auth': root / 'codex-home/auth.json',
         'agy_token': root / 'agy-home/.gemini/antigravity-cli/antigravity-oauth-token'}
if not all(p.exists() for p in paths.values()):
    raise SystemExit(0)
try:
    original = subprocess.run(['systemd-creds', 'decrypt', '--name=llm-auth.json', str(credential), '-'],
                              capture_output=True, check=True).stdout
    data = json.loads(original)
    for key, path in paths.items():
        # Never follow a service-user symlink with root privileges.
        if any(parent.is_symlink() for parent in (path, *path.parents)) or not path.resolve().is_relative_to(root):
            raise ValueError('unsafe_auth_path')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size > 64000:
                raise ValueError('invalid_auth_file')
            raw = os.read(fd, 64001).decode()
            if not isinstance(json.loads(raw), dict):
                raise ValueError('invalid_auth_json')
            data[key] = raw
        finally:
            os.close(fd)
    result = subprocess.run(['systemd-creds', 'encrypt', '--name=llm-auth.json', '--with-key=host', '-', '-'],
                            input=json.dumps(data).encode(), capture_output=True, check=True).stdout
    temp = credential.with_name('llm-auth.next.cred')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(result)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, credential)
except Exception:
    raise SystemExit('Rinviabot CLI credential refresh backup failed; original encrypted credential retained') from None
