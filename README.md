# Edicola

Un feed personale e senza social: ogni notte un'attività programmata raccoglie i post nuovi di un elenco di pagine pubbliche, li riassume e li traduce in italiano, e pubblica qui l'edizione del giorno.

- `index.html` – il sito (GitHub Pages)
- `data.json` – l'edizione del giorno
- `briefing.json` – il riassunto che usa il briefing del mattino
- `tools/pagine.json` – le pagine seguite, con la categoria
- `tools/prepare.py`, `tools/merge.py` – preparano e uniscono l'edizione
- `tools/stato.json` – ultimo post visto per ogni pagina (per accorgersi di quelle ferme)
