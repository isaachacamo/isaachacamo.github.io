# Presenter

A tool for giving lectures and seminars from HTML slides: a command box, a notes
pane, every figure and table from the paper one keystroke away, and Claude on
call — without leaving the slide.

The tool **plays decks; it does not make them.** A deck is a plain HTML file.
Convert your Beamer slides into one in a Claude conversation, where you can look
at the result and adjust it, then hand the file to the presenter. The contract
that file has to meet is [`DECK-SPEC.md`](DECK-SPEC.md), and
[`examples/example-deck.html`](examples/example-deck.html) is a working template.

---

## Start

```bash
open app/presenter.html          # or double-click it
```

Drop a deck onto the page. That is the whole setup — no install, no server.
Your last deck reopens by itself next time.

For the version you present from, staple deck and app into one file:

```bash
python3 bundle.py decks/talk.html -o ~/talks/unsw.html
```

That file needs nothing else: no network, no picker, no folder next to it. Put
it on a USB stick and it opens on any machine.

---

## During a talk

| key | |
|---|---|
| `→` `←` `space` | next / previous step, then slide |
| `/` or `⌘K` | command box |
| `E` | editing on / off — **off by default**, so nothing changes by accident |
| `H` or `⌘\` | show / hide the side pane |
| `B` | back to the slide you jumped from |
| `F` | full screen |
| `O` | open a different deck |
| `Esc` | close whatever is open |

### Commands

| | |
|---|---|
| `/go 14` · `/go identification` · `/go #robustness` | jump by number, title, or tag |
| `/back` | return to where you jumped from |
| `/fig 3` · `/table 2` · `/fig balance` | open a figure or table over the slide — `←/→` for the next, click to zoom, `Esc` to close |
| `/find placebo` | search figures, tables and slides together |
| `/ask …` | Claude, answering **only** from this deck |
| `/claude …` | Claude, unrestricted |
| `/price AAPL` · `/yield 10y` · `/series UNRATE` · `/fx USDCAD` · `/news oil` | live numbers, dropped into the pane |
| `/note …` · `/tag name` | a note or a tag on this slide |
| `/edit on\|off` · `/revert [all]` | slide editing; undo your edits |
| `/open` · `/help` | load another deck; list everything |

Anything you type that does not start with `/` is saved as a note on the current
slide. Select text on a slide and an **Ask Claude about this** button appears.

The pane shows the notes you prepared (in the deck file) above anything you add
live. Notes, tags and edits are stored per deck in the browser, keyed by the
deck's `id`, so they survive rebuilds of the same talk.

The AI and data commands need the optional backend in [`server/`](server) —
Google sign-in, an allowlist, and your API keys kept server-side. Without it
those commands say so and everything else works normally.

---

## Making a deck in a Claude conversation

Attach your Beamer PDF (and the `.tex` if you have it, and the paper), then ask
for a deck that follows the spec. Something like:

> Convert the attached Beamer PDF into a single HTML deck for my presenter tool.
> Rules: every slide is `<section class="slide">`; keep the exact Beamer look by
> measuring the PDF (font family, point sizes, line height, indents, colours,
> positions) rather than guessing; text slides become real editable HTML, charts
> and tables stay as page-exact images; fold `\pause` overlays into one slide
> with `f1…f9` classes, and picture builds into `.stack` images with `data-in`;
> embed fonts and images as `data:` URIs. Add a `deck-meta` JSON block with a
> stable `id`, the slide `size` in points, my `\note{}` speaker notes, tags, and
> a `figures` list built from the paper's "Figure N:" and "Table N:" captions.
> Then show me a few slides side by side against the original pages.

Iterate there until it looks right, save the file into `decks/`, and open it in
the presenter. `DECK-SPEC.md` is written to be pasted into that conversation.

---

## Online

The app is static files, so GitHub Pages will host it for free:
`https://<you>.github.io/presenter/`. Your decks do not have to go with it — a
deck you drop on the page is read in the browser and never uploaded, so the
public site can host a private talk. [`DEPLOY.md`](DEPLOY.md) has the steps.

## Layout

```
app/            presenter.html   open this
                presenter.js     the player: palette, pane, jumps, lightbox, edit mode
                presenter.css
bundle.py       deck + app -> one standalone file, local images and fonts inlined
tools/          extract-deck.py  pull a clean deck out of a page that already has slides
                make-corpus.py   the deck's text, for the server's grounded /ask
examples/       example-deck.html  a working deck that exercises every feature
decks/          your decks
server/         optional backend: Google sign-in, Claude, live data, note sync
extras/         the old PDF/LaTeX converter, kept for reference; not part of the tool
DECK-SPEC.md    what a deck file must contain
DEPLOY.md       putting the app on GitHub Pages (and keeping decks private)
index.html      entry point when hosted; forwards to app/presenter.html
```

## Notes

* The deck's own `<style>` is injected after the app's, so the deck controls how
  slides look and the app never fights it. `--pt` is one point of the slide size
  the deck declares, which is what makes Beamer measurements transfer directly.
* `<script>` inside a deck is ignored unless it carries `data-deck-script`, so a
  file that already contains a presenter can be opened as a plain deck.
* Everything is stored in the browser until you run the backend; then notes and
  tags follow your Google account between machines.
