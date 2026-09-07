# deck.json

What the converter writes and the presenter reads. Edit it by hand whenever the
automatic pass gets something wrong, then rebuild with `--from-json`.

```jsonc
{
  "theme": {
    "page_w": 453.54, "page_h": 255.12,   // slide size in points, from the PDF
    "family": "LMSans",                   // which bundled font to embed
    "body_size": 9.21,                    // measured, not the PDF's own claim
    "title_size": 14.35,
    "line_height": 10.96,
    "title_top": 8.2,                     // where the frame title sits
    "title_color": "#1a1a6e",
    "colors": ["#1a1a6e", "#851f26", "#008080"]   // accents -> .c<hex> classes
  },

  "slides": [
    {
      "n": 5,
      "kind": "text",                     // text | graphic | free
      "title": "Background: The 2014 Oil Price Collapse",
      "pages": [8],                       // pages of the source PDF it came from
      "steps": 0,                         // reveal steps (Beamer overlays)
      "box": { "left": 40.1, "right": 423.9, "top": 51.9 },   // text slides only
      "html": "<div class=\"it bullet\" style=\"--tx:50.2;--mx:40.1;--gap:0\" …>",
      "tags": ["background", "oil"],      // /go #oil
      "notes": ["WTI fell from $105 to $50 in H2 2014."],     // shown in the pane
      "sources": ["figs/oil_unemp.pdf"]   // from \includegraphics, when --tex is used
    }
  ],

  "figures": [
    {
      "id": "tab1", "kind": "table", "num": 1,
      "title": "Balancing Tests in 2013",
      "page": 20, "source": "paper",      // paper | deck
      "src": "data:image/png;base64,…"    // opened by /table 1
    }
  ],

  "extra_css": ""                         // appended to the bundle, for one-offs
}
```

## The three kinds of slide

**`text`** — rebuilt as real HTML. The body is a `<div class="body">` positioned
at `box`, holding a flat list of `<div class="it …">` blocks. Flat, not nested:
each block carries its own `--tx` (text x) and `--mx` (marker x) straight from
the PDF, so indentation is exact rather than inherited. `--gap` is the extra
space above the block *beyond* one normal line. Markers come from `data-m`;
bullets are drawn as a dot, arrows as the glyph.

**`graphic`** — the frame body as one image per reveal step, stacked. Later steps
are opaque and cover earlier ones, so a build replays exactly as it did in the
PDF. Titles stay live text above the image.

**`free`** — title and section pages: each line absolutely positioned where the
PDF put it. Faithful for anything centred and sparse.

## Reveal steps

`steps` is how many times `→` advances before moving on. In text slides an item
with class `f2` appears at step 2 (dimmed before that). In graphic slides the
image with `data-in="2"` is shown from step 2.

## Editable regions

`render.py` marks each title and body with `data-edit="s5-t"` / `data-edit="s5-b"`.
Edit mode toggles `contenteditable` on exactly those, and edits are stored under
that key — so they survive a rebuild as long as slide numbering does not change.

## Hand-written slides

Nothing stops you writing a slide's `html` yourself. That is how the animated
scenes work: build the SVG with `src/scenes/characters.py`, paste it into the
slide's `html`, set `steps`, and add any keyframes to `extra_css`.
