"""
Pull the figures and tables out of the paper behind the talk.

Finds "Figure 3: ..." / "Table 2. ..." captions, works out how much of the page
the float occupies, and crops it. The presenter then opens any of them mid-talk
with /fig 3 or /table 2, without leaving the slide.
"""
import base64, re
import pymupdf

CAPTION = re.compile(r"^\s*(Figure|Table|Fig\.?|Panel)\s+([A-Z]?\.?\d+[A-Za-z]?)\s*[:.—-]?\s*(.*)$",
                     re.I)


def lines_of(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            spans = [s for s in l["spans"] if s["text"].strip()]
            if spans:
                out.append(dict(text="".join(s["text"] for s in spans).strip(),
                                x0=min(s["bbox"][0] for s in spans),
                                y0=min(s["bbox"][1] for s in spans),
                                y1=max(s["bbox"][3] for s in spans),
                                x1=max(s["bbox"][2] for s in spans)))
    out.sort(key=lambda l: (round(l["y0"], 1), l["x0"]))
    return out


def float_box(page, lines, idx, above):
    """Extent of the float attached to the caption at `lines[idx]`."""
    cap = lines[idx]
    top, bot = cap["y0"], cap["y1"]
    body = [l for i, l in enumerate(lines) if i != idx]
    if above:                      # table: content sits above the caption
        gap_top = 0.0
        for l in body:
            if l["y1"] <= cap["y0"] - 1:
                gap_top = max(gap_top, l["y1"]) if l["y1"] < cap["y0"] - 26 else gap_top
        top = max(page.rect.y0 + 4, gap_top + 2 if gap_top else page.rect.y0 + 4)
        # everything between the previous prose block and the caption
        prev = [l["y1"] for l in body if l["y1"] < cap["y0"] - 4]
        starts = [l["y0"] for l in body if cap["y0"] - 4 > l["y0"]]
        top = min(starts) if starts else top
    else:                          # figure: content sits below the caption
        after = [l["y0"] for l in body if l["y0"] > cap["y1"] + 2]
        bot = min(after) - 3 if after else page.rect.y1 - 4
    # include drawings/images that overlap the band
    for d in page.get_drawings():
        r = d["rect"]
        if r.y1 > top - 60 and r.y0 < bot + 60 and r.width * r.height > 30:
            top, bot = min(top, r.y0), max(bot, r.y1)
    for img in page.get_images(full=True):
        for r in page.get_image_rects(img[0]):
            if r.y1 > top - 60 and r.y0 < bot + 60:
                top, bot = min(top, r.y0), max(bot, r.y1)
    top = max(page.rect.y0, top - 6)
    bot = min(page.rect.y1, max(bot, cap["y1"]) + 6)
    return pymupdf.Rect(page.rect.x0 + 2, top, page.rect.x1 - 2, bot)


def extract(pdf_path, dpi=200, max_items=80):
    doc = pymupdf.open(pdf_path)
    seen, out = set(), []
    for page in doc:
        lines = lines_of(page)
        for i, l in enumerate(lines):
            m = CAPTION.match(l["text"])
            if not m or len(l["text"]) < 8:
                continue
            kind = "table" if m.group(1).lower().startswith("table") else "figure"
            num = m.group(2)
            key = (kind, num)
            if key in seen:
                continue
            caption = m.group(3).strip() or l["text"]
            # captions often continue on the next line
            j = i + 1
            while j < len(lines) and len(caption) < 90 and lines[j]["y0"] - lines[i]["y1"] < 12 \
                    and not CAPTION.match(lines[j]["text"]):
                caption += " " + lines[j]["text"]
                j += 1
            rect = float_box(page, lines, i, above=(kind == "table"))
            if rect.height < 40 or rect.width < 40:
                continue
            seen.add(key)
            pix = page.get_pixmap(dpi=dpi, clip=rect)
            out.append(dict(id=f"{kind[:3]}{num}", kind=kind, num=num,
                            title=caption[:160], page=page.number + 1, source="paper",
                            src="data:image/png;base64," +
                                base64.b64encode(pix.tobytes("png")).decode()))
            if len(out) >= max_items:
                return out
    out.sort(key=lambda f: (f["kind"], _numkey(f["num"])))
    return out


def _numkey(n):
    m = re.search(r"\d+", str(n))
    return (re.sub(r"\d+", "", str(n)), int(m.group()) if m else 0)


if __name__ == "__main__":
    import sys
    for f in extract(sys.argv[1]):
        print(f'{f["kind"]:<7} {f["num"]:<5} p{f["page"]:<4} {f["title"][:70]}')
