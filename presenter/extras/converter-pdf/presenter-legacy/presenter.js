/* Presenter app. Expects a global DECK = {id,title,slides:[{title,tags,frags,html,notes:[..]}],figures:[..]} */
(function(){
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const deckEl=$('#deck'), slides=$$('.slide'), N=slides.length;
let cur=0, history=[], paneHidden=false;
const store={k:'prez:'+DECK.id, data:{notes:{},tags:{},edits:{},paneHidden:false}};
try{ Object.assign(store.data, JSON.parse(localStorage.getItem(store.k)||'{}')); }catch(e){}
const save=()=>{ try{ localStorage.setItem(store.k, JSON.stringify(store.data)); }catch(e){} };

/* ---------- edit mode (off by default: no accidental typing on slides) ---------- */
const editable=$$('[data-edit]'); let editMode=false;
function restoreEdits(){ for(const key in store.data.edits){ const el=document.querySelector(`[data-edit="${CSS.escape(key)}"]`); if(el) el.innerHTML=store.data.edits[key]; } }
function rememberEdit(el){ store.data.edits[el.dataset.edit]=el.innerHTML; save(); }
function setEdit(on){
  editMode=on;
  editable.forEach(el=>el.setAttribute('contenteditable', on?'true':'false'));
  document.body.classList.toggle('editing',on);
  $('#editBtn').textContent = on? 'Editing: on' : 'Editing: off';
  $('#editBtn').classList.toggle('on',on);
  if(!on && document.activeElement && document.activeElement.isContentEditable) document.activeElement.blur();
  toast(on? 'Editing on — click any text to change it' : 'Editing off — slides are locked');
}
editable.forEach(el=>{
  el.setAttribute('contenteditable','false');
  el.addEventListener('input',()=>rememberEdit(el));
  el.addEventListener('blur',()=>rememberEdit(el));
});
restoreEdits();

/* ---------- slides ---------- */
function applySteps(s){const st=+s.dataset.step; s.querySelectorAll('[data-in]').forEach(el=>el.classList.toggle('on',+el.dataset.in<=st));}
new MutationObserver(ms=>ms.forEach(m=>applySteps(m.target))).observe(deckEl,{attributes:true,subtree:true,attributeFilter:['data-step']});
slides.forEach(s=>s.dataset.step=0);
function show(i,{push=true,step=0}={}){
  if(push && i!==cur) history.push(cur);
  cur=(i+N)%N;
  slides.forEach((s,k)=>s.classList.toggle('active',k===cur));
  slides[cur].dataset.step = step==='last'? slides[cur].dataset.frags : 0;
  $('#counter').textContent=`${cur+1} / ${N}`;
  renderPane();
}
function next(){const s=slides[cur],st=+s.dataset.step,max=+s.dataset.frags; if(st<max) s.dataset.step=st+1; else if(cur<N-1) show(cur+1,{push:false});}
function prev(){const s=slides[cur],st=+s.dataset.step; if(st>0) s.dataset.step=st-1; else if(cur>0) show(cur-1,{push:false,step:'last'});}
function back(){ if(history.length){ const i=history.pop(); show(i,{push:false}); } else toast('Nothing to go back to'); }

/* ---------- slide meta ---------- */
const meta=i=>DECK.slides[i];
const tagsOf=i=>[...new Set([...(meta(i).tags||[]), ...(store.data.tags[i]||[])])];
function findSlides(q){
  q=q.trim().toLowerCase(); if(!q) return [];
  if(/^\d+$/.test(q)){ const n=+q; return n>=1&&n<=N? [n-1]:[]; }
  const tag=q.startsWith('#')? q.slice(1):null;
  const hits=[];
  for(let i=0;i<N;i++){
    const t=(meta(i).title||'').toLowerCase(), tg=tagsOf(i).map(x=>x.toLowerCase());
    if(tag){ if(tg.some(x=>x.startsWith(tag))) hits.push(i); }
    else if(t.includes(q) || tg.some(x=>x.includes(q))) hits.push(i);
  }
  return hits;
}

/* ---------- side pane ---------- */
const pane=$('#pane'), log=$('#log');
function notesOf(i){ return [...(meta(i).notes||[]).map(t=>({kind:'prep',text:t})), ...(store.data.notes[i]||[])]; }
function renderPane(){
  const m=meta(cur);
  $('#paneTitle').textContent=`Slide ${cur+1} · ${stripHtml(m.title||'')}`;
  const tg=tagsOf(cur); $('#paneTags').innerHTML=tg.map(t=>`<span class="tag">#${esc(t)}</span>`).join('')||'<span class="dim">no tags · /tag name</span>';
  log.innerHTML='';
  notesOf(cur).forEach(n=>addMsg(n.kind,n.html||esc(n.text),false));
  log.scrollTop=log.scrollHeight;
}
function addMsg(kind,html,persist=true){
  const d=document.createElement('div'); d.className='msg '+kind;
  const label={prep:'Prepared',live:'Note',q:'You → Claude',ai:'Claude',data:'Data',sys:'System'}[kind]||kind;
  d.innerHTML=`<div class="tag-l">${label}</div>${html}`; log.appendChild(d); log.scrollTop=log.scrollHeight;
  if(persist){ (store.data.notes[cur]=store.data.notes[cur]||[]).push({kind,html}); save(); }
}
function togglePane(force){ paneHidden = force===undefined? !paneHidden : force; document.body.classList.toggle('pane-hidden',paneHidden); store.data.paneHidden=paneHidden; save(); }
if(store.data.paneHidden) togglePane(true);

/* ---------- lightbox ---------- */
const lb=$('#lightbox'); let lbIdx=-1;
function openFigure(f){ if(!f) return toast('Not found');
  lbIdx=DECK.figures.indexOf(f);
  $('#lbImg').src=f.src; $('#lbCap').innerHTML=`<b>${f.kind==='table'?'Table':'Figure'} ${f.num}.</b> ${esc(f.title)} <span class="dim">· ${esc(f.source||'source')} p.${f.page} · click to zoom · ←/→ for the next one</span>`;
  lb.classList.remove('zoom'); lb.classList.add('open'); }
function closeLightbox(){ lb.classList.remove('open','zoom'); }
function stepFigure(d){ if(lbIdx<0) return; const n=(lbIdx+d+DECK.figures.length)%DECK.figures.length; openFigure(DECK.figures[n]); }
lb.addEventListener('click',e=>{ if(e.target===lb||e.target.classList.contains('lb-box')) closeLightbox(); });
$('#lbImg').onclick=e=>{ e.stopPropagation(); lb.classList.toggle('zoom'); };
$('.lb-prev').onclick=e=>{e.stopPropagation(); stepFigure(-1);}; $('.lb-next').onclick=e=>{e.stopPropagation(); stepFigure(1);};
const figByRef=(kind,ref)=>{ ref=String(ref).trim().toLowerCase();
  return DECK.figures.find(f=>f.kind===kind && (String(f.num)===ref || f.title.toLowerCase().includes(ref))); };

/* ---------- backend ---------- */
/* With no backend configured the AI and data commands explain themselves;
   point DECK.api at the server (see /server) and they go live.            */
const API = (typeof DECK.api === "string" && DECK.api) || null;
try{ window.PREZ_TOKEN = window.PREZ_TOKEN || localStorage.getItem('prez_token') || null; }catch(e){}
async function callApi(path, payload, onText){
  if(!API){ onText('<i>[No backend configured yet. Set DECK.api to your server URL '
    + 'and this answer will come from the API.]</i>'); return; }
  try{
    const r = await fetch(API.replace(/\/$/,'') + path, {
      method:'POST', headers:{'Content-Type':'application/json',
        ...(window.PREZ_TOKEN? {'Authorization':'Bearer '+window.PREZ_TOKEN}:{})},
      body: JSON.stringify(payload)});
    if(!r.ok){ onText('<i>[Server said '+r.status+'. '+esc(await r.text().catch(()=>''))+']</i>'); return; }
    const ct=r.headers.get('content-type')||'';
    if(ct.includes('text/event-stream')||ct.includes('text/plain')){
      const rd=r.body.getReader(), dec=new TextDecoder(); let acc='';
      for(;;){ const {value,done}=await rd.read(); if(done) break;
        acc+=dec.decode(value,{stream:true}); onText(esc(acc).replace(/\n/g,'<br>')); }
    } else { const j=await r.json(); onText(renderResult(j)); }
  }catch(e){ onText('<i>[Could not reach the server: '+esc(e.message)+']</i>'); }
}
function renderResult(j){
  if(j.html) return j.html;
  if(j.text) return esc(j.text).replace(/\n/g,'<br>');
  if(j.quote) return `<b>${esc(j.quote.symbol)}</b> ${esc(j.quote.price)} `
    + `<span class="${j.quote.change>=0?'up':'down'}">${j.quote.change>=0?'▲':'▼'} ${esc(j.quote.change)}%</span>`
    + `<div class="dim">${esc(j.quote.asOf||'')}</div>`;
  return '<pre>'+esc(JSON.stringify(j,null,1))+'</pre>';
}
/* a message that fills in when the answer arrives */
function streaming(kind){
  const d=document.createElement('div'); d.className='msg '+kind;
  const label={ai:'Claude',data:'Data'}[kind]||kind;
  d.innerHTML=`<div class="tag-l">${label}</div><div class="bd">…</div>`;
  log.appendChild(d); log.scrollTop=log.scrollHeight;
  const body=d.querySelector('.bd');
  return html=>{ body.innerHTML=html; log.scrollTop=log.scrollHeight;
                 store.data.notes[cur]=(store.data.notes[cur]||[]);
                 const rec={kind,html:`<div class="bd">${html}</div>`};
                 const last=store.data.notes[cur][store.data.notes[cur].length-1];
                 if(last && last.__live) Object.assign(last,rec); else store.data.notes[cur].push({...rec,__live:true});
                 save(); };
}
function slideContext(){
  const s=slides[cur], m=meta(cur);
  return {slide:cur+1, title:stripHtml(m.title||''), tags:tagsOf(cur),
          text:(s.innerText||'').trim().slice(0,4000),
          deck:DECK.title, notes:notesOf(cur).map(n=>n.text||stripHtml(n.html||''))};
}

/* ---------- commands ---------- */
const COMMANDS=[
 {name:'go',   args:'<number | title words | #tag>', help:'Jump to a slide', run:a=>{ const h=findSlides(a); if(!h.length) return toast('No slide matches "'+a+'"'); if(h.length===1) show(h[0]); else pickSlide(h); }},
 {name:'back', args:'', help:'Return to the slide you jumped from', run:back},
 {name:'fig',  args:'<number | words>', help:'Open a figure from the paper', run:a=>openFigure(figByRef('figure',a))},
 {name:'table',args:'<number | words>', help:'Open a table from the paper', run:a=>openFigure(figByRef('table',a))},
 {name:'find', args:'<words>', help:'Search figures, tables and slide titles', run:a=>{ const q=a.toLowerCase(); const fs=DECK.figures.filter(f=>f.title.toLowerCase().includes(q)); const ss=findSlides(a);
    if(!fs.length&&!ss.length) return toast('Nothing found');
    openPalette('', [...fs.map(f=>({label:`${f.kind==='table'?'Table':'Figure'} ${f.num} — ${f.title}`, run:()=>openFigure(f)})), ...ss.map(i=>({label:`Slide ${i+1} — ${stripHtml(meta(i).title)}`, run:()=>show(i)}))]); }},
 {name:'note', args:'<text>', help:'Save a note on this slide', run:a=>addMsg('live',esc(a))},
 {name:'tag',  args:'<name>', help:'Tag this slide', run:a=>{ const t=a.replace(/^#/,'').trim(); if(!t) return; (store.data.tags[cur]=store.data.tags[cur]||[]).push(t); save(); renderPane(); toast('Tagged #'+t); }},
 {name:'ask',  args:'<question>', help:'Ask Claude — answers only from this deck', run:a=>{
    addMsg('q',esc(a)); callApi('/ask',{question:a, context:slideContext(), scope:'deck'}, streaming('ai')); }},
 {name:'claude',args:'<question>', help:'Ask Claude — unrestricted', run:a=>{
    addMsg('q',esc(a)); callApi('/claude',{question:a, context:slideContext()}, streaming('ai')); }},
 {name:'price',args:'<TICKER>', help:'Latest stock quote', run:a=>{
    addMsg('q','/price '+esc(a)); callApi('/data/price',{symbol:a.trim().toUpperCase()}, streaming('data')); }},
 {name:'yield',args:'<10y | 2y | …>', help:'Latest Treasury yield (FRED)', run:a=>{
    addMsg('q','/yield '+esc(a)); callApi('/data/yield',{tenor:a.trim()||'10y'}, streaming('data')); }},
 {name:'news', args:'<topic>', help:'News snippet', run:a=>{
    addMsg('q','/news '+esc(a)); callApi('/data/news',{topic:a.trim()}, streaming('data')); }},
 {name:'fx',   args:'<PAIR e.g. USDCAD>', help:'Exchange rate', run:a=>{
    addMsg('q','/fx '+esc(a)); callApi('/data/fx',{pair:a.trim().toUpperCase()}, streaming('data')); }},
 {name:'series',args:'<FRED id e.g. UNRATE>', help:'Any FRED series, latest value', run:a=>{
    addMsg('q','/series '+esc(a)); callApi('/data/series',{id:a.trim().toUpperCase()}, streaming('data')); }},
 {name:'edit', args:'[on | off]', help:'Turn slide editing on or off (off by default)', run:a=>{ const t=a.trim().toLowerCase(); setEdit(t==='on'?true: t==='off'?false: !editMode); }},
 {name:'revert',args:'[all]', help:'Undo your edits to this slide (or the whole deck)', run:a=>{
    if(a.trim().toLowerCase()==='all'){ store.data.edits={}; save(); return location.reload(); }
    let n=0; slides[cur].querySelectorAll('[data-edit]').forEach(el=>{ if(store.data.edits[el.dataset.edit]!==undefined){ delete store.data.edits[el.dataset.edit]; n++; } });
    save(); if(n) location.reload(); else toast('No edits on this slide'); }},
 {name:'pane', args:'', help:'Show / hide the side pane', run:()=>togglePane()},
 {name:'help', args:'', help:'List commands', run:()=>openPalette('', COMMANDS.map(c=>({label:`/${c.name} ${c.args}`, sub:c.help, run:()=>openPalette('/'+c.name+' ')})))},
];
function runCommand(text){
  text=text.trim(); if(!text) return;
  if(!text.startsWith('/')){ addMsg('live',esc(text)); return; }
  const m=text.slice(1).match(/^(\S+)\s*(.*)$/); if(!m) return;
  const c=COMMANDS.find(c=>c.name===m[1].toLowerCase()); if(!c) return toast('Unknown command /'+m[1]);
  c.run(m[2]);
}
function pickSlide(hits){ openPalette('', hits.map(i=>({label:`Slide ${i+1} — ${stripHtml(meta(i).title)}`, sub:tagsOf(i).map(t=>'#'+t).join(' '), run:()=>show(i)}))); }

/* ---------- palette ---------- */
const pal=$('#palette'), palIn=$('#palInput'), palList=$('#palList'); let palItems=[], palSel=0, palMode='cmd';
function openPalette(text='', items=null){
  pal.classList.add('open'); palIn.value=text; palMode=items?'list':'cmd';
  if(items){ palItems=items; palIn.placeholder='Choose…'; } else palIn.placeholder='Type a command (/go 12, /fig 3, /ask …) or a note';
  renderPal(); palIn.focus(); palIn.setSelectionRange(text.length,text.length);
}
function closePalette(){ pal.classList.remove('open'); palIn.blur(); }
function suggest(text){
  if(palMode==='list') return palItems.filter(it=>it.label.toLowerCase().includes(text.toLowerCase()));
  if(!text.startsWith('/')) return text? [{label:'Save as note on this slide', sub:text, run:()=>runCommand(text)}]:[];
  const m=text.slice(1).match(/^(\S*)\s?(.*)$/); const name=m[1].toLowerCase(), arg=m[2];
  const exact=COMMANDS.find(c=>c.name===name);
  if(exact && (text.includes(' ')||arg)){
    if(exact.name==='go' && arg) return findSlides(arg).slice(0,8).map(i=>({label:`Slide ${i+1} — ${stripHtml(meta(i).title)}`, sub:tagsOf(i).map(t=>'#'+t).join(' '), run:()=>show(i)}));
    if((exact.name==='fig'||exact.name==='table') && arg){ const k=exact.name==='fig'?'figure':'table';
      return DECK.figures.filter(f=>f.kind===k && (String(f.num).startsWith(arg)||f.title.toLowerCase().includes(arg.toLowerCase()))).map(f=>({label:`${k==='table'?'Table':'Figure'} ${f.num} — ${f.title}`, sub:'page '+f.page, run:()=>openFigure(f)})); }
    if((exact.name==='fig'||exact.name==='table') && !arg){ const k=exact.name==='fig'?'figure':'table';
      return DECK.figures.filter(f=>f.kind===k).map(f=>({label:`${k==='table'?'Table':'Figure'} ${f.num} — ${f.title}`, sub:'page '+f.page, run:()=>openFigure(f)})); }
    return [{label:`/${exact.name} ${arg}`, sub:exact.help, run:()=>runCommand(text)}];
  }
  return COMMANDS.filter(c=>c.name.startsWith(name)).map(c=>({label:`/${c.name} ${c.args}`, sub:c.help, run:()=>{ if(c.args) openPalette('/'+c.name+' '); else { closePalette(); c.run(''); } }}));
}
function renderPal(){
  const items=suggest(palIn.value); palList.innerHTML=''; palSel=Math.min(palSel,Math.max(0,items.length-1));
  items.forEach((it,k)=>{ const d=document.createElement('div'); d.className='pal-item'+(k===palSel?' sel':''); d.innerHTML=`<div>${esc(it.label)}</div>${it.sub?`<div class="sub">${esc(it.sub)}</div>`:''}`; d.onmousedown=e=>{e.preventDefault(); closePalette(); it.run();}; palList.appendChild(d); });
  palList.dataset.items=JSON.stringify(items.map(i=>i.label)); palList._items=items;
}
palIn.addEventListener('input',()=>{palSel=0; renderPal();});
palIn.addEventListener('keydown',e=>{
  const items=palList._items||[];
  if(e.key==='ArrowDown'){ e.preventDefault(); palSel=Math.min(palSel+1,items.length-1); renderPal(); }
  else if(e.key==='ArrowUp'){ e.preventDefault(); palSel=Math.max(palSel-1,0); renderPal(); }
  else if(e.key==='Tab'){ e.preventDefault(); if(items[palSel] && items[palSel].label.startsWith('/')){ palIn.value=items[palSel].label.split(' <')[0]+' '; renderPal(); } }
  else if(e.key==='Enter'){ e.preventDefault(); const v=palIn.value;
    if(palMode==='list'){ if(items[palSel]){ closePalette(); items[palSel].run(); } return; }
    if(items[palSel] && (v.startsWith('/go ')||v.startsWith('/fig ')||v.startsWith('/table ')||!v.startsWith('/')) && items.length){ closePalette(); items[palSel].run(); }
    else { closePalette(); runCommand(v); } }
  else if(e.key==='Escape'){ e.preventDefault(); closePalette(); }
});

/* ---------- side-pane input ---------- */
const cmd=$('#cmd');
cmd.addEventListener('keydown',e=>{ if(e.key==='Enter'){ runCommand(cmd.value); cmd.value=''; } if(e.key==='Escape') cmd.blur(); });
$('#send').onclick=()=>{ runCommand(cmd.value); cmd.value=''; };

/* ---------- global keys ---------- */
document.addEventListener('keydown',e=>{
  const typing=document.activeElement && (document.activeElement.isContentEditable || /INPUT|TEXTAREA/.test(document.activeElement.tagName));
  if((e.metaKey||e.ctrlKey) && e.key.toLowerCase()==='k'){ e.preventDefault(); pal.classList.contains('open')? closePalette(): openPalette(''); return; }
  if((e.metaKey||e.ctrlKey) && e.key==='\\'){ e.preventDefault(); togglePane(); return; }
  if(e.key==='Escape'){ if(lb.classList.contains('open')) return closeLightbox(); if(pal.classList.contains('open')) return closePalette(); if(typing) document.activeElement.blur(); return; }
  if(typing || pal.classList.contains('open')) return;
  if(lb.classList.contains('open')){
    if(e.key==='ArrowRight'){e.preventDefault(); stepFigure(1);} if(e.key==='ArrowLeft'){e.preventDefault(); stepFigure(-1);}
    if(e.key==='z'||e.key==='Z') lb.classList.toggle('zoom');
    return; }
  if(e.key==='/'){ e.preventDefault(); openPalette('/'); return; }
  if(e.key==='h' || e.key==='H'){ togglePane(); return; }
  if(e.key==='e' || e.key==='E'){ setEdit(!editMode); return; }
  if(e.key==='b' || e.key==='B'){ back(); return; }
  if(e.key==='f' || e.key==='F'){ toggleFull(); return; }
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){ e.preventDefault(); next(); }
  if(e.key==='ArrowLeft'||e.key==='PageUp'){ e.preventDefault(); prev(); }
  if(e.key==='Home'){ show(0); } if(e.key==='End'){ show(N-1); }
});
$('#prev').onclick=prev; $('#next').onclick=next; $('#openPal').onclick=()=>openPalette(''); $('#hidePane').onclick=()=>togglePane();
$('#editBtn').onclick=()=>setEdit(!editMode);
function toggleFull(){ if(!document.fullscreenElement) document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen(); else document.exitFullscreen(); }

/* ---------- text selection → Ask Claude ---------- */
const askbtn=$('#askbtn'); let selText='';
document.addEventListener('selectionchange',()=>{ const sel=window.getSelection(); const t=sel.toString().trim();
  if(!t||!sel.rangeCount||!deckEl.contains(sel.anchorNode)){ askbtn.style.display='none'; return; }
  selText=t; const r=sel.getRangeAt(0).getBoundingClientRect(), d=deckEl.getBoundingClientRect();
  askbtn.style.display='block'; askbtn.style.left=Math.max(0,r.left-d.left)+'px'; askbtn.style.top=(r.bottom-d.top+6)+'px'; });
askbtn.onmousedown=e=>{ e.preventDefault(); askbtn.style.display='none'; window.getSelection().removeAllRanges(); openPalette('/ask Explain: “'+selText.slice(0,120)+'”'); };

/* ---------- utils ---------- */
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function stripHtml(s){const d=document.createElement('div'); d.innerHTML=s; return d.textContent;}
function later(f){ setTimeout(f,450); }
let toastT; function toast(msg){ const t=$('#toast'); t.textContent=msg; t.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('show'),1800); }
show(0,{push:false});
window.PREZ={show,next,prev,back,openPalette,closePalette,runCommand,openFigure,togglePane};
})();
