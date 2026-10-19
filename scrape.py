import html
import json
import os
import re
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("natjecaji.json")
COMMIT_MSG = Path(tempfile.gettempdir()) / "commit.txt"
UA = {"User-Agent": "Mozilla/5.0 (compatible; git-scraper)"}
EXCLUDE = re.compile(r"rezultat|odluk|poništenj|ispravak", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def ntfy(title, body, **headers):
    if topic := os.environ.get("NTFY_TOPIC"):
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), headers={"Title": title, **headers})
        urllib.request.urlopen(req, timeout=30)


def text(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def iso(d):
    day, month, year = re.findall(r"\d+", d)[:3]
    return f"{year}-{int(month):02d}-{int(day):02d}"


def zupanija():
    page = fetch("https://www.sibensko-kninska-zupanija.hr/pozivi-i-natjecaji")
    for block in page.split('<article class="l-item">')[1:]:
        date = re.search(r'class="o-date[^"]*">([^<]+)<', block)
        link = re.search(r'class="o-title[^"]*"><a href="([^"]+)" class="o-link">(.*?)</a>', block, re.S)
        if date and link:
            yield {"title": text(link[2]), "link": link[1], "published": iso(date[1])}


def grad_sibenik():
    page = fetch("https://gov.sibenik.hr/stranice/gospodarenje-nekretninama/128.html")
    pattern = r'od <b>([\d.]+)</b>.*?<a href="(https://gov\.sibenik\.hr/obavijesti/[^"]+)"[^>]*>\s*<h5[^>]*>(.*?)</h5>'
    for date, link, title in re.findall(pattern, page, re.S):
        yield {"title": text(title), "link": link, "published": iso(date)}


SOURCES = {
    "Šibensko-kninska županija": (zupanija, re.compile(r"kupnj\w* nekretnin.*vlasništvu Republike Hrvatske", re.I)),
    "Grad Šibenik": (grad_sibenik, re.compile(r"prodaj\w* .*(nekretnin|zemljišt)", re.I)),
}

first_run = not OUT.exists()
archive = {} if first_run else {i["link"]: i for i in json.loads(OUT.read_text(encoding="utf-8"))}
known = set(archive)
fetched = []
errors = []

for name, (scrape, include) in SOURCES.items():
    try:
        items = list(scrape())
    except Exception as e:
        errors.append(f"{name}: {type(e).__name__}: {e}")
        continue
    if not items:
        errors.append(f"{name}: parsed 0 items, the page layout probably changed")
        continue
    fetched += [
        {"source": name, **i}
        for i in items
        if include.search(i["title"]) and not EXCLUDE.search(i["title"])
    ]
    time.sleep(2)

new = {} if first_run else {i["link"]: i for i in fetched if i["link"] not in known}
archive |= {i["link"]: i for i in fetched}
OUT.write_text(
    json.dumps(sorted(archive.values(), key=lambda i: (i["published"], i["link"]), reverse=True),
               ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

msg = [datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")]
if first_run:
    msg += ["", f"Initial archive: {len(archive)} items"]
if new:
    msg += ["", "New:"] + [f"- [{i['source']}] {i['title']} {i['link']}" for i in new.values()]
COMMIT_MSG.write_text("\n".join(msg) + "\n", encoding="utf-8")
print("\n".join(msg))

if new:
    body = "\n\n".join(f"{i['source']}: {i['title']}\n{i['link']}" for i in new.values())
    ntfy(f"si-nekretnine: {len(new)} new", body, Tags="house")
if errors:
    print("\n".join(errors))
    ntfy("si-nekretnine: scraper error", "\n\n".join(errors), Tags="warning", Priority="high")
