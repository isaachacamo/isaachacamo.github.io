# Original flat-vector characters and backdrops, drawn in code. Local char box: 0..240 x 0..480 (feet at y=480)
SKIN='#f4cdae'; SKIN2='#e8b895'

def face(hair):
    back,front=hair
    return f'''
  {back}
  <rect x="106" y="108" width="28" height="22" fill="{SKIN2}"/>
  <circle cx="120" cy="72" r="46" fill="{SKIN}"/>
  {front}
  <circle cx="103" cy="76" r="4.2" fill="#2b2320"/><circle cx="137" cy="76" r="4.2" fill="#2b2320"/>
  <path d="M96 64 q7 -5 14 0" stroke="#3b2a22" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M130 64 q7 -5 14 0" stroke="#3b2a22" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M108 92 q12 10 24 0" stroke="#b0503f" stroke-width="3.5" fill="none" stroke-linecap="round"/>
  <ellipse cx="94" cy="88" rx="7" ry="4" fill="#f2a08e" opacity=".7"/><ellipse cx="146" cy="88" rx="7" ry="4" fill="#f2a08e" opacity=".7"/>'''

HAIR_WIFE=('''<path d="M66 80 q-4 -76 54 -76 q58 0 54 76 l-2 60 q-10 14 -24 4 v-60 q-4 -24 -28 -28 q-24 4 -28 28 v60 q-14 10 -24 -4z" fill="#6b3f2a"/>''',
  '''<path d="M76 70 q8 -46 44 -46 q36 0 44 46 q-18 -20 -44 -18 q-26 -2 -44 18z" fill="#7a4a33"/>''')
HAIR_MAN=('','''<path d="M78 62 q8 -40 42 -40 q34 0 42 40 q-18 -14 -42 -12 q-24 -2 -42 12z" fill="#3a2a22"/>''')

def hardhat(band):
    return f'''
  <path d="M70 60 q0 -48 50 -48 q50 0 50 48z" fill="#f2f2f2"/>
  <rect x="60" y="56" width="120" height="12" rx="6" fill="#e0e0e0"/>
  <rect x="104" y="18" width="32" height="16" rx="6" fill="{band}"/>'''

def limb(cls,x,y,w,h,color,extra=''):
    return f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w/2}" fill="{color}"/>{extra}</g>'

def character(kind):
    """kind: wife | oil | ctrl"""
    if kind=='wife':
        top='#c94a3d'; pants='#2c2f3a'; shoe='#3a2a22'; hair=HAIR_WIFE; hat=''
        stripes=''
        item='''<g class="item"><rect x="150" y="205" width="62" height="78" rx="4" fill="#d9722a" transform="rotate(-8 181 244)"/><rect x="156" y="205" width="8" height="78" fill="#b85a1c" transform="rotate(-8 181 244)"/></g>'''
    elif kind=='oil':
        top='#e8762c'; pants='#e8762c'; shoe='#3a3a3a'; hair=HAIR_MAN; hat=hardhat('#e8762c')
        stripes='<rect x="60" y="180" width="120" height="12" fill="#e6e6e6" opacity=".9"/><rect x="60" y="150" width="120" height="6" fill="#d0d0d0" opacity=".6"/>'
        item='''<g class="item"><rect x="146" y="215" width="70" height="88" rx="5" fill="#3a3a3a" transform="rotate(10 181 259)"/><rect x="153" y="228" width="56" height="70" fill="#fff" transform="rotate(10 181 259)"/><rect x="168" y="208" width="26" height="14" rx="3" fill="#777" transform="rotate(10 181 259)"/></g>'''
    else:
        top='#9ec1e6'; pants='#8fb3d9'; shoe='#3a3a3a'; hair=HAIR_MAN; hat=hardhat('#5b8fc9')
        stripes='<rect x="60" y="190" width="120" height="10" fill="#e6eef7" opacity=".9"/><path d="M112 130 l8 0 l6 44 l-10 8 l-10 -8z" fill="#2f4f8f"/><path d="M104 128 h32 l-16 12z" fill="#fff"/>'
        item='''<g class="item"><rect x="146" y="215" width="70" height="88" rx="5" fill="#3a3a3a" transform="rotate(10 181 259)"/><rect x="153" y="228" width="56" height="70" fill="#fff" transform="rotate(10 181 259)"/><rect x="168" y="208" width="26" height="14" rx="3" fill="#777" transform="rotate(10 181 259)"/></g>'''
    legs = (limb('leg legB',78,290,36,150,pants,f'<rect x="72" y="428" width="48" height="26" rx="12" fill="{shoe}"/>') +
            limb('leg legF',126,290,36,150,pants,f'<rect x="120" y="428" width="48" height="26" rx="12" fill="{shoe}"/>'))
    torso = f'<rect x="58" y="118" width="124" height="190" rx="30" fill="{top}"/>{stripes}'
    armB = limb('arm armB',44,128,36,140,top,f'<circle cx="62" cy="266" r="17" fill="{SKIN}"/>')
    armF = limb('arm armF',160,128,36,140,top,f'<circle cx="178" cy="266" r="17" fill="{SKIN}"/>')
    return f'<g class="char {kind}"><g class="bodybob">{legs}{torso}{armB}{face(hair)}{hat}{armF}{item}</g></g>'

def backdrop(kind):
    if kind=='treated':
        return '''
  <g class="bd">
   
   <!-- factory -->
   <rect x="40" y="330" width="290" height="130" rx="6" fill="#c9c9cf"/>
   <rect x="40" y="330" width="290" height="14" fill="#a9a9b3"/>
   <rect x="95" y="240" width="26" height="100" fill="#b3b3bd"/><rect x="150" y="215" width="26" height="125" fill="#b3b3bd"/><rect x="205" y="250" width="26" height="90" fill="#b3b3bd"/>
   <g fill="#e6e6ea" class="smoke"><ellipse cx="108" cy="226" rx="20" ry="12"/><ellipse cx="163" cy="196" rx="24" ry="14"/><ellipse cx="218" cy="236" rx="18" ry="11"/><ellipse cx="190" cy="176" rx="18" ry="10"/></g>
   <g fill="#7f7f89"><rect x="60" y="380" width="30" height="40"/><rect x="110" y="380" width="30" height="40"/><rect x="160" y="380" width="30" height="40"/><rect x="210" y="380" width="30" height="40"/><rect x="260" y="380" width="30" height="40"/></g>
   <!-- pumpjack -->
   <path d="M12 460 l24 -90 l24 90z" fill="#8a5a3a"/><rect x="0" y="372" width="90" height="10" rx="5" fill="#6d4530" transform="rotate(-14 45 377)"/><circle cx="36" cy="372" r="8" fill="#e26a2a"/>
   <!-- shop -->
   <rect x="380" y="400" width="330" height="200" rx="6" fill="#f4e7d8"/>
   <rect x="380" y="400" width="330" height="10" fill="#d8c7b2"/>
   <g><rect x="366" y="350" width="358" height="60" rx="8" fill="#e26a2a"/>
     <g fill="#fff"><rect x="400" y="350" width="34" height="60"/><rect x="468" y="350" width="34" height="60"/><rect x="536" y="350" width="34" height="60"/><rect x="604" y="350" width="34" height="60"/><rect x="672" y="350" width="34" height="60"/></g>
     <path d="M366 405 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 28 0 v-10 h-358z" fill="#c2551e"/></g>
   <rect x="400" y="430" width="180" height="120" rx="4" fill="#bfe0ee"/><rect x="600" y="430" width="90" height="170" rx="4" fill="#d8c7b2"/><circle cx="676" cy="520" r="5" fill="#6d4530"/>
   <g fill="#e26a2a" opacity=".7"><rect x="415" y="470" width="30" height="24"/><rect x="455" y="450" width="24" height="44"/><rect x="500" y="465" width="34" height="29"/><rect x="545" y="500" width="24" height="36"/></g>
   <rect x="380" y="600" width="330" height="20" fill="#b9553b"/>
  </g>'''
    else:
        return '''
  <g class="bd">
   
   <!-- office building -->
   <rect x="420" y="250" width="300" height="360" rx="6" fill="#c9dcef"/><rect x="420" y="250" width="300" height="14" fill="#9fbad9"/>
   <rect x="470" y="200" width="140" height="60" rx="6" fill="#b4cbe3"/>
   <g fill="#eef5fb"><rect x="440" y="300" width="40" height="40"/><rect x="500" y="300" width="40" height="40"/><rect x="560" y="300" width="40" height="40"/><rect x="620" y="300" width="40" height="40"/>
     <rect x="440" y="370" width="40" height="40"/><rect x="500" y="370" width="40" height="40"/><rect x="560" y="370" width="40" height="40"/><rect x="620" y="370" width="40" height="40"/>
     <rect x="440" y="440" width="40" height="40"/><rect x="500" y="440" width="40" height="40"/><rect x="560" y="440" width="40" height="40"/><rect x="620" y="440" width="40" height="40"/></g>
   <rect x="480" y="520" width="180" height="30" rx="4" fill="#6f95c0"/><text x="570" y="542" font-size="22" fill="#fff" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold">WATER</text>
   <!-- shop -->
   <rect x="40" y="400" width="330" height="200" rx="6" fill="#eef2f6"/><rect x="40" y="400" width="330" height="10" fill="#c9d3de"/>
   <g><rect x="26" y="350" width="358" height="60" rx="8" fill="#2f5f9f"/>
     <g fill="#fff"><rect x="60" y="350" width="34" height="60"/><rect x="128" y="350" width="34" height="60"/><rect x="196" y="350" width="34" height="60"/><rect x="264" y="350" width="34" height="60"/><rect x="332" y="350" width="34" height="60"/></g>
     <path d="M26 405 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 30 0 q15 24 28 0 v-10 h-358z" fill="#24487a"/></g>
   <rect x="60" y="430" width="180" height="120" rx="4" fill="#bfe0ee"/><rect x="260" y="430" width="90" height="170" rx="4" fill="#c9d3de"/><circle cx="336" cy="520" r="5" fill="#4a5a6a"/>
   <g fill="#2f5f9f" opacity=".6"><rect x="75" y="470" width="30" height="24"/><rect x="115" y="450" width="24" height="44"/><rect x="160" y="465" width="34" height="29"/><rect x="205" y="500" width="24" height="36"/></g>
   <rect x="40" y="600" width="330" height="20" fill="#3d5f8a"/>
   
  </g>'''

def tags(kind):
    if kind=='treated':
        return '''<g class="tg"><text x="384" y="80" font-size="46" text-anchor="middle" fill="#e26a2a" font-family="'LM Sans', Arial, sans-serif">Treated Entrepreneur</text>
  <rect x="100" y="104" width="568" height="3" fill="#bbb"/>
  <rect x="120" y="140" width="528" height="66" fill="#e26a2a"/><text x="384" y="186" font-size="34" text-anchor="middle" fill="#fff" font-family="'LM Sans', Arial, sans-serif">Spouse in Oil Sector 2013–2014</text></g>'''
    return '''<g class="tg"><text x="384" y="80" font-size="46" text-anchor="middle" fill="#2f4f8f" font-family="'LM Sans', Arial, sans-serif">Control Entrepreneur</text>
  <rect x="100" y="104" width="568" height="3" fill="#bbb"/>
  <rect x="120" y="140" width="528" height="66" fill="#2f4f8f"/><text x="384" y="186" font-size="34" text-anchor="middle" fill="#fff" font-family="'LM Sans', Arial, sans-serif">Spouse in Other Sector</text></g>'''

STORM='''<g class="storm-g">
  <rect x="0" y="215" width="768" height="420" fill="#6b7280" opacity=".35"/>
  <g fill="#5a616b"><ellipse cx="120" cy="290" rx="110" ry="50"/><ellipse cx="260" cy="260" rx="130" ry="60"/><ellipse cx="420" cy="290" rx="120" ry="50"/><ellipse cx="600" cy="270" rx="120" ry="55"/></g>
  <path d="M300 300 l-30 70 h30 l-24 70 l60 -90 h-30 l30 -50z" fill="#ffd84d"/>
</g>'''

def bubble(text, side):
    # side: 'right' bubble sits to the right of the speaker's head
    if side=='right':
        return f'''<g class="bub"><path d="M150 -10 h330 a16 16 0 0 1 16 16 v50 a16 16 0 0 1 -16 16 h-260 l-40 26 l6 -26 h-36 a16 16 0 0 1 -16 -16 v-50 a16 16 0 0 1 16 -16z" fill="#fff" stroke="#333" stroke-width="3"/>
        <text x="323" y="41" font-size="30" text-anchor="middle" font-family="'LM Sans', Arial, sans-serif">{text}</text></g>'''
    return f'''<g class="bub"><path d="M-260 -10 h330 a16 16 0 0 1 16 16 v50 a16 16 0 0 1 -16 16 h-36 l6 26 l-40 -26 h-260 a16 16 0 0 1 -16 -16 v-50 a16 16 0 0 1 16 -16z" fill="#fff" stroke="#333" stroke-width="3"/>
        <text x="-95" y="41" font-size="30" text-anchor="middle" font-family="'LM Sans', Arial, sans-serif">{text}</text></g>'''

def panel_svg(kind, steps):
    s_w,s_h,s_t = steps
    side='L' if kind=='treated' else 'R'
    if kind=='treated':
        wife_x, hus_x = 350, 110      # panel x of char box (240 wide) ; feet at y=1000
        bub = bubble("I work in the oil sector!", 'right'); bub_at=(hus_x-60, 400)
        hus_kind='oil'
    else:
        wife_x, hus_x = 200, 440
        bub = bubble("I work in another sector.", 'left'); bub_at=(hus_x+110, 400)
        hus_kind='ctrl'
    scale=1.05; y0=1000-480*scale
    return f'''<svg class="vpanel" viewBox="0 0 768 1024" xmlns="http://www.w3.org/2000/svg">
  <g class="layer scene" data-in="{s_t}">{backdrop(kind)}{STORM if kind=='treated' else ''}</g>
  <g class="layer tags" data-in="{s_t}">{tags(kind)}</g>
  <g class="actor from{side}" data-in="{s_w}"><g transform="translate({wife_x} {y0}) scale({scale})">{character('wife')}</g></g>
  <g class="actor from{side} husband" data-in="{s_h}"><g transform="translate({hus_x} {y0}) scale({scale})">{character(hus_kind)}</g>
     <g transform="translate({bub_at[0]} {bub_at[1]})">{bub}</g></g>
</svg>'''

CSS='''
.vpanel{position:absolute;top:0;width:50%;height:100%;overflow:visible}
.vpanel.treated{left:0} .vpanel.control{left:50%}
.layer{opacity:0;transition:opacity .6s} .layer.on{opacity:1}
.storm-g{opacity:0;transition:opacity 1s} .slide[data-step="9"] .storm-g{opacity:1}
.slide[data-step="9"] .vpanel.treated .husband .char{filter:grayscale(1) brightness(.85)}
.char{transition:filter 1s}
.actor{opacity:0} .actor.on{opacity:1}
.actor.fromL.on{animation:walkL 2.2s cubic-bezier(.35,.4,.45,1) forwards}
.actor.fromR.on{animation:walkR 2.2s cubic-bezier(.35,.4,.45,1) forwards}
@keyframes walkL{from{transform:translateX(-700px)}to{transform:translateX(0)}}
@keyframes walkR{from{transform:translateX(700px)}to{transform:translateX(0)}}
.leg,.arm{transform-box:fill-box;transform-origin:50% 8%}
.actor.on .legF{animation:swingA .5s ease-in-out 4} .actor.on .legB{animation:swingB .5s ease-in-out 4}
.actor.on .armF{animation:swingB .5s ease-in-out 4} .actor.on .armB{animation:swingA .5s ease-in-out 4}
@keyframes swingA{0%{transform:rotate(0)}25%{transform:rotate(-28deg)}75%{transform:rotate(28deg)}100%{transform:rotate(0)}}
@keyframes swingB{0%{transform:rotate(0)}25%{transform:rotate(28deg)}75%{transform:rotate(-28deg)}100%{transform:rotate(0)}}
.actor.on .bodybob{animation:vbob .25s ease-in-out 8}
@keyframes vbob{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
.bub{opacity:0;transform:scale(.6);transform-box:fill-box;transform-origin:20% 100%;transition:opacity .3s,transform .3s}
.actor.on .bub{opacity:1;transform:scale(1);transition-delay:2.3s}
.slide[data-step="9"] .bub{opacity:0}
.smoke{animation:drift 6s ease-in-out infinite alternate} @keyframes drift{to{transform:translate(10px,-8px)}}
'''
