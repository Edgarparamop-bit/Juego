import math
from shapely.geometry import Polygon,LineString,Point
from shapely.ops import unary_union
from engine import load_context,g,l,FR,UTM0,SX,SY,X0,Y0,src
HALF=5.5; PAV=4.0; R_RET=16.5; R_CURB=15.0
def polys(gm): return [q for q in getattr(gm,'geoms',[gm]) if q.geom_type=='Polygon' and q.area>0.01]
def clean(gm,e=0.01): return gm.buffer(e).buffer(-2*e).buffer(e)
def unit(a,b):
    d=(b[0]-a[0],b[1]-a[1]);L=math.hypot(*d);return (d[0]/L,d[1]/L),L
def half(a,t,s0,s1,w0=-1e3,w1=1e3):
    n=(-t[1],t[0])
    P=lambda s,w:(a[0]+t[0]*s+n[0]*w,a[1]+t[1]*s+n[1]*w)
    return Polygon([P(s0,w0),P(s1,w0),P(s1,w1),P(s0,w1)])
def fillet(c,t_in,n_out,R,parcel):
    P=lambda s,w:(c[0]+t_in[0]*s+n_out[0]*w,c[1]+t_in[1]*s+n_out[1]*w)
    return Polygon([P(-3,0),P(R,0),P(R,R),P(-3,R)]).difference(Point(P(R,R)).buffer(R,64)).intersection(parcel)
def is_std(q,A_T=600):
    r=q.minimum_rotated_rectangle
    return q.area/r.area>0.985 and abs(q.area-A_T)<=0.02*A_T

def layout3(parcel,o,pts,ret,mode='extend',W=24,D=25,A_T=600,garden=0.10):
    P=[g(o,p) for p in pts]; rc=g(o,ret)
    t0,_=unit(P[1],P[0]); P[0]=(P[0][0]+t0[0]*4,P[0][1]+t0[1]*4)   # cross the boundary
    line=LineString(P)
    road=line.buffer(HALF,cap_style=2,join_style=2).union(Point(rc).buffer(R_RET,96))
    pav=line.buffer(PAV,cap_style=2,join_style=2).union(Point(rc).buffer(R_RET-1.5,96))
    t_in,_=unit(P[0],P[1]); fil=[];filp=[]
    for side in (1,-1):
        n=(-t_in[1]*side,t_in[0]*side)
        el=LineString([(P[0][0]+n[0]*HALF,P[0][1]+n[1]*HALF),(P[1][0]+n[0]*HALF,P[1][1]+n[1]*HALF)])
        cp=el.intersection(parcel.boundary); pts_=list(getattr(cp,'geoms',[cp]))
        if not pts_ or cp.is_empty: continue
        cp=min(pts_,key=lambda p:p.distance(Point(P[0])))
        fil.append(fillet((cp.x,cp.y),t_in,n,R_CURB-1.5,parcel))
        filp.append(fillet((cp.x-n[0]*1.5,cp.y-n[1]*1.5),t_in,n,R_CURB,parcel))
    road=clean(unary_union([road]+fil).intersection(parcel))
    pav=clean(unary_union([pav]+filp).intersection(parcel)).intersection(road)
    avail=clean(parcel.difference(road)); lots=[]
    segs=list(zip(P[:-1],P[1:]))
    order=[len(segs)-1]+list(range(len(segs)-1))     # main straight first
    for si in order:
        a,b=segs[si]; t,L=unit(a,b); main=(si==len(segs)-1)
        for side in (1,-1):
            n=(-t[1]*side,t[0]*side)
            sd='W' if l(o,(a[0]+n[0],a[1]+n[1]))[1]<l(o,a)[1] else 'E'
            DD=300
            if main and sd=='E' and mode=='park': DD=HALF+D
            if main and sd=='E' and mode=='module': DD=HALF+2*D
            s0=-HALF-25 if not main else -HALF-5
            s1=L+(R_RET+D+5 if main else HALF)
            strip=half(a,t,s0,s1,0,DD) if side==1 else half(a,t,s0,s1,-DD,0)
            strip=strip.intersection(avail)
            for comp in sorted(polys(strip),key=lambda c:-c.area):
                if comp.area<0.5*A_T or comp.boundary.intersection(road.buffer(0.2)).length<8: continue
                res=slice3(comp,a,t,A_T,W)
                for q in res: lots.append(dict(g=q,a=a,t=t,n=n,side=sd,main=main))
                avail=clean(avail.difference(unary_union(res)))
    park=[]
    if mode=='module':
        for L_ in lots:
            if not(L_['main'] and L_['side']=='E'): continue
            q=L_['g'];a,t,n=L_['a'],L_['t'],L_['n']
            pr=[(p[0]-a[0])*t[0]+(p[1]-a[1])*t[1] for p in q.exterior.coords];w=max(pr)-min(pr)
            sg=1 if (n==(-t[1],t[0])) else -1
            for d in (2*D,D):
                band=half(a,t,-1e3,1e3,0,HALF+d) if sg==1 else half(a,t,-1e3,1e3,-HALF-d,0)
                r=q.intersection(band)
                if r.area>=0.93*w*d:
                    if q.area>r.area+20: park+=polys(clean(q.difference(band))); L_['g']=max(polys(r),key=lambda z:z.area)
                    break
    for c in sorted(polys(avail),key=lambda x:x.area):
        if c.area<0.5: continue
        fr=c.boundary.intersection(road.buffer(0.2)).length
        if mode!='extend' and fr<6 and c.area>0.3*A_T: park.append(c); continue
        bi=None;bl=0
        for i,L_ in enumerate(lots):
            sh=c.boundary.intersection(L_['g'].buffer(0.1)).length
            if sh>bl: bl,bi=sh,i
        if fr>=12 and c.area>=0.8*A_T:
            a,b=segs[-1];t,_=unit(a,b);lots.append(dict(g=c,a=a,t=t,n=(-t[1],t[0]),side='X',main=False));continue
        if bi is not None and bl>1:
            u=clean(unary_union([lots[bi]['g'],c.buffer(0.03)]),0.02)
            if u.geom_type=='Polygon': lots[bi]['g']=u; continue
        park.append(c)
    # lots below 0.8*A_T: merge with neighbour (no unusable corners) or keep as access green
    changed=True
    while changed:
        changed=False
        for i,L_ in enumerate(lots):
            if L_['g'].area>=0.8*A_T: continue
            bj=None;bl=0
            for j,M in enumerate(lots):
                if j==i: continue
                sh=L_['g'].boundary.intersection(M['g'].buffer(0.1)).length
                if sh>bl: bl,bj=sh,j
            if bj is not None and bl>3:
                u=clean(unary_union([lots[bj]['g'],L_['g'].buffer(0.03)]),0.02)
                if u.geom_type=='Polygon': lots[bj]['g']=u; lots.pop(i); changed=True; break
            park.append(L_['g']); lots.pop(i); changed=True; break
    # rear garden = 10% of lot, measured away from the road
    for L_ in lots:
        q=L_['g']; rd=road.buffer(0.3)
        # depth direction: away from nearest road -> use distance to road
        lo,hi=0,max(Point(p).distance(road) for p in q.exterior.coords)
        def rear(w): return q.difference(road.buffer(w,join_style=2))
        x0,x1=lo,hi
        for _ in range(35):
            xm=(x0+x1)/2
            if rear(xm).area>garden*q.area: x0=xm
            else: x1=xm
        L_['garden']=clean(rear((x0+x1)/2)); L_['net']=q.area-L_['garden'].area
    return dict(road=road,pav=pav,lots=lots,park=park,acc=P[0],axis=P,rc=rc)

def slice3(comp,a,t,A_T,W):
    proj=lambda p:(p[0]-a[0])*t[0]+(p[1]-a[1])*t[1]
    xs=[proj(p) for p in comp.exterior.coords]; lo,hi=min(xs),max(xs)
    part=lambda s0,s1: comp.intersection(half(a,t,s0,s1))
    def best(rev):
        cuts=[];s=lo if not rev else hi;out=[]
        while True:
            rem=part(s,hi) if not rev else part(lo,s)
            if rem.area<1.8*A_T: break
            x0,x1=(s,hi) if not rev else (lo,s)
            for _ in range(40):
                xm=(x0+x1)/2
                ar=(part(s,xm) if not rev else part(xm,s)).area
                if (ar<A_T)!=rev: x0=xm
                else: x1=xm
            x=(x1 if not rev else x0)
            x=max(x,s+W) if not rev else min(x,s-W)
            rest=part(x,hi) if not rev else part(lo,x)
            if rest.area<0.85*A_T or (abs((hi if not rev else lo)-x)<0.9*W): break
            cuts.append(x);s=x
        bnd=sorted([lo,hi]+cuts)
        for s0,s1 in zip(bnd[:-1],bnd[1:]):
            q=part(s0,s1);out.append(max(polys(q),key=lambda z:z.area))
        return out
    r1,r2=best(False),best(True)
    sc=lambda r:(sum(is_std(q,A_T) for q in r),len(r))
    return r1 if sc(r1)>=sc(r2) else r2
