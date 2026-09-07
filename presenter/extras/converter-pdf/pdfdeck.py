"""
Beamer PDF -> deck.json

Reads the *geometry* of a compiled Beamer deck (fonts, sizes, colours, positions)
and rebuilds each frame as editable HTML, with Beamer overlays turned into steps.

Two kinds of slide come out:
  * text slides    - bullets/arrows/enumerates rebuilt as real HTML elements
  * graphic slides - the frame body kept as a stack of page images, one per
                     overlay step, so builds replay exactly

Nothing here is specific to one deck: the indent levels, colours and title size
are learned from the document itself.
"""
import base64, io, re, statistics
import fonts
from collections import Counter, defaultdict
import pymupdf

DIM_MIN = 200          # a span whose darkest channel is above this is "not yet revealed"
BULLETS = "•‣◦-–—*"
ARROWS  = "→⇒▶➔"


def family(font):
    """LMSans10-Bold -> LMSans, so title/body variants of one face group together."""
    base = font.split("+")[-1]
    m = re.match(r"[A-Za-z]+", base)
    return (m.group(0) if m else base).rstrip("0123456789")


def rgb(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def hexcol(c):
    return "#%02x%02x%02x" % rgb(c)


def is_dim(c):
    return min(rgb(c)) > DIM_MIN


# ---------------------------------------------------------------- extraction
def page_lines(page):
    """Lines of text with their spans, sorted top-to-bottom then left-to-right."""
    lines = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            spans = [s for s in l["spans"] if s["text"]]
            ink = [s for s in spans if s["text"].strip()]
            if not ink:
                continue
            vertical = abs(l["dir"][1]) > 0.5
            x0 = min(s["bbox"][0] for s in ink)
            y0 = min(s["bbox"][1] for s in ink)
            y1 = max(s["bbox"][3] for s in ink)
            lines.append(dict(x=x0, y=y0, y1=y1, spans=spans, ink=ink, vertical=vertical,
                              size=max(s["size"] for s in ink),
                              text="".join(s["text"] for s in spans).strip()))
    lines.sort(key=lambda l: (round(l["y"], 1), l["x"]))
    return lines


def page_key(page):
    """Identity of a page's text, used to spot overlay steps of one frame."""
    return frozenset((l["text"], round(l["x"]), round(l["y"])) for l in page_lines(page))


def looks_tabular(lines, title_bottom):
    """Rows of cells sharing a baseline: a table, better kept as an image."""
    ys = Counter(round(l["y"], 0) for l in lines if l["y"] > title_bottom and not l["vertical"])
    return sum(1 for y, n in ys.items() if n >= 3) >= 3


def graphic_ink(page, title_bottom):
    """How much non-text drawing sits in the body area."""
    n_draw = 0
    for d in page.get_drawings():
        r = d["rect"]
        if r.y1 > title_bottom and r.width * r.height > 4:
            n_draw += 1
    return n_draw, len(page.get_images())


# ---------------------------------------------------------------- theme
class Theme:
    """Font sizes, colours and indent stops learned from the whole document."""

    def __init__(self, doc, text_pages=None):
        self.page_w = doc[0].rect.width
        self.page_h = doc[0].rect.height
        band = self.page_h * 0.14
        fams, top_sizes = Counter(), Counter()
        pages = text_pages if text_pages else list(doc)
        allpages = [page_lines(p) for p in pages]
        self.all_lines = [page_lines(p) for p in doc]
        for lines in self.all_lines:
            for l in lines:
                if l["vertical"]:
                    continue
                fams[family(l["ink"][0]["font"])] += len(l["text"])
                if l["y"] < band:
                    top_sizes[(family(l["ink"][0]["font"]), round(l["size"], 2))] += 1
        self.family = fams.most_common(1)[0][0]
        # the frame-title style is the size that shows up at the top of most pages
        (tf, self.title_size), _ = top_sizes.most_common(1)[0]
        # body text: commonest size in the deck's own family, below the title band
        sizes, xs, cols = Counter(), Counter(), Counter()
        for lines in allpages:
            for l in lines:
                if l["vertical"] or family(l["ink"][0]["font"]) != self.family:
                    continue
                if abs(l["size"] - self.title_size) < 0.4 and l["y"] < band:
                    continue
                sizes[round(l["size"], 2)] += len(l["text"])
                for s in l["spans"]:
                    cols[s["color"]] += len(s["text"])
        self.body_size = sizes.most_common(1)[0][0]
        for lines in allpages:
            for l in lines:
                if (family(l["ink"][0]["font"]) == self.family
                        and abs(l["size"] - self.body_size) < 0.4 and not l["vertical"]):
                    xs[round(l["x"], 1)] += 1
        common = sorted(x for x, n in xs.items() if n >= 6)
        self.stops = self._cluster(common)
        self.colors = {c: n for c, n in cols.items() if not is_dim(c)}
        self.measure(allpages)
        self.title_color = 0
        for lines in allpages:
            hit = [l for l in lines if l["y"] < band and abs(l["size"] - self.title_size) < 0.4]
            if hit:
                self.title_color = hit[0]["spans"][0]["color"]
                break

    def measure(self, allpages):
        """Calibrate true point sizes and the body line height."""
        body_lines, title_lines, leads = [], [], []
        for lines in allpages:
            same = [l for l in lines
                    if not l["vertical"] and family(l["ink"][0]["font"]) == self.family]
            for l in same:
                one_style = len({(("Bold" in s["font"]), s["color"]) for s in l["ink"]}) == 1
                if abs(l["size"] - self.body_size) < 0.4 and one_style and "Bold" not in l["ink"][0]["font"]:
                    body_lines.append(l)
                elif abs(l["size"] - self.title_size) < 0.4 and one_style:
                    title_lines.append(l)
            for a, b in zip(same, same[1:]):
                dy = b["y"] - a["y"]
                if abs(a["x"] - b["x"]) < 1.0 and 0 < dy < self.body_size * 2.2:
                    leads.append(dy)
        self.body_size = fonts.calibrate(body_lines, "400") or self.body_size
        self.title_size = fonts.calibrate(title_lines, "display") or self.title_size
        self.line_height = statistics.median(leads) if leads else self.body_size * 1.2
        tops = [l["y"] for lines in allpages for l in lines
                if abs(l["size"] - self.title_size * 0.94) < 1.2 and l["y"] < self.page_h * 0.14]
        self.title_y = statistics.median(tops) if tops else self.page_h * 0.05

    @staticmethod
    def _cluster(vals, tol=2.5):
        out = []
        for v in vals:
            if not out or v - out[-1][-1] > tol:
                out.append([v])
            else:
                out[-1].append(v)
        return [sum(g) / len(g) for g in out]

    def level_of(self, x):
        """Indent level (0,1,2,...) for a line starting at x."""
        best, bi = 1e9, 0
        for i, s in enumerate(self.stops):
            if abs(x - s) < best:
                best, bi = abs(x - s), i
        return bi


# ---------------------------------------------------------------- grouping
def group_pages(doc, theme):
    """Consecutive pages that are overlay steps of one frame."""
    infos = []
    for p in doc:
        lines = page_lines(p)
        title = [l for l in lines if abs(l["size"] - theme.title_size) < 0.4
                 and l["y"] < theme.page_h * 0.14 and not l["vertical"]
                 and family(l["ink"][0]["font"]) == theme.family]
        infos.append(dict(page=p, lines=lines, title=" ".join(l["text"] for l in title),
                          title_bottom=max([l["y1"] for l in title], default=theme.page_h * 0.10),
                          key=page_key(p)))
    groups, cur = [], [0]
    for i in range(1, len(infos)):
        a, b = infos[i - 1], infos[i]
        same_title = a["title"] == b["title"]
        subset = a["key"] <= b["key"] or b["key"] <= a["key"]
        if same_title and subset and (a["title"] or subset):
            cur.append(i)
        else:
            groups.append(cur)
            cur = [i]
    groups.append(cur)
    return groups, infos


# ---------------------------------------------------------------- text slides
def style_key(s):
    return ("Bold" in s["font"], "Italic" in s["font"] or "Oblique" in s["font"],
            s["color"] if not is_dim(s["color"]) else 0)


def spans_html(spans):
    """Runs of identically styled characters become one <span>."""
    def esc(t):
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def wrap(key, text):
        if key is None or not text:
            return esc(text)
        bold, ital, col = key
        cls = (["b"] if bold else []) + (["i"] if ital else [])
        if col:
            cls.append("c%06x" % col)
        return f'<span class="{" ".join(cls)}">{esc(text)}</span>' if cls else esc(text)

    out, cur, buf = [], None, ""
    for s in spans:
        if not s["text"].strip():          # whitespace keeps the current style
            buf += s["text"]
            continue
        k = style_key(s)
        if k != cur:
            out.append(wrap(cur, buf))
            cur, buf = k, s["text"]
        else:
            buf += s["text"]
    out.append(wrap(cur, buf))
    return "".join(out)


def build_items(group_infos, theme):
    """Rebuild the body of a frame as nested items, with a reveal step each."""
    last = group_infos[-1]
    steps_of = {}
    for step, info in enumerate(group_infos):
        for l in info["lines"]:
            dark = all(is_dim(s["color"]) is False for s in l["spans"])
            k = (l["text"], round(l["x"]), round(l["y"]))
            if dark and k not in steps_of:
                steps_of[k] = step

    body = [l for l in last["lines"]
            if l["y"] > last["title_bottom"] + 1 and not l["vertical"]]
    items, cur = [], None
    prev_y = None
    for l in body:
        first = l["ink"][0]["text"].strip()
        marker = first[0] if first and first[0] in BULLETS + ARROWS else None
        enum = re.match(r"^(\d+)\.$", first)
        spans = list(l["spans"])
        mx = l["x"]
        if marker or enum:
            while spans and not spans[0]["text"].strip():
                spans.pop(0)
            spans = spans[1:]
            while spans and not spans[0]["text"].strip():
                spans.pop(0)
            if not spans:
                continue
        tx = round(spans[0]["bbox"][0], 1)
        step = steps_of.get((l["text"], round(l["x"]), round(l["y"])), 0)
        html = spans_html(spans).strip()
        gap = 0.0 if prev_y is None else round(max(0.0, (l["y"] - prev_y) - theme.line_height), 1)
        prev_y = l["y"]
        if marker or enum:
            kind = ("enum" if enum else "arrow" if marker in ARROWS else "bullet")
            cur = dict(kind=kind, level=theme.level_of(tx), tx=tx, mx=round(mx, 1),
                       marker=(marker or first), mcol=l["ink"][0]["color"],
                       html=html, step=step, gap=gap)
            items.append(cur)
        else:
            if cur and abs(cur["tx"] - tx) < 2.0 and gap < theme.line_height * 0.4:
                cur["html"] += " " + html          # wrapped continuation line
            else:
                cur = dict(kind="para", level=theme.level_of(tx), tx=tx, mx=round(tx, 1),
                           marker="", mcol=None, html=html, step=step, gap=gap)
                items.append(cur)
    return items


def items_html(items):
    """A flat list of blocks, each indented exactly where Beamer put it.

    Nesting <ul> would make every indent relative to its parent; keeping the
    list flat lets each block carry its true x from the PDF."""
    out = []
    for it in items:
        cls = "it " + it["kind"] + (f' f{it["step"]}' if it["step"] else "")
        mark = it.get("marker", "") or ""
        style = (f'--tx:{it["tx"]};--mx:{it["mx"]};--gap:{it["gap"]}'
                 + (f';--mcol:{hexcol(it["mcol"])}' if it.get("mcol") is not None else ""))
        out.append(f'<div class="{cls}" style="{style}" data-m="{mark}">{it["html"]}</div>')
    return "".join(out)


# ---------------------------------------------------------------- graphic slides
def png_of(page, clip, dpi=150):
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    return "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode()


def graphic_html(group_infos, theme):
    """One opaque image per overlay step, stacked; later steps cover earlier ones."""
    top = min(i["title_bottom"] for i in group_infos) + 2
    clip = pymupdf.Rect(0, top, theme.page_w, theme.page_h)
    layers = []
    for step, info in enumerate(group_infos):
        src = png_of(info["page"], clip)
        layers.append(f'<img class="pagelayer" data-in="{step}" src="{src}" alt="">')
    style = (f"left:0;right:0;top:calc({top}*var(--pt));bottom:0")
    return f'<div class="graphic" style="{style}">{"".join(layers)}</div>', clip


# ---------------------------------------------------------------- free slides
def free_html(info, theme):
    """Title/section pages: place each line where the PDF puts it."""
    out = []
    for l in info["lines"]:
        if l["vertical"]:
            continue
        cx = (l["x"] + max(s["bbox"][2] for s in l["ink"])) / 2
        centered = abs(cx - theme.page_w / 2) < 6
        col = hexcol(l["ink"][0]["color"])
        html = spans_html(l["spans"])
        pos = (f"left:0;right:0;text-align:center" if centered
               else f"left:calc({l['x']:.1f}*var(--pt))")
        out.append(f'<div class="freeline" style="{pos};'
                   f'top:calc({l["y"] - 0.22 * l["size"]:.1f}*var(--pt));'
                   f'font-size:calc({l["size"]:.2f}*var(--pt));color:{col}">{html}</div>')
    return "".join(out)


# ---------------------------------------------------------------- main
def text_pages_of(doc):
    """Pages that are plain prose - used to learn the body text style."""
    out = []
    for p in doc:
        lines = page_lines(p)
        band = p.rect.height * 0.14
        n_draw = sum(1 for d in p.get_drawings()
                     if d["rect"].y1 > band and d["rect"].width * d["rect"].height > 4)
        if p.get_images() or n_draw > 12 or looks_tabular(lines, band):
            continue
        out.append(p)
    return out


def convert(pdf_path, dpi=150, max_slides=None):
    doc = pymupdf.open(pdf_path)
    theme = Theme(doc, text_pages_of(doc))
    groups, infos = group_pages(doc, theme)
    slides, figures = [], []
    nums = {"figure": 0, "table": 0}
    for gi, g in enumerate(groups):
        if max_slides and gi >= max_slides:
            break
        gis = [infos[i] for i in g]
        last = gis[-1]
        title = last["title"]
        n_draw, n_img = graphic_ink(last["page"], last["title_bottom"])
        body_lines = [l for l in last["lines"] if l["y"] > last["title_bottom"] + 1]
        tabular = looks_tabular(last["lines"], last["title_bottom"])
        is_graphic = (n_img > 0 or n_draw > 12 or tabular)
        has_marks = any(l["ink"][0]["text"].strip()[:1] in BULLETS + ARROWS
                        for l in body_lines if l["ink"])
        if not title and not has_marks and not is_graphic and len(body_lines) <= 12:
            kind, html = "free", free_html(last, theme)
        elif is_graphic:
            kind, (html, clip) = "graphic", graphic_html(gis, theme)
            fkind = "table" if tabular else "figure"
            nums[fkind] += 1
            figures.append(dict(
                id=f"{fkind[:3]}{nums[fkind]}", kind=fkind, num=nums[fkind],
                title=title or f"Slide {gi+1}", page=last["page"].number + 1,
                source="deck", src=png_of(last["page"], clip, dpi=200)))
        else:
            _items = []
            kind = "text"
            _items = build_items(gis, theme)
            html = items_html(_items)
        box = None
        if kind == "text" and _items:
            body_ink = [l for l in last["lines"] if l["y"] > last["title_bottom"] + 1]
            box = dict(left=min(it["mx"] for it in _items),
                       right=round(max(max(s["bbox"][2] for s in l["ink"]) for l in body_ink), 1),
                       top=round(min(l["y"] for l in body_ink), 1))
        slides.append(dict(
            n=gi, kind=kind, title=title, box=box,
            pages=[i["page"].number + 1 for i in gis],
            steps=(len(gis) - 1 if kind == "graphic"
                   else max([it["step"] for it in _items] or [0]) if kind == "text" else 0),
            html=html, tags=auto_tags(title), notes=[]))
    return dict(theme=dict(page_w=theme.page_w, page_h=theme.page_h, family=theme.family,
                           body_size=theme.body_size, title_size=theme.title_size,
                           line_height=theme.line_height,
                           title_top=theme.title_y - 0.22 * theme.title_size,
                           title_color=hexcol(theme.title_color or 0),
                           colors=[hexcol(c) for c in theme.colors]),
                slides=slides, figures=figures)


STOP = set("the a an of in on for and or to with by is are do does this that what "
           "we our us it its as at from part".split())


def auto_tags(title):
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", (title or "").lower())
    return [w for w in words if w not in STOP][:4]


if __name__ == "__main__":
    import json, sys
    deck = convert(sys.argv[1])
    print(json.dumps({k: (v if k != "slides" else
                          [{kk: vv for kk, vv in s.items() if kk != "html"} for s in v])
                      for k, v in deck.items() if k != "figures"}, indent=1)[:4000])
