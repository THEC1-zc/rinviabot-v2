# Phase 2026-03-25 Ruleset Changes

## Scopo

Questo file segna i cambiamenti introdotti nella fase di consolidamento ruleset, in modo da poterli revertare con facilita'.

## File toccati

- `bot.py`
- `ERROR_LOG.md`
- `RULESET.md`
- `DOUBT_FLOW.md` (documentazione gia' presente, non modificata in questa fase)

## Obiettivo della fase

- passare da fix puntuali su singoli errori a regole generali derivate dall'intero export storico
- spostare parte della responsabilita' dal prompt a validazioni hard del bot
- aumentare i casi che diventano `conferma` invece di generare eventi semanticamente sbagliati

## Modifiche logiche introdotte in `bot.py`

### Nuovi concetti

- riconoscimento esplicito di avvocati/domiciliatari come ruolo separato
- riconoscimento strutturato di riferimenti pratica/procedimento
- riconoscimento di attivita' ricorrenti da salvare in `note`
- controllo di presenza del contesto giudiziario

### Nuove condizioni di dubbio forzato

- parte che sembra luogo
- parte che sembra riferimento pratica
- parte che sembra avvocato
- giudice che sembra avvocato
- giudice che sembra luogo
- luogo che sembra solo riferimento pratica
- pattern `collegio pres. X` incoerente
- `tribunale di X` presente ma `luogo` incoerente
- `corte d'appello` presente ma `luogo` incoerente
- primo candidato parte finito nel campo giudice

### Nuove regole note

- le note includono:
  - riferimenti procedimento
  - attivita' ricorrenti
  - messaggio originale integrale

## Revert consigliato

Se questa fase peggiora troppo il comportamento, il revert piu' pulito e':

1. rimuovere le modifiche a `should_require_confirmation()`
2. rimuovere le helper:
   - `looks_like_lawyer`
   - `has_judicial_context`
   - `extract_reference_segments`
   - `extract_recurring_activities`
3. riportare `normalize_event_notes()` alla versione semplice
4. lasciare invariati logging e flusso dubbi

## Cosa non e' stato toccato in questa fase

- integrazione Cloudflare logging
- export chat
- struttura generale dei log
- stato conversazionale di base dei dubbi
- callback Telegram dei dubbi

