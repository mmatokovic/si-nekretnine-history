# si-nekretnine-history

A GitHub Action runs `scrape.py` daily, scrapes two Šibenik property-sale pages, saves the matching
calls as `natjecaji.json`, and commits the file if it changed.
The git history is the archive. New items trigger an [ntfy](https://ntfy.sh) push.

Neither site has an RSS feed, so the scraper parses the first page of each list as HTML:

| Source | Page | Kept |
|---|---|---|
| Šibensko-kninska županija | [Pozivi i natječaji → Imovinsko-pravni poslovi](https://www.sibensko-kninska-zupanija.hr/pozivi-i-natjecaji) | `kupnj… nekretnin… vlasništvu Republike Hrvatske` (state land sold through the county; it never shows up on hr-nekretnine.hr) |
| Grad Šibenik | [Gospodarenje nekretninama](https://gov.sibenik.hr/stranice/gospodarenje-nekretninama/128.html) | `prodaj… nekretnin/zemljišt` (no leases) |

Titles matching `rezultat|odluk|poništenj|ispravak` are dropped from both.
If a source is down, returns an HTTP error, or parses to 0 items, the scraper sends one
high-priority "scraper error" push listing the failed sources. The other sources are still archived.

The status shown on the list (e.g. "Završene prijave") is unreliable, so the scraper treats an item as new when its link has not been seen before, whatever its status.

## Setup
1. Add the repo secret `NTFY_TOPIC` (a hard-to-guess topic you subscribe to in the ntfy app).
2. In Settings → Pages, set the source to **GitHub Actions**.
3. Push. The committed `natjecaji.json` is the baseline, so only later items notify.

Each run also publishes `index.html` and `natjecaji.json` to GitHub Pages
(`https://mmatokovic.github.io/si-nekretnine-history/`).

## History
    git log -p natjecaji.json
