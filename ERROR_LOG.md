# Error Log

## Scopo

Questo file raccoglie errori reali emersi nell'uso del bot.

Serve a:

- mantenere uno storico dei casi sbagliati
- trasformare casi reali in regole migliori
- guidare replay, debug e redesign del prompt

## Formato consigliato

Per ogni nuovo errore aggiungere:

- data
- messaggio originale
- output del bot
- comportamento atteso
- tipo di errore
- ipotesi di causa
- stato

## Errori raccolti

### 2026-03-24 - Inversione parte/tribunale

- Messaggio originale:
  - `GUBIOTTI TRIBUNALE ROMA 26.03.2026 h 11.15 sez V 001966/23 Rg`
- Output del bot:
  - parte: `Tribunale di Roma`
  - giudice: `GUBIOTTI`
  - data: `26/03/2026`
  - ora: `11:15`
- Comportamento atteso:
  - parte: `GUBIOTTI`
  - giudice: assente/non specificato
  - location: `Tribunale di Roma, Sez. V`
  - note: includere `001966/23 RG`
- Tipo di errore:
  - interpretazione semantica errata
  - inversione tra parte e contesto giudiziario
- Ipotesi di causa:
  - Claude ha interpretato il primo cognome come giudice
  - il prompt non rafforza abbastanza la regola che il primo cognome e' quasi sempre la parte
  - manca una validazione forte che impedisca di usare "Tribunale di Roma" come parte
- Stato:
  - regole prompt aggiornate
  - validazione post-AI ancora da migliorare

### 2026-03-25 - Inversione parte/tribunale con data aggiornata

- Messaggio originale:
  - `GUBIOTTI TRIBUNALE ROMA 30.03.2026 h 11.15 sez V 001966/23 RG`
- Output del bot:
  - parte: `Tribunale di Roma`
  - giudice: `GUBIOTTI`
  - data: `30/03/2026`
  - ora: `11:15`
- Comportamento atteso:
  - parte: `GUBIOTTI`
  - giudice: assente/non specificato
  - luogo: `Tribunale di Roma, Sez. V`
  - note: includere `001966/23 RG` e il messaggio originale
- Tipo di errore:
  - interpretazione semantica errata
  - inversione tra parte e luogo
- Ipotesi di causa:
  - il parser continua a promuovere il contesto giudiziario a parte
  - manca ancora una barriera abbastanza forte su `Tribunale di <citta'> -> luogo`
- Stato:
  - da verificare sul nuovo parser dopo deploy

### 2026-03-25 - Procedimento usato come parte in contesto Collegio

- Messaggio originale:
  - `COLLEGIO PRES. FARINELLA 18.05.2026 h 12 procedimento n. 44/25`
- Output del bot:
  - parte: `procedimento n. 44/25`
  - giudice: `PRES. FARINELLA`
  - data: `18/05/2026`
  - ora: `12:00`
- Comportamento atteso:
  - parte: assente/non specificata, quindi dubbio oppure nessuna creazione automatica
  - giudice: `Farinella`
  - luogo: `Collegio`
  - note: includere `procedimento n. 44/25` e il messaggio originale
- Tipo di errore:
  - riferimento di procedimento promosso a parte
  - mancata distinzione tra luogo collegiale e giudice
- Ipotesi di causa:
  - il parser non riconosce ancora bene `Collegio Pres. X`
  - `procedimento n.` non viene escluso abbastanza presto dai candidati `parte`
- Stato:
  - da verificare sul nuovo parser dopo deploy

### 2026-03-25 - Collegio riconosciuto senza luogo esplicito

- Messaggio originale:
  - `Bianchi collegio pres. Farinella 18.05.2026 h 12 procedimento n. 44/25`
- Output del bot:
  - parte: `Bianchi`
  - giudice: `Farinella`
  - data: `18/05/2026`
  - ora: `12:00`
- Comportamento atteso:
  - parte: `Bianchi`
  - giudice: `Farinella`
  - luogo: `Collegio`
  - note: includere `procedimento n. 44/25` e il messaggio originale
- Tipo di errore:
  - perdita del luogo
  - mancata valorizzazione del contesto collegiale
- Ipotesi di causa:
  - il parser estrae il giudice ma non materializza `Collegio` come luogo separato
  - `procedimento n.` resta rumore non strutturato invece di finire pulito nelle note
- Stato:
  - da verificare sul nuovo parser dopo deploy
