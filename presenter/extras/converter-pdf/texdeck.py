"""
Beamer .tex support.

Two ways in:

  enrich(deck, "talk.tex")   - keep the PDF's exact layout, but take the things
                               only the source knows: \\note{} speaker notes,
                               \\label{}s, section names, figure file names.
                               This is the recommended path.

  convert("talk.tex")        - build a deck from the source alone, when there is
                               no compiled PDF. Layout is approximate.

The source is the ground truth for *structure*; the PDF is the ground truth for
*appearance*. Using both gives the best of each.
"""
import os, re

FRAME = re.compile(r"\\begin\{frame\}(.*?)\\end\{frame\}", re.S)
TITLE = re.compile(r"\\frametitle\s*(?:<[^>]*>)?\s*\{", re.S)
CMD_COLORS = {"alert": "alert", "structure": "structure"}


# ------------------------------------------------------------------ utilities
def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def balanced(s, start):
    """Content of the {...} group that starts at s[start] == '{'."""
    depth, i = 0, start
    while i < len(s):
        if s[i] == "{" and (i == 0 or s[i - 1] != "\\"):
            depth += 1
        elif s[i] == "}" and s[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        i += 1
    return s[start + 1:], len(s)


def arg_of(cmd, text, pos=0):
    """First {...} argument of \\cmd after pos, or None."""
    m = re.compile(r"\\" + cmd + r"\s*(?:<[^>]*>)?\s*\{").search(text, pos)
    if not m:
        return None, pos
    body, end = balanced(text, m.end() - 1)
    return body, end


def frames(tex):
    return [m.group(1) for m in FRAME.finditer(tex)]


# ------------------------------------------------------------------ inline text
INLINE = [
    (re.compile(r"\\textbf\s*\{"), lambda b: f'<span class="b">{b}</span>'),
    (re.compile(r"\\textit\s*\{"), lambda b: f'<span class="i">{b}</span>'),
    (re.compile(r"\\emph\s*\{"), lambda b: f'<span class="i">{b}</span>'),
    (re.compile(r"\\alert\s*(?:<[^>]*>)?\s*\{"), lambda b: f'<span class="b alert">{b}</span>'),
]
SYMBOLS = {r"\\rightarrow": "→", r"\\Rightarrow": "⇒", r"\\to": "→", r"\\sim": "∼",
           r"\\ldots": "…", r"\\dots": "…", r"\\%": "%", r"\\&": "&amp;", r"\\_": "_",
           r"\\\\": " ", r"~": " ", r"\\,": " ", r"\\;": " "}


def inline(tex):
    """LaTeX inline markup -> HTML. Math is left for KaTeX in the browser."""
    out = tex
    body, _ = None, None
    # \textcolor{c}{text}
    while True:
        m = re.search(r"\\textcolor\s*\{([^}]*)\}\s*\{", out)
        if not m:
            break
        inner, end = balanced(out, m.end() - 1)
        out = out[:m.start()] + f'<span class="tc-{m.group(1).strip()}">{inner}</span>' + out[end:]
    for pat, wrap in INLINE:
        while True:
            m = pat.search(out)
            if not m:
                break
            inner, end = balanced(out, m.end() - 1)
            out = out[:m.start()] + wrap(inner) + out[end:]
    for a, b in SYMBOLS.items():
        out = re.sub(a, b, out)
    out = re.sub(r"\$([^$]*)\$", lambda m: f'<span class="math">\\({m.group(1)}\\)</span>', out)
    out = re.sub(r"\\[a-zA-Z]+\s*", "", out)          # drop unknown commands
    return re.sub(r"[{}]", "", out).strip()


# ------------------------------------------------------------------ structure
def overlay_step(spec):
    """<2-> or <3> -> the step at which the item appears."""
    if not spec:
        return 0
    m = re.search(r"(\d+)", spec)
    return max(0, int(m.group(1)) - 1) if m else 0


def parse_items(body):
    """itemize / enumerate / description nests -> flat items with levels."""
    items, level, pause = [], 0, 0
    token = re.compile(r"\\(begin|end)\{(itemize|enumerate|description)\}"
                       r"|\\item\s*(?:<([^>]*)>)?|\\pause")
    pos, cur = 0, None
    for m in token.finditer(body):
        if cur is not None:
            cur["tex"] += body[pos:m.start()]
        pos = m.end()
        if m.group(1) == "begin":
            level += 1
            cur = None
        elif m.group(1) == "end":
            level = max(0, level - 1)
            cur = None
        elif m.group(0).startswith("\\item"):
            step = overlay_step(m.group(3)) or pause
            cur = dict(level=level, kind="enum" if m.group(2) == "enumerate" else "bullet",
                       step=step, tex="")
            items.append(cur)
        else:                                    # \pause
            pause += 1
            cur = None
    if cur is not None:
        cur["tex"] += body[pos:]
    for it in items:
        it["html"] = inline(it["tex"])
    return [it for it in items if it["html"]]


def frame_meta(body):
    title, _ = arg_of("frametitle", body)
    note, _ = arg_of("note", body)
    label, _ = arg_of("label", body)
    graphics = re.findall(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}", body)
    return dict(title=inline(title or ""), note=(note or "").strip(),
                label=(label or "").strip(), graphics=graphics)


# ------------------------------------------------------------------ public API
def _item_div(it):
    kind = it["kind"] if it["level"] < 2 else ("enum" if it["kind"] == "enum" else "arrow")
    mark = {"bullet": "\u2022", "arrow": "\u2192", "enum": ""}[kind]
    step = f' f{it["step"]}' if it["step"] else ""
    tx, mx = 28 + 22 * it["level"], 18 + 22 * it["level"]
    return (f'<div class="it {kind}{step}" data-m="{mark}" '
            f'style="--tx:{tx};--mx:{mx};--gap:{6 if it["level"] == 1 else 3};'
            f'--mcol:{"#851f26" if kind == "bullet" else "#7f7f7f"}">{it["html"]}</div>')


def enrich(deck, tex_path):
    """Attach source-only knowledge to a deck built from the PDF."""
    tex = strip_comments(open(tex_path, encoding="utf-8", errors="ignore").read())
    metas = [frame_meta(f) for f in frames(tex)]
    sections = re.findall(r"\\section\s*\{([^}]*)\}", tex)
    for slide, meta in zip(deck["slides"], metas):
        if meta["note"]:
            slide.setdefault("notes", []).append(inline(meta["note"]))
        if meta["label"]:
            slide.setdefault("tags", []).append(meta["label"])
        if meta["graphics"]:
            slide["sources"] = [os.path.basename(g) for g in meta["graphics"]]
    deck["sections"] = sections
    return deck


def convert(tex_path, page=(453.543, 255.118)):
    """Build a deck from LaTeX alone (no PDF): structure exact, layout approximate."""
    tex = strip_comments(open(tex_path, encoding="utf-8", errors="ignore").read())
    W, H = page
    slides = []
    for n, body in enumerate(frames(tex)):
        meta = frame_meta(body)
        items = parse_items(body)
        html = "".join(_item_div(it) for it in items)
        slides.append(dict(n=n, kind="text" if items else "free", title=meta["title"],
                           box=dict(left=28.0, right=W - 24, top=30.0),
                           pages=[n + 1], steps=max([i["step"] for i in items] or [0]),
                           html=html, tags=[meta["label"]] if meta["label"] else [],
                           notes=[inline(meta["note"])] if meta["note"] else [],
                           sources=[os.path.basename(g) for g in meta["graphics"]]))
    return dict(theme=dict(page_w=W, page_h=H, family="LMSans", body_size=9.2,
                           title_size=14.35, line_height=10.96, title_top=8.2,
                           title_color="#19196e",
                           colors=["#19196e", "#851f26", "#008080", "#7f7f7f"]),
                slides=slides, figures=[],
                extra_css=".tc-alert,.alert{color:#851f26}.tc-structure{color:#19196e}")


if __name__ == "__main__":
    import json, sys
    d = convert(sys.argv[1])
    for s in d["slides"][:20]:
        print(f'{s["n"]:>3} steps={s["steps"]} {s["title"][:60]}')
