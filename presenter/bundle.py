#!/usr/bin/env python3
"""
bundle.py - staple a deck and the presenter into one standalone HTML file.

    python3 bundle.py my-talk.html                 -> my-talk-presenter.html
    python3 bundle.py my-talk.html -o ~/talks/unsw.html

Use it for the version you actually present from: it needs no server, no file
picker and no network. Every local image, font and stylesheet the deck refers to
is inlined, so the single file works from a USB stick on a machine you have
never seen before.

During authoring you do not need this at all - just open app/presenter.html and
drop the deck onto it.
"""
import argparse, base64, mimetypes, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")

URL_IN_CSS = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")
SRC_IN_HTML = re.compile(r'\b(src|href)\s*=\s*(["\'])([^"\']+)\2', re.I)
SKIP = re.compile(r"^(data:|https?:|//|#|mailto:)", re.I)


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def inline_assets(text, base_dir, seen=None, report=None):
    """Replace local url(...) and src=/href= references with data: URIs."""
    seen = seen if seen is not None else set()

    def resolve(ref):
        p = os.path.normpath(os.path.join(base_dir, ref.split("?")[0].split("#")[0]))
        return p if os.path.isfile(p) else None

    def css_sub(m):
        ref = m.group(2)
        if SKIP.match(ref):
            return m.group(0)
        p = resolve(ref)
        if not p:
            report.append(f"  missing: {ref}")
            return m.group(0)
        seen.add(p)
        return f"url({data_uri(p)})"

    def html_sub(m):
        attr, q, ref = m.group(1), m.group(2), m.group(3)
        if SKIP.match(ref):
            return m.group(0)
        p = resolve(ref)
        if not p:
            report.append(f"  missing: {ref}")
            return m.group(0)
        # a linked stylesheet becomes an inline <style> further down; leave href
        if attr.lower() == "href" and p.lower().endswith(".css"):
            return m.group(0)
        seen.add(p)
        return f'{attr}={q}{data_uri(p)}{q}'

    text = URL_IN_CSS.sub(css_sub, text)
    text = SRC_IN_HTML.sub(html_sub, text)
    return text


def pull_stylesheets(text, base_dir, report):
    """<link rel=stylesheet href=local.css> -> an inline <style> block."""
    def sub(m):
        href = m.group(1)
        if SKIP.match(href):
            return m.group(0)
        p = os.path.normpath(os.path.join(base_dir, href))
        if not os.path.isfile(p):
            report.append(f"  missing stylesheet: {href}")
            return m.group(0)
        css = inline_assets(open(p, encoding="utf-8").read(), os.path.dirname(p), report=report)
        return f"<style>\n{css}\n</style>"
    return re.sub(r'<link[^>]*rel=["\']?stylesheet["\']?[^>]*href=["\']([^"\']+)["\'][^>]*>',
                  sub, text, flags=re.I)


def build(deck_path, out_path, app_dir=APP):
    base = os.path.dirname(os.path.abspath(deck_path))
    report = []
    deck = open(deck_path, encoding="utf-8").read()
    deck = pull_stylesheets(deck, base, report)
    deck = inline_assets(deck, base, report=report)

    app_css = open(os.path.join(app_dir, "presenter.css"), encoding="utf-8").read()
    app_js = open(os.path.join(app_dir, "presenter.js"), encoding="utf-8").read()
    shell = open(os.path.join(app_dir, "presenter.html"), encoding="utf-8").read()

    # the shell, with its external references replaced by the real thing
    shell = shell.replace('<link rel="stylesheet" href="presenter.css">',
                          f"<style>\n{app_css}\n</style>")
    shell = shell.replace('<script src="presenter.js"></script>',
                          f"<script>\n{app_js}\n</script>")

    title = re.search(r"<title>(.*?)</title>", deck, re.S | re.I)
    if title:
        shell = re.sub(r"<title>.*?</title>", f"<title>{title.group(1).strip()}</title>",
                       shell, count=1, flags=re.S | re.I)

    # the deck travels as inert text so nothing in it runs or renders twice
    payload = deck.replace("</script", "<\\/script")
    shell = shell.replace('<div id="toast"></div>',
                          f'<div id="toast"></div>\n<script type="text/plain" id="deck-source">'
                          f"{payload}</script>")
    open(out_path, "w", encoding="utf-8").write(shell)
    return len(shell), report


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="the deck HTML file")
    ap.add_argument("-o", "--out", help="output file")
    args = ap.parse_args()
    if not os.path.isfile(args.deck):
        sys.exit(f"no such file: {args.deck}")
    out = args.out or os.path.splitext(args.deck)[0] + "-presenter.html"
    size, report = build(args.deck, out)
    print(f"{out}  ({size // 1024} KB)")
    if report:
        print("could not inline:")
        print("\n".join(sorted(set(report))))


if __name__ == "__main__":
    main()
