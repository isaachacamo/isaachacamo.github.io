/**
 * Presenter backend.
 *
 *   - Google sign-in decides WHO may use the tool; an allowlist of e-mail
 *     addresses decides who is let through. The browser never sees an API key.
 *   - /ask      answers only from the material of the deck you are showing
 *   - /claude   unrestricted, same key, no context restriction
 *   - /data/*   live numbers: quotes, Treasury yields, FRED series, FX, news
 *   - /notes    per-slide notes, so they follow you between machines
 *
 * Run:  cp .env.example .env && npm install && npm start
 */
import express from "express";
import cors from "cors";
import fs from "node:fs";
import path from "node:path";
import { OAuth2Client } from "google-auth-library";
import Anthropic from "@anthropic-ai/sdk";

const PORT = process.env.PORT || 8787;
const ALLOWED = (process.env.ALLOWED_EMAILS || "").split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const DAILY_LIMIT = Number(process.env.DAILY_TOKEN_LIMIT || 400000);

const google = new OAuth2Client(GOOGLE_CLIENT_ID);
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MODEL_FAST = process.env.MODEL_FAST || "claude-sonnet-4-5";
const MODEL_DEEP = process.env.MODEL_DEEP || "claude-opus-4-6";

const app = express();
app.use(cors({ origin: (process.env.ALLOWED_ORIGINS || "*").split(","), credentials: false }));
app.use(express.json({ limit: "1mb" }));

/* ---------------------------------------------------------------- auth */
const usage = new Map();                       // email -> {day, tokens}

async function auth(req, res, next) {
  if (process.env.AUTH_DISABLED === "1") { req.user = { email: "local@localhost" }; return next(); }
  const token = (req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (!token) return res.status(401).send("Sign in with Google first.");
  try {
    const ticket = await google.verifyIdToken({ idToken: token, audience: GOOGLE_CLIENT_ID });
    const { email, email_verified } = ticket.getPayload();
    if (!email_verified) return res.status(403).send("Unverified Google account.");
    if (ALLOWED.length && !ALLOWED.includes(email.toLowerCase()))
      return res.status(403).send(`${email} is not on the allowlist.`);
    req.user = { email };
    next();
  } catch (e) {
    res.status(401).send("Could not verify that sign-in.");
  }
}

function budget(email, tokens) {
  const day = new Date().toISOString().slice(0, 10);
  const u = usage.get(email) || { day, tokens: 0 };
  if (u.day !== day) { u.day = day; u.tokens = 0; }
  u.tokens += tokens;
  usage.set(email, u);
  return u.tokens <= DAILY_LIMIT;
}

/* ---------------------------------------------------------------- Claude */
const GROUNDED = `You are helping a professor answer questions during a live lecture.
Answer ONLY from the lecture material provided below. If the answer is not in the
material, say plainly that this lecture does not cover it and stop - do not fill
the gap from general knowledge. Two or three sentences unless asked for more;
this is being read aloud to a room.`;

const OPEN = `You are helping a professor during a live lecture. Be brief and concrete -
two or three sentences unless more is asked for. If a claim is uncertain, say so.`;

async function stream(res, { model, system, prompt, maxTokens = 700, email }) {
  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache");
  let used = 0;
  try {
    const s = await anthropic.messages.stream({
      model, max_tokens: maxTokens, system,
      messages: [{ role: "user", content: prompt }],
    });
    for await (const ev of s) {
      if (ev.type === "content_block_delta" && ev.delta.type === "text_delta") {
        used += 1;
        res.write(ev.delta.text);
      }
    }
    const final = await s.finalMessage();
    budget(email, (final.usage?.input_tokens || 0) + (final.usage?.output_tokens || 0));
    res.end();
  } catch (e) {
    res.write(`\n[model error: ${e.message}]`);
    res.end();
  }
}

function contextBlock(c = {}) {
  return [
    c.deck && `Deck: ${c.deck}`,
    c.title && `Current slide (${c.slide}): ${c.title}`,
    c.tags?.length && `Tags: ${c.tags.join(", ")}`,
    c.text && `Slide text:\n${c.text}`,
    c.notes?.length && `Speaker notes:\n- ${c.notes.join("\n- ")}`,
    c.corpus && `Related material:\n${c.corpus}`,
  ].filter(Boolean).join("\n\n");
}

app.post("/ask", auth, async (req, res) => {
  const { question, context } = req.body || {};
  if (!budget(req.user.email, 0)) return res.status(429).send("Daily budget reached.");
  const corpus = retrieve(question, context);
  await stream(res, {
    model: MODEL_FAST, system: GROUNDED, email: req.user.email,
    prompt: `LECTURE MATERIAL\n${contextBlock({ ...context, corpus })}\n\nQUESTION\n${question}`,
  });
});

app.post("/claude", auth, async (req, res) => {
  const { question, context } = req.body || {};
  if (!budget(req.user.email, 0)) return res.status(429).send("Daily budget reached.");
  await stream(res, {
    model: MODEL_DEEP, system: OPEN, email: req.user.email, maxTokens: 1200,
    prompt: `${contextBlock(context)}\n\nQUESTION\n${question}`,
  });
});

/* -------------------------------------------------- lecture corpus (grounding)
 * decks/<id>/corpus.json is an array of {title, text} chunks written by the
 * converter. A keyword score is enough for one course; swap in embeddings if
 * the corpus grows past a few hundred pages.                                */
const CORPUS = new Map();
function corpusOf(deckId) {
  if (CORPUS.has(deckId)) return CORPUS.get(deckId);
  const p = path.join(process.env.DECK_DIR || "./decks", deckId, "corpus.json");
  const c = fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : [];
  CORPUS.set(deckId, c);
  return c;
}
function retrieve(question, context = {}, k = 6) {
  const chunks = corpusOf(context.deckId || "default");
  if (!chunks.length) return "";
  const words = (question || "").toLowerCase().match(/[a-z]{4,}/g) || [];
  return chunks
    .map(c => ({ c, s: words.reduce((n, w) => n + (c.text.toLowerCase().includes(w) ? 1 : 0), 0) }))
    .filter(x => x.s > 0).sort((a, b) => b.s - a.s).slice(0, k)
    .map(x => `[${x.c.title}] ${x.c.text}`).join("\n\n");
}

/* ---------------------------------------------------------------- live data */
const cache = new Map();
async function cached(key, ttlMs, fn) {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.t < ttlMs) return hit.v;
  const v = await fn();
  cache.set(key, { t: Date.now(), v });
  return v;
}
const jget = async url => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} from ${new URL(url).host}`);
  return r.json();
};

app.post("/data/price", auth, async (req, res) => {
  const symbol = String(req.body.symbol || "").toUpperCase().slice(0, 12);
  try {
    const j = await cached("q" + symbol, 60_000, () => jget(
      `https://finnhub.io/api/v1/quote?symbol=${symbol}&token=${process.env.FINNHUB_KEY}`));
    if (!j || j.c === 0) return res.json({ text: `No quote for ${symbol}.` });
    res.json({ quote: { symbol, price: j.c.toFixed(2), change: (j.dp ?? 0).toFixed(2),
                        asOf: new Date().toLocaleTimeString() } });
  } catch (e) { res.json({ text: `Quote unavailable: ${e.message}` }); }
});

const FRED = { "3m": "DGS3MO", "2y": "DGS2", "5y": "DGS5", "10y": "DGS10", "30y": "DGS30" };
app.post("/data/yield", auth, async (req, res) => {
  const id = FRED[String(req.body.tenor || "10y").toLowerCase()] || "DGS10";
  req.body.id = id;
  return series(req, res, `${req.body.tenor || "10y"} Treasury yield`, "%");
});
app.post("/data/series", auth, (req, res) => series(req, res, req.body.id, ""));

async function series(req, res, label, unit) {
  const id = String(req.body.id || "DGS10").toUpperCase().slice(0, 24);
  try {
    const j = await cached("f" + id, 30 * 60_000, () => jget(
      `https://api.stlouisfed.org/fred/series/observations?series_id=${id}` +
      `&api_key=${process.env.FRED_KEY}&file_type=json&sort_order=desc&limit=8`));
    const obs = (j.observations || []).filter(o => o.value !== ".");
    if (!obs.length) return res.json({ text: `No data for ${id}.` });
    const [now, prev] = obs;
    res.json({ html: `<b>${label}</b> ${now.value}${unit} <span class="dim">(${now.date}` +
      (prev ? `, previous ${prev.value}${unit}` : "") + `)</span>` });
  } catch (e) { res.json({ text: `FRED unavailable: ${e.message}` }); }
}

app.post("/data/fx", auth, async (req, res) => {
  const pair = String(req.body.pair || "USDCAD").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 6);
  const [a, b] = [pair.slice(0, 3), pair.slice(3) || "USD"];
  try {
    const j = await cached("x" + pair, 60_000, () => jget(
      `https://api.frankfurter.app/latest?from=${a}&to=${b}`));
    res.json({ html: `<b>${a}/${b}</b> ${j.rates[b]} <span class="dim">(${j.date})</span>` });
  } catch (e) { res.json({ text: `FX unavailable: ${e.message}` }); }
});

app.post("/data/news", auth, async (req, res) => {
  const q = encodeURIComponent(String(req.body.topic || "").slice(0, 80));
  try {
    const j = await cached("n" + q, 5 * 60_000, () => jget(
      `https://gnews.io/api/v4/search?q=${q}&lang=en&max=3&apikey=${process.env.GNEWS_KEY}`));
    const arts = (j.articles || []).slice(0, 3);
    if (!arts.length) return res.json({ text: "Nothing found." });
    res.json({ html: arts.map(a =>
      `<div><a href="${a.url}" target="_blank" rel="noopener"><b>${escapeHtml(a.title)}</b></a>` +
      `<div class="dim">${escapeHtml(a.source?.name || "")} · ${new Date(a.publishedAt).toLocaleDateString()}</div>` +
      `<div>${escapeHtml((a.description || "").slice(0, 220))}</div></div>`).join("<hr>") });
  } catch (e) { res.json({ text: `News unavailable: ${e.message}` }); }
});

const escapeHtml = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

/* ---------------------------------------------------------------- notes sync */
const NOTES_DIR = process.env.NOTES_DIR || "./notes";
fs.mkdirSync(NOTES_DIR, { recursive: true });
const notesFile = (email, deck) =>
  path.join(NOTES_DIR, `${email.replace(/[^\w.@-]/g, "_")}__${deck.replace(/[^\w-]/g, "_")}.json`);

app.get("/notes/:deck", auth, (req, res) => {
  const f = notesFile(req.user.email, req.params.deck);
  res.json(fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : {});
});
app.post("/notes/:deck", auth, (req, res) => {
  fs.writeFileSync(notesFile(req.user.email, req.params.deck), JSON.stringify(req.body || {}));
  res.json({ ok: true });
});

/* ---------------------------------------------------------------- decks */
app.use("/decks", express.static(process.env.DECK_DIR || "./decks"));
app.get("/health", (_, res) => res.json({ ok: true, model: MODEL_FAST }));

app.listen(PORT, () => console.log(`presenter backend on http://localhost:${PORT}`));
