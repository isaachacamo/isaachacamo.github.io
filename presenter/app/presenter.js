/* Presenter — a player for HTML decks. See DECK-SPEC.md for the deck contract.
 *
 * Loads a deck from: a bundled <template id="deck">, ?deck=<url> when served
 * over http, a dropped/picked file, or the last deck it cached in IndexedDB.
 */
(function () {
"use strict";
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const stripTags = s => { const d = document.createElement("div"); d.innerHTML = s; return d.textContent.trim(); };

/* ------------------------------------------------------------------ storage */
const DB = (() => {
  let p;
  const open = () => p || (p = new Promise((res, rej) => {
    const r = indexedDB.open("presenter", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("decks");
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
  }));
  const tx = async (mode, fn) => {
    try {
      const db = await open();
      return await new Promise((res, rej) => {
        const t = db.transaction("decks", mode), s = t.objectStore("decks");
        const q = fn(s); t.oncomplete = () => res(q && q.result); t.onerror = () => rej(t.error);
      });
    } catch (e) { return null; }
  };
  return { get: k => tx("readonly", s => s.get(k)), set: (k, v) => tx("readwrite", s => s.put(v, k)) };
})();

const LS = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
};

/* ------------------------------------------------------------------ parsing */
function parseDeck(htmlText, name) {
  const doc = new DOMParser().parseFromString(htmlText, "text/html");
  const sections = [...doc.querySelectorAll("section.slide")];
  if (!sections.length) throw new Error("No <section class=\"slide\"> found in " + (name || "that file"));

  let meta = {};
  const metaEl = doc.querySelector('script[type="application/json"]#deck-meta, script[type="application/json"].deck-meta');
  if (metaEl) { try { meta = JSON.parse(metaEl.textContent); } catch (e) { console.warn("deck-meta is not valid JSON:", e); } }

  const styles = [...doc.querySelectorAll("style")].map(s => s.textContent).join("\n");
  const scripts = [...doc.querySelectorAll("script[data-deck-script]")].map(s => s.textContent);

  const slides = sections.map((sec, i) => {
    const titleEl = sec.querySelector(".ftitle, h1, h2");
    const title = (sec.dataset.title || (titleEl ? titleEl.textContent : "") || "").trim();
    let steps = sec.dataset.steps !== undefined ? +sec.dataset.steps : 0;
    if (sec.dataset.steps === undefined) {
      for (const el of sec.querySelectorAll("[class],[data-in]")) {
        const m = /(?:^|\s)f([1-9])(?:\s|$)/.exec(el.className || "");
        if (m) steps = Math.max(steps, +m[1]);
        if (el.dataset.in) steps = Math.max(steps, +el.dataset.in);
      }
    }
    const tags = (sec.dataset.tags || "").split(",").map(t => t.trim().replace(/^#/, "")).filter(Boolean);
    if (sec.id) tags.push(sec.id);
    if (!tags.length) tags.push(...autoTags(title));
    const notes = (sec.dataset.notes || "").split(/\||\n/).map(s => s.trim()).filter(Boolean);
    return { i, el: sec, title: title || `Slide ${i + 1}`, tags, steps, notes };
  });

  // notes from deck-meta, by slide number or by title
  const mnotes = meta.notes || {};
  slides.forEach((s, i) => {
    const byNum = mnotes[String(i + 1)], byTitle = mnotes[s.title];
    const extra = [].concat(byNum || [], byTitle || []);
    if (extra.length) s.notes = s.notes.concat(extra);
  });

  const size = Array.isArray(meta.size) && meta.size.length === 2 ? meta.size : [960, 540];
  return {
    id: meta.id || slugify(meta.title || name || (slides[0] && slides[0].title) || "deck"),
    title: meta.title || (slides[0] && slides[0].title) || name || "Deck",
    size, api: meta.api || null,
    minutes: +meta.minutes > 0 ? +meta.minutes : null,   // the talk's own slot length
    figures: (meta.figures || []).map((f, k) => ({
      kind: f.kind || "figure", num: f.num ?? k + 1, title: f.title || "",
      src: f.src, page: f.page, source: f.source || "paper",
    })).filter(f => f.src),
    slides, styles, scripts, html: htmlText,
  };
}

const STOP = new Set("the a an of in on for and or to with by is are do does this that what we our us it its as at from part".split(" "));
const autoTags = t => (t.toLowerCase().match(/[a-z][a-z-]{2,}/g) || []).filter(w => !STOP.has(w)).slice(0, 4);
const slugify = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "deck";

/* ------------------------------------------------------------------ mounting */
let D = null;                     // the live deck
let cur = 0, history = [], editMode = false, paneHidden = false, store = null;
let hideAsk = () => {};             // set once the ask button is wired

function mountDeck(deck) {
  D = deck;
  const stage = $("#deck");
  const askbtn = $("#askbtn");          // keep these: innerHTML="" would drop them
  const badge = $("#noteBadge");
  stage.innerHTML = "";
  $("#deckStyles").textContent = deck.styles || "";
  document.documentElement.style.setProperty("--slide-w", deck.size[0]);
  document.documentElement.style.setProperty("--slide-h", deck.size[1]);
  stage.style.aspectRatio = `${deck.size[0]}/${deck.size[1]}`;

  deck.slides.forEach(s => {
    const el = document.importNode(s.el, true);
    el.classList.add("slide");
    el.dataset.frags = s.steps;
    el.dataset.step = 0;
    stage.appendChild(el);
    s.node = el;
  });
  if (askbtn) stage.appendChild(askbtn);
  if (badge) stage.appendChild(badge);

  // deck-authored scripts, opted in with data-deck-script
  deck.scripts.forEach(code => {
    const el = document.createElement("script");
    el.textContent = code;
    document.body.appendChild(el);
  });

  SlideClock.stop();               // bank the outgoing deck's time before we swap stores
  store = {
    key: "prez:" + deck.id,
    data: LS.get("prez:" + deck.id, { notes: {}, tags: {}, edits: {}, paneHidden: false }),
  };
  markEditable();
  restoreEdits();
  Timer.load();
  SlideClock.load();
  chat = [];
  paneHidden = !!store.data.paneHidden;
  document.body.classList.toggle("pane-hidden", paneHidden);
  document.body.classList.remove("no-deck");
  document.body.classList.add("has-deck");
  document.title = deck.title + " — Presenter";
  $("#deckName").textContent = deck.title;
  cur = 0; history = [];
  setEdit(false, true);
  show(0, { push: false });
  DB.set("last", { html: deck.html, name: deck.title });
  toast(`${deck.slides.length} slides loaded`);
}

/* editable regions: whatever the deck marks, else title + body per slide */
function markEditable() {
  D.slides.forEach((s, i) => {
    if (s.node.querySelector("[data-edit]")) return;
    const t = s.node.querySelector(".ftitle, h1, h2");
    if (t) t.dataset.edit = `s${i}-t`;
    const b = s.node.querySelector(".body") || (t ? null : s.node);
    if (b && b !== s.node) b.dataset.edit = `s${i}-b`;
    else if (!b && !t) s.node.dataset.edit = `s${i}-all`;
    else if (!s.node.querySelector(".body")) {
      // no explicit body: wrap the rest so typing cannot break the layout
      const rest = [...s.node.children].filter(c => c !== t && !c.classList.contains("askbtn"));
      rest.forEach((c, k) => (c.dataset.edit = `s${i}-c${k}`));
    }
  });
}
const editables = () => $$("#deck [data-edit]");
function restoreEdits() {
  for (const [k, v] of Object.entries(store.data.edits || {})) {
    const el = $(`#deck [data-edit="${CSS.escape(k)}"]`);
    if (el) el.innerHTML = v;
  }
}
function setEdit(on, quiet) {
  editMode = !!on;
  editables().forEach(el => {
    el.setAttribute("contenteditable", editMode ? "true" : "false");
    if (!el._wired) {
      el._wired = true;
      const remember = () => { store.data.edits[el.dataset.edit] = el.innerHTML; save(); };
      el.addEventListener("input", remember);
      el.addEventListener("blur", remember);
    }
  });
  document.body.classList.toggle("editing", editMode);
  const b = $("#editBtn");
  b.textContent = editMode ? "Editing: on" : "Editing: off";
  b.classList.toggle("on", editMode);
  if (!editMode && document.activeElement && document.activeElement.isContentEditable)
    document.activeElement.blur();
  if (!quiet) toast(editMode ? "Editing on — click any text to change it"
                             : "Editing off — slides are locked");
}
const save = () => LS.set(store.key, store.data);

/* ------------------------------------------------------------------ timer
 * Set it once at the start of the talk; it counts down and keeps going
 * (in red, with a +) once you are over. Survives a reload mid-talk.        */
const clock = s => {
  const over = s < 0; s = Math.abs(Math.round(s));
  const h = (s / 3600) | 0, m = ((s % 3600) / 60) | 0, ss = s % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return (over ? "+" : "") + (h ? h + ":" : "") + mm + ":" + String(ss).padStart(2, "0");
};

const Timer = (() => {
  const DEFAULT = 90 * 60;                       // 1.5 hours
  let total = DEFAULT, left = DEFAULT, running = false, since = 0, tick = null;

  const fmt = clock;
  const remaining = () => running ? left - (Date.now() - since) / 1000 : left;

  function render() {
    const el = $("#timer"); if (!el) return;
    const r = remaining();
    el.textContent = fmt(r);
    el.classList.toggle("running", running);
    el.classList.toggle("warn", r <= 300 && r > 0);
    el.classList.toggle("over", r <= 0);
    el.title = running ? "Running — click to pause" : "Paused — click to start";
  }
  function persist() {
    if (!store) return;
    store.data.timer = { total, left, running, since }; save();
  }
  function loop() { clearInterval(tick); if (running) tick = setInterval(render, 250); render(); }

  return {
    load() {
      const t = (store && store.data.timer) || null;
      const slot = (D && D.minutes ? D.minutes * 60 : 0) || DEFAULT;
      if (t) ({ total, left, running, since } = t); else { total = left = slot; running = false; }
      loop();
    },
    set(minutes, andStart = true) {
      total = left = Math.max(1, Math.round(minutes * 60));
      running = false; since = 0;
      if (andStart) this.start(); else { persist(); loop(); }
      toast(`Timer set to ${minutes} min` + (andStart ? " and started" : ""));
    },
    start() { if (!running) { running = true; since = Date.now(); persist(); loop(); } },
    pause() { if (running) { left = remaining(); running = false; persist(); loop(); } },
    toggle() { running ? this.pause() : this.start(); },
    reset() { left = total; running = false; since = 0; persist(); loop(); toast("Timer reset"); },
    render, remaining,
  };
})();

/* ------------------------------------------------------------------ per-slide clock
 * Each slide has its own stopwatch. It runs while the slide is up, stops when
 * you leave, and picks up where it left off if you come back. Stored per deck,
 * so the numbers survive a reload and tell you afterwards where the time went. */
const SlideClock = (() => {
  let idx = null, since = 0, tick = null, saved = 0;
  const table = () => (store.data.slideTime = store.data.slideTime || {});
  const live = () => (idx !== null && since ? (Date.now() - since) / 1000 : 0);

  /* move the seconds run so far into the store; keep counting unless told to stop */
  function bank(keepRunning) {
    if (idx !== null && since) {
      const t = table();
      t[idx] = (t[idx] || 0) + (Date.now() - since) / 1000;
    }
    since = keepRunning ? Date.now() : 0;
    saved = Date.now();
  }
  function render() {
    const el = $("#slideTime"); if (!el || !D) return;
    if (idx === null) { el.textContent = ""; el.classList.remove("running"); return; }
    el.textContent = clock((table()[idx] || 0) + live());
    el.classList.toggle("running", !!since);
    el.title = `Time on slide ${idx + 1} · /times for the whole breakdown`;
    // a heartbeat, so a crash or a closed laptop mid-talk loses at most ~20s
    if (since && Date.now() - saved > 20000) { bank(true); save(); }
  }
  function loop() { clearInterval(tick); if (since) tick = setInterval(render, 500); render(); }

  return {
    /* called on every slide change: close the old slide's books, open the new one */
    enter(i) {
      if (i === idx && since) return;
      bank(false);
      idx = i; since = Date.now(); saved = Date.now();
      save(); loop();
    },
    pause() { if (!since) return; bank(false); save(); loop(); },
    resume() { if (idx === null || since) return; since = Date.now(); saved = Date.now(); loop(); },
    stop() {
      if (!store) { idx = null; since = 0; clearInterval(tick); return; }
      bank(false); save(); idx = null; clearInterval(tick); render();
    },
    /* a deck opened afresh starts its slide times from zero; the previous
       run's times are kept once, for /times last */
    load() {
      idx = null; since = 0; clearInterval(tick);
      if (store && store.data.slideTime && Object.keys(store.data.slideTime).length) {
        store.data.slideTimeLast = store.data.slideTime;
      }
      if (store) { store.data.slideTime = {}; save(); }
    },
    last: i => (store.data.slideTimeLast || {})[i] || 0,
    total: i => (table()[i] || 0) + (i === idx ? live() : 0),
    grand() { return D ? D.slides.reduce((a, _, i) => a + this.total(i), 0) : 0; },
    reset() { store.data.slideTime = {}; if (idx !== null) since = Date.now(); saved = Date.now(); save(); render(); },
    render,
  };
})();

/* ------------------------------------------------------------------ navigation */
function applySteps(node) {
  const st = +node.dataset.step;
  node.querySelectorAll("[data-in]").forEach(el => el.classList.toggle("on", +el.dataset.in <= st));
}
let rollT = null;
const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Slides roll: the outgoing one travels up and out, the new one comes up
   from below (reversed when you go backwards).                            */
function roll(fromIdx, toIdx, dir) {
  const to = D.slides[toIdx].node;
  const from = fromIdx === toIdx ? null : D.slides[fromIdx].node;
  clearTimeout(rollT);
  D.slides.forEach(s => s.node.classList.remove("leaveUp", "leaveDown", "enterUp", "enterDown"));
  if (!from || !dir || reduceMotion()) {
    D.slides.forEach((s, k) => s.node.classList.toggle("active", k === toIdx));
    return;
  }
  const up = dir > 0;
  from.classList.add(up ? "leaveUp" : "leaveDown");
  to.classList.add("active", up ? "enterUp" : "enterDown");
  rollT = setTimeout(() => {
    D.slides.forEach((s, k) => s.node.classList.toggle("active", k === toIdx));
    from.classList.remove("leaveUp", "leaveDown");
    to.classList.remove("enterUp", "enterDown");
  }, 500);
}

/* A long jump: the slides in between pass by as a quick, soft riffle — three
   frames, cross-faded — and the target settles in with a short fade rather
   than a roll, so there is no lurch at the end. */
let riffleT = null;
function riffle(fromIdx, toIdx, done) {
  const span = toIdx - fromIdx, n = Math.min(3, Math.abs(span) - 1);
  const steps = Array.from({ length: n }, (_, k) => fromIdx + Math.round(span * (k + 1) / (n + 1)));
  clearTimeout(riffleT);
  D.slides.forEach(s => s.node.classList.remove("leaveUp", "leaveDown", "enterUp", "enterDown", "flick"));
  document.body.classList.add("riffling");
  let k = 0, prev = D.slides[fromIdx].node;
  const tick = () => {
    prev.classList.remove("active", "flick");
    if (k < steps.length) {
      const n = D.slides[steps[k]].node;
      n.classList.add("active", "flick");
      prev = n; k++; riffleT = setTimeout(tick, 95);
    } else {
      document.body.classList.remove("riffling");
      done();
    }
  };
  tick();
}

function show(i, { push = true, step = 0, dir } = {}) {
  if (!D) return;
  const fromIdx = cur;
  if (push && i !== cur) history.push(cur);
  cur = (i + D.slides.length) % D.slides.length;
  linkIdx = -1;
  hideAsk();
  const far = Math.abs(cur - fromIdx) > 2 && !reduceMotion();
  if (far) {
    riffle(fromIdx, cur, () => {
      D.slides.forEach((s, k) => s.node.classList.toggle("active", k === cur));
      const n = D.slides[cur].node;
      n.classList.add("settle"); setTimeout(() => n.classList.remove("settle"), 400);
    });
  } else {
    roll(fromIdx, cur, dir !== undefined ? dir : Math.sign(cur - fromIdx));
  }
  const n = D.slides[cur].node;
  n.dataset.step = step === "last" ? n.dataset.frags : 0;
  applySteps(n);
  $("#counter").textContent = `${cur + 1} / ${D.slides.length}`;
  SlideClock.enter(cur);
  renderPane();
}
function next() {
  const n = D.slides[cur].node, st = +n.dataset.step, max = +n.dataset.frags;
  if (st < max) { n.dataset.step = st + 1; applySteps(n); }
  else if (cur < D.slides.length - 1) show(cur + 1, { push: false, dir: 1 });
}
function prev() {
  const n = D.slides[cur].node, st = +n.dataset.step;
  if (st > 0) { n.dataset.step = st - 1; applySteps(n); }
  else if (cur > 0) show(cur - 1, { push: false, step: "last", dir: -1 });
}
function back() {
  if (history.length) show(history.pop(), { push: false });
  else toast("Nothing to go back to");
}
const meta = i => D.slides[i];
const tagsOf = i => [...new Set([...(meta(i).tags || []), ...((store.data.tags || {})[i] || [])])];

function findSlides(q) {
  q = (q || "").trim().toLowerCase();
  if (!q) return [];
  if (/^\d+$/.test(q)) { const n = +q; return n >= 1 && n <= D.slides.length ? [n - 1] : []; }
  const tag = q.startsWith("#") ? q.slice(1) : null;
  const hits = [];
  D.slides.forEach((s, i) => {
    const t = s.title.toLowerCase(), tg = tagsOf(i).map(x => x.toLowerCase());
    if (tag ? tg.some(x => x.startsWith(tag)) : (t.includes(q) || tg.some(x => x.includes(q)))) hits.push(i);
  });
  return hits;
}

/* ------------------------------------------------------------------ side pane */
function notesOf(i) {
  return [...(meta(i).notes || []).map(t => ({ kind: "prep", text: t })),
          ...((store.data.notes || {})[i] || [])];
}
function renderPane() {
  $("#paneTitle").textContent = `Slide ${cur + 1} · ${meta(cur).title}`;
  const tg = tagsOf(cur);
  $("#paneTags").innerHTML = tg.map(t => `<span class="tag">#${esc(t)}</span>`).join("")
    || '<span class="dim">no tags · /tag name</span>';
  const log = $("#log");
  log.innerHTML = "";
  const prepared = (meta(cur).notes || []).length;
  notesOf(cur).forEach((n, i) => {
    const d = addMsg(n.kind, n.html || esc(n.text), false);
    // anything you added live can be taken back; the deck's own notes cannot
    if (i >= prepared) d.dataset.own = i - prepared;
  });
  log.scrollTop = log.scrollHeight;
  renderNoteBadge();
}
/* Remove one of your own notes from this slide. */
function deleteNote(k) {
  const arr = store.data.notes[cur];
  if (!arr || !arr[k]) return;
  arr.splice(k, 1);
  if (!arr.length) delete store.data.notes[cur];
  save(); renderPane(); toast("Note deleted");
}
function addMsg(kind, html, persist = true) {
  const log = $("#log");
  const d = document.createElement("div");
  d.className = "msg " + kind;
  const label = { prep: "Prepared", live: "Note", q: "You → Claude", ai: "Claude", data: "Data" }[kind] || kind;
  d.innerHTML = `<div class="tag-l">${label}</div><button class="del" title="Delete">&times;</button>${html}`;
  log.appendChild(d); log.scrollTop = log.scrollHeight;
  if (persist) {
    const arr = (store.data.notes[cur] = store.data.notes[cur] || []);
    arr.push({ kind, html });
    d.dataset.own = arr.length - 1;          // deletable straight away, not only after a re-render
    save(); renderNoteBadge();
    if (kind === "live") flyNote(stripTags(html));
  }
  return d;
}
/* A small marker on the slide itself when it carries notes, parked in
   whichever corner is free of content.                                   */
let noteOrigin = null;                     // rect of whatever box you typed in
const captureOrigin = el => { try { noteOrigin = el.getBoundingClientRect(); } catch (e) {} };

/* The note leaves the box you typed it in and lands on the marker. */
function flyNote(text) {
  const badge = $("#noteBadge");
  if (!badge || badge.hidden || reduceMotion()) { pop(badge); return; }
  const to = badge.getBoundingClientRect();
  const from = noteOrigin && noteOrigin.width ? noteOrigin : to;
  const ghost = document.createElement("div");
  ghost.className = "note-fly";
  ghost.textContent = (text || "note").slice(0, 60);
  ghost.style.left = from.left + "px";
  ghost.style.top = from.top + "px";
  ghost.style.width = Math.min(from.width || 220, 280) + "px";
  document.body.appendChild(ghost);
  const g = ghost.getBoundingClientRect();
  const dx = to.left + to.width / 2 - (g.left + g.width / 2);
  const dy = to.top + to.height / 2 - (g.top + g.height / 2);
  const anim = ghost.animate(
    [{ transform: "translate(0,0) scale(1)", opacity: 1 },
     { transform: `translate(${dx * 0.55}px,${dy * 0.55}px) scale(.66)`, opacity: .95, offset: .6 },
     { transform: `translate(${dx}px,${dy}px) scale(.18)`, opacity: 0 }],
    { duration: 620, easing: "cubic-bezier(.4,.05,.25,1)" });
  anim.onfinish = () => { ghost.remove(); pop(badge); };
  setTimeout(() => { if (ghost.isConnected) { ghost.remove(); pop(badge); } }, 900);
}
function pop(badge) {
  if (!badge || badge.hidden) return;
  badge.classList.remove("pop");
  void badge.offsetWidth;                  // restart the animation
  badge.classList.add("pop");
}

/* a quiet stroked speech bubble — reads at any size, takes its colour from the pill */
const NOTE_ICON =
  '<svg class="ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
  + '<path d="M20.5 11.9c0 3.9-3.8 7.05-8.5 7.05-.87 0-1.72-.11-2.5-.31L4.6 20.4l1.36-3.3'
  + 'C4.4 15.82 3.5 13.96 3.5 11.9 3.5 8 7.3 4.85 12 4.85s8.5 3.15 8.5 7.05Z"'
  + ' stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>'
  + '<path d="M8.5 10.6h7M8.5 13.6h4.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
  + "</svg>";

function renderNoteBadge() {
  const badge = $("#noteBadge"); if (!badge || !D) return;
  const n = ((store.data.notes || {})[cur] || []).length;
  badge.hidden = !n;
  if (!n) return;
  badge.innerHTML = NOTE_ICON + `<span class="n">${n}</span>`;
  badge.title = `${n} note${n > 1 ? "s" : ""} on this slide — click to open the pane`;
  placeBadge(badge);
}
function placeBadge(badge) {
  const slide = D.slides[cur].node;
  const r = slide.getBoundingClientRect();
  if (!r.width) return;
  // scale with the slide, measured rather than left to cqw (Safari resolves it as 0 here)
  badge.style.fontSize = Math.max(12, Math.min(24, r.width * 0.0175)) + "px";
  const pad = r.width * 0.012, w = r.width * 0.075, h = r.height * 0.075;
  // only leaf elements: containers span the whole slide and would look "occupied"
  const boxes = [...slide.querySelectorAll("*")]
    .filter(el => el !== badge && !el.contains(badge)
                  && (!el.firstElementChild || /^(IMG|SVG|CANVAS)$/.test(el.tagName))
                  && el.offsetParent !== null)
    .map(el => el.getBoundingClientRect())
    .filter(b => b.width > 2 && b.height > 2)
    .map(b => ({ x: b.left - r.left, y: b.top - r.top, w: b.width, h: b.height }));
  const spots = [
    ["br", r.width - w - pad, r.height - h - pad],
    ["bl", pad, r.height - h - pad],
    ["tr", r.width - w - pad, pad],
    ["bc", (r.width - w) / 2, r.height - h - pad],
  ];
  const free = spots.find(([, x, y]) =>
    !boxes.some(b => x < b.x + b.w && x + w > b.x && y < b.y + b.h && y + h > b.y));
  const [, x, y] = free || spots[0];
  badge.style.left = (x / r.width * 100) + "%";
  badge.style.top = (y / r.height * 100) + "%";
}

function togglePane(force) {
  paneHidden = force === undefined ? !paneHidden : force;
  document.body.classList.toggle("pane-hidden", paneHidden);
  store.data.paneHidden = paneHidden; save();
}

/* ------------------------------------------------------------------ lightbox */
let lbIdx = -1;
function openFigure(f) {
  if (!f) return toast("Not found");
  lbIdx = D.figures.indexOf(f);
  $("#lbImg").src = f.src;
  $("#lbCap").innerHTML = `<b>${f.kind === "table" ? "Table" : "Figure"} ${esc(f.num)}.</b> ${esc(f.title)}`
    + `<span class="dim"> · ${esc(f.source || "")}${f.page ? " p." + f.page : ""}`
    + ` · click to zoom · ←/→ for the next one</span>`;
  const lb = $("#lightbox"); lb.classList.remove("zoom"); lb.classList.add("open");
}
/* Show another slide over this one without leaving it — for a deck link that
   should feel like opening an exhibit rather than jumping away. */
function peekSlide(n, opts = {}) {
  const s = D.slides[n]; if (!s) return toast("No such slide");
  const holder = $("#lbNode");
  holder.innerHTML = "";
  const clone = s.node.cloneNode(true);
  clone.classList.add("peek");
  clone.classList.remove("active", "leaveUp", "leaveDown", "enterUp", "enterDown");
  if (opts.play && +clone.dataset.frags) {
    // played from its first step: ←/→ step it inside the popup
    clone.dataset.step = 0; applySteps(clone);
  } else {
    clone.dataset.step = clone.dataset.frags || 0;      // fully revealed
    clone.querySelectorAll("[data-in]").forEach(el => el.classList.add("on"));
  }
  clone.querySelectorAll("[data-goto],[data-peek],.askbtn,#noteBadge").forEach(el => el.remove());
  // a slide can ask the popup to zoom to one region of it ("x y w h", fractions)
  const crop = (s.node.dataset.peekCrop || "").split(/\s+/).map(Number);
  holder.style.aspectRatio = "";
  if (crop.length === 4 && crop.every(v => isFinite(v)) && crop[2] > 0 && crop[3] > 0) {
    const [x, y, w, h] = crop;
    holder.style.aspectRatio = `${D.size[0] * w} / ${D.size[1] * h}`;
    clone.style.cssText += `;left:${-x / w * 100}%;top:${-y / h * 100}%;width:${100 / w}%;height:${100 / h}%;`
      + `--pt:calc(100cqw / ${D.size[0] * w})`;
  }
  holder.appendChild(clone);
  $("#lbCap").innerHTML = `<b>Slide ${n + 1}.</b> ${esc(meta(n).title)}`
    + `<span class="dim"> · Esc to close · /go ${n + 1} to stay there</span>`;
  const lb = $("#lightbox");
  lb.classList.remove("zoom"); lb.classList.add("open", "node");
  lbIdx = -1;
  if (opts.from && !reduceMotion()) {
    // grow out of the element that asked for it, so the popup reads as a zoom
    const box = $("#lightbox .lb-box"), f = opts.from;
    requestAnimationFrame(() => {
      const b = box.getBoundingClientRect();
      const dx = (f.left + f.width / 2) - (b.left + b.width / 2);
      const dy = (f.top + f.height / 2) - (b.top + b.height / 2);
      box.animate([{ transform: `translate(${dx}px,${dy}px) scale(${f.width / b.width},${f.height / b.height})`, opacity: .35 },
                   { transform: "none", opacity: 1 }],
                  { duration: 520, easing: "cubic-bezier(.2,.8,.25,1)" });
    });
  }
}
/* K walks the slide's buttons in order: each press opens the next one's
   popup (or jumps to it); after the last, the popup closes. */
let linkIdx = -1;
function cycleLink() {
  const links = [...D.slides[cur].node.querySelectorAll("[data-peek],[data-goto]")];
  if (!links.length) return toast("No links on this slide");
  linkIdx += 1;
  if (linkIdx >= links.length) { linkIdx = -1; closeLightbox(); return toast("Back to the slide"); }
  const a = links[linkIdx], n = +(a.dataset.peek || a.dataset.goto);
  if (!(n >= 1 && n <= D.slides.length)) return;
  if (a.dataset.peek) {
    closeLightbox();
    peekSlide(n - 1, { play: a.hasAttribute("data-peek-play"),
                       from: a.hasAttribute("data-peek-zoom") ? a.getBoundingClientRect() : null });
    toast(`Link ${linkIdx + 1} of ${links.length} · K for the next`);
  } else show(n - 1);
}
const closeLightbox = () => {
  $("#lightbox").classList.remove("open", "zoom", "node");
  $("#lbNode").innerHTML = "";
};
function stepFigure(d) {
  if (lbIdx < 0 || !D.figures.length) return;
  openFigure(D.figures[(lbIdx + d + D.figures.length) % D.figures.length]);
}
const figByRef = (kind, ref) => {
  ref = String(ref || "").trim().toLowerCase();
  const pool = D.figures.filter(f => f.kind === kind);
  return pool.find(f => String(f.num).toLowerCase() === ref)
      || pool.find(f => (f.title || "").toLowerCase().includes(ref) && ref)
      || (!ref ? pool[0] : null);
};

/* ------------------------------------------------------------------ backend */
const API = () => (D && D.api) || null;
try { window.PREZ_TOKEN = window.PREZ_TOKEN || localStorage.getItem("prez_token") || null; } catch (e) {}

async function callApi(path, payload, onText) {
  if (!API()) {
    onText('<i>[No backend configured. Add <code>"api": "http://localhost:8787"</code> to the '
      + "deck's <code>deck-meta</code> and this answer will come from the server.]</i>");
    return "";
  }
  try {
    const r = await fetch(API().replace(/\/$/, "") + path, {
      method: "POST",
      headers: { "Content-Type": "application/json",
                 ...(window.PREZ_TOKEN ? { Authorization: "Bearer " + window.PREZ_TOKEN } : {}) },
      body: JSON.stringify(payload),
    });
    if (!r.ok) { onText(`<i>[Server said ${r.status}. ${esc(await r.text().catch(() => ""))}]</i>`); return ""; }
    const ct = r.headers.get("content-type") || "";
    if (ct.includes("text/plain") || ct.includes("event-stream")) {
      const rd = r.body.getReader(), dec = new TextDecoder(); let acc = "";
      for (;;) { const { value, done } = await rd.read(); if (done) break;
        acc += dec.decode(value, { stream: true }); onText(esc(acc).replace(/\n/g, "<br>")); }
      return acc;
    }
    const j = await r.json();
    onText(renderResult(j));
    return j.text || stripTags(renderResult(j));
  } catch (e) { onText("<i>[Could not reach the server: " + esc(e.message) + "]</i>"); return ""; }
}
function renderResult(j) {
  if (j.html) return j.html;
  if (j.text) return esc(j.text).replace(/\n/g, "<br>");
  if (j.quote) return `<b>${esc(j.quote.symbol)}</b> ${esc(j.quote.price)} `
    + `<span class="${j.quote.change >= 0 ? "up" : "down"}">${j.quote.change >= 0 ? "▲" : "▼"} ${esc(j.quote.change)}%</span>`
    + `<div class="dim">${esc(j.quote.asOf || "")}</div>`;
  return "<pre>" + esc(JSON.stringify(j, null, 1)) + "</pre>";
}
/* Where an answer goes: the pane when it is open, a floating card when it
   is hidden. Either way you can follow up without losing the thread.     */
let chat = [];              // running conversation with Claude
let lastMode = "ask";

function answerCard(kind) {
  const box = $("#answer"), body = $("#ansBody");
  $("#ansLabel").textContent = kind === "data" ? "Data" : "Claude";
  body.innerHTML = "…";
  box.hidden = false;
  box.classList.add("open");
  return html => { body.innerHTML = html; body.scrollTop = body.scrollHeight; };
}
const closeAnswer = () => { const b = $("#answer"); b.classList.remove("open"); b.hidden = true; };

function sink(kind) {
  const toPane = streaming(kind);
  if (!paneHidden) return toPane;
  const toCard = answerCard(kind);
  return html => { toPane(html); toCard(html); };     // pane keeps the record either way
}

async function askClaude(mode, question) {
  const q = (question || "").trim();
  if (!q) return;
  lastMode = mode;
  addMsg("q", esc(q));
  const history = chat.slice(-8);
  chat.push({ role: "user", content: q });
  const answer = await callApi(mode === "ask" ? "/ask" : "/claude",
    { question: q, context: slideContext(), history, scope: mode === "ask" ? "deck" : undefined },
    sink("ai"));
  chat.push({ role: "assistant", content: answer || "" });
  offerFollowUp();
}
function offerFollowUp() {
  const last = [...$("#log").querySelectorAll(".msg.ai")].pop();
  if (last && !last.querySelector(".followup")) {
    const b = document.createElement("button");
    b.className = "followup"; b.textContent = "Follow up ↩";
    b.onclick = () => paneHidden ? $("#ansInput").focus() : (openPalette("/" + lastMode + " "));
    last.appendChild(b);
  }
  if (!$("#answer").hidden) $("#ansInput").focus();
}

function streaming(kind) {
  const d = addMsg(kind, '<div class="bd">…</div>', false);
  const body = d.querySelector(".bd");
  let saved = null;
  return html => {
    body.innerHTML = html;
    $("#log").scrollTop = $("#log").scrollHeight;
    const rec = { kind, html: `<div class="bd">${html}</div>` };
    const arr = (store.data.notes[cur] = store.data.notes[cur] || []);
    if (saved) Object.assign(saved, rec); else { saved = rec; arr.push(rec); }
    save();
  };
}
const slideContext = () => ({
  slide: cur + 1, title: meta(cur).title, tags: tagsOf(cur), deck: D.title, deckId: D.id,
  text: (D.slides[cur].node.innerText || "").trim().slice(0, 4000),
  notes: notesOf(cur).map(n => n.text || stripTags(n.html || "")),
});

/* ------------------------------------------------------------------ commands */
const COMMANDS = [
  { name: "go", args: "<number | title | #tag>", help: "Jump to a slide", run: a => {
      const h = findSlides(a);
      if (!h.length) return toast(`No slide matches “${a}”`);
      h.length === 1 ? show(h[0]) : pickSlide(h);
    } },
  { name: "slides", args: "", help: "List every slide and jump to one (L)", run: () => slideList() },
  { name: "back", args: "", help: "Return to the slide you jumped from", run: back },
  { name: "fig", args: "<number | words>", help: "Open a figure", run: a => openFigure(figByRef("figure", a)) },
  { name: "table", args: "<number | words>", help: "Open a table", run: a => openFigure(figByRef("table", a)) },
  { name: "find", args: "<words>", help: "Search figures, tables and slides", run: a => {
      const q = a.toLowerCase();
      const fs = D.figures.filter(f => (f.title || "").toLowerCase().includes(q));
      const ss = findSlides(a);
      if (!fs.length && !ss.length) return toast("Nothing found");
      openPalette("", [
        ...fs.map(f => ({ label: `${f.kind === "table" ? "Table" : "Figure"} ${f.num} — ${f.title}`, run: () => openFigure(f) })),
        ...ss.map(i => ({ label: `Slide ${i + 1} — ${meta(i).title}`, run: () => show(i) })),
      ]);
    } },
  { name: "note", args: "<text>", help: "Save a note on this slide", run: a => addMsg("live", esc(a)) },
  { name: "tag", args: "<name>", help: "Tag this slide", run: a => {
      const t = a.replace(/^#/, "").trim(); if (!t) return;
      (store.data.tags[cur] = store.data.tags[cur] || []).push(t); save(); renderPane(); toast("Tagged #" + t);
    } },
  { name: "ask", args: "<question>", help: "Claude, answering only from this deck",
    run: a => askClaude("ask", a) },
  { name: "claude", args: "<question>", help: "Claude, unrestricted",
    run: a => askClaude("claude", a) },
  { name: "forget", args: "", help: "Start a fresh conversation with Claude",
    run: () => { chat = []; toast("New thread — earlier answers forgotten"); } },
  { name: "price", args: "<TICKER>", help: "Latest stock quote", run: a => {
      addMsg("q", "/price " + esc(a)); callApi("/data/price", { symbol: a.trim().toUpperCase() }, sink("data"));
    } },
  { name: "yield", args: "<10y | 2y | …>", help: "Treasury yield (FRED)", run: a => {
      addMsg("q", "/yield " + esc(a)); callApi("/data/yield", { tenor: a.trim() || "10y" }, sink("data"));
    } },
  { name: "series", args: "<FRED id>", help: "Any FRED series, latest value", run: a => {
      addMsg("q", "/series " + esc(a)); callApi("/data/series", { id: a.trim().toUpperCase() }, sink("data"));
    } },
  { name: "fx", args: "<USDCAD>", help: "Exchange rate", run: a => {
      addMsg("q", "/fx " + esc(a)); callApi("/data/fx", { pair: a.trim().toUpperCase() }, sink("data"));
    } },
  { name: "news", args: "<topic>", help: "News snippet", run: a => {
      addMsg("q", "/news " + esc(a)); callApi("/data/news", { topic: a.trim() }, sink("data"));
    } },
  { name: "edit", args: "[on | off]", help: "Slide editing (off by default)", run: a => {
      const t = a.trim().toLowerCase(); setEdit(t === "on" ? true : t === "off" ? false : !editMode);
    } },
  { name: "revert", args: "[all]", help: "Undo your edits to this slide, or all", run: a => {
      if (a.trim().toLowerCase() === "all") { store.data.edits = {}; save(); return location.reload(); }
      let n = 0;
      D.slides[cur].node.querySelectorAll("[data-edit]").forEach(el => {
        if (store.data.edits[el.dataset.edit] !== undefined) { delete store.data.edits[el.dataset.edit]; n++; }
      });
      save(); n ? location.reload() : toast("No edits on this slide");
    } },
  { name: "timer", args: "[minutes | start | pause | reset]", help: "Talk timer (default 90 min)",
    run: a => {
      const t = a.trim().toLowerCase();
      if (!t) return Timer.toggle();
      if (t === "start") return Timer.start();
      if (t === "pause" || t === "stop") return Timer.pause();
      if (t === "reset") return Timer.reset();
      const m = parseFloat(t);
      if (isFinite(m) && m > 0) Timer.set(m); else toast("Try /timer 45");
    } },
  { name: "times", args: "[reset|last]", help: "Time spent on each slide (this run; 'last' for the previous one)", run: a => {
      const arg = a.trim().toLowerCase();
      if (arg === "reset") { SlideClock.reset(); return toast("Slide times cleared"); }
      const prev = arg === "last";
      const rows = D.slides.map((_, i) => ({ i, s: prev ? SlideClock.last(i) : SlideClock.total(i) })).filter(r => r.s >= 1);
      if (!rows.length) return toast(prev ? "No previous run recorded" : "No time recorded yet");
      rows.sort((a, b) => b.s - a.s);
      const grand = prev ? rows.reduce((t, r) => t + r.s, 0) : SlideClock.grand();
      addMsg("data",
        `<b>Time per slide</b> — ${clock(grand)} over ${rows.length} slide${rows.length > 1 ? "s" : ""}`
        + '<table class="times">'
        + rows.map(r => `<tr><td>${r.i + 1}</td><td>${esc(meta(r.i).title)}</td>`
            + `<td class="t">${clock(r.s)}</td>`
            + `<td class="b"><i style="width:${Math.round(100 * r.s / rows[0].s)}%"></i></td></tr>`).join("")
        + "</table>", false);
      if (paneHidden) togglePane(false);
    } },
  { name: "pane", args: "", help: "Show / hide the side pane", run: () => togglePane() },
  { name: "open", args: "", help: "Open a different deck", run: () => $("#file").click() },
  { name: "help", args: "", help: "List commands", run: () => openPalette("",
      COMMANDS.map(c => ({ label: `/${c.name} ${c.args}`, sub: c.help,
                           run: () => openPalette("/" + c.name + " ") }))) },
];
function runCommand(text) {
  text = (text || "").trim(); if (!text) return;
  if (!text.startsWith("/")) return void addMsg("live", esc(text));
  const m = text.slice(1).match(/^(\S+)\s*([\s\S]*)$/); if (!m) return;
  const c = COMMANDS.find(c => c.name === m[1].toLowerCase());
  c ? c.run(m[2]) : toast("Unknown command /" + m[1]);
}
const slideItem = i => {
  const bits = [tagsOf(i).map(t => "#" + t).join(" "),
                SlideClock.total(i) >= 1 ? clock(SlideClock.total(i)) : "",
                ((store.data.notes || {})[i] || []).length ? "✎" : "",
                i === cur ? "← you are here" : ""].filter(Boolean);
  return { label: `${i + 1}. ${meta(i).title}`, sub: bits.join(" · "), run: () => show(i) };
};
const pickSlide = hits => openPalette("", hits.map(slideItem));

/* Every slide at once — type to filter, ↑↓ to move, Enter to jump. */
const slideList = () =>
  openPalette("", D.slides.map((_, i) => slideItem(i)), { sel: cur, placeholder: "Go to slide…" });

/* ------------------------------------------------------------------ palette */
let palItems = [], palSel = 0, palMode = "cmd";
function openPalette(text = "", items = null, opts = {}) {
  const pal = $("#palette");
  pal.classList.add("open");
  const inp = $("#palInput");
  inp.value = text;
  palMode = items ? "list" : "cmd";
  palItems = items || [];
  inp.placeholder = opts.placeholder || (items ? "Choose…" : "Command (/go 12, /fig 3, /ask …) or a note");
  palSel = opts.sel || 0; renderPal(); inp.focus(); inp.setSelectionRange(text.length, text.length);
}
const closePalette = () => { $("#palette").classList.remove("open"); $("#palInput").blur(); };
function suggest(text) {
  if (palMode === "list") return palItems.filter(it => it.label.toLowerCase().includes(text.toLowerCase()));
  if (!text.startsWith("/"))
    return text ? [{ label: "Save as note on this slide", sub: text, run: () => runCommand(text) }] : [];
  const m = text.slice(1).match(/^(\S*)\s?([\s\S]*)$/);
  const name = m[1].toLowerCase(), arg = m[2];
  const exact = COMMANDS.find(c => c.name === name);
  if (exact && (text.includes(" ") || arg)) {
    if (exact.name === "go" && arg)
      return findSlides(arg).slice(0, 8).map(i => ({ label: `Slide ${i + 1} — ${meta(i).title}`,
        sub: tagsOf(i).map(t => "#" + t).join(" "), run: () => show(i) }));
    if (exact.name === "fig" || exact.name === "table") {
      const k = exact.name === "fig" ? "figure" : "table";
      return D.figures.filter(f => f.kind === k &&
          (!arg || String(f.num).startsWith(arg) || (f.title || "").toLowerCase().includes(arg.toLowerCase())))
        .map(f => ({ label: `${k === "table" ? "Table" : "Figure"} ${f.num} — ${f.title}`,
                     sub: f.page ? "page " + f.page : "", run: () => openFigure(f) }));
    }
    return [{ label: `/${exact.name} ${arg}`, sub: exact.help, run: () => runCommand(text) }];
  }
  return COMMANDS.filter(c => c.name.startsWith(name)).map(c => ({
    label: `/${c.name} ${c.args}`, sub: c.help,
    // a command that takes anything reopens the box ready for it; only a command
    // with no argument at all runs on the first Enter
    run: () => { if (c.args) openPalette("/" + c.name + " ");
                 else { closePalette(); c.run(""); } } }));
}
function renderPal() {
  const list = $("#palList"), items = suggest($("#palInput").value);
  list.innerHTML = ""; palSel = Math.min(palSel, Math.max(0, items.length - 1));
  items.forEach((it, k) => {
    const d = document.createElement("div");
    d.className = "pal-item" + (k === palSel ? " sel" : "");
    d.innerHTML = `<div>${esc(it.label)}</div>${it.sub ? `<div class="pal-sub">${esc(it.sub)}</div>` : ""}`;
    d.onmousedown = e => { e.preventDefault(); closePalette(); it.run(); };
    list.appendChild(d);
    if (k === palSel) requestAnimationFrame(() => d.scrollIntoView({ block: "nearest" }));
  });
  list._items = items;
}

/* ------------------------------------------------------------------ loading UI */
async function loadFile(file) {
  try {
    mountDeck(parseDeck(await file.text(), file.name.replace(/\.html?$/i, "")));
  } catch (e) { toast(e.message); console.error(e); }
}
async function loadUrl(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} loading ${url}`);
  mountDeck(parseDeck(await r.text(), url.split("/").pop()));
}
async function boot() {
  const inline = document.getElementById("deck-source");
  if (inline) {
    // bundle.py escapes "</script" so the payload can sit inside a <script>
    const html = inline.textContent.replace(/<\\\/script/g, "</script");
    mountDeck(parseDeck(html, document.title));
    return;
  }
  const url = new URLSearchParams(location.search).get("deck");
  if (url) { try { return await loadUrl(url); } catch (e) { toast(e.message); } }
  const last = await DB.get("last");
  if (last && last.html) {
    try { mountDeck(parseDeck(last.html, last.name)); toast("Reopened your last deck"); return; }
    catch (e) { /* fall through to the drop zone */ }
  }
  document.body.classList.add("no-deck");
}

/* ------------------------------------------------------------------ wiring */
document.addEventListener("DOMContentLoaded", () => {
  $("#prev").onclick = prev; $("#next").onclick = next;
  $("#hidePane").onclick = () => togglePane();
  $("#editBtn").onclick = () => setEdit(!editMode);
  $("#timer").onclick = () => Timer.toggle();
  $("#noteBadge").onclick = () => { if (paneHidden) togglePane(false); };
  $("#log").addEventListener("click", e => {
    const b = e.target.closest(".del"); if (!b) return;
    const msg = b.closest(".msg");
    if (msg && msg.dataset.own !== undefined) deleteNote(+msg.dataset.own);
    else toast("That note came with the deck");
  });
  /* a deck can link one slide to another (Beamer's buttons become these);
     B brings you back, as with any jump */
  $("#deck").addEventListener("click", e => {
    const a = e.target.closest("[data-goto],[data-peek]");
    if (!a || !D) return;
    e.preventDefault();
    const n = +(a.dataset.peek || a.dataset.goto);
    if (!(n >= 1 && n <= D.slides.length)) return;
    a.dataset.peek ? peekSlide(n - 1, { play: a.hasAttribute("data-peek-play"),
                                        from: a.hasAttribute("data-peek-zoom") ? a.getBoundingClientRect() : null })
                   : show(n - 1);
  });
  $("#ansClose").onclick = closeAnswer;
  const ansIn = $("#ansInput");
  const sendFollowUp = () => {
    const v = ansIn.value.trim(); if (!v) return;
    ansIn.value = ""; askClaude(lastMode, v);
  };
  ansIn.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); sendFollowUp(); }
    if (e.key === "Escape") { e.preventDefault(); closeAnswer(); }
    e.stopPropagation();
  });
  $("#ansSend").onclick = sendFollowUp;
  $("#openBtn").onclick = () => $("#file").click();
  $("#file").onchange = e => e.target.files[0] && loadFile(e.target.files[0]);
  $(".lb-prev").onclick = e => { e.stopPropagation(); stepFigure(-1); };
  $(".lb-next").onclick = e => { e.stopPropagation(); stepFigure(1); };
  $("#lbImg").onclick = e => { e.stopPropagation(); $("#lightbox").classList.toggle("zoom"); };
  $("#lightbox").addEventListener("click", e => {
    if (e.target === $("#lightbox") || e.target.classList.contains("lb-box")) closeLightbox();
  });

  const inp = $("#palInput");
  inp.addEventListener("input", () => { palSel = 0; renderPal(); });
  inp.addEventListener("keydown", e => {
    const items = $("#palList")._items || [];
    if (e.key === "ArrowDown") { e.preventDefault(); palSel = Math.min(palSel + 1, items.length - 1); renderPal(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); palSel = Math.max(palSel - 1, 0); renderPal(); }
    else if (e.key === "Tab") { e.preventDefault();
      if (items[palSel] && items[palSel].label.startsWith("/")) { inp.value = items[palSel].label.split(" <")[0] + " "; renderPal(); } }
    else if (e.key === "Enter") { e.preventDefault();
      const v = inp.value;
      captureOrigin($(".pal-box"));
      // Enter takes the highlighted suggestion (the first one unless you moved);
      // a command that needs an argument reopens the box prefilled with it.
      if (items[palSel]) { closePalette(); items[palSel].run(); return; }
      closePalette(); if (palMode !== "list") runCommand(v); }
    else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
  });

  const cmd = $("#cmd");
  cmd.addEventListener("keydown", e => {
    if (e.key === "Enter") { captureOrigin(cmd); runCommand(cmd.value); cmd.value = ""; }
    if (e.key === "Escape") cmd.blur();
  });
  $("#send").onclick = () => { captureOrigin(cmd); runCommand(cmd.value); cmd.value = ""; };

  // drag and drop a deck anywhere
  ["dragenter", "dragover"].forEach(t => document.addEventListener(t, e => {
    e.preventDefault(); document.body.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach(t => document.addEventListener(t, e => {
    if (t === "dragleave" && e.relatedTarget) return;
    document.body.classList.remove("dragging");
  }));
  document.addEventListener("drop", e => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) loadFile(f);
  });

  // selection -> ask Claude
  const askbtn = $("#askbtn"); let selText = "";
  hideAsk = () => { askbtn.style.display = "none"; try { window.getSelection().removeAllRanges(); } catch (e) {} };
  document.addEventListener("selectionchange", () => {
    const sel = window.getSelection(), t = sel.toString().trim();
    const stage = $("#deck");
    if (!t || !sel.rangeCount || !stage.contains(sel.anchorNode)) { askbtn.style.display = "none"; return; }
    selText = t;
    const r = sel.getRangeAt(0).getBoundingClientRect(), d = stage.getBoundingClientRect();
    askbtn.style.display = "block";
    askbtn.style.left = Math.max(0, r.left - d.left) + "px";
    askbtn.style.top = (r.bottom - d.top + 6) + "px";
  });
  askbtn.onmousedown = e => {
    e.preventDefault(); askbtn.style.display = "none"; window.getSelection().removeAllRanges();
    openPalette('/ask Explain: “' + selText.slice(0, 140) + '”');
  };

  document.addEventListener("keydown", e => {
    const ae = document.activeElement;
    const typing = ae && (ae.isContentEditable || /INPUT|TEXTAREA/.test(ae.tagName));
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault(); $("#palette").classList.contains("open") ? closePalette() : openPalette(""); return; }
    if ((e.metaKey || e.ctrlKey) && e.key === "\\") { e.preventDefault(); togglePane(); return; }
    if (e.key === "Escape") {
      if ($("#lightbox").classList.contains("open")) return closeLightbox();
      if ($("#palette").classList.contains("open")) return closePalette();
      if (!$("#answer").hidden) return closeAnswer();
      if (typing) ae.blur();
      return;
    }
    if (typing || $("#palette").classList.contains("open") || !D) return;
    const k = e.key.toLowerCase();
    if ($("#lightbox").classList.contains("open")) {
      const peek = $("#lbNode .slide");
      const stepPeek = d => {                            // a popped-up slide steps like the real one
        const st = +peek.dataset.step, max = +peek.dataset.frags || 0, to = st + d;
        if (to > max) return closeLightbox();              // played through: back to the slide
        if (to < 0) return;
        peek.dataset.step = to; applySteps(peek);
      };
      if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); peek ? stepPeek(1) : stepFigure(1); }
      if (e.key === "ArrowLeft") { e.preventDefault(); peek ? stepPeek(-1) : stepFigure(-1); }
      if (e.key.toLowerCase() === "z") $("#lightbox").classList.toggle("zoom");
      if (e.key.toLowerCase() === "k") { e.preventDefault(); cycleLink(); }
      return;
    }
    if (k === "k") { e.preventDefault(); return cycleLink(); }
    if (e.key === "/") { e.preventDefault(); openPalette("/"); return; }
    if (k === "l") { e.preventDefault(); return slideList(); }   // else the "l" lands in the box
    if (k === "h") return togglePane();
    if (k === "e") return setEdit(!editMode);
    // whole slides, ignoring the reveals inside them (→ and ← still step through those)
    if (k === "n") { e.preventDefault(); return show(Math.min(cur + 1, D.slides.length - 1), { push: false, dir: 1 }); }
    if (k === "b") { e.preventDefault(); return show(Math.max(cur - 1, 0), { push: false, step: "last", dir: -1 }); }
    if (k === "f") return toggleFull();
    if (k === "t") return Timer.toggle();
    if (k === "o") return $("#file").click();
    if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") { e.preventDefault(); next(); }
    if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); prev(); }
    if (e.key === "Home") show(0);
    if (e.key === "End") show(D.slides.length - 1);
  });

  window.addEventListener("resize", () => { if (D) renderNoteBadge(); });
  // a scroll on the slide moves a slide: down is forward. One move per gesture,
  // so a trackpad's inertia does not carry you through the deck.
  let wheelAt = 0, wheelAcc = 0;
  $("#deck").addEventListener("wheel", e => {
    if (!D || $("#lightbox").classList.contains("open") || $("#palette").classList.contains("open")) return;
    e.preventDefault();
    const now = Date.now();
    if (now - wheelAt < 650) return;
    wheelAcc += e.deltaY;
    if (Math.abs(wheelAcc) < 40) return;
    wheelAt = now;
    const fwd = wheelAcc > 0; wheelAcc = 0;
    if (fwd) { if (cur < D.slides.length - 1) show(cur + 1, { push: false, dir: 1 }); }
    else if (cur > 0) show(cur - 1, { push: false, step: "last", dir: -1 });
  }, { passive: false });
  // don't charge a slide for time when the deck isn't on screen
  document.addEventListener("visibilitychange", () =>
    document.hidden ? SlideClock.pause() : SlideClock.resume());
  window.addEventListener("pagehide", () => SlideClock.pause());
  boot();
});

function toggleFull() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
  else document.exitFullscreen();
}
let toastT;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 2000);
}

window.PREZ = { show: i => show(i), next, prev, back, openPalette, closePalette, runCommand,
                openFigure, peekSlide, togglePane, setEdit, loadFile, Timer, SlideClock, slideList, askClaude,
                get deck() { return D; }, get chat() { return chat; } };
})();
