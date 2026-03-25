# Ruleset

## Scopo

Questo documento raccoglie le regole operative emerse dall'analisi completa dello storico Telegram.

Serve a:

- separare regole di dominio da esempi singoli
- guidare prompt, validazione e fallback
- rendere reversibili e tracciabili le modifiche di parsing

## Principio generale

Un evento si crea automaticamente solo se ogni campo operativo deriva da una prova testuale coerente e non conflittuale.

Traduzione pratica:

- `parte`, `giudice`, `luogo`, `data`, `ora` devono avere ancoraggi riconoscibili nel testo
- un token non puo' essere assegnato a un ruolo se appartiene piu' plausibilmente a un altro
- se due letture sono in conflitto, il bot deve chiedere conferma invece di creare

## Regole forti di ruolo

### Parte

- Il primo cognome o primo blocco nominale e' di default la parte/imputato assistito.
- `parte` non puo' essere:
  - un tribunale
  - una corte
  - un collegio
  - un riferimento pratica o procedimento
  - un avvocato o domiciliatario

### Giudice

- Il giudice puo' mancare.
- Un giudice non va inventato.
- `giudice` non puo' essere:
  - avvocato
  - domiciliatario
  - tribunale
  - corte
  - collegio
  - riferimento di procedimento

### Luogo

- `Tribunale di <citta'>` e' sempre `luogo`.
- `Corte d'Appello` e varianti sono sempre `luogo`.
- `Collegio Pres. Tizio` produce:
  - `luogo = Collegio`
  - `giudice = Tizio`
- `RG`, `R.G.`, `RGNR`, `RG DIB`, `procedimento n.` non sono mai `luogo`.

## Regole sulle note

Le note devono conservare:

- il messaggio originale integrale
- riferimenti pratica/procedimento
- attivita' procedurali ricorrenti

Attivita' ricorrenti da preservare:

- discussione
- esame imputato
- esame testi
- testi pm
- testi difesa
- stessi incombenti
- incombenti
- tpm
- fine tpm
- impedimento
- teste po
- acquisito
- 507
- perizia
- incidente esecuzione
- obbligo pg
- udienza preliminare
- apertura dibattimento
- citazione
- diffidati

## Regole su data e ora

- La lettura deve restare intelligente, non meccanica.
- Bias verso il futuro.
- Le date relative vanno risolte rispetto alla data reale del messaggio.
- Se una data esplicita cade nel passato in modo sospetto, usare `data_passata`.

## Regole sui dubbi

Il dubbio deve essere forzato quando:

- la parte sembra un luogo giudiziario
- la parte sembra un riferimento di procedimento
- la parte sembra un avvocato
- il giudice sembra un avvocato
- il giudice sembra un luogo
- il luogo sembra solo un riferimento pratica
- nel testo compare `collegio pres.` ma non si ottiene `luogo = Collegio`
- nel testo compare un tribunale/corte ma il luogo non viene ricostruito coerentemente
- il primo cognome plausibile viene spostato nel campo giudice

## Regole sui messaggi non-udienza

Non creare automaticamente un evento se il messaggio:

- non ha contesto giudiziario sufficiente
- sembra un link, comando tecnico o messaggio di servizio
- non contiene abbastanza segnali coerenti per una udienza

Se contiene parte + data + ora ma resta ambiguo:

- meglio `conferma` che `non capito`

