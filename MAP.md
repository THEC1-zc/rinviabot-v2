# RinviaBot Map

## Obiettivo

Questo file serve come mappa operativa del progetto:

- ricordare la struttura del bot
- capire rapidamente dove intervenire
- pianificare refactor, debug e revisioni AI

La sorgente runtime canonica del bot e':

- `bot.py`

## Struttura attuale del repo

- `bot.py`: logica principale del bot Telegram, parsing AI, validazione, creazione eventi
- `requirements.txt`: dipendenze Python
- `Procfile`: entrypoint deploy
- `README.md`: documentazione utente/deploy
- `AISYNC.md`: note operative condivise
- `files/`: asset di supporto legacy

## Flusso generale

```text
Telegram message
  -> handle_message()
  -> parse_message_with_ai()
    -> analisi preliminare testo
    -> prompt Claude
    -> parse JSON AI
    -> validazione/normalizzazione
    -> eventuale richiesta conferma
  -> se rinvio:
    -> format_calendar_event()
    -> create_google_calendar_event()
  -> risposta all'utente
```

## Mappa delle funzioni

### Setup e configurazione

- `get_google_calendar_service()`
  - inizializza il client Google Calendar da `GOOGLE_SERVICE_ACCOUNT_JSON`
  - dipende da `SCOPES`, `GOOGLE_CALENDAR_ID`
  - rischio: errori env/configurazione bloccano la creazione evento

- `main()`
  - bootstrap del bot Telegram
  - registra handler messaggi ed errori
  - decide tra webhook e polling
  - punto critico per deploy e avvio runtime

### Preprocessing del testo

- `normalize_whitespace(value)`
  - compatta spazi e trim

- `normalize_message_text(message_text)`
  - normalizza newline
  - converte separatori multipli in `----`
  - corregge alcuni typo numerici OCR/manuali

- `split_message_blocks(message_text)`
  - separa blocchi multipli di messaggi/eventi

- `extract_dates_from_text(message_text)`
  - estrae date candidate

- `extract_times_from_text(message_text)`
  - estrae ore candidate

- `build_message_analysis(message_text)`
  - crea una vista tecnica del messaggio
  - include blocchi, date, ore, indizi di udienza e non-udienza

### Parsing AI e post-processing

- `extract_json_object(raw_text)`
  - prova a recuperare un JSON valido dalla risposta AI
  - utile se Claude risponde con testo extra o markdown

- `normalize_judge_name(value)`
  - standardizza il nome del giudice
  - usa mapping di giudici noti e typo comuni

- `normalize_event_date(date_value)`
  - porta la data in formato `DD/MM/YYYY`

- `normalize_event_time(time_value)`
  - porta l'ora in formato `HH:MM`
  - default `09:00` se manca

- `infer_tipo_from_text(message_text)`
  - fallback euristico per classificare il messaggio
  - tipi: `rinvio`, `sentenza`, `riserva`, `trattenuta`, `nota`

- `validate_and_normalize_parsed_data(parsed_data, original_message)`
  - rende coerente il JSON AI
  - normalizza eventi
  - elimina campi inconsistenti
  - crea fallback se il parser AI non e' affidabile

- `should_require_confirmation(parsed_data, analysis)`
  - decide se chiedere conferma prima di creare l'evento
  - usa confidence, warning, blocchi multipli e qualita' estrazione

- `build_confirmation_from_events(parsed_data, reason)`
  - costruisce un payload `tipo=conferma` a partire dagli eventi letti

- `parse_message_with_ai(message_text)`
  - orchestratore del parsing AI
  - costruisce il prompt
  - invia a Claude
  - recupera JSON
  - valida e normalizza
  - puo' trasformare l'output in richiesta conferma

### Calendar

- `format_calendar_event(evento)`
  - converte un evento logico in struttura pronta per Google Calendar
  - imposta titolo, data/ora, location e descrizione

- `create_google_calendar_event(event_data)`
  - inserisce l'evento nel calendario
  - restituisce il payload creato da Google o `None`

### Runtime Telegram

- `handle_message(update, context)`
  - funzione centrale del bot
  - legge il messaggio
  - chiama il parsing AI
  - gestisce i casi:
    - `sentenza`
    - `riserva`
    - `trattenuta`
    - `nota`
    - `conferma`
    - `data_passata`
    - `rinvio`
  - crea uno o piu' eventi e risponde in chat

- `error_handler(update, context)`
  - fallback per errori runtime

## Tipi logici gestiti dal parser

- `rinvio`
  - uno o piu' eventi da creare

- `sentenza`
  - nessun evento

- `riserva`
  - nessun evento

- `trattenuta`
  - nessun evento

- `nota`
  - nessun evento

- `conferma`
  - l'AI ha un dubbio e chiede conferma all'utente

- `data_passata`
  - la data letta e' nel passato e va chiarita

## Stato attuale: criticita' note

### 1. Flusso conferme incompleto

Il bot sa chiedere conferma, ma non ha ancora una vera gestione dello stato conversazionale:

- non salva il contesto del dubbio
- non aggancia la risposta successiva dell'utente alla richiesta precedente
- `si/no` e `a/b` vengono trattati come nuovi messaggi normali

Impatto:

- i casi ambigui non si chiudono correttamente

### 2. UI messaggi dubbio da ripensare

Attualmente i dubbi vengono mostrati come testo semplice.
Serve un nuovo formato piu' chiaro, ad esempio:

- motivo del dubbio
- lettura proposta
- azione richiesta all'utente
- possibili risposte ammesse

### 3. Parsing AI molto carico nel prompt

`parse_message_with_ai()` contiene molte responsabilita':

- prompting
- parsing risposta
- fallback
- normalizzazione
- logica di sicurezza

Impatto:

- manutenzione difficile
- debug piu' lento
- alto rischio di regressioni quando cambiamo regole AI

## Piano tecnico consigliato

### Fase 1: pulizia e controllo

- rivedere `handle_message()`
- mappare input/output di ogni funzione
- aggiungere log migliori
- definire una strategia test minima

### Fase 2: stato conversazionale

- introdurre memoria breve per conferme e date passate
- associare messaggio dubbio -> risposta utente
- gestire `si/no`, `a/b`, correzioni testuali

### Fase 3: revisione AI

- riscrivere e modularizzare il prompt
- separare regole hard da istruzioni “soft”
- coprire edge case reali
- definire formato JSON piu' robusto

### Fase 4: UX dei dubbi

- nuovo formato messaggi dubbio
- testo piu' chiaro e piu' guidato
- magari pulsanti in futuro, se utile

## Checklist di revisione futura

- parsing date senza anno
- date nel passato
- ore mancanti
- piu' eventi nello stesso messaggio
- avvocato scambiato per giudice
- cognomi stranieri
- typo numerici
- messaggi non-udienza classificati male
- evento calendario duplicato
- risposta dell'utente ai dubbi

## Regola pratica di lavoro

Quando modifichiamo il bot, teniamo separati questi livelli:

1. preprocessing del testo
2. decisione AI
3. validazione hard-coded
4. UX conversazionale
5. integrazione Google Calendar

Se mischiamo questi livelli nello stesso punto del codice, il debug diventa molto piu' difficile.
