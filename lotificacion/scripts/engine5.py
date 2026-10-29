import math
from shapely.geometry import Polygon,LineString,Point,box,MultiLineString
from shapely.ops import unary_union,split
from engine import load_context,g,l,FR,UTM0,SX,SY,X0,Y0,src
HALF=5.5;PAV=4.0;R_RET=16.5;R_CURB=15.0;FW=30.0
def polys(gm): return [q for q in getattr(gm,'geoms',[gm]) if q.geom_type=='Polygon' and q.area>0.05]
def clean(gm,e=0.01): return gm.buffer(e).buffer(-2*e).buffer(e)
def tolocal(P,o): return Polygon([l(o,p) for p in P.exterior.coords])
def toglobal(q,o):
    if q.geom_type=='Polygon': return Polygon([g(o,p) for p in q.exterior.coords],[[g(o,p) for p in r.coords] for r in q.interiors])
    if q.geom_type=='Point': return Point(g(o,(q.x,q.y)))
    return LineString([g(o,p) for p in q.coords])
def edges(PL):
    cs=list(PL.exterior.coords);out={'W':[],'S':[],'N':[],'C':[]}
    um=sum(p[0] for p in cs)/len(cs)
    for a,b in zip(cs[:-1],cs[1:]):
        du,dv=b[0]-a[0],b[1]-a[1]
        if abs(a[1])<0.6 and abs(b[1])<0.6: out['W'].append((a,b));continue
        if abs(dv)>3*abs(du): out['S' if (a[0]+b[0])/2<um else 'N'].append((a,b))
        else: out['C'].append((a,b))
    return {k:MultiLineString(v) for k,v in out.items() if v}
def road_geom(PL,pts,ur,vc):
    line=LineString(pts)
    road=line.buffer(HALF,cap_style=2,join_style=2).union(Point(ur,vc).buffer(R_RET,96))
    pav=line.buffer(PAV,cap_style=2,join_style=2).union(Point(ur,vc).buffer(R_RET-1.5,96))
    a,b=pts[0],pts[1];L=math.dist(a,b);t=((b[0]-a[0])/L,(b[1]-a[1])/L)
    for side in (1,-1):
        n=(-t[1]*side,t[0]*side)
        el=LineString([(a[0]+n[0]*HALF,a[1]+n[1]*HALF),(b[0]+n[0]*HALF,b[1]+n[1]*HALF)])
        cp=el.intersection(PL.boundary)
        if cp.is_empty: continue
        cp=min(list(getattr(cp,'geoms',[cp])),key=lambda p:p.distance(Point(a)))
        for R,off,tg in ((R_CURB-1.5,0,0),(R_CURB,1.5,1)):
            cc=(cp.x-n[0]*off,cp.y-n[1]*off)
            P_=lambda s,w:(cc[0]+t[0]*s+n[0]*w,cc[1]+t[1]*s+n[1]*w)
            f=Polygon([P_(-3,0),P_(R,0),P_(R,R),P_(-3,R)]).difference(Point(P_(R,R)).buffer(R,64))
            if tg==0: road=road.union(f)
            else: pav=pav.union(f)
    road=clean(road.intersection(PL)); pav=clean(pav.intersection(PL)).intersection(road)
    return road,pav
def layout5(parcel,o,c,entry,green_mode,target=0.10,nret_margin=24):
    PL=tolocal(parcel,o)
    vc=c+(R_RET-HALF)
    E=edges(PL)
    # retorno: leave ~one lot depth (nret_margin) to the north boundary
    ur=0
    for uu in [x*0.5 for x in range(600)]:
        if PL.contains(Point(uu,vc).buffer(R_RET+1)) and PL.contains(Point(uu+R_RET+nret_margin,vc)): ur=uu
    pts=entry+[(ur,c)]
    road,pav=road_geom(PL,pts,ur,vc)
    # ---- donation green: 10% of macrolote, along public-street edges
    if green_mode=='perimetral': src_e=unary_union([E[k] for k in ('S','C','N') if k in E])
    elif green_mode=='colector': src_e=E['C']
    elif green_mode=='calles': src_e=unary_union([E[k] for k in ('S','N') if k in E])
    tgt=target*PL.area
    def gr(w): return clean(PL.intersection(src_e.buffer(w,cap_style=2,join_style=2)).difference(road))
    lo,hi=0,150
    for _ in range(40):
        m=(lo+hi)/2
        if gr(m).area<tgt: lo=m
        else: hi=m
    w=(lo+hi)/2; green=gr(w)
    avail=clean(PL.difference(road).difference(green))
    # ---- lot cells: cuts orthogonal to the spine every 30 m, anchored at the start of the bulb
    westpoly=Polygon([(pts[0][0]-80,pts[0][1])]+pts[1:]+[(ur,vc),(ur+300,vc),(ur+300,-300),(pts[0][0]-80,-300)])
    u_anchor=ur
    cuts=[u_anchor+FW*k for k in range(-12,3)]
    lots=[]
    for side in ('W','E'):
        reg=avail.intersection(westpoly) if side=='W' else avail.difference(westpoly)
        cells=[]
        bnd=[-1e3]+[x for x in cuts]+[1e3]
        for u0,u1 in zip(bnd[:-1],bnd[1:]):
            for q in polys(clean(reg.intersection(box(u0,-500,u1,500)))):
                cells.append(q)
        lots+=[dict(g=q,side=side) for q in cells]
    # merge cells without frontage or too small/narrow into the neighbour with longest shared edge
    def frontage(q): return q.boundary.intersection(road.buffer(0.2)).length
    changed=True
    while changed:
        changed=False
        for i,L_ in enumerate(lots):
            q=L_['g']
            if frontage(q)>=15 and q.area>=450: continue
            bj=None;bl=0
            for j,M in enumerate(lots):
                if j==i: continue
                sh=q.boundary.intersection(M['g'].buffer(0.1)).length
                if sh>bl: bl,bj=sh,j
            if bj is None or bl<1:
                green=unary_union([green,q]); lots.pop(i); changed=True; break
            u=clean(unary_union([lots[bj]['g'],q.buffer(0.03)]),0.02)
            if u.geom_type=='Polygon': lots[bj]['g']=u; lots.pop(i); changed=True; break
            green=unary_union([green,q]); lots.pop(i); changed=True; break
    # orthogonal warehouse footprint: largest axis-aligned rectangle inside the lot
    for L_ in lots:
        q=L_['g'];best=box(0,0,0,0)
        us=[p[0] for p in q.exterior.coords];vs=[p[1] for p in q.exterior.coords]
        u0,u1,v0,v1=min(us),max(us),min(vs),max(vs)
        N=9
        for ia in range(N):
            a=u0+(u1-u0)*ia/N
            for ib in range(ia+1,N+1):
                b=u0+(u1-u0)*ib/N
                for iv in range(N+1):
                    vt=v1-(v1-v0)*iv/N if L_['side']=='W' else v0+(v1-v0)*iv/N
                    lo_,hi_=0,v1-v0
                    mk=lambda m:box(a,vt-m,b,vt) if L_['side']=='W' else box(a,vt,b,vt+m)
                    if (b-a)*(v1-v0)<=best.area: continue
                    for _ in range(18):
                        m=(lo_+hi_)/2
                        if mk(m).difference(q).area<0.2: lo_=m
                        else: hi_=m
                    r=mk(lo_)
                    if r.area>best.area: best=r
        L_['rect']=best
        L_['front']=q.boundary.intersection(road.buffer(0.2)).length
    return dict(PL=PL,road=road,pav=pav,lots=lots,green=clean(green),axis=pts,rc=(ur,vc),w=w,edges=E)
