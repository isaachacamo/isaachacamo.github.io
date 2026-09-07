"""
Font handling: embed the deck's typeface in the bundle and calibrate sizes.

PDF font-size attributes are not reliable for Type 1 subsets (Beamer's Latin
Modern reports ~8.97 for text that is actually set at ~9.2pt), so we measure:
size = rendered width of a line / sum of glyph advances in the real font.
"""
import base64, os, re, statistics
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "assets", "fonts")

# family reported by the PDF -> the woff2 files we ship for it
BUNDLED = {
    "LMSans": {"400": "lmsans10-regular.woff2", "700": "lmsans10-bold.woff2",
               "italic": "lmsans10-oblique.woff2", "display": "lmsans12-regular.woff2"},
}
OTF = {
    "400": "/usr/share/texmf/fonts/opentype/public/lm/lmsans10-regular.otf",
    "700": "/usr/share/texmf/fonts/opentype/public/lm/lmsans10-bold.otf",
    "display": "/usr/share/texmf/fonts/opentype/public/lm/lmsans12-regular.otf",
}


@lru_cache(maxsize=8)
def _metrics(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    return f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm


def advance(text, weight="400"):
    """Width of `text` in em, or None if the font isn't available here."""
    path = OTF.get(weight)
    if not path or not os.path.exists(path):
        return None
    cmap, hmtx, upm = _metrics(path)
    total = 0.0
    for ch in text:
        gid = cmap.get(ord(ch))
        if gid is None:
            return None
        total += hmtx[gid][0] / upm
    return total


def calibrate(lines, weight="400"):
    """True point size of a set of single-style lines, measured from advances."""
    est = []
    for l in lines:
        ink = l["ink"]
        if len(ink) == 0:
            continue
        text = "".join(s["text"] for s in l["spans"]).rstrip()
        w = max(s["bbox"][2] for s in ink) - min(s["bbox"][0] for s in ink)
        adv = advance(text.strip(), weight)
        if adv and adv > 3 and w > 20:
            est.append(w / adv)
    return statistics.median(est) if len(est) >= 3 else None


def css_faces(family="LMSans"):
    """@font-face rules with the woff2 files inlined, so the deck works offline."""
    files = BUNDLED.get(family)
    if not files:
        return "", "system-ui, sans-serif", "system-ui, sans-serif"
    out = []
    for key, weight, style, name in (("400", "400", "normal", "DeckSans"),
                                     ("700", "700", "normal", "DeckSans"),
                                     ("italic", "400", "italic", "DeckSans"),
                                     ("display", "400", "normal", "DeckDisplay")):
        p = os.path.join(FONT_DIR, files[key])
        if not os.path.exists(p):
            continue
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        out.append(f'@font-face{{font-family:"{name}";font-weight:{weight};'
                   f'font-style:{style};font-display:block;'
                   f'src:url(data:font/woff2;base64,{b64}) format("woff2")}}')
    return ("\n".join(out),
            '"DeckSans", system-ui, sans-serif',
            '"DeckDisplay", "DeckSans", system-ui, sans-serif')
