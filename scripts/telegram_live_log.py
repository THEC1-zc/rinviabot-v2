import argparse
import asyncio
import json
import os
import re
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytz
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User


ROME_TZ = pytz.timezone("Europe/Rome")
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
RAW_LOG_PATH = LOG_DIR / "telegram" / "raw" / "messages.jsonl"
SESSION_DIR = ROOT_DIR / ".telegram-userbot"


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_directories() -> None:
    for path in (
        RAW_LOG_PATH.parent,
        SESSION_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def stable_trace_id(chat_id: Any, message_id: Any, message_date: str, text: str) -> str:
    payload = f"{chat_id}:{message_id}:{message_date}:{text}"
    digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"live-{chat_id}-{message_id}-{digest}"


def entity_title(entity: Any) -> str:
    if isinstance(entity, User):
        full_name = " ".join(part for part in [entity.first_name, entity.last_name] if part)
        return full_name or (entity.username or f"user-{entity.id}")
    if isinstance(entity, (Channel, Chat)):
        return getattr(entity, "title", None) or getattr(entity, "username", None) or f"chat-{entity.id}"
    return str(getattr(entity, "id", "unknown"))


def entity_username(entity: Any) -> str:
    return str(getattr(entity, "username", "") or "")


def extract_text(message: Any) -> str:
    text = getattr(message, "message", None)
    if text:
        return str(text)
    return ""


def parse_chat_filters(values: list[str]) -> tuple[set[int], set[str]]:
    ids: set[int] = set()
    names: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized:
            continue
        if re.fullmatch(r"-?\d+", normalized):
            ids.add(int(normalized))
        else:
            names.add(normalized.casefold())
    return ids, names


def already_logged(chat_id: Any, message_id: Any) -> bool:
    if not RAW_LOG_PATH.exists():
        return False

    chat_id_str = str(chat_id)
    message_id_str = str(message_id)
    with RAW_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get("chat_id")) == chat_id_str and str(payload.get("message_id")) == message_id_str:
                return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ascolta i nuovi messaggi Telegram via userbot e li appende ai log del repo."
    )
    parser.add_argument("--api-id", type=int, default=int(os.getenv("TELEGRAM_API_ID", "0") or "0"))
    parser.add_argument("--api-hash", default=os.getenv("TELEGRAM_API_HASH", ""))
    parser.add_argument(
        "--session",
        default="rinviabot-history",
        help="Nome sessione locale Telethon salvata in .telegram-userbot/",
    )
    parser.add_argument(
        "--chat",
        action="append",
        default=[],
        help="Chat da monitorare. Ripetibile: ID numerico, nome o username.",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    ensure_directories()

    if not args.api_id or not args.api_hash:
        raise RuntimeError("TELEGRAM_API_ID e TELEGRAM_API_HASH sono obbligatori.")

    session_path = SESSION_DIR / args.session
    client = TelegramClient(str(session_path), args.api_id, args.api_hash)
    await client.start()

    filter_ids, filter_names = parse_chat_filters(args.chat)

    me = await client.get_me()
    print(f"Sessione attiva come: {entity_title(me)}")
    print(f"Log raw: {RAW_LOG_PATH}")
    if filter_ids or filter_names:
        print(f"Filtri chat attivi: ids={sorted(filter_ids)} names={sorted(filter_names)}")
    else:
        print("Nessun filtro chat: verranno registrati tutti i nuovi messaggi visibili all'account.")

    @client.on(events.NewMessage)
    async def on_new_message(event: events.NewMessage.Event) -> None:
        chat = await event.get_chat()
        sender = await event.get_sender()
        message = event.message

        chat_id = int(getattr(event, "chat_id", 0) or 0)
        chat_name = entity_title(chat) if chat else ""

        if filter_ids and chat_id not in filter_ids:
            return
        if filter_names and chat_name.casefold() not in filter_names and entity_username(chat).casefold() not in filter_names:
            return

        if already_logged(chat_id, message.id):
            return

        date_utc = message.date
        if date_utc.tzinfo is None:
            date_utc = pytz.utc.localize(date_utc)
        ts = date_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        text = extract_text(message)

        payload = {
            "ts": ts,
            "trace_id": stable_trace_id(chat_id, message.id, ts, text),
            "chat_id": str(chat_id),
            "chat_title": chat_name,
            "message_id": message.id,
            "user_id": getattr(sender, "id", None) if sender else None,
            "username": entity_username(sender) if sender else "",
            "sender_name": entity_title(sender) if sender else "",
            "text": text,
            "source": "telegram_live_log",
            "reply_to_msg_id": getattr(message, "reply_to_msg_id", None),
            "logged_at": utc_now_iso(),
        }
        append_jsonl(RAW_LOG_PATH, payload)
        print(
            f"[{datetime.now(ROME_TZ).strftime('%Y-%m-%d %H:%M:%S')}] "
            f"chat={chat_id} msg={message.id} sender={payload['sender_name'] or payload['username']}"
        )

    await client.run_until_disconnected()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
