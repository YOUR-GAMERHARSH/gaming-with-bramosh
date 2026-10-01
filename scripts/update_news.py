#!/usr/bin/env python3
import html, json, re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

SOURCE = "https://www.pubgmobile.com/en-US/news.shtml"
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DATA = ROOT / "data" / "news.json"

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.buf = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.buf = []
    def handle_data(self, data):
        if self.href is not None:
            self.buf.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, re.sub(r"\s+", " ", " ".join(self.buf)).strip()))
            self.href = None
            self.buf = []

def main():
    req = Request(SOURCE, headers={"User-Agent": "GamingWithBramosh-NewsBot/1.0"})
    with urlopen(req, timeout=30) as response:
        raw = response.read().decode("utf-8", "ignore")
    parser = LinkParser()
    parser.feed(raw)

    items, seen = [], set()
    keywords = ("version", "beta", "update", "announcement", "event", "mode")
    for href, title in parser.links:
        if not href or not title or not 10 <= len(title) <= 180:
            continue
        if not any(k in title.lower() for k in keywords):
            continue
        url = urljoin(SOURCE, href)
        if "pubgmobile.com" not in url or url in seen:
            continue
        seen.add(url)
        items.append({
            "title": title,
            "url": url,
            "source": "PUBG MOBILE Official",
            "fetched_at": datetime.now(timezone.utc).isoformat()
        })
        if len(items) == 8:
            break

    if not items:
        print("No official news items detected; nothing changed.")
        return

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps({
        "source": SOURCE,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": items
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    text = INDEX.read_text(encoding="utf-8")
    start = '<div class="grid" id="articles">'
    end = '</div></div></section>\n\n<section><div class="wrap"><div class="head"><div><div class="eyebrow">Explore</div>'
    a = text.find(start)
    b = text.find(end, a)
    if a < 0 or b < 0:
        raise RuntimeError("Latest Articles section not found")

    cards = []
    for item in items[:6]:
        title = html.escape(item["title"], quote=True)
        url = html.escape(item["url"], quote=True)
        cards.append(
            f'<article class="card" data-title="{title}"><img class="thumb" src="https://images.pexels.com/photos/7915523/pexels-photo-7915523.jpeg?auto=compress&dpr=1&h=750&w=1260" alt="Gaming news"><div class="body"><span class="tag">PUBG MOBILE</span><small class="credit">Source: PUBG MOBILE Official</small><h3>{title}</h3><p>Latest announcement from the official PUBG MOBILE news feed.</p><a class="read" href="{url}" target="_blank" rel="noopener">Read official news →</a></div></article>'
        )
    INDEX.write_text(text[:a] + start + "\n" + "\n".join(cards) + "\n" + text[b:], encoding="utf-8")
    print("Automatic news update complete.")

if __name__ == "__main__":
    main()
