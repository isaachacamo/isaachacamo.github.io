# Putting the presenter online

The app is static HTML, CSS and JavaScript, so GitHub Pages hosts it for free
and it needs no build step.

**Your slides do not have to go online with it.** GitHub Pages is public, but a
deck you drag onto the page never leaves your browser — the app reads it with
the File API. So the normal arrangement is: the app is public, your decks stay
on your laptop. Publish a deck only when you actually want the world to see it.

---

## 1. Make the repository

From the project folder:

```bash
cd "~/Dropbox/Claude Projects/presentation tool"
git init -b main
git add .
git commit -m "Presenter: an HTML deck player for lectures and seminars"
```

`.gitignore` already excludes `decks/` (your talks are usually unpublished work,
and a bundled deck runs to several megabytes), `server/.env` (your API keys) and
`server/notes/`. Check what you are about to publish before you push:

```bash
git status --short
git ls-files | head -40
```

Create an empty repository on GitHub — call it `presenter`, no README, no
`.gitignore` — then:

```bash
git remote add origin https://github.com/<you>/presenter.git
git push -u origin main
```

## 2. Turn Pages on

On GitHub: **Settings → Pages → Build and deployment**. Set *Source* to
**Deploy from a branch**, *Branch* to `main`, folder `/ (root)`, then **Save**.
A minute later the site is at:

```
https://<you>.github.io/presenter/
```

That URL forwards to `app/presenter.html`. Bookmark it; drop a deck on it and
present. The `.nojekyll` file in the repo stops GitHub trying to run Jekyll over
the files.

### If you want it at the top level

A repository named exactly `<you>.github.io` is served at
`https://<you>.github.io/` with no path. If you already use that repository for
an academic homepage, put this project in a subfolder of it instead — say
`presenter/` — and it will appear at `https://<you>.github.io/presenter/`
without disturbing the rest of the site.

## 3. Use it

Open the URL, drop `your-talk.html` on it, present. The browser remembers the
last deck, so on the day you can just open the bookmark.

Two conveniences once it is hosted:

* **Link straight to a deck** you have published in the repo:
  `https://<you>.github.io/presenter/?deck=decks/unsw.html`
  Only works for decks that are actually online — a private deck stays a
  drag-and-drop.
* **Share a talk with one link** by publishing a bundled file, which carries the
  player inside it:
  ```bash
  python3 bundle.py decks/unsw.html -o decks/unsw-presenter.html
  git add -f decks/unsw-presenter.html && git commit -m "UNSW talk" && git push
  ```
  → `https://<you>.github.io/presenter/decks/unsw-presenter.html`
  Anyone who opens that sees the slides, the pane and the figures. Remember that
  it is public: only do this for work you are happy to circulate.

---

## Keeping decks private

Options, in the order most people want them:

1. **Don't publish them.** Drag the local file onto the hosted app. Nothing
   leaves the machine. This is the default and it costs nothing.
2. **Present offline.** `python3 bundle.py` gives you a single file that needs
   no network at all — the safest option for a conference room with bad wifi.
3. **A private host.** If you want `?deck=` to work against decks that are not
   public, you need a host that can authenticate: a private repo on GitHub
   Enterprise, or Netlify/Cloudflare Pages with access control, or the backend
   in `server/` serving `/decks` behind Google sign-in. The last one is already
   written: `DECK_DIR` points at a folder and `express.static` serves it.

Note that a page served over `https://` cannot fetch a deck from a plain
`http://` host — browsers block that. Use https for anything you host.

---

## The backend

GitHub Pages serves static files only, so `/ask`, `/claude` and the data
commands need the Node server in `server/` running somewhere else. Render,
Fly.io and Railway all take it as-is; it is a plain Express app with a
`start` script.

Once it is deployed, point decks at it in their `deck-meta`:

```json
{ "id": "unsw-2026", "api": "https://presenter-api.onrender.com" }
```

and add your Pages origin to `ALLOWED_ORIGINS` in the server's `.env`:

```
ALLOWED_ORIGINS=https://<you>.github.io
```

Two things that catch people out:

* **Mixed content.** From an `https://` Pages site you cannot call an
  `http://` API. Deploy the server with https (all the hosts above do this by
  default). `http://localhost` is the one exception most browsers allow, so
  developing against a local server still works.
* **Sign-in origins.** In the Google Cloud console, add
  `https://<you>.github.io` as an authorised JavaScript origin for your OAuth
  client, and put the same client ID into `server/signin.html`.

Keep `server/.env` out of git — it is already in `.gitignore`. Set the keys as
environment variables in the host's dashboard instead.

---

## Updating

```bash
git add app tools bundle.py *.md
git commit -m "presenter: bigger lightbox"
git push
```

Pages redeploys in under a minute. Anyone using the site gets the new version on
their next reload; their notes, tags and edits are stored per deck in their own
browser and are not affected.

---

## Other hosts

Nothing here is GitHub-specific — it is a folder of static files.

* **Netlify / Cloudflare Pages**: drag the folder onto their dashboard, or
  connect the repo. Both offer password protection on the free-ish tiers, which
  GitHub Pages does not.
* **Your university web space**: copy `index.html`, `app/` and, if you want,
  `decks/` over by scp or rsync. Often the simplest option, and it can sit
  behind the university's own authentication.
* **No host at all**: `bundle.py` output is one file. Email it to yourself,
  keep it on a USB stick, open it anywhere.
