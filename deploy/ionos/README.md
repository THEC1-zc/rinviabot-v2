# Rinviabot su IONOS

Migrazione verificata il 22 ottobre 2026. Bot Telegram `rinviav2bot` e calendario
Google invariati. Ricezione in polling, senza porta pubblica aggiuntiva.

## Percorsi e isolamento

- Codice e venv: `/opt/rinviabot/app`, `/opt/rinviabot/venv`.
- Utente e unit dedicati: `rinviabot`, `rinviabot.service`.
- Stato, log, export e ricevute private: `/var/lib/rinviabot` (0700).
- Credenziale cifrata: `/etc/rinviabot/runtime.cred`; caricamento systemd
  `LoadCredentialEncrypted` con nome `rinviabot.json`. Il launcher legge il JSON
  dal filesystem credenziali runtime, elimina solo `WEBHOOK_URL` nell'ambiente del
  processo e imposta directory log e origine `rinviabot-ionos`.
- Originali conservati: `/etc/rinviabot/render-original.cred` e
  `/opt/rinviabot/app/bot.render-original.py` (commit Render `a58f569`).
- Segreti recuperabili dal vault centrale Mac:
  `vault://rinviabot/production/render-env` (export originale, testo dotenv) e
  `vault://rinviabot/production/ionos-config` (JSON operativo corretto).
  Non stampare i valori. La cifratura systemd usa la chiave host: per il ripristino
  su una nuova macchina usare il JSON del vault e ricifrarlo sul nuovo host.

Accesso esclusivamente tramite
`/Users/fabio/workspace/STUDIO/scripts/vps-ssh.sh`, dopo lettura di
`/Users/fabio/workspace/STUDIO/docs/accesso-vps-condiviso.md`.
Non gestire le unit QWE/STUDIO. Il launcher conserva l'integrazione Anthropic
preesistente a consumo, senza introdurre altre chiavi LLM o cambiare provider.

## Stato e controlli

Comandi remoti, da passare come argomento allo script SSH:

```sh
systemctl show rinviabot.service -p ActiveState -p SubState -p NRestarts -p MemoryCurrent
systemctl is-enabled rinviabot.service
```

Il controllo provider non consuma aggiornamenti Telegram e non modifica il
calendario:

```sh
systemd-run --unit=rinviabot-health --wait --collect --pipe \
  -p User=rinviabot -p Group=rinviabot -p WorkingDirectory=/var/lib/rinviabot \
  -p LoadCredentialEncrypted=rinviabot.json:/etc/rinviabot/runtime.cred \
  -p UMask=0077 /opt/rinviabot/venv/bin/python /opt/rinviabot/app/health.py
```

`preflight.py` **scrive** due eventi sintetici nel calendario reale, li rilegge e
li elimina; chiama Claude a consumo. Eseguirlo solo per un collaudo autorizzato.
Conserva prima gli ID in `preflight-test-events.json` per recuperare una pulizia
interrotta. `logging_probe.py` scrive un solo log sintetico locale e remoto.
Le ricevute sono in `preflight-proof.json`, `health-proof.json`,
`logger-proof.json`. La loro esistenza da sola non prova lo stato attuale.

Non chiamare `getUpdates` in parallelo al servizio per controllarlo. Non invocare
`main()` o `run_polling()` durante un controllo importando il modulo. I log
possono contenere dati clienti: restano privati sulla VPS, non nel repository.

## Esito della migrazione

Alle 21:26 circa Europe/Rome Render è stato sospeso, poi è partito il polling VPS
con cancellazione del webhook senza scartare gli aggiornamenti pendenti.
Rilevati sul nuovo runtime il comando `/1`, messaggi reali, risposte Claude,
risposte Telegram e interazione con pulsanti di chiarimento.

Collaudo live riuscito: token bot; estrazione Claude; inserimento/rilettura di
udienza da un'ora senza promemoria; turno giornaliero; eliminazione verificata
degli eventi sintetici. Dopo la correzione logging, salute provider e scrittura
log nuovamente verificate. Riavvio systemd riuscito e avvio automatico abilitato;
nessun reboot dell'host eseguito. Circa 52–67 MiB residenti a riposo osservati.

QWE e STUDIO: i nove servizi persistenti attivi prima della migrazione sono
rimasti attivi con gli stessi PID al controllo finale. Le unit fallite già
presenti non sono state riparate o modificate.

Il logging esportato da Render aveva URL con una virgoletta iniziale spuria e
un token non accettato dal Worker. Corretto il JSON IONOS, riallineato il solo
`LOG_INGEST_TOKEN` del Worker `rinviabot-logger`, aggiunto User-Agent alle
richieste logging (la richiesta urllib standard riceveva 403). La prima prova
subito dopo il cambio secret ha ricevuto 401 durante la propagazione; la rilettura
successiva ha verificato risposta positiva e scrittura DB. Nessuna modifica ad
altri Worker o database. Non è stato rieseguito lo storico dei log falliti.

Render: servizio `srv-d64spc4r85hc73aqalo0`, workspace
`tea-d5kv58n5r7bs73cnbk40`, sospeso dall'utente; conservato per rollback.
Auto-deploy era `On Commit`: non è stato modificato. Non riattivare Render mentre
il polling VPS è attivo. La VPS non si aggiorna automaticamente da GitHub.

## Aggiornamento e rollback

Per aggiornare, conservare copia di codice/config correnti, verificare risorse e
stato condiviso, trasferire solo i file del rilascio verificato, controllare hash,
compilazione e unit, poi riavviare solo `rinviabot.service`. Le maschere e i
chiarimenti pendenti sono in memoria e non sopravvivono a un riavvio: evitare
riavvii durante una compilazione attiva quando possibile. Non cambiare il bot o
il calendario nel JSON. Il nuovo script non richiede modifiche alla logica dei
rinvii: il diff applicativo riguarda solo User-Agent e origine dei log.

Per tornare su Render: fermare e disabilitare **solo** `rinviabot.service`,
verificare l'arresto, recuperare la configurazione corretta dal vault, aggiornare
in Render solo URL/token del logger mantenendo `WEBHOOK_URL` originale, poi
riprendere il servizio Render. Il bot registra nuovamente il webhook. Verificare
`getWebhookInfo`, identità bot e ricezione reale. Non scartare aggiornamenti e
non tentare scritture calendario per replay senza verificare i duplicati.

Nessun disco Render o database PostgreSQL risultava associato. Il filesystem
locale della vecchia istanza gratuita non è stato esportato: non dichiarare
migrato lo storico locale Render. Gli eventi Google e le chat Telegram restano
nelle rispettive fonti, con la loro identità. Conservazione e backup periodico
dello stato VPS non sono stati aggiunti come nuova automazione in questa fase.
