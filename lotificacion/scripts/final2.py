import json,math,re
from engine3 import *
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
A,B=load_context();P={'A':A,'B':B}
CFG=json.load(open('n.json'))
OPTS=[('op1','extend','Opción 1 · Espina recta, lotes hasta el lindero','Sin remanentes. Lotes de 600 m² al poniente y bodegas mayores al oriente.'),
      ('op2','park','Opción 2 · Espina recta, todo lote de 600 m²','Todos los lotes de 600 m². El sobrante queda como parque lineal hacia el colector.'),
      ('op3','module','Opción 3 · Espina recta, módulos de 600 y 1,200 m²','Lotes de 1 o 2 módulos. El sobrante queda como parque lineal.')]
ctx=[re.search(r'Data="([^"]*)"',a).group(1) for n_,a in re.findall(r'<Path Name="(\S+)" ([^>]*)/?>',src) if 'Fill=' not in a]
def pth(p): return ''.join('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in r.coords)+'Z' for r in [p.exterior]+list(p.interiors))
M={}
for key,mode,title,sub in OPTS:
    res={k:layout3(P[k],FR[k],mode=mode,**CFG[k]) for k in 'AB'}
    per={}
    for k,r in res.items():
        o=FR[k]
        r['lots'].sort(key=lambda L:(l(o,(L['g'].centroid.x,L['g'].centroid.y))[0]))
        for i,L in enumerate(r['lots']): L['id']=f'{k}-{i+1:02d}'
        ls=r['lots']
        per[k]=dict(n=len(ls),std=sum(is_std(L['g']) for L in ls),near=sum(abs(L['g'].area-600)<=30 for L in ls),
            big=sum(L['g'].area>900 for L in ls),lot=sum(L['g'].area for L in ls),garden=sum(L['garden'].area for L in ls),
            net=sum(L['net'] for L in ls),park=sum(q.area for q in r['park']),road=r['road'].area,
            rl=LineString(r['axis']).length,gross=P[k].area,
            minA=min(L['g'].area for L in ls),maxA=max(L['g'].area for L in ls))
    tot={kk:per['A'][kk]+per['B'][kk] for kk in per['A'] if kk not in('minA','maxA')}
    tot['minA']=min(per['A']['minA'],per['B']['minA']);tot['maxA']=max(per['A']['maxA'],per['B']['maxA'])
    M[key]=dict(title=title,sub=sub,per=per,tot=tot)
    # ---- SVG
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="262 -440 420 440" role="img" aria-label="{title}"><g transform="scale(1,-1)">']
    s.append(f'<g transform="matrix({1/SX},0,0,{-1/SY},{-X0/SX},{Y0/SY})" fill="none" stroke="var(--ctx)" stroke-width="5">'+''.join(f'<path d="{d}"/>' for d in ctx)+'</g>')
    for k,r in res.items():
        s.append(f'<path d="{pth(P[k])}" class="parcel"/>')
        for q in r['park']: s.append(f'<path d="{pth(q)}" class="park"/>')
        for q in polys(r['road']): s.append(f'<path d="{pth(q)}" class="walk"/>')
        for q in polys(r['pav']): s.append(f'<path d="{pth(q)}" class="pav"/>')
        s.append('<path class="cl" d="M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in r['axis'])+'"/>')
        for L in r['lots']:
            q=L['g'];cls='std' if is_std(q) else ('big' if q.area>900 else 'irr')
            s.append(f'<path d="{pth(q)}" class="lot {cls}"><title>{L["id"]} · {q.area:.1f} m² · jardín {L["garden"].area:.1f} m²</title></path>')
            for gq in polys(L['garden']): s.append(f'<path d="{pth(gq)}" class="gdn"/>')
            c=q.representative_point()
            s.append(f'<text x="{c.x:.1f}" y="{-c.y+0.6:.1f}" transform="scale(1,-1)" class="lt">{L["id"][2:]}</text><text x="{c.x:.1f}" y="{-c.y+3.6:.1f}" transform="scale(1,-1)" class="la">{q.area:.0f}</text>')
        ax,ay=r['acc'];s.append(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="5.5" class="acc"/>')
    s.append('<text x="268" y="-150" transform="scale(1,-1)" class="pl">MACROLOTE A</text><text x="420" y="-330" transform="scale(1,-1)" class="pl">MACROLOTE B</text>')
    s.append('<text x="300" y="-14" transform="scale(1,-1)" class="pl av">AVENIDA PRINCIPAL</text>')
    s.append('</g></svg>'); open(f'v2_{key}.svg','w').write('\n'.join(s))
    # ---- DXF in UTM
    doc=ezdxf.new('R2010',setup=True);msp=doc.modelspace()
    for nm,col in [('POLIGONO',5),('VIAL-DERECHO-VIA',9),('VIAL-ARROYO',8),('VIAL-EJE',1),('LOTES',2),('LOTES-GRANDES',6),('JARDIN-DONACION-10',3),('PARQUE-LINEAL',94),('ACCESO',1),('TEXTO',7)]:
        doc.layers.add(nm,color=col)
    T=lambda pts:[(x+UTM0[0],y+UTM0[1]) for x,y in pts]
    def lw(gm,layer):
        for q in polys(gm):
            msp.add_lwpolyline(T(q.exterior.coords),close=True,dxfattribs={'layer':layer})
            for ri in q.interiors: msp.add_lwpolyline(T(ri.coords),close=True,dxfattribs={'layer':layer})
    def tx(txt,p,h,layer='TEXTO',rot=0):
        x,y=T([p])[0]; msp.add_text(txt,height=h,rotation=rot,dxfattribs={'layer':layer}).set_placement((x,y),align=TA.MIDDLE_CENTER)
    for k,r in res.items():
        lw(P[k],'POLIGONO'); lw(r['road'],'VIAL-DERECHO-VIA'); lw(r['pav'],'VIAL-ARROYO')
        msp.add_lwpolyline(T(r['axis']),dxfattribs={'layer':'VIAL-EJE','linetype':'CENTER'})
        for q in r['park']: lw(q,'PARQUE-LINEAL')
        for L in r['lots']:
            lw(L['g'],'LOTES' if L['g'].area<=900 else 'LOTES-GRANDES'); lw(L['garden'],'JARDIN-DONACION-10')
            c=L['g'].representative_point()
            tx(L['id'],(c.x,c.y+1.5),2.2); tx(f"{L['g'].area:.2f} m2",(c.x,c.y-1.2),1.5); tx(f"Jardin {L['garden'].area:.2f}",(c.x,c.y-3.4),1.2)
        a0,a1=r['axis'][0],r['axis'][1]
        tx(f'ACCESO {k} - DESDE AV. PRINCIPAL',(a0[0]-14,a0[1]-6),2.5,'ACCESO')
        tx('RADIOS DE GIRO R=15.00',(a0[0]-14,a0[1]-9.5),1.8,'ACCESO')
        tx('RETORNO ARROYO R=15.00 / DV R=16.50',(r['rc'][0],r['rc'][1]),1.6,'ACCESO')
        tx('VIALIDAD 11.00 m: BANQ 1.50 + ARROYO 8.00 + BANQ 1.50',((r['axis'][-2][0]+r['axis'][-1][0])/2,(r['axis'][-2][1]+r['axis'][-1][1])/2),1.3,'TEXTO',69.25)
    doc.saveas(f'bodegas_{key}.dxf')
    with open(f'tabla_lotes_{key}.csv','w') as f:
        f.write('lote,area_bruta_m2,jardin_donacion_m2,area_util_m2,frente_a_vialidad\n')
        for k,r in res.items():
            for L in r['lots']: f.write(f"{L['id']},{L['g'].area:.2f},{L['garden'].area:.2f},{L['net']:.2f},si\n")
    if key=='op1':
        ax=res['A']['acc']; print('A acc to collector junction', round(math.dist(ax,(332.6,59.8)),1))
        bx=res['B']['acc']; print('B acc to collector', round(Point(bx).distance(LineString([(332.6,59.8),(497.1,197.6),(551.7,243.7)])),1))
json.dump(M,open('metrics2.json','w'),indent=1,default=float)
for k,m in M.items(): print(k,{a:round(b) for a,b in m['tot'].items()})
