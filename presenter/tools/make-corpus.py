#!/usr/bin/env python3
"""
make-corpus.py - the text of a deck, one chunk per slide.

`/ask` is the mode that must answer only from the lecture. The server needs the
deck's own words to do that, and this is what produces them:

    python3 tools/make-corpus.py decks/talk.html -o server/decks/<deck-id>/corpus.json

The deck id is the `id` in the deck's deck-meta block - the same key the server
looks under. Run it again whenever the slides change.
"""
import argparse, json, os, re, sys
from html.parser import HTMLParser


class Slides(HTMLParser):
    """Pull out <section class="slide"> text, plus the deck-meta block."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0            # section nesting inside a slide
        self.slides, self.buf = [], []
        self.title, self.titles = None, []
        self.in_title = 0
        self.skip = 0             # inside <script>/<style>
        self.meta_raw, self.in_meta = None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self.skip += 1
            if a.get("id") == "deck-meta":
                self.in_meta = True
            return
        if tag == "style":
            self.skip += 1
            return
        if tag == "section" and "slide" in (a.get("class") or ""):
            self.depth = 1
            self.buf, self.title = [], (a.get("data-title") or "").strip() or None
            if a.get("data-notes"):
                self.buf.append(a["data-notes"].replace("|", ". "))
            return
        if self.depth:
            if tag == "section":
                self.depth += 1
            if tag in ("h1", "h2") or "ftitle" in (a.get("class") or ""):
                self.in_title += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
            self.in_meta = False
            return
        if tag == "section" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                text = re.sub(r"\s+", " ", " ".join(self.buf)).strip()
                self.slides.append((self.title, text))
                self.titles.append(self.title)
            return
        if self.depth and tag in ("h1", "h2"):
            self.in_title = max(0, self.in_title - 1)

    def handle_data(self, data):
        if self.in_meta:
            self.meta_raw = (self.meta_raw or "") + data
            return
        if self.skip or not self.depth:
            return
        t = data.strip()
        if not t:
            return
        self.buf.append(t)
        if self.in_title and not self.title:
            self.title = t


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck")
    ap.add_argument("-o", "--out", help="corpus.json (default: next to the deck)")
    args = ap.parse_args()

    html = open(args.deck, encoding="utf-8").read()
    p = Slides()
    p.feed(html)
    if not p.slides:
        sys.exit('no <section class="slide"> found')

    meta = {}
    if p.meta_raw:
        try:
            meta = json.loads(p.meta_raw)
        except json.JSONDecodeError:
            pass
    notes = meta.get("notes", {})

    chunks = []
    for i, (title, text) in enumerate(p.slides):
        title = title or f"Slide {i + 1}"
        extra = list(notes.get(str(i + 1), [])) + list(notes.get(title, []))
        body = text + (" | notes: " + " ".join(extra) if extra else "")
        if body.strip():
            chunks.append({"slide": i + 1, "title": title, "text": body[:4000]})

    out = args.out or os.path.join(os.path.dirname(args.deck) or ".", "corpus.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(chunks, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{out}  ({len(chunks)} slides, deck id: {meta.get('id', '?')})")


if __name__ == "__main__":
    main()
