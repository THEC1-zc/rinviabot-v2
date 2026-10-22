"""Private durable clarification threads, scoped by chat and human author."""
import json
from pathlib import Path
import sqlite3
import uuid
from contextlib import contextmanager

class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY, chat TEXT NOT NULL, actor TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS active(chat TEXT, actor TEXT, thread TEXT, PRIMARY KEY(chat,actor))')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, chat, actor):
        with self.connect() as db:
            row = db.execute('SELECT t.* FROM threads t JOIN active a ON a.thread=t.id WHERE a.chat=? AND a.actor=? AND t.status="open"', (str(chat), str(actor))).fetchone()
        if row is None: return None
        data = json.loads(row['data']); data['_id'] = row['id']; data['_rev'] = row['revision']
        return data

    def save(self, data):
        identity = data.get('_id') or uuid.uuid4().hex[:12]
        chat, actor = str(data['chat_id']), str(data['user_id'])
        with self.connect() as db:
            existing = db.execute('SELECT chat,actor,revision,status FROM threads WHERE id=?', (identity,)).fetchone()
            if existing and (existing['chat'] != chat or existing['actor'] != actor):
                raise ValueError('conversation_owner_mismatch')
            if existing and (existing['status'] != 'open' or data.get('_rev') != existing['revision']):
                raise ValueError('conversation_revision_conflict')
            revision = existing['revision'] + 1 if existing else 1
            value = dict(data, _id=identity, _rev=revision)
            db.execute('INSERT INTO threads VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,status=excluded.status,data=excluded.data', (identity, chat, actor, revision, 'open', json.dumps(value, ensure_ascii=False)))
            db.execute('INSERT INTO active VALUES(?,?,?) ON CONFLICT(chat,actor) DO UPDATE SET thread=excluded.thread', (chat, actor, identity))
        data.update(_id=identity, _rev=revision)
        return data

    def close(self, chat, actor):
        with self.connect() as db:
            row = db.execute('SELECT thread FROM active WHERE chat=? AND actor=?', (str(chat), str(actor))).fetchone()
            if row: db.execute('UPDATE threads SET status="closed" WHERE id=?', (row['thread'],))
            db.execute('DELETE FROM active WHERE chat=? AND actor=?', (str(chat), str(actor)))

    def park(self, chat, actor):
        with self.connect() as db:
            db.execute('DELETE FROM active WHERE chat=? AND actor=?', (str(chat), str(actor)))

    def list_open(self, chat, actor):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM threads WHERE chat=? AND actor=? AND status="open" ORDER BY rowid DESC LIMIT 20', (str(chat), str(actor))).fetchall()
        return [dict(json.loads(r['data']), _id=r['id'], _rev=r['revision']) for r in rows]

    def select(self, identity, chat, actor):
        with self.connect() as db:
            row = db.execute('SELECT id FROM threads WHERE id=? AND chat=? AND actor=? AND status="open"', (identity, str(chat), str(actor))).fetchone()
            if row is None: return None
            db.execute('INSERT INTO active VALUES(?,?,?) ON CONFLICT(chat,actor) DO UPDATE SET thread=excluded.thread', (str(chat), str(actor), identity))
        return self.get(chat, actor)
