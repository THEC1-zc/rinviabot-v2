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

- `Parte`
- `Domiciliatario`
- `Giudice`
- `Cosa e' successo`
- `Cosa succedera'`
- `Rinvio`
- `Altro`

Tutti i campi sono opzionali, tranne il fatto che per creare un evento serve almeno `Rinvio` leggibile come data/ora.

## UX

1. Fabio manda `/1`
2. Il bot mostra una scheda riassuntiva vuota
3. Fabio sceglie un campo con bottone
4. Il messaggio successivo riempie solo quel campo
5. Il bot rimostra la scheda aggiornata
6. Fabio puo' compilare i campi in ordine libero
7. Con `Crea evento` il bot crea direttamente l'evento

## Logica

- la maschera non passa dal parser libero
- costruisce un evento in modo diretto
- usa:
  - `parte`
  - `giudice`
  - `rinvio` per data/ora
  - `altro` per tentare un luogo
  - tutti gli altri campi nelle note

## Coesistenza con il flusso libero

- messaggio libero: Claude + validatore + eventuale dubbio
- `/1`: compilazione guidata + creazione quasi deterministica

