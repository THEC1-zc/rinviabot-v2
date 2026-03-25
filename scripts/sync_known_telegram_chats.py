import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
from telethon import TelegramClient

from export_telegram_history import (
    EXPORT_DIR,
    RAW_LOG_PATH,
    ROME_TZ,
    SESSION_DIR,
    append_jsonl,
    entity_title,
    entity_username,
    ensure_directories,
    extract_text,
    json_dumps,
    render_markdown,
    resolve_entity,
    sanitize_component,
    stable_trace_id,
    utc_now_iso,
)


KNOWN_CHATS = [
    "-5011341129",
    "-1003792884377",
]


def load_logged_message_keys() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if not RAW_LOG_PATH.exists():
        return keys

    with RAW_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            keys.add((str(payload.get("chat_id")), str(payload.get("message_id"))))
    return keys


async def export_chat(client: TelegramClient, chat_ref: str, logged_keys: set[tuple[str, str]]) -> dict[str, Any]:
    entity = await resolve_entity(client, chat_ref)
    chat_title = entity_title(entity)
    chat_id = str(getattr(entity, "id", chat_ref))
    exported_at = utc_now_iso()

    messages: list[dict[str, Any]] = []
    new_records: list[dict[str, Any]] = []

    async for message in client.iter_messages(entity, reverse=True):
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
            "chat_id": chat_id,
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

        key = (chat_id, str(message.id))
        if key not in logged_keys:
            new_records.append({
                "ts": ts,
                "trace_id": trace_id,
                "chat_id": chat_id,
                "message_id": message.id,
                "user_id": sender_id,
                "username": sender_username or sender_name,
                "text": text,
                "source": "telegram_history_import",
            })
            logged_keys.add(key)

    for record in new_records:
        append_jsonl(RAW_LOG_PATH, record)

    chat_meta = {
        "chat_id": chat_id,
        "title": chat_title,
        "username": entity_username(entity),
        "exported_at": exported_at,
        "message_count": len(messages),
        "source": "telegram-mtproto-userbot",
    }

    base_name = (
        f"{sanitize_component(chat_id)}-"
        f"{sanitize_component(chat_title)}-"
        f"{datetime.now(ROME_TZ).strftime('%Y%m%d-%H%M%S')}"
    )
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

    return {
        "chat_id": chat_id,
        "title": chat_title,
        "total_messages": len(messages),
        "new_messages_appended": len(new_records),
        "json": str(json_path),
        "jsonl": str(jsonl_path),
        "markdown": str(md_path),
    }


async def main_async() -> None:
    ensure_directories()

    api_id = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        raise RuntimeError("TELEGRAM_API_ID e TELEGRAM_API_HASH sono obbligatori.")

    session_path = SESSION_DIR / "rinviabot-history"
    client = TelegramClient(str(session_path), api_id, api_hash)
    await client.start()
    try:
        logged_keys = load_logged_message_keys()
        results = []
        for chat_ref in KNOWN_CHATS:
            results.append(await export_chat(client, chat_ref, logged_keys))
        print(json.dumps({"synced_at": utc_now_iso(), "results": results}, ensure_ascii=False, indent=2))
    finally:
        await client.disconnect()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
