# QuintaElementare

Appunti di scuola primaria che partono da una foto e diventano materiale di
studio utilizzabile: un **poster ridisegnato** al posto del cartellone
fotografato storto, e una **verifica di 3 pagine** pronta da stampare.

La trasformazione è automatizzata dalla skill [`appunti-lezione`](.claude/skills/appunti-lezione/SKILL.md),
che vive dentro questo repo e si attiva da sola quando si lavora qui.

## Com'è organizzato

```
QuintaElementare/
├── .claude/skills/appunti-lezione/   la skill: istruzioni + due script Python
│   ├── SKILL.md
│   └── scripts/
│       ├── build_appunti.py          appunti.json  -> poster PDF + PNG + markdown
│       └── build_verifica.py         verifica.json -> verifica DOCX + PDF
└── TheUniverse/                      una lezione = una cartella
```

Ogni lezione sta in una cartella con il nome dell'argomento. Dentro convivono
tre tipi di file:

| | File | |
|---|---|---|
| **Origine** | `TheUniverse.jpeg` | La foto del cartellone scritto a mano |
| **Fonte di verità** | `appunti.json`, `verifica.json` | Scritti a mano, si modificano solo questi |
| **Generati** | `Appunti-*.pdf`, `Appunti-*.png`, `appunti.md`, `Verifica-*.docx`, `Verifica-*.pdf` | Riscritti a ogni esecuzione |

**I file generati non vanno modificati a mano**: la prossima esecuzione degli
script cancella le modifiche. Se una domanda non convince o una frase è
sbagliata, si corregge il JSON e si rigenera.

## Il flusso

1. **Foto** del cartellone o dello schema disegnato in classe.
2. Il modello **legge l'immagine** e ne ricostruisce il contenuto in
   `appunti.json`: testo, elenchi, e soprattutto i disegni *ridisegnati* —
   le sequenze con le frecce diventano blocchi `flow`, i confronti diventano
   `table`.
3. `build_appunti.py` rende quel JSON come **poster A4 a colori** (PDF + PNG a
   200 dpi) e come markdown, riprendendo i colori degli evidenziatori originali.
4. Il modello ricava da quegli appunti **5 domande a scelta multipla e 5 aperte**
   in `verifica.json`, con soluzioni e spiegazioni.
5. `build_verifica.py` produce la **verifica di 3 pagine**: scelta multipla,
   domande aperte con le righe per rispondere, soluzioni per chi corregge.

La regola che tiene insieme tutto: la verifica deve poter essere superata
leggendo *solo* quegli appunti. Nessuna domanda richiede nozioni che non stanno
sul foglio.

## Requisiti

Python 3 (testato su 3.11) e tre librerie:

```bash
pip install python-docx reportlab pymupdf
```

`pymupdf` serve solo per il PNG del poster: senza, usa `--no-png`.

## Uso

Dalla radice del repo:

```bash
# poster ridisegnato: PDF + PNG + appunti.md
python .claude/skills/appunti-lezione/scripts/build_appunti.py TheUniverse/appunti.json

# verifica di 3 pagine: DOCX + PDF
python .claude/skills/appunti-lezione/scripts/build_verifica.py TheUniverse/verifica.json --pdf
```

Gli output nascono sempre accanto al JSON. Entrambi gli script accettano `-h`.

Opzioni utili:

- `build_appunti.py --dpi 300` per un PNG da stampa, `--no-png`, `--no-md`
- `build_verifica.py --pdf` per affiancare il PDF al DOCX, `-o` per il nome file

Gli script validano l'input e si fermano con un messaggio esplicito: la verifica
richiede esattamente 5 domande per tipo e avvisa se la risposta corretta è
sempre la stessa lettera.

## Aggiungere una lezione

Crea una cartella con l'immagine dentro e chiedi in chat:

> fammi gli appunti e la verifica da `NuovaLezione/foto.jpg`

La skill fa il resto. Le lingue seguono gli appunti: un cartellone CLIL in
inglese produce una verifica in inglese, uno in italiano una verifica in
italiano.

## Lezioni presenti

| Cartella | Argomento | Lingua |
|---|---|---|
| [`TheUniverse/`](TheUniverse/) | Universo, big bang, dimensioni e anni luce | Inglese (CLIL) |
