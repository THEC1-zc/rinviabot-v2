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
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User


ROME_TZ = pytz.timezone("Europe/Rome")
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
RAW_LOG_PATH = LOG_DIR / "telegram" / "raw" / "messages.jsonl"
EXPORT_DIR = ROOT_DIR / "exports" / "telegram-history"
SESSION_DIR = ROOT_DIR / ".telegram-userbot"


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_directories() -> None:
    for path in (
        RAW_LOG_PATH.parent,
        EXPORT_DIR,
        SESSION_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=False)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json_dumps(payload) + "\n")


def sanitize_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value)
    return cleaned.strip("-") or "telegram-chat"


def stable_trace_id(chat_id: Any, message_id: Any, message_date: str, text: str) -> str:
    payload = f"{chat_id}:{message_id}:{message_date}:{text}"
    digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"hist-{chat_id}-{message_id}-{digest}"


def render_markdown(chat_meta: dict[str, Any], messages: list[dict[str, Any]]) -> str:
    lines = [
        "# Telegram History Export",
        "",
        f"- Chat title: `{chat_meta.get('title') or 'N/A'}`",
        f"- Chat id: `{chat_meta.get('chat_id')}`",
        f"- Exported at: `{chat_meta.get('exported_at')}`",
        f"- Messages: `{len(messages)}`",
        "",
    ]

    for item in messages:
        lines.extend([
            f"## {item['message_id']}",
            "",
            f"- Timestamp: `{item['date_local']}`",
            f"- Sender: `{item.get('sender_name') or 'N/A'}`",
            f"- Sender ID: `{item.get('sender_id') or 'N/A'}`",
            "",
            item.get("text") or "_Messaggio vuoto o non testuale_",
            "",
        ])

    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Esporta la history di una chat Telegram via MTProto e la salva nel formato del repo."
    )
    parser.add_argument("--api-id", type=int, default=int(os.getenv("TELEGRAM_API_ID", "0") or "0"))
    parser.add_argument("--api-hash", default=os.getenv("TELEGRAM_API_HASH", ""))
    parser.add_argument(
        "--chat",
        required=True,
        help="Username, link t.me, invite link o ID numerico della chat",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Numero massimo di messaggi da esportare. 0 = tutta la history disponibile.",
    )
    parser.add_argument(
        "--session",
        default="rinviabot-history",
        help="Nome sessione locale Telethon salvata in .telegram-userbot/",
    )
    parser.add_argument(
        "--append-raw-log",
        action="store_true",
        help="Aggiunge i messaggi esportati a logs/telegram/raw/messages.jsonl",
    )
    return parser.parse_args()


def extract_text(message: Any) -> str:
    text = getattr(message, "message", None)
    if text:
        return str(text)
    return ""


def entity_title(entity: Any) -> str:
    if isinstance(entity, User):
        full_name = " ".join(part for part in [entity.first_name, entity.last_name] if part)
        return full_name or (entity.username or f"user-{entity.id}")
    if isinstance(entity, (Channel, Chat)):
        return getattr(entity, "title", None) or getattr(entity, "username", None) or f"chat-{entity.id}"
    return str(getattr(entity, "id", "unknown"))


def entity_username(entity: Any) -> str:
    return str(getattr(entity, "username", "") or "")


async def resolve_entity(client: TelegramClient, chat_ref: str) -> Any:
    try:
        return await client.get_entity(chat_ref)
    except (ValueError, TypeError):
        pass

    normalized = str(chat_ref).strip()
    numeric_id = None
    if re.fullmatch(r"-?\d+", normalized):
        numeric_id = int(normalized)

    async for dialog in client.iter_dialogs(limit=500):
        if numeric_id is not None and int(dialog.id) == numeric_id:
            return dialog.entity
        if dialog.name and dialog.name.strip().casefold() == normalized.casefold():
            return dialog.entity

    raise ValueError(f"Cannot find any entity corresponding to {chat_ref!r}")


async def export_history(args: argparse.Namespace) -> dict[str, Path]:
    ensure_directories()

    if not args.api_id or not args.api_hash:
        raise RuntimeError("TELEGRAM_API_ID e TELEGRAM_API_HASH sono obbligatori.")

    session_path = SESSION_DIR / args.session
    client = TelegramClient(str(session_path), args.api_id, args.api_hash)
    await client.start()

    try:
        entity = await resolve_entity(client, args.chat)
        chat_title = entity_title(entity)
        chat_id = getattr(entity, "id", args.chat)
        exported_at = utc_now_iso()

        messages: list[dict[str, Any]] = []
        raw_log_records: list[dict[str, Any]] = []

        async for message in client.iter_messages(entity, limit=args.limit or None, reverse=True):
            if not getattr(message, "id", None):
                continue

            sender = await message.get_sender()
            sender_name = entity_title(sender) if sender else ""
            sender_username = entity_username(sender) if sender else ""
            sender_id = getattr(sender, "id", None) if sender else None
            text = extract_text(message)
            date_utc = message.date
            if date_utc.tzinfo is None:
                date_utc = pytz.utc.localize(date_utc)
            date_local = date_utc.astimezone(ROME_TZ)
            ts = date_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
            trace_id = stable_trace_id(chat_id, message.id, ts, text)

            item = {
                "trace_id": trace_id,
                "chat_id": str(chat_id),
                "message_id": message.id,
                "date_utc": ts,
                "date_local": date_local.strftime("%d/%m/%Y %H:%M:%S %Z"),
                "sender_id": sender_id,
                "sender_name": sender_name,
                "sender_username": sender_username,
                "text": text,
                "reply_to_msg_id": getattr(message, "reply_to_msg_id", None),
                "views": getattr(message, "views", None),
                "forwards": getattr(message, "forwards", None),
            }
            messages.append(item)

            raw_log_records.append({
                "ts": ts,
                "trace_id": trace_id,
                "chat_id": str(chat_id),
                "message_id": message.id,
                "user_id": sender_id,
                "username": sender_username or sender_name,
                "text": text,
                "source": "telegram_history_import",
            })

        chat_meta = {
            "chat_id": str(chat_id),
            "title": chat_title,
            "username": entity_username(entity),
            "exported_at": exported_at,
            "message_count": len(messages),
            "source": "telegram-mtproto-userbot",
        }

        base_name = f"{sanitize_component(str(chat_id))}-{sanitize_component(chat_title)}-{datetime.now(ROME_TZ).strftime('%Y%m%d-%H%M%S')}"
        json_path = EXPORT_DIR / f"{base_name}.json"
        jsonl_path = EXPORT_DIR / f"{base_name}.jsonl"
        md_path = EXPORT_DIR / f"{base_name}.md"

        json_path.write_text(
            json.dumps({"chat": chat_meta, "messages": messages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with jsonl_path.open("w", encoding="utf-8") as fh:
            for item in messages:
                fh.write(json_dumps(item) + "\n")
        md_path.write_text(render_markdown(chat_meta, messages), encoding="utf-8")

        if args.append_raw_log:
            for record in raw_log_records:
                append_jsonl(RAW_LOG_PATH, record)

        return {
            "json": json_path,
            "jsonl": jsonl_path,
            "markdown": md_path,
            "raw_log": RAW_LOG_PATH,
        }
    finally:
        await client.disconnect()


def main() -> None:
    args = parse_args()
    result = asyncio.run(export_history(args))
    print(f"JSON export: {result['json']}")
    print(f"JSONL export: {result['jsonl']}")
    print(f"Markdown export: {result['markdown']}")
    if args.append_raw_log:
        print(f"Appended raw log: {result['raw_log']}")


if __name__ == "__main__":
    main()
