import re,glob,math,json
from shapely.geometry import Polygon,LineString,Point,box,MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
F=glob.glob('dwf/dwf/documents/*/sections/com.autodesk.dwf.ePlot_*/FixedPage.fpage')[0]
SX,SY=8.388729177,8.388881293
X0,Y0=472.440945,26456.69291
UTM0=(2999753.314/SX,19169112.75/SY)   # m -> UTM offset
def tok(d): return re.findall(r'[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?',d)
def parse(d):
    t=tok(d);i=0;cur=(0,0);cmd=None;segs=[];sub=[]
    while i<len(t):
        if t[i].isalpha(): cmd=t[i];i+=1;continue
        if cmd in 'Mm':
            x,y=float(t[i]),float(t[i+1]);i+=2
            cur=(x,y) if cmd=='M' else (cur[0]+x,cur[1]+y)
            if sub: segs.append(sub)
            sub=[cur]; cmd='l' if cmd=='m' else 'L'
        elif cmd in 'Ll':
            x,y=float(t[i]),float(t[i+1]);i+=2
            cur=(x,y) if cmd=='L' else (cur[0]+x,cur[1]+y);sub.append(cur)
        elif cmd in 'hH':
            x=float(t[i]);i+=1;cur=(x if cmd=='H' else cur[0]+x,cur[1]);sub.append(cur)
        elif cmd in 'vV':
            y=float(t[i]);i+=1;cur=(cur[0],y if cmd=='V' else cur[1]+y);sub.append(cur)
        elif cmd in 'aA':
            i+=7  # arcs only in strokes; fills are polylines
        else: i+=1
    if sub: segs.append(sub)
    return segs
def m(p): return ((p[0]-X0)/SX,(Y0-p[1])/SY)
src=open(F).read()
def load_context():
    """return parcels (A,B) and context stroke polylines (meters)"""
    tris=[]
    strokes=[]
    for name,attrs in re.findall(r'<Path Name="(\S+)" ([^>]*)/?>',src):
        d=re.search(r'Data="([^"]*)"',attrs).group(1)
        if 'Fill=' in attrs:
            for sub in parse(d):
                pts=[m(p) for p in sub]
                if len(pts)>=3: tris.append(Polygon(pts).buffer(0))
    U=unary_union([p.buffer(0.05,join_style=2) for p in tris]).buffer(-0.05,join_style=2)
    gs=sorted(U.geoms,key=lambda g:g.centroid.x)
    A=Polygon(gs[0].simplify(0.3).exterior); B=Polygon(gs[1].simplify(0.3).exterior)
    return A,B
TH=math.atan2(164.51,62.34); C,S=math.cos(TH),math.sin(TH)
FR={'A':(285.98,62.7),'B':(453.7,216.0)}
ACC={'A':(5.14,26.25),'B':(6.73,38.35)}
def g(o,p):  # local (u,v) -> global meters
    u,v=p; return (o[0]+u*C+v*S, o[1]+u*S-v*C)
def l(o,p):
    dx,dy=p[0]-o[0],p[1]-o[1]; return (dx*C+dy*S, dx*S-dy*C)

ROW=11.0; HALF=ROW/2

def layout(parcel,lines,retornos,A_T,D,order=None,merge_max=1.4,rtn_r=12.0):
    roads=[]
    skip=set()
    norm=[]
    for li,ln in enumerate(lines):
        if isinstance(ln,dict):
            for si in ln.get('skip',[]): skip.add((li,si))
            ln=ln['p']
        norm.append(ln)
    lines=norm
    for ln in lines:
        roads.append(LineString(ln).buffer(HALF,cap_style=2,join_style=2,mitre_limit=3))
        # round joint smoothing at ends that touch other lines handled by union
    for p in retornos: roads.append(Point(p).buffer(rtn_r,32))
    road=unary_union(roads).intersection(parcel)
    road=road.buffer(0.01).buffer(-0.01)
    blocks=parcel.difference(road).buffer(-0.01).buffer(0.01)
    assigned=[]
    avail=blocks
    segs=[]
    for li,ln in enumerate(lines):
        for si,(a,b) in enumerate(zip(ln[:-1],ln[1:])):
            if (li,si) not in skip: segs.append((a,b))
    if order: segs=[segs[i] for i in order]
    lots=[]
    for (a,b) in segs:
        L=math.dist(a,b); t=((b[0]-a[0])/L,(b[1]-a[1])/L)
        for side in (1,-1):
            n=(-t[1]*side,t[0]*side)
            # strip in segment frame
            ext=HALF+D*0.9  # reach into outer corners
            p0=(a[0]-t[0]*ext+n[0]*HALF, a[1]-t[1]*ext+n[1]*HALF)
            fr=LineString([(a[0]+n[0]*HALF,a[1]+n[1]*HALF),(b[0]+n[0]*HALF,b[1]+n[1]*HALF)])
            pts=[p0,(p0[0]+t[0]*(L+2*ext),p0[1]+t[1]*(L+2*ext))]
            pts+= [(pts[1][0]+n[0]*D,pts[1][1]+n[1]*D),(p0[0]+n[0]*D,p0[1]+n[1]*D)]
            strip=Polygon(pts).intersection(avail)
            comps=[c for c in getattr(strip,'geoms',[strip]) if c.geom_type=='Polygon' and c.area>0.3*A_T]
            # need frontage: component must touch the road edge of this segment
            for comp in comps:
                front=comp.intersection(fr.buffer(0.3))
                if front.area<0.6*6: continue
                best=None
                for rev in (False,True):
                    res=slice_comp(comp,a,t,A_T,rev)
                    sc=sum(1 for q in res if is_std(q,A_T))
                    if best is None or sc>best[0]: best=(sc,res)
                for q in best[1]:
                    lots.append(q)
                avail=avail.difference(unary_union(best[1])).buffer(-0.005).buffer(0.005)
    # leftovers
    greens=[]
    left=[c for c in getattr(avail,'geoms',[avail]) if c.geom_type=='Polygon' and c.area>2]
    for c in sorted(left,key=lambda x:x.area):
        bi=None;bl=0
        for i,q in enumerate(lots):
            sh=c.boundary.intersection(q.buffer(0.1)).length
            if sh>bl: bl,bi=sh,i
        if bi is not None and bl>3 and lots[bi].area+c.area<=merge_max*A_T:
            u=unary_union([lots[bi],c.buffer(0.02)]).buffer(-0.02)
            if u.geom_type=='Polygon': lots[bi]=u; continue
        greens.append(c)
    keep=[]
    rb=road.boundary
    for q in lots:
        fr=q.boundary.intersection(road.buffer(0.15)).length
        if q.area<0.8*A_T or fr<7: greens.append(q)
        else: keep.append(q)
    # try to merge orphan greens into neighbouring lots
    out=[]
    for c in greens:
        bi=None;bl=0
        for i,q in enumerate(keep):
            sh=c.boundary.intersection(q.buffer(0.1)).length
            if sh>bl: bl,bi=sh,i
        if bi is not None and bl>3 and keep[bi].area+c.area<=merge_max*A_T:
            u=unary_union([keep[bi],c.buffer(0.02)]).buffer(-0.02)
            if u.geom_type=='Polygon': keep[bi]=u; continue
        out.append(c)
    greens=out
    return road,keep,greens

def slice_comp(comp,a,t,A_T,rev):
    proj=lambda p:(p[0]-a[0])*t[0]+(p[1]-a[1])*t[1]
    xs=[proj(p) for p in comp.exterior.coords]
    lo,hi=min(xs),max(xs); T=comp.area
    def cut(x):  # area of part with s<=x (or >= if rev)
        big=1e4
        if not rev: hp=half(a,t,lo-1,x)
        else: hp=half(a,t,x,hi+1)
        return comp.intersection(hp)
    n=max(1,round(T/A_T)); 
    k_full=int(T//A_T); r=T-k_full*A_T
    # plan target areas
    if k_full==0: targets=[T]
    elif r>=0.85*A_T: targets=[A_T]*k_full+[r]
    elif r>=0.7*A_T and k_full>=1: targets=[A_T]*(k_full-1)+[(A_T+r)/2]*2
    else: targets=[A_T]*(k_full-1)+[A_T+r]
    pieces=[];acc=0;prev=lo if not rev else hi
    for i,ta in enumerate(targets[:-1]):
        acc+=ta
        x0,x1=lo,hi
        for _ in range(40):
            xm=(x0+x1)/2; ar=cut(xm).area
            if (ar<acc)!=(rev): x0=xm
            else: x1=xm
        xm=(x0+x1)/2
        pieces.append(xm)
    bounds=[lo]+pieces+[hi] if not rev else [hi]+pieces+[lo]
    out=[]
    for i in range(len(bounds)-1):
        s0,s1=sorted((bounds[i],bounds[i+1]))
        q=comp.intersection(half(a,t,s0,s1))
        if q.geom_type!='Polygon':
            q=max(getattr(q,'geoms',[q]),key=lambda z:z.area)
        out.append(q)
    return out
def half(a,t,s0,s1):
    n=(-t[1],t[0]);B=1e3
    P=lambda s,w:(a[0]+t[0]*s+n[0]*w,a[1]+t[1]*s+n[1]*w)
    return Polygon([P(s0,-B),P(s1,-B),P(s1,B),P(s0,B)])
def is_std(q,A_T):
    r=q.minimum_rotated_rectangle
    return q.area/r.area>0.985 and abs(q.area-A_T)<=0.02*A_T
