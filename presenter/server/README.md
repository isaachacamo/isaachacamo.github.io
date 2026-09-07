# Backend

Optional. The deck works without it; this is what makes `/ask`, `/claude` and the
data commands live, and what lets notes follow you between machines.

The point of the design: **the browser never holds an API key**. Google sign-in
decides who you are, an allowlist decides whether you are let in, and the server
holds the keys and calls Claude and the data providers on your behalf.

## Run it

```bash
cd server
cp .env.example .env         # fill in the keys
npm install
npm start                    # http://localhost:8787
```

Point a deck at it with one line in the deck's `deck-meta` block:

```json
{ "id": "unsw-2026", "api": "http://localhost:8787" }
```

For deck-wide grounding, write the deck's text where the server looks for it:

```bash
python3 tools/make-corpus.py decks/talk.html -o server/decks/unsw-2026/corpus.json
```

For local work you can skip sign-in entirely with `AUTH_DISABLED=1` in `.env`.

## Signing in

`signin.html` is a one-page Google sign-in. Put your OAuth client ID in it, open
it once, and the ID token is stored in the browser; the presenter sends it with
every request. Serve it from the same origin as your decks.

To get a client ID: Google Cloud Console → APIs & Services → Credentials →
OAuth client ID → Web application, with your deck's origin as an authorised
JavaScript origin.

## Endpoints

| | |
|---|---|
| `POST /ask` | Claude, with a system prompt that forbids answering from anything but the deck's `corpus.json` (generate it with `tools/make-corpus.py`) |
| `POST /claude` | Claude, unrestricted, bigger model |
| `POST /data/price` | quote (Finnhub) |
| `POST /data/yield` `POST /data/series` | Treasury yields and any FRED series |
| `POST /data/fx` | exchange rate (Frankfurter, no key needed) |
| `POST /data/news` | headline + first paragraph (GNews) |
| `GET/POST /notes/:deck` | note sync, per signed-in user |

All of them answer in plain text (streamed, for the model calls) or JSON, which
is what the presenter's `callApi` expects.

## Costs and limits

`/ask` uses the fast model and sends only the current slide plus the handful of
retrieved chunks, so a lecture's worth of questions is cents. `DAILY_TOKEN_LIMIT`
caps each account per day. `MODEL_FAST` and `MODEL_DEEP` are set in `.env`, so
switching models is a config change, not a code change.

## Deploying

Any Node host works. Vercel: put `server.js` behind a serverless function and
move `NOTES_DIR` to a database, since serverless filesystems are not durable.
Fly.io or Render keep the filesystem and need no changes.
