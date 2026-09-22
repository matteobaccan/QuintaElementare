---
name: appunti-lezione
description: Use when the user points at a photo or scan of handwritten lesson notes, a school poster, a mind map or a "schema" and wants it transcribed, redrawn, turned into a clean picture, or turned into a quiz, test, worksheet or verifica - keywords appunti, schema, cartellone, lezione, ridisegna, verifica, quiz, domande, scuola, homework, study sheet.
---

# Appunti di lezione: da immagine a poster e verifica

Trasforma la foto di uno schema scritto o disegnato a mano in due artefatti:

1. un **poster ridisegnato** — PDF + PNG puliti e a colori, che sostituiscono la
   foto storta del cartellone;
2. una **verifica di 3 pagine** — DOCX + PDF (scelta multipla, aperte, soluzioni).

**Principio guida:** la verifica deve poter essere superata leggendo *solo* quegli
appunti. Nessuna domanda richiede conoscenze che non stanno sul foglio.

**Due file JSON sono la fonte di verità.** Tutto il resto è generato: non
modificare mai a mano PDF, PNG, DOCX o `appunti.md` — correggi il JSON e rilancia.

## Quando usarla

- "fammi una verifica da questi appunti", "genera domande su questa foto"
- "riscrivi questo schema al computer", "ridisegna questo cartellone"
- Una directory con una sola immagine di appunti e nient'altro

Non usarla per: generare quiz da un testo già digitale (salta al passo 4), o per
correggere verifiche già svolte.

## Workflow

Cinque passi. I comandi si lanciano **dalla radice del repo**; gli output
nascono sempre accanto al JSON, cioè nella cartella dell'immagine.

### 1. Leggi l'immagine

Usa il tool **Read** sul file immagine (visione nativa, niente OCR esterno).
Se una zona è illeggibile **non inventarla**: chiedi all'utente, oppure scrivi
`[illeggibile]` nel testo.

### 2. Ricostruisci gli appunti in `appunti.json`

```json
{
  "title": "The Universe",
  "subject": "Science - Class 5",
  "accent": "#17B8C4",
  "layout": { "orientation": "landscape", "columns": 2 },
  "keywords_label": "KEYWORDS TO REMEMBER",
  "keywords": ["big bang", "13.8 billion years ago"],
  "sections": [
    {
      "heading": "THE BIG BANG",
      "color": "#8BC34A",
      "blocks": [ { "type": "text", "text": "... **big bang** ..." } ]
    }
  ]
}
```

- `**doppi asterischi**` = evidenziato sul foglio → diventa giallo evidenziatore.
- `color` per sezione: riprendi il colore dell'evidenziatore usato a mano.
  Se lo ometti, la palette ne assegna uno.
- Trascrizione **fedele**: correggi solo i refusi evidenti, non aggiungere
  contenuti che non sono sul foglio nemmeno se sai che sono veri.

**Tipi di blocco** — qui sta il vero *ridisegno*:

| `type` | Campi | Usalo per |
|---|---|---|
| `text` | `text` | Paragrafi di prosa |
| `list` | `items[]` | Elenchi puntati |
| `flow` | `steps[]`, `caption` | **Sequenze e processi disegnati con le frecce** |
| `table` | `headers[]`, `rows[][]` | Confronti, quantità, grandezze |
| `caption` | `text` | Illustrazioni decorative: una riga che dice cosa c'era |

Un disegno va **ridisegnato, non descritto**. "C'è una freccia dal sole alla
galassia" non è un ridisegno: quella è una `flow`. Usa `caption` solo per le
illustrazioni puramente decorative, che non portano informazione.

### 3. Genera il poster ridisegnato

```bash
python .claude/skills/appunti-lezione/scripts/build_appunti.py <cartella-lezione>/appunti.json
```

Produce `Appunti-<Titolo>.pdf`, `Appunti-<Titolo>.png` (l'immagine migliorativa,
200 dpi) e `appunti.md`. Opzioni: `--dpi N`, `--no-png`, `--no-md`.

### 4. Scrivi `verifica.json`

```json
{
  "title": "The Universe",
  "subject": "Science - Class 5",
  "language": "en",
  "multiple_choice": [
    { "question": "...", "options": ["...", "...", "...", "..."],
      "answer": 2, "explanation": "una riga: perché è questa" }
  ],
  "open_questions": [
    { "question": "...", "lines": 4, "model_answer": "risposta attesa in 1-3 frasi" }
  ]
}
```

- `language`: **la lingua degli appunti** (`it` o `en`), non quella della chat.
  Determina le etichette del documento e la lingua di domande e soluzioni.
- `answer`: indice **0-based** dell'opzione corretta.
- `lines`: righe bianche per rispondere (3 per richiamo, 4-5 per spiegazioni).
- Servono esattamente 5 domande per tipo: lo script rifiuta il file altrimenti.

### 5. Genera la verifica

```bash
python .claude/skills/appunti-lezione/scripts/build_verifica.py <cartella-lezione>/verifica.json --pdf
```

Produce `Verifica-<Titolo>.docx` e `.pdf`: pag. 1 scelta multipla, pag. 2 aperte
con le righe per rispondere, pag. 3 soluzioni.

## Regole di qualità delle domande

Sono la parte che distingue una verifica usabile da una inutile.

| Regola | Perché |
|---|---|
| Ogni risposta è verificabile sugli appunti | Altrimenti si valuta la fortuna, non lo studio |
| Distrattori plausibili e di lunghezza simile | L'opzione più lunga o più precisa si indovina |
| Niente "tutte le precedenti" / "nessuna delle precedenti" | Si risolvono per esclusione, non per conoscenza |
| La lettera corretta cambia tra le domande | Una colonna di B è un regalo |
| Le 5 aperte su livelli diversi | Richiamo, spiegazione, confronto, "perché", applicazione |
| Registro da scuola primaria, frasi brevi | Il testo della domanda non deve essere l'ostacolo |
| `explanation` cita il punto degli appunti | Serve al genitore che corregge, non solo al bambino |

## Errori comuni

- **Descrivere i disegni invece di ridisegnarli.** Le sequenze sono blocchi
  `flow`, i confronti sono `table`.
- **Modificare `appunti.md`, il DOCX o il PDF a mano.** Sono rigenerati: la
  prossima esecuzione cancella le modifiche. Correggi il JSON.
- **Domande su nozioni non presenti sul foglio** (nomi di pianeti, date extra).
- **Aperte che si risponde con sì/no.** Chiedi "spiega", "descrivi", "perché".
- **Usare la lingua della chat** invece di quella degli appunti.

## Risoluzione problemi

| Sintomo | Causa / rimedio |
|---|---|
| Una colonna del poster resta mezza vuota | Poco testo per due colonne: `"layout": {"columns": 1}` o `"orientation": "portrait"` |
| Il poster va a 2 pagine | Riduci le `caption`, o passa a `landscape` con 2 colonne |
| Colori del poster inattesi | I colori sezione sono `#RRGGBB` a 6 cifre: reportlab legge 8 cifre come un intero RGB |
| `Invalid quiz file: ...` | Lo script elenca i campi mancanti: correggi il JSON |
| `WARNING: every correct answer is the same letter` | Rimescola le opzioni |
| La verifica va a 4 pagine | Accorcia le domande o riduci `lines` |
| `ModuleNotFoundError` | `pip install python-docx reportlab pymupdf` |
