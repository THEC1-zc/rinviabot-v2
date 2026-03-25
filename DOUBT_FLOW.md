# Doubt Flow

## Obiettivo

Quando il bot ha un dubbio, non deve fermarsi in una conversazione morta.

Deve invece aprire un flusso guidato, in cui Fabio possa:

- confermare
- correggere
- riscrivere
- annullare

e il sistema possa poi riprendere il messaggio originale e arrivare a una decisione finale.

## Problema attuale

Oggi il bot puo' rispondere con un dubbio, ma non gestisce davvero il seguito.

Se Fabio risponde in modo secco:

- `si`
- `no`
- `a`
- `b`

il bot tende a trattare quella risposta come un nuovo messaggio autonomo.

Quindi il ciclo non si chiude.

## Flusso desiderato

```text
Messaggio utente
  -> Claude interpreta
  -> Bot valuta rischio
  -> Se dubbio:
       - salva stato pending
       - mostra dubbio guidato
       - mostra bottoni
  -> Utente:
       - conferma
       - corregge
       - riscrive
       - annulla
  -> Bot riprende il pending
  -> Claude rilegge con contesto
  -> Bot crea evento oppure formula un nuovo dubbio piu' mirato
```

## Stati del flusso

Per ogni dubbio aperto, serve una memoria breve.

## Pending clarification

Campi minimi da memorizzare:

- `pending_id`
- `trace_id`
- `chat_id`
- `message_id_originale`
- `user_id`
- `created_at`
- `expires_at`
- `status`
- `original_message`
- `analysis`
- `parsed_data`
- `reason`
- `suggested_interpretation`
- `pending_type`

### pending_type

Valori iniziali utili:

- `generic_confirmation`
- `missing_party`
- `missing_judge`
- `role_conflict`
- `past_date`
- `multi_event_ambiguity`

## Azioni utente

Il bot deve offrire 4 scelte principali.

### 1. Conferma

Bottone:

- `✅ Conferma`

Significato:

- l'interpretazione proposta va bene
- il bot puo' procedere con la creazione dell'evento

### 2. Correggi

Bottone:

- `✏️ Correggi`

Significato:

- Fabio vuole correggere uno o piu' campi

Comportamento:

- il bot risponde chiedendo una correzione breve
- esempio:
  - `Scrivimi solo la correzione, ad esempio: parte=Serafini, giudice=Sodani, luogo=Tribunale Roma, data=26/03/2026, ora=11:15`

### 3. Riscrivi

Bottone:

- `🔁 Riscrivi`

Significato:

- Fabio preferisce riscrivere il messaggio da capo

Comportamento:

- il bot attende un nuovo messaggio
- il nuovo messaggio resta legato al pending
- Claude lo rilegge insieme al contesto del caso aperto

### 4. Non creare

Bottone:

- `❌ Non creare`

Significato:

- il bot deve chiudere il dubbio senza creare evento

Questo bottone e' molto utile per evitare esecuzioni indesiderate.

## Formato del messaggio di dubbio

Il dubbio deve essere leggibile in pochi secondi.

Formato proposto:

```text
Ho bisogno di una conferma prima di creare l'evento.

Lettura proposta:
- Parte: GUBIOTTI
- Giudice: non rilevato
- Luogo: Tribunale di Roma, Sez. V
- Data: 26/03/2026
- Ora: 11:15

Punto incerto:
- Non trovo un giudice esplicito nel messaggio

Scegli:
- Conferma
- Correggi
- Riscrivi
- Non creare
```

## Gestione delle azioni

### Caso A: Conferma

Input:

- click su `✅ Conferma`

Azione:

- usa l'interpretazione salvata
- crea l'evento
- chiude il pending

### Caso B: Correggi

Input:

- click su `✏️ Correggi`
- poi testo utente

Azione:

- Claude riceve:
  - messaggio originale
  - interpretazione precedente
  - motivo del dubbio
  - correzione utente
- produce un nuovo payload strutturato
- il bot rivalida

### Caso C: Riscrivi

Input:

- click su `🔁 Riscrivi`
- poi nuovo messaggio utente

Azione:

- Claude riceve:
  - messaggio originale
  - nuovo testo utente
  - informazione che si tratta della riscrittura dello stesso caso
- produce nuova interpretazione

### Caso D: Non creare

Input:

- click su `❌ Non creare`

Azione:

- il pending viene chiuso
- il bot risponde con conferma di annullamento

## Log necessari

Ogni flusso dubbio deve produrre log chiari.

Eventi aggiuntivi da introdurre:

- `clarification_opened`
- `clarification_button_clicked`
- `clarification_text_received`
- `clarification_resolved`
- `clarification_cancelled`

## Dati da passare a Claude nel secondo giro

Nel secondo giro, Claude non deve ripartire alla cieca.

Input consigliato:

- `original_message`
- `previous_interpretation`
- `reason_for_doubt`
- `user_action`
- `user_followup_text` se presente

## Regola importante

Il prompt non va "corretto" dinamicamente in modo libero.

Quello che cambia e':

- il contesto di input
- il tipo di richiesta

Questa scelta rende il sistema piu' stabile e piu' debuggabile.

## Struttura tecnica consigliata

### In memory, per iniziare

Per partire si puo' usare:

- `context.bot_data["pending_clarifications"]`

chiave:

- `chat_id`
- oppure `chat_id:user_id`

### Persistenza futura

Poi si puo' passare a:

- file locale JSON
- sqlite
- D1 / storage remoto

## Prima implementazione consigliata

### Fase 1

- bottoni Telegram inline
- pending in memoria
- supporto a:
  - `Conferma`
  - `Riscrivi`
  - `Non creare`

### Fase 2

- aggiunta di `Correggi`
- parsing della correzione testuale

### Fase 3

- log completi del flusso dubbio
- replay dei casi dubbiosi

## Casi da coprire subito

- parte mancante
- giudice mancante
- parte/giudice invertiti
- luogo scambiato per giudice
- data nel passato
- messaggio con piu' eventi

## Risultato atteso

Alla fine del refactor, un dubbio non deve piu' bloccare la pipeline.

Deve diventare:

- un caso guidato
- risolvibile in chat
- tracciato nei log
- riutilizzabile per migliorare il sistema
