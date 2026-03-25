#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${TELEGRAM_API_ID:-}" ]]; then
  read -r -p "TELEGRAM_API_ID: " TELEGRAM_API_ID
  export TELEGRAM_API_ID
fi

if [[ -z "${TELEGRAM_API_HASH:-}" ]]; then
  read -r -p "TELEGRAM_API_HASH: " TELEGRAM_API_HASH
  export TELEGRAM_API_HASH
fi

python3 scripts/sync_known_telegram_chats.py
