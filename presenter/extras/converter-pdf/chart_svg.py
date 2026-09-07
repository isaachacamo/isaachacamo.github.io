import pymupdf
P='/root/.claude/uploads/034f2805-7ddf-597f-b993-5185d8c61144/8f19e444-Entrepreneurs_as_households.pdf'
pg=pymupdf.open(P)[8]
X0,Y0,X1,Y1 = 80,44,372,212   # chart region in page pt

def col(c):
    if c is None: return 'none'
    return '#%02x%02x%02x'%tuple(int(round(v*255)) for v in c)

def series_key(d):
    c=d.get('color'); w=round(d.get('width') or 0,2)
    if c is None: return None
    r0=d['rect']
    if r0.x0>222 and r0.y1<80: return None   # legend samples stay static
    r,g,b=[round(v,2) for v in c]
    if (r,g,b)==(0,0,0) and w==0.77: return 'canada'
    if (r,g,b)==(0.13,0.13,0.13) and w==0.77: return 'oil'
    if (r,g,b)==(1,0,0) and w==0.77: return 'wti'
    return None

def path_d(d):
    out=[]
    for it in d['items']:
        if it[0]=='l':
            a,b=it[1],it[2]; out.append(f'M{a.x:.2f} {a.y:.2f}L{b.x:.2f} {b.y:.2f}')
        elif it[0]=='re':
            r=it[1]; out.append(f'M{r.x0:.2f} {r.y0:.2f}H{r.x1:.2f}V{r.y1:.2f}H{r.x0:.2f}Z')
        elif it[0]=='c':
            p=it[1:5]; out.append(f'M{p[0].x:.2f} {p[0].y:.2f}C{p[1].x:.2f} {p[1].y:.2f} {p[2].x:.2f} {p[2].y:.2f} {p[3].x:.2f} {p[3].y:.2f}')
    return ''.join(out)

static=[]; series={'canada':[], 'oil':[], 'wti':[]}
for d in pg.get_drawings():
    r=d['rect']
    if r.x1<X0 or r.x0>X1 or r.y1<Y0 or r.y0>Y1: continue
    k=series_key(d)
    stroke=col(d.get('color')); fill=col(d.get('fill'))
    w=d.get('width') or 0
    el=f'<path d="{path_d(d)}" stroke="{stroke}" stroke-width="{w:.2f}" fill="{fill}" stroke-linecap="{["butt","round","square"][d.get("lineCap",(0,))[0] if isinstance(d.get("lineCap"),tuple) else 0]}"/>'
    (series[k] if k else static).append(el)

texts=[]
for b in pg.get_text('dict')['blocks']:
    for l in b.get('lines',[]):
        for s in l['spans']:
            x,y0,x1,y1=s['bbox']
            if x<X0 or x>X1 or y0<Y0 or y1>Y1 or not s['text'].strip(): continue
            size=s['size']; t=s['text']
            if l['dir'][1]!=0:   # rotated 90°
                # origin approx: bottom-left of bbox for vertical text going up
                texts.append(f'<text transform="translate({x1-size*0.22:.2f} {y1:.2f}) rotate(-90)" font-size="{size:.2f}">{t}</text>')
            else:
                texts.append(f'<text x="{x:.2f}" y="{y1-size*0.21:.2f}" font-size="{size:.2f}">{t}</text>')

W=X1-X0; H=Y1-Y0
svg=f'''<svg class="chart" viewBox="{X0} {Y0} {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Arial, Helvetica, sans-serif" fill="#000">
<defs>
 <clipPath id="cw"><rect class="wipe" x="{X0}" y="{Y0}" width="0" height="{H}"/></clipPath>
 <clipPath id="cu"><rect class="wipe" x="{X0}" y="{Y0}" width="0" height="{H}"/></clipPath>
</defs>
<g class="static">{''.join(static)}</g>
<g class="labels">{''.join(texts)}</g>
<g class="ser wti" clip-path="url(#cw)">{''.join(series['wti'])}</g>
<g class="ser unemp" clip-path="url(#cu)">{''.join(series['canada'])}{''.join(series['oil'])}</g>
</svg>'''
open('chart.svg','w').write(svg)
print(len(static),len(series['wti']),len(series['canada']),len(series['oil']),len(texts),len(svg))
