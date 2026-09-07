"""
deck (from pdfdeck/texdeck) -> a single self-contained presenter HTML file.

Everything is inlined: fonts, images, the presenter app. The result opens
offline, from a USB stick, on any machine.
"""
import json, os, re
import fonts

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "presenter-legacy")


def slide_css(deck):
    t = deck["theme"]
    W, H = t["page_w"], t["page_h"]
    faces, body_font, disp_font = fonts.css_faces(t.get("family", "LMSans"))
    colors = "\n".join(f'.c{c.lstrip("#")}{{color:{c}}}' for c in t["colors"])
    return f"""
{faces}
.deck{{width:min(100%,calc((100vh - 92px)*{W}/{H}));aspect-ratio:{W}/{H}}}
.slide{{--pt:{100.0 / W:.6f}cqw;position:absolute;inset:0;display:none;
  font-family:{body_font};font-size:calc({t['body_size']:.2f}*var(--pt));
  line-height:calc({t['line_height']:.2f}*var(--pt));color:#000;background:#fff}}
.slide.active{{display:block}}
.ftitle{{position:absolute;left:0;right:0;top:calc({t['title_top']:.1f}*var(--pt));
  text-align:center;font-family:{disp_font};color:{t['title_color']};
  font-size:calc({t['title_size']:.2f}*var(--pt));line-height:1.2}}
.body{{position:absolute}}
.it{{position:relative;margin-left:calc((var(--tx) - var(--bl))*var(--pt));
  margin-top:calc(var(--gap)*var(--pt))}}
.it::before{{content:attr(data-m);position:absolute;color:var(--mcol,#000);
  left:calc((var(--mx) - var(--tx))*var(--pt));font-family:{body_font}}}
.it.para::before{{content:none}}
.it.bullet::before{{content:"";width:.30em;height:.30em;border-radius:50%;
  background:var(--mcol,#000);top:.46em}}
.it.arrow::before{{font-family:system-ui,"DejaVu Sans",sans-serif;font-size:.92em}}
.b{{font-weight:700}} .i{{font-style:italic}}
{colors}
.freebox{{position:absolute;inset:0}}
.freeline{{position:absolute;white-space:nowrap;line-height:1.2}}
.graphic{{position:absolute}}
.pagelayer{{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;
  opacity:0;transition:opacity .35s}}
.pagelayer.on{{opacity:1}}
.f1,.f2,.f3,.f4,.f5{{opacity:1;transition:opacity .25s}}
.slide[data-step="0"] .f1,.slide[data-step="0"] .f2,.slide[data-step="1"] .f2,
.slide[data-step="0"] .f3,.slide[data-step="1"] .f3,.slide[data-step="2"] .f3,
.slide[data-step="0"] .f4,.slide[data-step="1"] .f4,.slide[data-step="2"] .f4,.slide[data-step="3"] .f4
  {{opacity:.18}}
"""


def slide_html(s, deck):
    """One <section>, with editable regions marked for the app's edit mode."""
    n = s["n"]
    parts = []
    if s["title"]:
        parts.append(f'<div class="ftitle" data-edit="s{n}-t">{s["title"]}</div>')
    if s["kind"] == "text" and s.get("box"):
        b = s["box"]
        W = deck["theme"]["page_w"]
        style = (f'--bl:{b["left"]};left:calc({b["left"]}*var(--pt));'
                 f'right:calc({W - b["right"]:.1f}*var(--pt));top:calc({b["top"]}*var(--pt))')
        parts.append(f'<div class="body" style="{style}" data-edit="s{n}-b">{s["html"]}</div>')
    elif s["kind"] == "free":
        parts.append(f'<div class="freebox" data-edit="s{n}-b">{s["html"]}</div>')
    else:
        parts.append(s["html"])
    return (f'<section class="slide {s["kind"]}" data-frags="{s["steps"]}">'
            + "".join(parts) + "</section>")


def build(deck, out_path, deck_id, title, app_dir=APP):
    app_js = open(os.path.join(app_dir, "presenter.js")).read()
    app_css = open(os.path.join(app_dir, "presenter.css")).read()
    extra = deck.get("extra_css", "")

    meta = dict(id=deck_id, title=title,
                slides=[dict(title=re.sub("<[^>]+>", "", s["title"]) or f"Slide {s['n']+1}",
                             tags=s.get("tags", []), frags=s["steps"],
                             notes=s.get("notes", []), pages=s.get("pages", []))
                        for s in deck["slides"]],
                figures=deck.get("figures", []))
    body = "\n".join(slide_html(s, deck) for s in deck["slides"])
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
{slide_css(deck)}
{app_css}
{extra}
</style></head><body>
<div class="pz">
 <div class="stage">
  <div class="deck" id="deck">
{body}
   <div class="askbtn" id="askbtn">Ask Claude about this &#8599;</div>
  </div>
  <div class="bar">
   <button id="prev">&#8592;</button><span id="counter"></span><button id="next">&#8594;</button>
   <button id="openPal">&#8984;K command</button>
   <button id="editBtn">Editing: off</button>
   <span class="grow"></span>
   <span><span class="kbd">/</span> command <span class="kbd">E</span> edit
     <span class="kbd">H</span> pane <span class="kbd">B</span> back <span class="kbd">F</span> full</span>
   <button id="hidePane">Hide pane</button>
  </div>
 </div>
 <aside id="pane">
  <header><div id="paneTitle"></div><div id="paneTags"></div></header>
  <div id="log"></div>
  <div class="inp"><input id="cmd" placeholder="Note, or /go 6, /fig 3, /ask &hellip;"><button id="send">Send</button></div>
 </aside>
</div>
<div id="palette"><div class="pal-box"><input id="palInput" autocomplete="off" spellcheck="false"><div id="palList"></div>
 <div class="pal-hint">&#8593;&#8595; choose &middot; Tab complete &middot; Enter run &middot; Esc close &middot; /help for all commands</div></div></div>
<div id="lightbox"><div class="lb-close">Esc to close</div><div class="lb-nav lb-prev">&#8249;</div><div class="lb-nav lb-next">&#8250;</div>
 <div class="lb-box"><div class="lb-fig"><img id="lbImg" alt=""></div><div id="lbCap"></div></div></div>
<div id="toast"></div>
<script>const DECK={json.dumps(meta)};</script>
<script>{app_js}</script>
</body></html>"""
    open(out_path, "w").write(html)
    return len(html)
