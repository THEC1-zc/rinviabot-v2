# Input Mask

## Scopo

La maschera `/1` introduce un secondo canale di input, guidato e quasi deterministico, accanto al messaggio libero.

Obiettivo:

- ridurre ambiguita' quando Fabio vuole inserire i dati a campi
- mantenere Telegram come unico punto di lavoro
- non sostituire il parser libero, ma affiancarlo

## Trigger

- comando: `/1`

## Campi

- `Parte/Giudice/Domiciliatario`
- `Rinvio`
- `Successo`
- `Altro`

Tutti i campi sono opzionali, ma per creare un evento serve almeno `Rinvio` leggibile come data/ora.

## UX

1. Fabio manda `/1`
2. Il bot mostra una scheda riassuntiva vuota
3. Fabio sceglie un campo con bottone
4. Il messaggio successivo riempie solo quel campo
5. Il bot rimostra la scheda aggiornata
6. Fabio puo' compilare i campi in ordine libero
7. Con `Crea evento` il bot crea direttamente l'evento

## Formati compatti

### Parte/Giudice/Domiciliatario

Ordine fisso:

- `Parte  Giudice  Domiciliatario`

Esempi:

- `Gubiotti  Farinella  Candeloro`
- `Gubiotti  Farinella`
- `Gubiotti`

Separatore preferito:

- spazi doppi tra i blocchi

Se vengono inseriti solo due blocchi, vengono riempiti solo i primi due campi.
Se viene usato un solo spazio, il bot prova comunque a interpretare l'input nel modo piu' sensato.

### Rinvio

Formato compatto:

- `Data Ora Cosa succedera'`

Esempio:

- `30/03/2026 h 11.15 discussione`

Il bot legge data/ora in `Rinvio` e, se presente, mette il resto in `Successo`.

## Logica

- la maschera non passa dal messaggio libero
- costruisce un testo strutturato interno
- quel testo viene letto da Claude
- poi passa comunque dal validatore finale del bot
- questo serve soprattutto per leggere meglio:
  - data
  - ora
  - luogo
  - note
- i campi raccolti dalla maschera restano quindi guidati, ma la lettura finale e' intelligente

## Coesistenza con il flusso libero

- messaggio libero: Claude + validatore + eventuale dubbio
- `/1`: compilazione guidata + creazione quasi deterministica
