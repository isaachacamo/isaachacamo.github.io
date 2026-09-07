#!/usr/bin/env python3
"""
extract-deck.py - pull a clean deck file out of an HTML page that already
contains slides.

Useful for a page that bundles slides together with some other app (an older
presenter build, a Reveal.js export, anything that puts its slides in
<section class="slide">). It keeps the slides and their CSS, drops the other
application's markup and scripts, and writes a deck that follows DECK-SPEC.md.

    python3 tools/extract-deck.py old-thing.html -o decks/talk.html

If the page carries a legacy `const DECK = {...}` block, its title, id, figures
and notes are carried over into a proper deck-meta block.
"""
import argparse, json, os, re, sys


def find_json_object(text, start):
    """The {...} literal beginning at `start`, respecting strings."""
    depth, i, in_str, esc = 0, start, None, False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == in_str:
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    return None


def legacy_meta(html):
    m = re.search(r"\bDECK\s*=\s*\{", html)
    if not m:
        return {}
    blob = find_json_object(html, m.end() - 1)
    if not blob:
        return {}
    try:
        d = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    meta = {k: d[k] for k in ("id", "title", "api", "size") if k in d}
    if d.get("figures"):
        meta["figures"] = d["figures"]
    notes = {}
    for i, s in enumerate(d.get("slides", [])):
        if s.get("notes"):
            notes[str(i + 1)] = s["notes"]
    if notes:
        meta["notes"] = notes
    # slide tags travel back onto the sections
    meta["_tags"] = [s.get("tags", []) for s in d.get("slides", [])]
    return meta


def sections_of(html):
    """Each <section ... class="...slide..."> ... </section>, nesting-aware."""
    out, i = [], 0
    open_re = re.compile(r"<section\b[^>]*>", re.I)
    while True:
        m = open_re.search(html, i)
        if not m:
            break
        if "slide" not in m.group(0):
            i = m.end()
            continue
        depth, j = 1, m.end()
        tag = re.compile(r"</?section\b[^>]*>", re.I)
        while depth and j < len(html):
            t = tag.search(html, j)
            if not t:
                break
            depth += -1 if t.group(0).startswith("</") else 1
            j = t.end()
        out.append(html[m.start():j])
        i = j
    return out


def styles_of(html):
    return re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)


APP_RULE = re.compile(r"^\s*(\.pz|\.stage|\.bar|#pane|#log|#palette|\.pal-|#lightbox|\.lb-"
                      r"|#toast|\.askbtn|#welcome|\.msg|\.inp|\.tag\b|#paneT|#deckName|#cmd"
                      r"|body\.|html,body|:root|\*\{)")


def strip_app_css(css):
    """Drop rules that style a presenter's own chrome rather than the slides."""
    kept, i = [], 0
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css, re.S):
        sel = m.group(1)
        if APP_RULE.search(sel.split(",")[0]):
            continue
        kept.append(m.group(0))
    # keep @font-face / @media blocks whole
    for m in re.finditer(r"@(?:font-face|media|supports|keyframes)[^{]*\{(?:[^{}]|\{[^{}]*\})*\}",
                         css, re.S):
        if m.group(0) not in "".join(kept):
            kept.append(m.group(0))
    return "\n".join(kept)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--keep-all-css", action="store_true",
                    help="do not try to drop the other app's chrome CSS")
    args = ap.parse_args()

    html = open(args.source, encoding="utf-8").read()
    secs = sections_of(html)
    if not secs:
        sys.exit('no <section class="slide"> found')
    meta = legacy_meta(html)
    tags = meta.pop("_tags", [])
    css = "\n".join(styles_of(html))
    if not args.keep_all_css:
        css = strip_app_css(css)

    # put slide tags back on the sections themselves
    for i, t in enumerate(tags[:len(secs)]):
        if t and "data-tags" not in secs[i]:
            secs[i] = re.sub(r"<section\b", f'<section data-tags="{",".join(t)}"', secs[i], count=1)

    meta.setdefault("title", (re.search(r"<title>(.*?)</title>", html, re.S | re.I)
                              or re.match("", "")) and
                    re.search(r"<title>(.*?)</title>", html, re.S | re.I).group(1).strip()
                    if re.search(r"<title>(.*?)</title>", html, re.S | re.I) else "Deck")
    meta.setdefault("id", os.path.splitext(os.path.basename(args.out))[0])

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{meta.get('title', 'Deck')}</title>
<script type="application/json" id="deck-meta">
{json.dumps(meta, indent=1)}
</script>
<style>
{css}
</style>
</head>
<body>

{os.linesep.join(secs)}

</body>
</html>
"""
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write(doc)
    print(f"{args.out}  ({len(doc)//1024} KB, {len(secs)} slides, "
          f"{len(meta.get('figures', []))} figures)")


if __name__ == "__main__":
    main()
