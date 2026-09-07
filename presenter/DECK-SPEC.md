# The deck file

A deck is **one HTML file**. The presenter reads it; it does not care how the
file was made. Write it by hand, generate it, or have Claude convert your Beamer
slides into it.

The rules are deliberately few. Everything except `<section class="slide">` is
optional, and sensible defaults are guessed from the content.

---

## The minimum

```html
<section class="slide">
  <h1>Why households matter</h1>
  <p>Most entrepreneurs are married.</p>
</section>

<section class="slide">
  <h1>The 2014 oil collapse</h1>
  <img src="data:image/png;base64,iVBORw0…">
</section>
```

That is a working two-slide deck. Titles come from the `<h1>`, so `/go oil`
already finds the second slide.

---

## Slides

Each `<section class="slide">` is one slide. Attributes, all optional:

| attribute | meaning | default |
|---|---|---|
| `data-title` | the name used by `/go` and shown in the pane | text of the first `h1`, `h2` or `.ftitle` |
| `data-tags` | comma-separated, for `/go #tag` | words from the title |
| `data-steps` | how many times `→` advances within the slide | highest `f1…f9` class found inside |
| `data-notes` | prepared notes, one per line (`\|` also splits) | none |
| `id` | also usable as a tag by `/go` | none |

## Reveal steps

Anything with class `f1` … `f9` is dimmed until that step. `data-steps` is
inferred from the highest one present, so this slide advances twice:

```html
<section class="slide">
  <h1>What we do</h1>
  <p>Empirics: Canada's 2014 oil shock.</p>
  <p class="f1">Model: heterogeneous agents, endogenous occupation choice.</p>
  <p class="f2">Result: marriage amplifies the shock.</p>
</section>
```

For a build made of whole images (a chart gaining callouts), stack them and give
each one `data-in="N"`; the presenter shows it from step N onward:

```html
<section class="slide" data-steps="2">
  <h1>Design</h1>
  <div class="stack">
    <img data-in="0" src="data:image/png;base64,…">   <!-- base picture -->
    <img data-in="1" src="data:image/png;base64,…">   <!-- + first callout -->
    <img data-in="2" src="data:image/png;base64,…">   <!-- + second callout -->
  </div>
</section>
```

`.stack` is provided by the app: children are absolutely positioned on top of
each other, later ones opaque.

---

## Deck metadata

An optional JSON block anywhere in the file. Everything in it is optional too.

```html
<script type="application/json" id="deck-meta">
{
  "id":    "unsw-2026",                 // keys your notes and edits; keep it stable
  "title": "Entrepreneurs and (Risky) Spouses",
  "size":  [453.543, 255.118],          // slide size in points; sets the aspect ratio
                                        // and the --pt unit. Default [960, 540].
  "api":   "http://localhost:8787",     // backend for /ask, /claude, /price …

  "notes": {                            // prepared notes, by slide number or title
    "1":  ["Joint work with Valentina (SMU)."],
    "The 2014 oil collapse": ["WTI $105 → $50 in H2 2014.", "OPEC held output, Nov 2014."]
  },

  "figures": [                          // what /fig and /table open
    { "kind": "figure", "num": 3, "title": "Spousal job loss around the shock",
      "src": "data:image/png;base64,…", "page": 14, "source": "paper" },
    { "kind": "table",  "num": 1, "title": "Balancing tests in 2013",
      "src": "figs/table1.png" }
  ]
}
</script>
```

`id` matters: notes, tags and slide edits are stored under it, so keep it the
same across rebuilds of the same talk and different between talks.

---

## Sizing and CSS

The presenter sets two things you can build on:

* `--pt` — one point of the declared slide size. With `"size": [453.543, 255.118]`
  (Beamer's default 16:9 frame), `calc(12*var(--pt))` is 12pt at any projector
  resolution.
* the deck box keeps the declared aspect ratio and scales to the window.

Put your own CSS in a `<style>` block in the deck file; it is injected after the
app's and wins. Position things absolutely against the slide when you need
Beamer-exact placement:

```html
<style>
  .slide      { font-family: "Latin Modern Sans", system-ui; }
  .ftitle     { position:absolute; left:0; right:0; top:calc(9*var(--pt));
                text-align:center; color:#19196e; font-size:calc(14.35*var(--pt)); }
  .body       { position:absolute; left:calc(40*var(--pt)); right:calc(30*var(--pt));
                top:calc(52*var(--pt)); }
</style>
```

**Fonts and images must be self-contained**: embed fonts as `data:` URIs in
`@font-face`, and images as `data:` URIs — or run `bundle.py`, which inlines
every local file it finds and writes one standalone HTML you can present from a
USB stick. A deck opened by drag-and-drop cannot load files next to it, because
browsers do not allow it.

---

## Editable regions

Editing is off until you press `E`. When it is on, the app makes every element
carrying `data-edit="<key>"` editable and remembers what you changed under that
key. If you mark nothing, the app falls back to making each slide's title and
its `.body` (or the whole slide) editable.

```html
<h1 class="ftitle" data-edit="s7-title">Empirical design</h1>
<div class="body" data-edit="s7-body"> … </div>
```

Keep the keys stable across rebuilds and your edits survive them.

---

## Scripts

`<script>` inside a deck is **not** executed unless it carries `data-deck-script`.
That way a file that already contains a presenter (a bundled deck) can be opened
as a plain deck without two apps fighting. Add the attribute when a slide really
needs code:

```html
<script data-deck-script>
  /* e.g. wire up a custom animation on slide 8 */
</script>
```

---

## Checklist for a generated deck

- [ ] every slide is `<section class="slide">`
- [ ] titles present (`<h1>`, `.ftitle`, or `data-title`)
- [ ] images and fonts are `data:` URIs, or you will run `bundle.py`
- [ ] progressive reveals use `f1…f9`, image builds use `.stack` + `data-in`
- [ ] `deck-meta` has a stable `id`, the `size` in points, and the figure index
- [ ] opens in a browser on its own and looks right before the presenter sees it
