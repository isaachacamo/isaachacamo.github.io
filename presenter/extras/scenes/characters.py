# Richer vector characters: shading, proportions, face detail, ground shadows. Char box 0..240 x 0..480, feet at y=480.
import vector_chars as v1
SKIN='#f3c9a6'; SKIN_SH='#e0a985'; SKIN_HI='#fbe0c8'

DEFS='''<defs>
 <linearGradient id="gSkin" x1="0" x2="1"><stop offset="0" stop-color="#fbe0c8"/><stop offset=".55" stop-color="#f3c9a6"/><stop offset="1" stop-color="#dfa783"/></linearGradient>
 <linearGradient id="gRed" x1="0" x2="1"><stop offset="0" stop-color="#e06a5b"/><stop offset=".5" stop-color="#c94a3d"/><stop offset="1" stop-color="#9c3328"/></linearGradient>
 <linearGradient id="gOrange" x1="0" x2="1"><stop offset="0" stop-color="#f7955a"/><stop offset=".5" stop-color="#e8762c"/><stop offset="1" stop-color="#b9541a"/></linearGradient>
 <linearGradient id="gBlue" x1="0" x2="1"><stop offset="0" stop-color="#c2dcf3"/><stop offset=".5" stop-color="#9ec1e6"/><stop offset="1" stop-color="#6f97c4"/></linearGradient>
 <linearGradient id="gDark" x1="0" x2="1"><stop offset="0" stop-color="#454a5c"/><stop offset=".5" stop-color="#2c2f3a"/><stop offset="1" stop-color="#1b1d24"/></linearGradient>
 <linearGradient id="gHat" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#e9e9ea"/><stop offset="1" stop-color="#c9c9cc"/></linearGradient>
 <linearGradient id="gHair" x1="0" x2="1"><stop offset="0" stop-color="#8a5a3c"/><stop offset=".5" stop-color="#6b3f2a"/><stop offset="1" stop-color="#4a2a1b"/></linearGradient>
 <linearGradient id="gHairM" x1="0" x2="1"><stop offset="0" stop-color="#5a4236"/><stop offset=".5" stop-color="#3a2a22"/><stop offset="1" stop-color="#241812"/></linearGradient>
 <linearGradient id="gSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eef5fc"/><stop offset="1" stop-color="#ffffff"/></linearGradient>
 <linearGradient id="gWall" x1="0" x2="1"><stop offset="0" stop-color="#d7d7dd"/><stop offset="1" stop-color="#b3b3bc"/></linearGradient>
 <linearGradient id="gGlass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#dff0f8"/><stop offset=".5" stop-color="#b9dcea"/><stop offset="1" stop-color="#9ccadd"/></linearGradient>
 <linearGradient id="gStorm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4b5563"/><stop offset="1" stop-color="#9aa3ad" stop-opacity="0"/></linearGradient>
 <radialGradient id="gShadow"><stop offset="0" stop-color="#000" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
 <radialGradient id="gCheek"><stop offset="0" stop-color="#ef8f7c" stop-opacity=".55"/><stop offset="1" stop-color="#ef8f7c" stop-opacity="0"/></radialGradient>
</defs>'''

def face(hair, male=False):
    back,front=hair
    brow = 'stroke-width="3.5"' if male else 'stroke-width="2.6"'
    return f'''
  {back}
  <path d="M104 100 h32 v26 q-16 10 -32 0z" fill="{SKIN_SH}"/>
  <ellipse cx="120" cy="74" rx="46" ry="49" fill="url(#gSkin)"/>
  <ellipse cx="76" cy="78" rx="7" ry="10" fill="{SKIN_SH}"/><ellipse cx="164" cy="78" rx="7" ry="10" fill="{SKIN_SH}"/>
  {front}
  <ellipse cx="103" cy="78" rx="6.5" ry="7" fill="#fff"/><ellipse cx="137" cy="78" rx="6.5" ry="7" fill="#fff"/>
  <circle cx="104.5" cy="79" r="4" fill="#3b2a22"/><circle cx="138.5" cy="79" r="4" fill="#3b2a22"/>
  <circle cx="106" cy="77" r="1.3" fill="#fff"/><circle cx="140" cy="77" r="1.3" fill="#fff"/>
  <path d="M95 66 q8 -6 16 -1" stroke="#4a3328" {brow} fill="none" stroke-linecap="round"/>
  <path d="M129 65 q8 -5 16 1" stroke="#4a3328" {brow} fill="none" stroke-linecap="round"/>
  <path d="M120 84 q-4 8 2 10" stroke="{SKIN_SH}" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  <path d="M107 100 q13 12 26 0" stroke="#a84a3c" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M110 101 q10 7 20 0z" fill="#fff" opacity=".9"/>
  <circle cx="92" cy="94" r="10" fill="url(#gCheek)"/><circle cx="148" cy="94" r="10" fill="url(#gCheek)"/>'''

HAIR_WIFE=('''<path d="M64 84 q-6 -84 56 -84 q62 0 56 84 l0 66 q-12 16 -26 4 v-66 q-4 -28 -30 -32 q-26 4 -30 32 v66 q-14 12 -26 -4z" fill="url(#gHair)"/>''',
  '''<path d="M74 74 q6 -52 46 -52 q40 0 46 52 q-14 -24 -46 -22 q-32 -2 -46 22z" fill="url(#gHair)"/>
     <path d="M86 40 q14 -16 34 -14" stroke="#a5765a" stroke-width="4" fill="none" stroke-linecap="round" opacity=".7"/>''')
HAIR_MAN=('','''<path d="M76 66 q6 -44 44 -44 q38 0 44 44 q-16 -18 -44 -16 q-28 -2 -44 16z" fill="url(#gHairM)"/>''')

def hardhat(band):
    return f'''
  <path d="M68 62 q2 -54 52 -54 q50 0 52 54z" fill="url(#gHat)"/>
  <path d="M82 40 q10 -20 30 -22" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round" opacity=".8"/>
  <rect x="56" y="58" width="128" height="13" rx="6.5" fill="#d4d4d8"/><rect x="56" y="58" width="128" height="6" rx="3" fill="#ececef"/>
  <rect x="102" y="16" width="36" height="14" rx="6" fill="{band}"/>'''

def limb(cls,x,y,w,h,grad,extra=''):
    return f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w/2}" fill="{grad}"/><rect x="{x+w*0.62}" y="{y+8}" width="{w*0.22}" height="{h-16}" rx="{w*0.11}" fill="#000" opacity=".12"/>{extra}</g>'

def hand(cx,cy):
    return f'<circle cx="{cx}" cy="{cy}" r="17" fill="url(#gSkin)"/><path d="M{cx-10} {cy+4} q10 10 20 0" stroke="{SKIN_SH}" stroke-width="2" fill="none"/>'

def shoe(x,color):
    return f'<path d="M{x} 452 h48 q6 0 6 8 v6 q0 6 -6 6 h-48 q-8 0 -8 -8 q0 -12 8 -12z" fill="{color}"/><rect x="{x-8}" y="462" width="62" height="6" rx="3" fill="#111" opacity=".5"/>'

def character(kind):
    if kind=='wife':
        top='url(#gRed)'; pants='url(#gDark)'; sh='#2a1c14'; hair=HAIR_WIFE; hat=''; male=False
        detail='<path d="M92 122 q28 22 56 0 v14 q-28 18 -56 0z" fill="#a23a2f"/><path d="M60 300 h120" stroke="#8a2f25" stroke-width="3"/>'
        item='<g class="item" transform="rotate(-8 181 244)"><rect x="150" y="205" width="64" height="80" rx="4" fill="#d9722a"/><rect x="150" y="205" width="10" height="80" fill="#a9521a"/><rect x="165" y="215" width="40" height="60" fill="#e69a63" opacity=".5"/></g>'
    elif kind=='oil':
        top='url(#gOrange)'; pants='url(#gOrange)'; sh='#2e2e2e'; hair=HAIR_MAN; hat=hardhat('#e8762c'); male=True
        detail='''<path d="M104 118 h32 l-6 18 h-20z" fill="#fff" opacity=".85"/><rect x="118" y="136" width="4" height="160" fill="#b9541a" opacity=".6"/>
          <rect x="58" y="176" width="124" height="14" fill="#e9e9e9"/><rect x="58" y="180" width="124" height="6" fill="#c9c9c9" opacity=".6"/>
          <rect x="70" y="200" width="36" height="34" rx="4" fill="#c85f1e" opacity=".5"/><rect x="134" y="200" width="36" height="34" rx="4" fill="#c85f1e" opacity=".5"/>'''
        item=clipboard()
    else:
        top='url(#gBlue)'; pants='url(#gBlue)'; sh='#2e2e2e'; hair=HAIR_MAN; hat=hardhat('#4a7fbf'); male=True
        detail='''<path d="M100 118 h40 l-20 16z" fill="#fff"/><path d="M112 128 h16 l6 46 l-14 12 l-14 -12z" fill="#2f4f8f"/><path d="M112 128 h16 l-8 8z" fill="#1f3a6b"/>
          <rect x="58" y="188" width="124" height="10" fill="#e7eef7" opacity=".9"/>
          <rect x="70" y="206" width="36" height="34" rx="4" fill="#5f88b8" opacity=".35"/><rect x="134" y="206" width="36" height="34" rx="4" fill="#5f88b8" opacity=".35"/>'''
        item=clipboard()
    legs = (limb('leg legB',80,288,36,168,pants,shoe(74,sh)) + limb('leg legF',124,288,36,168,pants,shoe(118,sh)))
    torso = f'<path d="M56 150 q0 -32 30 -32 h68 q30 0 30 32 v150 q0 16 -16 16 h-96 q-16 0 -16 -16z" fill="{top}"/><path d="M150 118 q34 0 34 32 v150 q0 16 -16 16 h-20z" fill="#000" opacity=".1"/>{detail}'
    armB = limb('arm armB',40,126,36,146,top,hand(58,272))
    armF = limb('arm armF',164,126,36,146,top,hand(182,272))
    shadow='<ellipse cx="120" cy="470" rx="70" ry="10" fill="url(#gShadow)"/>'
    return f'<g class="char {kind}">{shadow}<g class="bodybob">{legs}{torso}{armB}{face(hair,male)}{hat}{armF}{item}</g></g>'

def clipboard():
    return '''<g class="item" transform="rotate(10 181 259)"><rect x="146" y="215" width="72" height="90" rx="6" fill="#4a3b2f"/><rect x="153" y="228" width="58" height="72" fill="#fbfbf7"/>
      <g stroke="#b9c2cc" stroke-width="2"><path d="M160 244 h44 M160 256 h44 M160 268 h30"/></g><rect x="166" y="207" width="32" height="16" rx="4" fill="#8a8f96"/><rect x="172" y="203" width="20" height="8" rx="3" fill="#b8bcc2"/></g>'''

def backdrop(kind):
    if kind=='treated':
        return '''
  <g class="bd">
   <rect x="0" y="215" width="768" height="400" fill="url(#gSky)"/>
   <rect x="0" y="600" width="768" height="424" fill="url(#gSky)"/><ellipse cx="384" cy="1000" rx="400" ry="22" fill="#e9e4dc"/><ellipse cx="200" cy="628" rx="180" ry="12" fill="#000" opacity=".07"/><ellipse cx="545" cy="628" rx="170" ry="12" fill="#000" opacity=".07"/>
   <!-- factory -->
   <rect x="40" y="330" width="290" height="140" rx="6" fill="url(#gWall)"/><path d="M40 330 h290 v14 h-290z" fill="#9a9aa4"/>
   <path d="M40 330 l0 -30 l58 -20 l0 50z M156 330 l0 -30 l58 -20 l0 50z" fill="#b9b9c2"/>
   <g fill="#a6a6b0"><rect x="95" y="230" width="26" height="100"/><rect x="150" y="205" width="26" height="125"/><rect x="205" y="240" width="26" height="90"/></g>
   <g fill="#8f8f9a"><rect x="93" y="230" width="30" height="8"/><rect x="148" y="205" width="30" height="8"/><rect x="203" y="240" width="30" height="8"/></g>
   <g fill="#eeeef1" class="smoke" opacity=".95"><ellipse cx="108" cy="214" rx="22" ry="13"/><ellipse cx="128" cy="196" rx="18" ry="11"/><ellipse cx="163" cy="184" rx="26" ry="15"/><ellipse cx="190" cy="166" rx="20" ry="12"/><ellipse cx="218" cy="224" rx="20" ry="12"/></g>
   <g fill="url(#gGlass)" stroke="#8b8b95" stroke-width="2"><rect x="60" y="380" width="30" height="42"/><rect x="110" y="380" width="30" height="42"/><rect x="160" y="380" width="30" height="42"/><rect x="210" y="380" width="30" height="42"/><rect x="260" y="380" width="30" height="42"/></g>
   <!-- pumpjack -->
   <path d="M14 470 l22 -100 l22 100z" fill="#7a4e33"/><path d="M14 470 l22 -100 l-4 100z" fill="#5f3b26"/>
   <rect x="-4" y="366" width="96" height="10" rx="5" fill="#5c3a26" transform="rotate(-16 44 371)"/><circle cx="36" cy="368" r="9" fill="#e8762c"/><circle cx="36" cy="368" r="4" fill="#b9541a"/>
   <!-- shop -->
   <rect x="380" y="330" width="330" height="290" rx="6" fill="#f2e3d1"/><rect x="380" y="330" width="330" height="26" rx="6" fill="#c9553a"/>
   <text x="545" y="349" font-size="18" fill="#fff" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" letter-spacing="3">GENERAL STORE</text>
   <g><path d="M366 360 h358 v52 q-8 8 -16 8 h-326 q-8 0 -16 -8z" fill="#e26a2a"/>
     <g fill="#fff8f2"><rect x="400" y="360" width="34" height="58"/><rect x="468" y="360" width="34" height="58"/><rect x="536" y="360" width="34" height="58"/><rect x="604" y="360" width="34" height="58"/><rect x="672" y="360" width="34" height="58"/></g>
     <path d="M366 412 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 28 0 v-12 h-358z" fill="#b94f1c"/>
     <rect x="366" y="418" width="358" height="14" fill="#000" opacity=".08"/></g>
   <rect x="400" y="440" width="180" height="130" rx="4" fill="url(#gGlass)" stroke="#c9b7a0" stroke-width="4"/><path d="M405 445 l60 0 l-60 60z" fill="#fff" opacity=".35"/>
   <rect x="600" y="440" width="90" height="180" rx="4" fill="#caa987" stroke="#a9896a" stroke-width="4"/><rect x="612" y="452" width="66" height="70" rx="3" fill="url(#gGlass)"/><circle cx="676" cy="540" r="5" fill="#5c3a26"/>
   <g fill="#e26a2a" opacity=".75"><rect x="415" y="490" width="30" height="24"/><rect x="455" y="470" width="24" height="44"/><rect x="500" y="485" width="34" height="29"/><rect x="545" y="520" width="24" height="36"/></g>
   <rect x="410" y="520" width="160" height="6" fill="#a9896a"/>
  </g>'''
    else:
        return '''
  <g class="bd">
   <rect x="0" y="215" width="768" height="400" fill="url(#gSky)"/>
   <rect x="0" y="600" width="768" height="424" fill="url(#gSky)"/><ellipse cx="384" cy="1000" rx="400" ry="22" fill="#e3e8ee"/><ellipse cx="205" cy="628" rx="180" ry="12" fill="#000" opacity=".07"/><ellipse cx="570" cy="628" rx="160" ry="12" fill="#000" opacity=".07"/>
   <!-- office building -->
   <rect x="420" y="250" width="300" height="372" rx="4" fill="#c9dcef"/><path d="M420 250 h300 v14 h-300z" fill="#8fadd0"/><rect x="700" y="250" width="20" height="372" fill="#000" opacity=".08"/>
   <rect x="470" y="200" width="140" height="60" rx="4" fill="#b4cbe3"/><rect x="470" y="200" width="140" height="8" fill="#8fadd0"/>
   <g fill="url(#gGlass)" stroke="#8fadd0" stroke-width="2"><rect x="440" y="300" width="40" height="40"/><rect x="500" y="300" width="40" height="40"/><rect x="560" y="300" width="40" height="40"/><rect x="620" y="300" width="40" height="40"/>
     <rect x="440" y="370" width="40" height="40"/><rect x="500" y="370" width="40" height="40"/><rect x="560" y="370" width="40" height="40"/><rect x="620" y="370" width="40" height="40"/>
     <rect x="440" y="440" width="40" height="40"/><rect x="500" y="440" width="40" height="40"/><rect x="560" y="440" width="40" height="40"/><rect x="620" y="440" width="40" height="40"/></g>
   <rect x="480" y="520" width="180" height="34" rx="4" fill="#4f78ab"/><text x="570" y="544" font-size="22" fill="#fff" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" letter-spacing="2">WATER</text>
   <rect x="540" y="570" width="60" height="52" fill="url(#gGlass)" stroke="#8fadd0" stroke-width="3"/>
   <!-- shop -->
   <rect x="40" y="330" width="330" height="290" rx="6" fill="#eef2f6"/><rect x="40" y="330" width="330" height="26" rx="6" fill="#2f5f9f"/>
   <text x="205" y="349" font-size="18" fill="#fff" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" letter-spacing="3">GENERAL STORE</text>
   <g><path d="M26 360 h358 v52 q-8 8 -16 8 h-326 q-8 0 -16 -8z" fill="#2f5f9f"/>
     <g fill="#f4f8fc"><rect x="60" y="360" width="34" height="58"/><rect x="128" y="360" width="34" height="58"/><rect x="196" y="360" width="34" height="58"/><rect x="264" y="360" width="34" height="58"/><rect x="332" y="360" width="34" height="58"/></g>
     <path d="M26 412 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 30 0 q15 22 28 0 v-12 h-358z" fill="#22477a"/>
     <rect x="26" y="418" width="358" height="14" fill="#000" opacity=".08"/></g>
   <rect x="60" y="440" width="180" height="130" rx="4" fill="url(#gGlass)" stroke="#b7c3d0" stroke-width="4"/><path d="M65 445 l60 0 l-60 60z" fill="#fff" opacity=".35"/>
   <rect x="260" y="440" width="90" height="180" rx="4" fill="#9fb3c8" stroke="#7f95ad" stroke-width="4"/><rect x="272" y="452" width="66" height="70" rx="3" fill="url(#gGlass)"/><circle cx="336" cy="540" r="5" fill="#3a4a5c"/>
   <g fill="#2f5f9f" opacity=".6"><rect x="75" y="490" width="30" height="24"/><rect x="115" y="470" width="24" height="44"/><rect x="160" y="485" width="34" height="29"/><rect x="205" y="520" width="24" height="36"/></g>
   <rect x="70" y="520" width="160" height="6" fill="#7f95ad"/>
   <g><ellipse cx="392" cy="612" rx="36" ry="24" fill="#6fa36a"/><ellipse cx="372" cy="600" rx="24" ry="18" fill="#7fb37a"/><ellipse cx="410" cy="598" rx="22" ry="16" fill="#86bb80"/></g>
  </g>'''

STORM='''<g class="storm-g">
  <rect x="0" y="215" width="768" height="420" fill="url(#gStorm)"/>
  <g fill="#4b515b"><ellipse cx="120" cy="290" rx="120" ry="52"/><ellipse cx="260" cy="262" rx="140" ry="62"/><ellipse cx="420" cy="290" rx="130" ry="52"/><ellipse cx="600" cy="272" rx="130" ry="58"/></g>
  <g fill="#5d646f"><ellipse cx="180" cy="320" rx="90" ry="34"/><ellipse cx="500" cy="322" rx="110" ry="36"/></g>
  <path d="M300 300 l-30 70 h30 l-24 70 l60 -90 h-30 l30 -50z" fill="#ffd84d" stroke="#fff3b0" stroke-width="3"/>
</g>'''

def panel_svg(kind, steps):
    s_w,s_h,s_t = steps
    side='L' if kind=='treated' else 'R'
    if kind=='treated':
        wife_x, hus_x = 350, 110; bub=v1.bubble("I work in the oil sector!",'right'); bub_at=(hus_x-60,400); hus_kind='oil'
    else:
        wife_x, hus_x = 200, 440; bub=v1.bubble("I work in another sector.",'left'); bub_at=(hus_x+110,400); hus_kind='ctrl'
    scale=1.05; y0=1000-480*scale
    return f'''<svg class="vpanel {kind}" viewBox="0 0 768 1024" xmlns="http://www.w3.org/2000/svg">{DEFS}
  <g class="layer scene" data-in="{s_t}">{backdrop(kind)}{STORM if kind=='treated' else ''}</g>
  <g class="layer tags" data-in="{s_t}">{v1.tags(kind)}</g>
  <g class="actor from{side}" data-in="{s_w}"><g transform="translate({wife_x} {y0}) scale({scale})">{character('wife')}</g></g>
  <g class="actor from{side} husband" data-in="{s_h}"><g transform="translate({hus_x} {y0}) scale({scale})">{character(hus_kind)}</g>
     <g transform="translate({bub_at[0]} {bub_at[1]})">{bub}</g></g>
</svg>'''

CSS = v1.CSS
