# extras

Not part of the presenter. Kept because it works and may be useful.

## converter-pdf/

An automatic Beamer PDF → slides converter: it measures a compiled deck's
geometry (font family, calibrated point sizes, line height, indent stops,
colours, positions), rebuilds text frames as HTML, keeps charts and tables as
page-exact images, and folds `\pause` overlays into reveal steps. It also reads
a paper PDF's "Figure N:" / "Table N:" captions into a figure index.

It emits a `deck.json` plus a bundled HTML in an older format. `deck-json-format.md`
describes that format. To feed its output to the current presenter:

    python3 tools/extract-deck.py <its-output>.html -o decks/talk.html

Superseded by converting slides in a Claude conversation, where the handful of
judgement calls per deck can actually be looked at.

## scenes/

A vector-character kit (people built from parts, so they can walk in, speak and
change) plus flat-style variants. Use it when one slide deserves a real
animation: build the SVG, drop it into that slide's `<section>`, and drive it
with `f1…f9` or `data-in` steps like anything else.
