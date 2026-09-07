#!/usr/bin/env python3
"""
convert.py - turn a Beamer deck into a presenter file.

    python3 convert.py slides.pdf                       # deck only
    python3 convert.py slides.pdf --paper paper.pdf     # + /fig and /table
    python3 convert.py slides.tex --paper paper.pdf     # from LaTeX source
    python3 convert.py slides.pdf -o ~/talks/ecb.html --title "ECB seminar"

Writes a single self-contained HTML file (fonts, figures and app inlined) and,
next to it, deck.json - the editable description of the deck: slide titles,
tags, prepared notes, and the figure index. Edit deck.json and re-run with
--from-json to rebuild without re-reading the PDF.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdfdeck, render, paperfigs


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48] or "deck"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="compiled Beamer PDF, or the .tex source")
    ap.add_argument("--tex", help="Beamer source for the same deck: adds \\note{} speaker "
                                  "notes, \\label{} tags and figure file names")
    ap.add_argument("--paper", help="the paper behind the talk; its figures and "
                                    "tables become /fig and /table")
    ap.add_argument("-o", "--out", help="output .html (default: alongside the source)")
    ap.add_argument("--title", help="deck title (default: from the first slide)")
    ap.add_argument("--dpi", type=int, default=150, help="raster quality for graphic slides")
    ap.add_argument("--from-json", metavar="DECK", help="rebuild from an edited deck.json")
    ap.add_argument("--notes", metavar="FILE",
                    help="prepared notes: a markdown file, '## <slide title or number>' per section")
    args = ap.parse_args()

    if args.from_json:
        deck = json.load(open(args.from_json))
    elif args.source.endswith(".tex"):
        import texdeck
        deck = texdeck.convert(args.source)
    else:
        deck = pdfdeck.convert(args.source, dpi=args.dpi)

    if args.tex:
        import texdeck
        texdeck.enrich(deck, args.tex)

    if args.paper:
        deck["figures"] = paperfigs.extract(args.paper) + [
            f for f in deck.get("figures", []) if f.get("source") == "deck"]

    title = args.title or first_title(deck) or os.path.basename(args.source)
    if args.notes:
        attach_notes(deck, args.notes)

    out = args.out or os.path.splitext(args.source)[0] + "-presenter.html"
    n = render.build(deck, out, slug(title), title)
    outdir = os.path.dirname(out) or "."
    json.dump(deck, open(os.path.join(outdir, "deck.json"), "w"))
    write_corpus(deck, outdir)
    print(f"{out}  ({n//1024} KB, {len(deck['slides'])} slides, "
          f"{len(deck.get('figures', []))} figures/tables)")


def write_corpus(deck, outdir):
    """The text of the deck, chunk per slide - what /ask is allowed to use."""
    chunks = []
    for i, s in enumerate(deck["slides"]):
        text = re.sub(r"<[^>]+>", " ", s.get("html", ""))
        text = re.sub(r"\s+", " ", text).strip()
        notes = " ".join(s.get("notes", []))
        if text or notes:
            chunks.append(dict(title=re.sub("<[^>]+>", "", s["title"]) or f"Slide {i+1}",
                               slide=i + 1, text=(text + (" | notes: " + notes if notes else ""))[:4000]))
    json.dump(chunks, open(os.path.join(outdir, "corpus.json"), "w"))


def first_title(deck):
    for s in deck["slides"]:
        txt = re.sub("<[^>]+>", " ", s["html"])
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            return txt[:80]
    return None


def attach_notes(deck, path):
    """Markdown notes: '## 12' or '## Covariate Balance' then bullet lines."""
    cur, buckets = None, {}
    for line in open(path):
        m = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1).strip().lower()
            buckets[cur] = []
        elif cur and line.strip():
            buckets[cur].append(re.sub(r"^[-*]\s*", "", line.strip()))
    for i, s in enumerate(deck["slides"]):
        key_n, key_t = str(i + 1), re.sub("<[^>]+>", "", s["title"]).strip().lower()
        s["notes"] = buckets.get(key_n) or buckets.get(key_t) or s.get("notes", [])


if __name__ == "__main__":
    main()
