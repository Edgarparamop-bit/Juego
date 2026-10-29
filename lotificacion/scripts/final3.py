import json,re
from engine5 import *
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
A,B=load_context();PP={'A':A,'B':B}
C=25.5
ENT={'A':[(2.4,12),(16,12),(48,C)],'B':[(-2,C)]}
OPTS=[('d1','perimetral','Opción 1 · Franja perimetral continua','Una franja de ancho uniforme sobre todos los linderos con calle pública: avenida, colector y calles norte y sur.'),
      ('d2','colector','Opción 2 · Franja sobre el lado largo','Toda la donación va sobre el colector diagonal, que es el lindero público más largo.'),
      ('d3','calles','Opción 3 · Franjas sobre calles transversales','La donación va sobre las calles cortas de cada macrolote: avenida o calle sur y calle norte.')]
ctx=[re.search(r'Data="([^"]*)"',a).group(1) for n_,a in re.findall(r'<Path Name="(\S+)" ([^>]*)/?>',src) if 'Fill=' not in a]
def pth(p): return ''.join('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in r.coords)+'Z' for r in [p.exterior]+list(p.interiors))
M={}
for key,mode,title,sub in OPTS:
    res={k:layout5(PP[k],FR[k],C,ENT[k],mode) for k in 'AB'}
    per={}
    for k,r in res.items():
        r['lots'].sort(key=lambda L:(L['g'].centroid.x, 0 if L['side']=='W' else 1))
        r['lots'].sort(key=lambda L:L['g'].centroid.x)
        for i,L in enumerate(r['lots']): L['id']=f'{k}-{i+1:02d}'
        ls=r['lots'];PL=r['PL']
        per[k]=dict(n=len(ls),lot=sum(L['g'].area for L in ls),bod=sum(L['rect'].area for L in ls),green=r['green'].area,road=r['road'].area,
                    gross=PL.area,w=r['w'],rl=LineString(r['axis']).length,n600=sum(L['g'].area<=700 for L in ls),
                    minA=min(L['g'].area for L in ls),maxA=max(L['g'].area for L in ls))
    tot={kk:per['A'][kk]+per['B'][kk] for kk in ('n','lot','bod','green','road','gross','rl','n600')}
    tot['minA']=min(per[k]['minA'] for k in 'AB');tot['maxA']=max(per[k]['maxA'] for k in 'AB')
    M[key]=dict(title=title,sub=sub,per=per,tot=tot)
    # ---- SVG for the page
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="262 -440 420 440" role="img" aria-label="{title}"><g transform="scale(1,-1)">']
    s.append(f'<g transform="matrix({1/SX},0,0,{-1/SY},{-X0/SX},{Y0/SY})" fill="none" stroke="var(--ctx)" stroke-width="5">'+''.join(f'<path d="{d}"/>' for d in ctx)+'</g>')
    for k,r in res.items():
        G=lambda q,o=FR[k]:toglobal(q,o)
        s.append(f'<path d="{pth(PP[k])}" class="parcel"/>')
        for q in polys(r['green']): s.append(f'<path d="{pth(G(q))}" class="park"/>')
        for q in polys(r['road']): s.append(f'<path d="{pth(G(q))}" class="walk"/>')
        for q in polys(r['pav']): s.append(f'<path d="{pth(G(q))}" class="pav"/>')
        s.append('<path class="cl" d="M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in [g(FR[k],p) for p in r['axis']])+'"/>')
        for L in r['lots']:
            q=G(L['g'])
            s.append(f'<path d="{pth(q)}" class="lot std"><title>{L["id"]} · lote {L["g"].area:.1f} m² · frente {L["front"]:.1f} m · bodega {L["rect"].area:.0f} m²</title></path>')
            s.append(f'<path d="{pth(G(L["rect"]))}" class="bod"/>')
            c=q.representative_point()
            s.append(f'<text x="{c.x:.1f}" y="{-c.y+0.6:.1f}" transform="scale(1,-1)" class="lt">{L["id"][2:]}</text><text x="{c.x:.1f}" y="{-c.y+3.6:.1f}" transform="scale(1,-1)" class="la">{L["g"].area:.0f}</text>')
        ax,ay=g(FR[k],r['axis'][0]);s.append(f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="5.5" class="acc"/>')
    s.append('<text x="268" y="-150" transform="scale(1,-1)" class="pl">MACROLOTE A</text><text x="420" y="-330" transform="scale(1,-1)" class="pl">MACROLOTE B</text>')
    s.append('<text x="300" y="-14" transform="scale(1,-1)" class="pl av">AVENIDA PRINCIPAL</text>')
    s.append('</g></svg>');open(f'v3_{key}.svg','w').write('\n'.join(s))
    # ---- DXF (UTM)
    doc=ezdxf.new('R2010',setup=True);msp=doc.modelspace()
    for nm,col in [('POLIGONO',5),('VIAL-DERECHO-VIA',9),('VIAL-ARROYO',8),('VIAL-EJE',1),('LOTES',2),('BODEGA-HUELLA',30),('DONACION-AREA-VERDE',3),('ACCESO',1),('TEXTO',7)]:
        doc.layers.add(nm,color=col)
    T=lambda pts:[(x+UTM0[0],y+UTM0[1]) for x,y in pts]
    def lw(gm,layer,o):
        for q in polys(gm):
            q=toglobal(q,o)
            msp.add_lwpolyline(T(q.exterior.coords),close=True,dxfattribs={'layer':layer})
            for ri in q.interiors: msp.add_lwpolyline(T(ri.coords),close=True,dxfattribs={'layer':layer})
    def tx(txt,p,h,layer='TEXTO',rot=0):
        x,y=T([p])[0]; msp.add_text(txt,height=h,rotation=rot,dxfattribs={'layer':layer}).set_placement((x,y),align=TA.MIDDLE_CENTER)
    for k,r in res.items():
        o=FR[k]
        msp.add_lwpolyline(T(PP[k].exterior.coords),close=True,dxfattribs={'layer':'POLIGONO'})
        lw(r['road'],'VIAL-DERECHO-VIA',o); lw(r['pav'],'VIAL-ARROYO',o); lw(r['green'],'DONACION-AREA-VERDE',o)
        msp.add_lwpolyline(T([g(o,p) for p in r['axis']]),dxfattribs={'layer':'VIAL-EJE','linetype':'CENTER'})
        for L in r['lots']:
            lw(L['g'],'LOTES',o); lw(L['rect'],'BODEGA-HUELLA',o)
            c=toglobal(L['g'].representative_point(),o)
            tx(L['id'],(c.x,c.y+1.6),2.2); tx(f"{L['g'].area:.2f} m2",(c.x,c.y-1.0),1.5); tx(f"Frente {L['front']:.2f} m",(c.x,c.y-3.0),1.2)
        gp=max(polys(r['green']),key=lambda z:z.area).representative_point(); gp=toglobal(gp,o)
        tx(f"DONACION AREA VERDE {r['green'].area:.2f} m2 (10%)",(gp.x,gp.y),1.6,'DONACION-AREA-VERDE')
        a0=g(o,r['axis'][0]); tx(f'ACCESO MACROLOTE {k}',(a0[0]-16,a0[1]-5),2.4,'ACCESO'); tx('RADIOS DE GIRO R=15.00',(a0[0]-16,a0[1]-8.5),1.7,'ACCESO')
        rc=g(o,r['rc']); tx('RETORNO ARROYO R=15.00',(rc[0],rc[1]),1.6,'ACCESO')
        m1=g(o,((r['axis'][-1][0]+r['axis'][-2][0])/2,C)); tx('VIALIDAD 11.00: BANQ 1.50 + ARROYO 8.00 + BANQ 1.50',m1,1.3,'TEXTO',69.25)
    doc.saveas(f'bodegas_{key}.dxf')
    with open(f'tabla_lotes_{key}.csv','w') as f:
        f.write('lote,area_lote_m2,frente_m,huella_bodega_ortogonal_m2\n')
        for k,r in res.items():
            for L in r['lots']: f.write(f"{L['id']},{L['g'].area:.2f},{L['front']:.2f},{L['rect'].area:.2f}\n")
json.dump(M,open('metrics3.json','w'),indent=1,default=float)
for k,m in M.items(): print(k,{a:round(b,1) for a,b in m['tot'].items()},'w',round(m['per']['A']['w'],2),round(m['per']['B']['w'],2))
