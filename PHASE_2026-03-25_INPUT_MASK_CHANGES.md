# Phase 2026-03-25 Input Mask Changes

## Scopo

Questa fase introduce la maschera guidata `/1` come secondo canale di input Telegram.

## File toccati

- `bot.py`
- `INPUT_MASK.md`

## Cosa aggiunge

- comando `/1`
- stato temporaneo di compilazione per utente/chat
- bottoni per selezionare il campo da compilare
- creazione evento diretta da maschera

## Cosa non tocca

- parser libero dei messaggi
- Cloudflare logging
- export storico
- flusso dubbi preesistente

## Revert consigliato

Se la maschera crea confusione o interferenze:

1. rimuovere:
   - `CommandHandler('1', handle_mask_start)`
   - `CallbackQueryHandler(handle_mask_callback, pattern=r'^mask:')`
2. rimuovere le helper:
   - `get_mask_store`
   - `get_mask_form`
   - `set_mask_form`
   - `clear_mask_form`
   - `build_mask_keyboard`
   - `render_mask_summary`
   - `build_mask_structured_text`
   - `build_event_from_mask`
3. rimuovere il branch `awaiting_field` in `handle_message()`

