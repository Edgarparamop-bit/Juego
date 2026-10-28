import json,math,re
from engine import *
import ezdxf
from shapely.geometry import LineString,Point
A,B=load_context(); P={'A':A,'B':B}
TYPES=[('t1','Tipo 1 · Espina + peine con retornos','Lote 20 × 30 m'),
       ('t2','Tipo 2 · Espina desplazada, lote profundo','Lote 15 × 40 m'),
       ('t3','Tipo 3 · Circuito cerrado sin retornos','Lote 20 × 30 m')]
ctx=[]
for name,attrs in re.findall(r'<Path Name="(\S+)" ([^>]*)/?>',src):
    if 'Fill=' in attrs: continue
    ctx.append(re.search(r'Data="([^"]*)"',attrs).group(1))
def pth(p):
    rings=[p.exterior]+list(p.interiors)
    return ''.join('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in r.coords)+'Z' for r in rings)
def polys(gm): return [q for q in getattr(gm,'geoms',[gm]) if q.geom_type=='Polygon']
results={}
for key,title,mod in TYPES:
    alt=json.load(open(key+'.json')); AT=alt['A_T']
    out={'lots':[],'roads':[],'pav':[],'green':[],'cl':[]}
    met={'title':title,'mod':mod}
    tot=dict(n=0,std=0,lot=0,road=0,green=0,rl=0,ret=0,near=0,gross=0)
    per={}
    for k in 'AB':
        o=FR[k];cfg=alt[k]
        lines=[({'p':[g(o,p) for p in ln['p']],'skip':ln.get('skip',[])} if isinstance(ln,dict) else [g(o,p) for p in ln]) for ln in cfg['lines']]
        rts=[g(o,p) for p in cfg.get('ret',[])]
        road,lots,gr=layout(P[k],lines,rts,AT,alt['D'])
        pl=[ln['p'] if isinstance(ln,dict) else ln for ln in lines]
        pav=unary_union([LineString(p).buffer(4.0,cap_style=2,join_style=2,mitre_limit=3) for p in pl]+[Point(r).buffer(10.5,32) for r in rts]).intersection(P[k])
        lots.sort(key=lambda q:(round(l(o,(q.centroid.x,q.centroid.y))[0]/4),l(o,(q.centroid.x,q.centroid.y))[1]))
        # number along W row first then rest by u
        lots.sort(key=lambda q:l(o,(q.centroid.x,q.centroid.y))[0])
        rl=sum(LineString(p).length for p in pl)
        std=sum(is_std(q,AT) for q in lots); near=sum(abs(q.area-AT)<=0.05*AT for q in lots)
        per[k]=dict(n=len(lots),std=std,near=near,lot=sum(q.area for q in lots),road=road.area,green=sum(q.area for q in gr),rl=rl,ret=len(rts),gross=P[k].area)
        for kk in tot: tot[kk]+=per[k][kk]
        for i,q in enumerate(lots):
            out['lots'].append(dict(id=f'{k}-{i+1:02d}',g=q,a=q.area,std=is_std(q,AT)))
        out['roads']+=polys(road); out['pav']+=polys(pav); out['green']+=gr; out['cl']+=pl
    met['per']=per; met['tot']=tot
    results[key]=(met,out)
    # ---------- SVG ----------
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="262 -440 420 420" role="img" aria-label="{title}"><g transform="scale(1,-1)">']
    s.append(f'<g transform="matrix({1/SX},0,0,{-1/SY},{-X0/SX},{Y0/SY})" fill="none" stroke="var(--ctx)" stroke-width="5">'+''.join(f'<path d="{d}"/>' for d in ctx)+'</g>')
    for k in 'AB': s.append(f'<path d="{pth(P[k])}" class="parcel"/>')
    for q in out['green']: s.append(f'<path d="{pth(q)}" class="green"/>')
    for q in out['roads']: s.append(f'<path d="{pth(q)}" class="walk"/>')
    for q in out['pav']: s.append(f'<path d="{pth(q)}" class="pav"/>')
    for p in out['cl']: s.append('<path class="cl" d="M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in p)+'"/>')
    for L in out['lots']:
        q=L['g']; c=q.representative_point()
        s.append(f'<path d="{pth(q)}" class="lot {"std" if L["std"] else "irr"}"><title>{L["id"]} · {L["a"]:.1f} m²</title></path>')
        s.append(f'<text x="{c.x:.1f}" y="{-c.y+0.6:.1f}" transform="scale(1,-1)" class="lt">{L["id"][2:]}</text><text x="{c.x:.1f}" y="{-c.y+3.6:.1f}" transform="scale(1,-1)" class="la">{L["a"]:.0f}</text>')
    for k in 'AB':
        ax,ay=g(FR[k],ACC[k]); s.append(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="5.4" class="acc"/>')
        cx,cy=P[k].centroid.x,P[k].centroid.y
    s.append('<text x="268" y="-150" transform="scale(1,-1)" class="pl">POLÍGONO A</text><text x="430" y="-330" transform="scale(1,-1)" class="pl">POLÍGONO B</text>')
    s.append('</g></svg>')
    open(f'out_{key}.svg','w').write('\n'.join(s))
    # ---------- DXF (UTM) ----------
    doc=ezdxf.new('R2010',setup=True); msp=doc.modelspace()
    for nm,col in [('LOT-LOTES',2),('LOT-LOTES-IRREG',30),('VIAL-ARROYO',8),('VIAL-BANQUETA',9),('VIAL-EJE',1),('AREA-VERDE',3),('LOT-TEXTO',7),('POLIGONO',5)]:
        doc.layers.add(nm,color=col)
    doc.linetypes  # CENTER loaded by setup
    T=lambda pts:[(x+UTM0[0],y+UTM0[1]) for x,y in pts]
    def lw(geom,layer):
        for q in polys(geom):
            msp.add_lwpolyline(T(q.exterior.coords),close=True,dxfattribs={'layer':layer})
            for r in q.interiors: msp.add_lwpolyline(T(r.coords),close=True,dxfattribs={'layer':layer})
    for k in 'AB': lw(P[k],'POLIGONO')
    for q in out['roads']: lw(q,'VIAL-BANQUETA')
    for q in out['pav']: lw(q,'VIAL-ARROYO')
    for q in out['green']: lw(q,'AREA-VERDE')
    for p in out['cl']: msp.add_lwpolyline(T(p),dxfattribs={'layer':'VIAL-EJE','linetype':'CENTER'})
    for L in out['lots']:
        lw(L['g'],'LOT-LOTES' if L['std'] else 'LOT-LOTES-IRREG')
        c=L['g'].representative_point(); x,y=T([(c.x,c.y)])[0]
        msp.add_text(L['id'],height=2.2,dxfattribs={'layer':'LOT-TEXTO'}).set_placement((x,y+1),align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"{L['a']:.2f} m2",height=1.6,dxfattribs={'layer':'LOT-TEXTO'}).set_placement((x,y-2),align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    doc.saveas(f'lotificacion_{key}.dxf')
    # CSV
    with open(f'tabla_lotes_{key}.csv','w') as f:
        f.write('lote,area_m2,tipo\n')
        for L in out['lots']: f.write(f"{L['id']},{L['a']:.2f},{'estandar' if L['std'] else 'irregular'}\n")
json.dump({k:v[0] for k,v in results.items()},open('metrics.json','w'),indent=1,default=float)
for k,(m_,_) in results.items():
    t=m_['tot']; print(k,{a:round(b) for a,b in t.items()}, 'aprov%',round(100*t['lot']/t['gross'],1),'via%',round(100*t['road']/t['gross'],1))
    for kk,v in m_['per'].items(): print('   ',kk,{a:round(b) for a,b in v.items()})
