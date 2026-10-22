#!/usr/bin/env python3
"""Genera planos DXF (R12) + vista previa SVG de una estructura de madera
para un trovisel de 122 x 244 cm (parte inferior a 88 cm, superior a 210 cm).

Todo en Python puro (sin dependencias). Unidades: centimetros.

Uso:  python3 generar_planos.py [carpeta_salida]
"""
import math
import os
import sys

# ---------------------------------------------------------------- vectores
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def unit(a):
    l = length(a)
    return (a[0] / l, a[1] / l, a[2] / l)

def cross2(a, b): return a[0] * b[1] - a[1] * b[0]
def sub2(a, b): return (a[0] - b[0], a[1] - b[1])
def dist2(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

EPS = 1e-6


# ------------------------------------------------------- geometria 2D
def clean_poly(poly):
    out = []
    for p in poly:
        if not out or dist2(out[-1], p) > 1e-7:
            out.append(p)
    while len(out) > 1 and dist2(out[0], out[-1]) <= 1e-7:
        out.pop()
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if abs(cross2(sub2(b, a), sub2(c, b))) < 1e-9:
                out.pop(i)
                changed = True
                break
    return out


def signed_area(poly):
    return 0.5 * sum(cross2(poly[i - 1], poly[i]) for i in range(len(poly)))


def clip_halfplane(poly, a, b, c):
    """Conserva puntos con a*x + b*y + c >= 0 (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp = a * p[0] + b * p[1] + c
        fq = a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def clip_rect(poly, x0, x1, y0, y1):
    for a, b, c in ((1, 0, -x0), (-1, 0, x1), (0, 1, -y0), (0, -1, y1)):
        poly = clip_halfplane(poly, a, b, c)
        if not poly:
            return []
    return clean_poly(poly)


def strip_poly(p0, p1, width, ext=1000.0):
    d = sub2(p1, p0)
    l = math.hypot(*d)
    u = (d[0] / l, d[1] / l)
    n = (-u[1] * width / 2, u[0] * width / 2)
    a = (p0[0] - u[0] * ext, p0[1] - u[1] * ext)
    b = (p1[0] + u[0] * ext, p1[1] + u[1] * ext)
    return [(a[0] - n[0], a[1] - n[1]), (b[0] - n[0], b[1] - n[1]),
            (b[0] + n[0], b[1] + n[1]), (a[0] + n[0], a[1] + n[1])]


def point_in_poly(p, poly, tol=1e-6):
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ab = sub2(b, a)
        l2 = ab[0] ** 2 + ab[1] ** 2
        if l2 < 1e-18:
            continue
        t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / l2))
        if dist2(p, (a[0] + t * ab[0], a[1] + t * ab[1])) <= tol:
            return True
    inside = False
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return inside


def point_in_poly_strict(p, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return inside


def seg_poly_intervals(a, b, poly):
    """Intervalos de t en [0,1] donde a+t(b-a) esta dentro del poligono (incl. borde)."""
    d = sub2(b, a)
    dl = math.hypot(*d)
    ts = [0.0, 1.0]
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        e = sub2(q, p)
        den = cross2(d, e)
        ap = sub2(p, a)
        if abs(den) > 1e-12:
            t = cross2(ap, e) / den
            u = cross2(ap, d) / den
            if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
                ts.append(min(1.0, max(0.0, t)))
        elif abs(cross2(ap, d)) / dl < 1e-6:
            for r in (p, q):
                t = ((r[0] - a[0]) * d[0] + (r[1] - a[1]) * d[1]) / (dl * dl)
                if 0 < t < 1:
                    ts.append(t)
    ts.sort()
    res = []
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-9:
            continue
        m = 0.5 * (t0 + t1)
        if point_in_poly((a[0] + m * d[0], a[1] + m * d[1]), poly):
            if res and abs(res[-1][1] - t0) < 1e-9:
                res[-1] = (res[-1][0], t1)
            else:
                res.append((t0, t1))
    return res


def interior_point(poly):
    s = 1 if signed_area(poly) > 0 else -1
    n = len(poly)
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        if cross2(sub2(b, a), sub2(c, b)) * s <= 1e-12:
            continue
        ok = True
        for j in range(n):
            if j in (i - 1 if i > 0 else n - 1, i, (i + 1) % n):
                continue
            if point_in_poly_strict(poly[j], [a, b, c]):
                ok = False
                break
        if ok:
            return ((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


# ---------------------------------------------------------- solidos 3D
class Face:
    def __init__(self, pts):
        self.pts = pts
        nx = ny = nz = 0.0
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
        self.n = unit((nx, ny, nz))
        self._setup()

    def _setup(self):
        self.d = dot(self.n, self.pts[0])
        self.o = self.pts[0]
        self.e1 = unit(sub(self.pts[1], self.pts[0]))
        self.e2 = cross(self.n, self.e1)
        self.p2d = [self.to2d(p) for p in self.pts]

    def to2d(self, p):
        v = sub(p, self.o)
        return (dot(v, self.e1), dot(v, self.e2))

    def flip(self):
        self.pts = self.pts[::-1]
        self.n = mul(self.n, -1)
        self._setup()


class Solid:
    def __init__(self, polys, layer="MADERA", smooth=False):
        self.layer = layer
        self.smooth = smooth
        self.faces = [Face(p) for p in polys]
        # orientar normales hacia afuera (prueba de paridad con un rayo)
        for f in self.faces:
            ip2 = interior_point(f.p2d)
            ip = add(f.o, add(mul(f.e1, ip2[0]), mul(f.e2, ip2[1])))
            if self._inside(add(ip, mul(f.n, 1e-4))):
                f.flip()
        self.edges = {}
        for f in self.faces:
            n = len(f.pts)
            for i in range(n):
                a, b = f.pts[i], f.pts[(i + 1) % n]
                ka = tuple(round(c, 6) for c in a)
                kb = tuple(round(c, 6) for c in b)
                key = (ka, kb) if ka < kb else (kb, ka)
                self.edges.setdefault(key, []).append(f)

    def _inside(self, q):
        r = unit((0.5773, 0.5571, 0.5967))
        cnt = 0
        for f in self.faces:
            den = dot(f.n, r)
            if abs(den) < 1e-12:
                continue
            t = (f.d - dot(f.n, q)) / den
            if t <= 1e-9:
                continue
            if point_in_poly_strict(f.to2d(add(q, mul(r, t))), f.p2d):
                cnt += 1
        return cnt % 2 == 1


def prism_polys(profile, ea, eb, ec, c0, c1, origin=(0, 0, 0)):
    def P(a, b, c):
        return add(origin, add(mul(ea, a), add(mul(eb, b), mul(ec, c))))
    profile = clean_poly(profile)
    bot = [P(a, b, c0) for a, b in profile]
    top = [P(a, b, c1) for a, b in profile]
    polys = [bot, top]
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        polys.append([bot[i], bot[j], top[j], top[i]])
    return polys


X_, Y_, Z_ = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def box(x0, x1, y0, y1, z0, z1):
    return ("pxy", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1)


def spec_polys(spec):
    k = spec[0]
    if k == "pxy":
        return prism_polys(spec[1], X_, Y_, Z_, spec[2], spec[3])
    if k == "pxz":
        return prism_polys(spec[1], X_, Z_, Y_, spec[2], spec[3])
    if k == "pyz":
        return prism_polys(spec[1], Y_, Z_, X_, spec[2], spec[3])
    if k == "cyl":   # ("cyl", eje, centro, radio, c0, c1, lados)
        _, axis, cen, r, c0, c1, sides = spec
        prof = [(r * math.cos(2 * math.pi * (i + 0.5) / sides),
                 r * math.sin(2 * math.pi * (i + 0.5) / sides)) for i in range(sides)]
        ea, eb, ec = {"x": (Y_, Z_, X_), "y": (Z_, X_, Y_), "z": (X_, Y_, Z_)}[axis]
        o = tuple(0 if ec[i] else cen[i] for i in range(3))
        return prism_polys(prof, ea, eb, ec, c0, c1, origin=o)
    if k == "raw":
        return spec[1]
    raise ValueError(k)


def clip_spec(spec, reg):
    """reg = (x0,x1,y0,y1,z0,z1). Recorta prismas alineados a ejes."""
    x0, x1, y0, y1, z0, z1 = reg
    k = spec[0]
    if k in ("pxy", "pxz", "pyz"):
        r2, r3 = {"pxy": ((x0, x1, y0, y1), (z0, z1)),
                  "pxz": ((x0, x1, z0, z1), (y0, y1)),
                  "pyz": ((y0, y1, z0, z1), (x0, x1))}[k]
        poly = clip_rect(spec[1], *r2)
        c0, c1 = max(spec[2], r3[0]), min(spec[3], r3[1])
        if len(poly) < 3 or c1 - c0 < 1e-6 or abs(signed_area(poly)) < 1e-6:
            return None
        return (k, poly, c0, c1)
    if k == "cyl":
        c = spec[2]
        if x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and z0 <= c[2] <= z1:
            return spec
        return None
    return spec


def translate_polys(polys, v):
    return [[add(p, v) for p in poly] for poly in polys]


# ------------------------------------------------------ lineas ocultas
def view_basis(direction):
    V = unit(direction)
    R = cross(V, Z_)
    if length(R) < 1e-9:
        R = (1, 0, 0)
    R = unit(R)
    U = cross(R, V)
    return R, U, V


def hidden_line(solids, view, eps=1e-4, smooth_cos=math.cos(math.radians(30))):
    R, U, V = view
    pf = []
    for s in solids:
        for f in s.faces:
            nv = dot(f.n, V)
            if abs(nv) < 1e-9:
                continue
            poly = [(dot(p, R), dot(p, U)) for p in f.pts]
            if abs(signed_area(poly)) < 1e-9:
                continue
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            pf.append((f, poly, (min(xs), max(xs), min(ys), max(ys)), nv))
    allfaces = [(s, f) for s in solids for f in s.faces]
    out = []
    seen = set()
    for s in solids:
        for (ka, kb), faces in s.edges.items():
            if s.smooth and len(faces) == 2:
                n1, n2 = faces[0].n, faces[1].n
                if dot(n1, n2) > smooth_cos and dot(n1, V) * dot(n2, V) > 0:
                    continue
            a, b = ka, kb
            pa = (dot(a, R), dot(a, U))
            pb = (dot(b, R), dot(b, U))
            if dist2(pa, pb) < 1e-6:
                continue
            da, db = dot(a, V), dot(b, V)
            ex0, ex1 = min(pa[0], pb[0]), max(pa[0], pb[0])
            ey0, ey1 = min(pa[1], pb[1]), max(pa[1], pb[1])
            hidden = []
            for f, poly, bb, nv in pf:
                if f in faces:
                    continue
                if bb[1] < ex0 - 1e-6 or bb[0] > ex1 + 1e-6 or bb[3] < ey0 - 1e-6 or bb[2] > ey1 + 1e-6:
                    continue
                for t0, t1 in seg_poly_intervals(pa, pb, poly):
                    g = []
                    for t in (t0, t1):
                        sx = pa[0] + t * (pb[0] - pa[0])
                        sy = pa[1] + t * (pb[1] - pa[1])
                        pt = add(mul(R, sx), mul(U, sy))
                        fd = (f.d - dot(f.n, pt)) / nv
                        g.append(fd - (da + t * (db - da)))
                    g0, g1 = g
                    if g0 < -eps and g1 < -eps:
                        hidden.append((t0, t1))
                    elif g0 < -eps or g1 < -eps:
                        tc = t0 + (t1 - t0) * (-eps - g0) / (g1 - g0)
                        hidden.append((t0, tc) if g0 < -eps else (tc, t1))
            # costuras: la cara adyacente continua coplanar en otro solido
            ev = sub(b, a)
            mid = mul(add(a, b), 0.5)
            for fa in faces:
                m = unit(cross(fa.n, ev))
                if point_in_poly(fa.to2d(add(mid, mul(m, 1e-3))), fa.p2d, tol=1e-9):
                    m = mul(m, -1)
                a2, b2 = add(a, mul(m, 1e-3)), add(b, mul(m, 1e-3))
                for s2, g in allfaces:
                    if s2 is s or dot(g.n, fa.n) < 1 - 1e-9 or abs(g.d - fa.d) > 1e-6:
                        continue
                    hidden += seg_poly_intervals(g.to2d(a2), g.to2d(b2), g.p2d)
            hidden.sort()
            vis = []
            cur = 0.0
            for t0, t1 in hidden:
                if t0 > cur + 1e-7:
                    vis.append((cur, t0))
                cur = max(cur, t1)
            if cur < 1 - 1e-7:
                vis.append((cur, 1.0))
            for t0, t1 in vis:
                p = (pa[0] + t0 * (pb[0] - pa[0]), pa[1] + t0 * (pb[1] - pa[1]))
                q = (pa[0] + t1 * (pb[0] - pa[0]), pa[1] + t1 * (pb[1] - pa[1]))
                if dist2(p, q) < 1e-4:
                    continue
                key = tuple(round(c, 3) for c in (min(p, q) + max(p, q)))
                if key in seen:
                    continue
                seen.add(key)
                out.append((s.layer, p, q))
    return out


def project(p, view):
    R, U, _ = view
    return (dot(p, R), dot(p, U))


# --------------------------------------------------------------- dibujo
LAYERS = {  # nombre: (color ACI, tipo de linea)
    "MADERA": (7, "CONTINUOUS"),
    "TROVISEL": (5, "CONTINUOUS"),
    "HERRAJES": (30, "CONTINUOUS"),
    "COTAS": (1, "CONTINUOUS"),
    "TEXTO": (7, "CONTINUOUS"),
    "EJES": (6, "CENTER"),
    "PEGAMENTO": (3, "DASHED"),
    "PISO": (8, "CONTINUOUS"),
    "MARCO": (7, "CONTINUOUS"),
}
SVG_COLORS = {7: "#111", 5: "#1a4fd6", 30: "#d96a00", 1: "#d01010", 6: "#a020a0", 3: "#139a2c", 8: "#777"}


class Drawing:
    def __init__(self):
        self.items = []

    def line(self, layer, p, q):
        self.items.append(("line", layer, p, q))

    def poly(self, layer, pts, closed=False):
        n = len(pts)
        for i in range(n if closed else n - 1):
            self.line(layer, pts[i], pts[(i + 1) % n])

    def rect(self, layer, x0, y0, x1, y1):
        self.poly(layer, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)

    def circle(self, layer, c, r):
        self.items.append(("circle", layer, c, r))

    def text(self, layer, p, h, s, align="left", rot=0.0):
        self.items.append(("text", layer, p, h, s, align, rot))

    def lines(self, segs, transform=None):
        for layer, p, q in segs:
            if transform:
                p, q = transform(p), transform(q)
            self.line(layer, p, q)

    # ---- cotas
    def dim(self, p1, p2, off, txt=None, h=3.5, fmt="{:.1f}"):
        u = sub2(p2, p1)
        L = math.hypot(*u)
        u = (u[0] / L, u[1] / L)
        nrm = (-u[1], u[0])
        sg = 1 if off >= 0 else -1
        q1 = (p1[0] + nrm[0] * off, p1[1] + nrm[1] * off)
        q2 = (p2[0] + nrm[0] * off, p2[1] + nrm[1] * off)
        for p, q in ((p1, q1), (p2, q2)):
            self.line("COTAS", (p[0] + nrm[0] * sg * 1.0, p[1] + nrm[1] * sg * 1.0),
                      (q[0] + nrm[0] * sg * 2.0, q[1] + nrm[1] * sg * 2.0))
        self.line("COTAS", (q1[0] - u[0] * 2, q1[1] - u[1] * 2), (q2[0] + u[0] * 2, q2[1] + u[1] * 2))
        tk = (u[0] + nrm[0], u[1] + nrm[1])
        for q in (q1, q2):
            self.line("COTAS", (q[0] - tk[0] * 1.2, q[1] - tk[1] * 1.2), (q[0] + tk[0] * 1.2, q[1] + tk[1] * 1.2))
        if txt is None:
            txt = fmt.format(L)
            if "." in txt:
                txt = txt.rstrip("0").rstrip(".")
        ang = math.degrees(math.atan2(u[1], u[0]))
        if ang > 90.01 or ang < -89.99:
            ang += 180
        mid = ((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2)
        a = math.radians(ang)
        up = (-math.sin(a), math.cos(a))
        self.text("COTAS", (mid[0] + up[0] * 1.2, mid[1] + up[1] * 1.2), h, txt, "center", ang)

    def leader(self, p, q, txt, h=3.2):
        self.line("TEXTO", p, q)
        self.circle("TEXTO", p, 0.5)
        right = q[0] >= p[0]
        lines = txt.split("\n")
        w = max(len(l) for l in lines) * h * 0.72
        end = (q[0] + (w if right else -w), q[1])
        self.line("TEXTO", q, end)
        x = q[0] if right else end[0]
        for i, l in enumerate(lines):
            self.text("TEXTO", (x, q[1] + 1.0 - i * h * 1.5), h, l)

    def bbox(self):
        xs, ys = [], []
        for it in self.items:
            if it[0] == "line":
                xs += [it[2][0], it[3][0]]
                ys += [it[2][1], it[3][1]]
            elif it[0] == "circle":
                xs += [it[2][0] - it[3], it[2][0] + it[3]]
                ys += [it[2][1] - it[3], it[2][1] + it[3]]
            else:
                xs.append(it[2][0])
                ys.append(it[2][1])
        return min(xs), min(ys), max(xs), max(ys)

    # ---- salida DXF R12
    def to_dxf(self, path):
        o = []
        def g(code, val):
            o.append(str(code))
            if isinstance(val, float):
                o.append("%.6f" % val)
            else:
                o.append(str(val))
        x0, y0, x1, y1 = self.bbox()
        g(0, "SECTION"); g(2, "HEADER")
        g(9, "$ACADVER"); g(1, "AC1009")
        g(9, "$INSBASE"); g(10, 0.0); g(20, 0.0); g(30, 0.0)
        g(9, "$EXTMIN"); g(10, float(x0)); g(20, float(y0)); g(30, 0.0)
        g(9, "$EXTMAX"); g(10, float(x1)); g(20, float(y1)); g(30, 0.0)
        g(9, "$LTSCALE"); g(40, 4.0)
        g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "TABLES")
        g(0, "TABLE"); g(2, "LTYPE"); g(70, 3)
        for name, desc, pat in (("CONTINUOUS", "Solid line", []),
                                ("DASHED", "__ __ __", [0.5, -0.25]),
                                ("CENTER", "____ _ ____", [1.25, -0.25, 0.25, -0.25])):
            g(0, "LTYPE"); g(2, name); g(70, 0); g(3, desc); g(72, 65)
            g(73, len(pat)); g(40, float(sum(abs(x) for x in pat)))
            for x in pat:
                g(49, float(x))
        g(0, "ENDTAB")
        g(0, "TABLE"); g(2, "LAYER"); g(70, len(LAYERS))
        for name, (col, lt) in LAYERS.items():
            g(0, "LAYER"); g(2, name); g(70, 0); g(62, col); g(6, lt)
        g(0, "ENDTAB")
        g(0, "TABLE"); g(2, "STYLE"); g(70, 1)
        g(0, "STYLE"); g(2, "STANDARD"); g(70, 0); g(40, 0.0); g(41, 1.0); g(50, 0.0)
        g(71, 0); g(42, 2.5); g(3, "txt"); g(4, "")
        g(0, "ENDTAB")
        g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "ENTITIES")
        for it in self.items:
            if it[0] == "line":
                _, layer, p, q = it
                g(0, "LINE"); g(8, layer)
                g(10, float(p[0])); g(20, float(p[1])); g(30, 0.0)
                g(11, float(q[0])); g(21, float(q[1])); g(31, 0.0)
            elif it[0] == "circle":
                _, layer, c, r = it
                g(0, "CIRCLE"); g(8, layer)
                g(10, float(c[0])); g(20, float(c[1])); g(30, 0.0); g(40, float(r))
            else:
                _, layer, p, h, s, align, rot = it
                g(0, "TEXT"); g(8, layer)
                g(10, float(p[0])); g(20, float(p[1])); g(30, 0.0)
                g(40, float(h)); g(1, s)
                if rot:
                    g(50, float(rot))
                if align == "center":
                    g(72, 1); g(11, float(p[0])); g(21, float(p[1])); g(31, 0.0)
        g(0, "ENDSEC")
        g(0, "EOF")
        with open(path, "w", encoding="ascii", newline="\r\n") as fh:
            fh.write("\n".join(o) + "\n")

    # ---- vista previa SVG
    def to_svg(self, path, px_per_cm=1.6):
        x0, y0, x1, y1 = self.bbox()
        m = 5
        W, H = (x1 - x0 + 2 * m), (y1 - y0 + 2 * m)
        def T(p):
            return (p[0] - x0 + m, y1 - p[1] + m)
        o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %.2f %.2f">'
             % (W * px_per_cm, H * px_per_cm, W, H),
             '<rect width="100%" height="100%" fill="white"/>']
        dash = {"DASHED": ' stroke-dasharray="1.2,0.6"', "CENTER": ' stroke-dasharray="3,0.8,0.8,0.8"'}
        for it in self.items:
            layer = it[1]
            col = SVG_COLORS.get(LAYERS[layer][0], "#000")
            if it[0] == "line":
                p, q = T(it[2]), T(it[3])
                sw = 0.35 if layer in ("MADERA", "TROVISEL", "HERRAJES", "MARCO") else 0.2
                o.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="%s" stroke-width="%.2f"%s/>'
                         % (p[0], p[1], q[0], q[1], col, sw, dash.get(LAYERS[layer][1], "")))
            elif it[0] == "circle":
                c = T(it[2])
                o.append('<circle cx="%.3f" cy="%.3f" r="%.3f" stroke="%s" stroke-width="0.2" fill="none"/>'
                         % (c[0], c[1], it[3], col))
            else:
                _, layer, p, h, s, align, rot = it
                c = T(p)
                anchor = "middle" if align == "center" else "start"
                s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                o.append('<text x="%.3f" y="%.3f" font-size="%.2f" font-family="Arial, Helvetica, sans-serif" '
                         'fill="%s" text-anchor="%s" transform="rotate(%.2f %.3f %.3f)">%s</text>'
                         % (c[0], c[1], h * 1.38, col, anchor, -rot, c[0], c[1], s))
        o.append("</svg>")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(o))


# ------------------------------------------------------------ el modelo
ANCHO, ALTO = 244.0, 122.0
Z_INF, Z_SUP = 88.0, 210.0
T_TROV = 0.6     # espesor del trovisel (6 mm)
IN = 2.54

VERSIONES = {
    "V1": dict(nombre='VERSION 1 - POLIN DE 1" x 1 1/2"', w=1.0 * IN, d=1.5 * IN,
               seccion='1" x 1 1/2" (2.54 x 3.81 cm)', pie=70.0, zt=45.0,
               perno='1/4"', perno_r=0.3175, cabeza_r=0.95,
               tornillo='#8 x 2" (5 cm)', tornillo_x='#8 x 1 1/2" (3.8 cm)'),
    "V2": dict(nombre='VERSION 2 - POLIN DE 2" x 3"', w=2.0 * IN, d=3.0 * IN,
               seccion='2" x 3" (5.08 x 7.62 cm)', pie=80.0, zt=50.0,
               perno='3/8"', perno_r=0.476, cabeza_r=1.4,
               tornillo='#10 x 3 1/2" (9 cm)', tornillo_x='#10 x 3" (7.6 cm)'),
}


def build_model(P):
    """Devuelve lista de (nombre, capa, spec) y datos utiles."""
    w, d = P["w"], P["d"]
    tb = T_TROV
    y0, y1 = tb, tb + d            # bastidor
    yx0, yx1 = y1, y1 + w          # cruz trasera (pieza acostada)
    wx = d                         # ancho de la pieza de la cruz
    yc = tb + d / 2
    Lf = P["pie"]
    zt = P["zt"]
    cx1, cx2 = ANCHO / 3, 2 * ANCHO / 3
    zr = Z_INF + ALTO / 2
    zc1, zc2 = Z_INF + ALTO / 3, Z_INF + 2 * ALTO / 3
    M = []
    M.append(("trovisel", "TROVISEL", box(0, ANCHO, 0, tb, Z_INF, Z_SUP)))
    # patas laterales (forman los costados del bastidor)
    M.append(("pata_izq", "MADERA", box(0, w, y0, y1, 0, Z_SUP)))
    M.append(("pata_der", "MADERA", box(ANCHO - w, ANCHO, y0, y1, 0, Z_SUP)))
    # travesanos superior e inferior
    M.append(("trav_sup", "MADERA", box(w, ANCHO - w, y0, y1, Z_SUP - w, Z_SUP)))
    M.append(("trav_inf", "MADERA", box(w, ANCHO - w, y0, y1, Z_INF, Z_INF + w)))
    # montantes
    for i, c in enumerate((cx1, cx2)):
        M.append(("montante%d" % (i + 1), "MADERA", box(c - w / 2, c + w / 2, y0, y1, Z_INF + w, Z_SUP - w)))
    # travesanos intermedios (alternados para atornillar de frente)
    M.append(("trav_lat_izq", "MADERA", box(w, cx1 - w / 2, y0, y1, zr - w / 2, zr + w / 2)))
    M.append(("trav_lat_der", "MADERA", box(cx2 + w / 2, ANCHO - w, y0, y1, zr - w / 2, zr + w / 2)))
    for i, zc in enumerate((zc1, zc2)):
        M.append(("trav_cen%d" % (i + 1), "MADERA", box(cx1 + w / 2, cx2 - w / 2, y0, y1, zc - w / 2, zc + w / 2)))
    # cruz trasera: X1 continua (atras), X2 en dos tramos (media madera)
    a1, b1 = (0.0, Z_SUP), (ANCHO, Z_INF)
    a2, b2 = (0.0, Z_INF), (ANCHO, Z_SUP)
    x1poly = clip_rect(strip_poly(a1, b1, wx), 0, ANCHO, Z_INF, Z_SUP)
    x2full = clip_rect(strip_poly(a2, b2, wx), 0, ANCHO, Z_INF, Z_SUP)
    M.append(("cruz1", "MADERA", ("pxz", x1poly, yx0, yx1)))
    dx, dz = b1[0] - a1[0], b1[1] - a1[1]
    L = math.hypot(dx, dz)
    na, nb = -dz / L, dx / L
    nc = -(na * a1[0] + nb * a1[1])
    for k, sg in enumerate((1, -1)):
        piece = clean_poly(clip_halfplane(x2full, sg * na, sg * nb, sg * nc - wx / 2))
        M.append(("cruz2%s" % "ab"[k], "MADERA", ("pxz", piece, yx0, yx1)))
    # pies abatibles, tacos y tornapuntas (a los lados, cara exterior de la pata)
    r, rh = P["perno_r"], P["cabeza_r"]
    P1 = (yc + Lf / 2 - 6, d / 2)
    P2 = (yc, zt)
    ext = d * 0.75
    u = sub2(P1, P2)
    ul = math.hypot(*u)
    u = (u[0] / ul, u[1] / ul)
    e1 = (P2[0] - u[0] * ext, P2[1] - u[1] * ext)
    e2 = (P1[0] + u[0] * ext, P1[1] + u[1] * ext)
    brace = clip_rect(strip_poly(e1, e2, d, ext=0), yc - Lf / 2, yc + Lf / 2, 0, 300)
    bolts = []
    for side, (xl, sg) in (("izq", (0.0, -1)), ("der", (ANCHO, 1))):
        def X(a):   # distancia hacia afuera desde la cara exterior de la pata
            return xl + sg * a
        def rng(a, b):
            return (min(X(a), X(b)), max(X(a), X(b)))
        fx = rng(0, w)
        bx = rng(w, 2 * w)
        M.append(("pie_" + side, "MADERA", box(fx[0], fx[1], yc - Lf / 2, yc + Lf / 2, 0, d)))
        M.append(("taco_" + side, "MADERA", box(fx[0], fx[1], y0, y1, zt - 5, zt + 5)))
        M.append(("tornapunta_" + side, "MADERA", ("pyz", brace, bx[0], bx[1])))
        # pernos: (centro y,z), desde (afuera) hasta (adentro)
        for nm, (py, pz), outer in (("pivote", (yc, d / 2), w),
                                    ("tp_sup", P2, 2 * w),
                                    ("tp_inf", P1, 2 * w)):
            inner = -w if nm != "tp_inf" else 0.0   # sale por la cara interior
            c_out, c_in = X(outer), X(inner - 1.2)
            ca, cb = min(c_out, c_in), max(c_out, c_in)
            M.append(("perno_%s_%s" % (nm, side), "HERRAJES",
                      ("cyl", "x", (0, py, pz), r, ca, cb, 16)))
            h0, h1 = sorted((X(outer), X(outer + 0.5)))
            M.append(("cabeza_%s_%s" % (nm, side), "HERRAJES",
                      ("cyl", "x", (0, py, pz), rh, h0, h1, 16)))
            n0, n1 = sorted((X(inner - 0.2), X(inner - 0.9)))
            M.append(("tuerca_%s_%s" % (nm, side), "HERRAJES",
                      ("cyl", "x", (0, py, pz), rh * 0.95, n0, n1, 6)))
            bolts.append((side, nm, py, pz))
    info = dict(w=w, d=d, yc=yc, Lf=Lf, zt=zt, cx1=cx1, cx2=cx2, zr=zr, zc1=zc1, zc2=zc2,
                y0=y0, y1=y1, yx0=yx0, yx1=yx1, wx=wx, x1poly=x1poly, brace=brace, P1=P1, P2=P2,
                bolts=bolts)
    return M, info


def solids_from(M, names=None, region=None, offsets=None):
    out = []
    for name, layer, spec in M:
        if names is not None and not any(name.startswith(n) for n in names):
            continue
        if region is not None:
            spec = clip_spec(spec, region)
            if spec is None:
                continue
        polys = spec_polys(spec)
        if offsets:
            for pre, v in offsets.items():
                if name.startswith(pre):
                    polys = translate_polys(polys, v)
        out.append(Solid(polys, layer, smooth=(spec[0] == "cyl" and spec[6] > 8)))
    return out


def poly_len(poly, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    pr = [((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L for p in poly]
    return max(pr) - min(pr)


# ------------------------------------------------- pieza a media madera
def notched_strip(o, e1, e2, e3, L, W, t, uc, phi, notch_top=True):
    """Pieza recta (largo L, ancho W, grueso t) con caja a media madera
    para cruzar otra pieza a un angulo phi; la caja queda en la cara w=t
    (notch_top) o en w=0."""
    def P(u, v, w):
        if not notch_top:
            w = t - w
        return add(o, add(mul(e1, u), add(mul(e2, v), mul(e3, w))))
    s, c = math.sin(phi), math.cos(phi)
    def uu(v, sg):
        return uc + (v * c + sg * W / 2) / s
    ua, ub = sorted((uu(-W / 2, -1), uu(-W / 2, 1)))
    ud, ue = sorted((uu(W / 2, -1), uu(W / 2, 1)))
    h = t / 2
    m, M_ = -W / 2, W / 2
    polys = [
        [P(0, m, 0), P(L, m, 0), P(L, M_, 0), P(0, M_, 0)],
        [P(0, m, t), P(ua, m, t), P(ud, M_, t), P(0, M_, t)],
        [P(ub, m, t), P(L, m, t), P(L, M_, t), P(ue, M_, t)],
        [P(ua, m, h), P(ub, m, h), P(ue, M_, h), P(ud, M_, h)],
        [P(ua, m, h), P(ud, M_, h), P(ud, M_, t), P(ua, m, t)],
        [P(ub, m, h), P(ue, M_, h), P(ue, M_, t), P(ub, m, t)],
        [P(0, m, 0), P(L, m, 0), P(L, m, t), P(ub, m, t), P(ub, m, h), P(ua, m, h), P(ua, m, t), P(0, m, t)],
        [P(0, M_, 0), P(L, M_, 0), P(L, M_, t), P(ue, M_, t), P(ue, M_, h), P(ud, M_, h), P(ud, M_, t), P(0, M_, t)],
        [P(0, m, 0), P(0, M_, 0), P(0, M_, t), P(0, m, t)],
        [P(L, m, 0), P(L, M_, 0), P(L, M_, t), P(L, m, t)],
    ]
    return polys


# ------------------------------------------------------------- laminas
def place(segs, view_fn, dx, dy):
    return [(l, (p[0] + dx, p[1] + dy), (q[0] + dx, q[1] + dy)) for l, p, q in segs]


def make_sheet(key, P, outdir):
    M, I = build_model(P)
    w, d, yc, Lf, zt = I["w"], I["d"], I["yc"], I["Lf"], I["zt"]
    D = Drawing()
    full = solids_from(M)

    FRONT = view_basis((0, 1, 0))
    REAR = view_basis((0, -1, 0))
    SIDE = view_basis((-1, 0, 0))

    # ---------------- alzado frontal (x, z)
    OX_F = 0.0
    D.lines(hidden_line(full, FRONT), lambda p: (p[0] + OX_F, p[1]))
    D.line("PISO", (OX_F - 25, 0), (OX_F + ANCHO + 25, 0))
    for i in range(14):
        x = OX_F - 22 + i * 21
        D.line("PISO", (x, 0), (x - 3, -3))
    D.text("TEXTO", (OX_F + ANCHO / 2, 116), 6, "TROVISEL 122 x 244", "center")
    D.text("TEXTO", (OX_F + ANCHO / 2, 106), 3.5, "(PVC espumado 6 mm, pegado al bastidor)", "center")
    D.dim((OX_F, Z_SUP), (OX_F + ANCHO, Z_SUP), 10)
    D.dim((OX_F - 2 * w, 0), (OX_F + ANCHO + 2 * w, 0), -14, fmt="{:.1f}")
    D.dim((OX_F - 2 * w, 0), (OX_F - 2 * w, Z_INF), 12)
    D.dim((OX_F, Z_INF), (OX_F, Z_SUP), 12 + 2 * w)
    D.dim((OX_F + ANCHO + 2 * w, 0), (OX_F + ANCHO + 2 * w, Z_SUP), -12)
    D.text("TEXTO", (OX_F + ANCHO / 2, 240), 7, "ALZADO FRONTAL", "center")
    D.text("TEXTO", (OX_F + ANCHO / 2, 232), 3.5, "ESC. 1:20 (al imprimir el plano completo a 1:20)", "center")

    # ---------------- alzado posterior
    OX_R = 330.0 + ANCHO
    D.lines(hidden_line(full, REAR), lambda p: (p[0] + OX_R, p[1]))
    D.line("PISO", (OX_R - ANCHO - 25, 0), (OX_R + 25, 0))
    for i in range(14):
        x = OX_R - ANCHO - 22 + i * 21
        D.line("PISO", (x, 0), (x - 3, -3))
    rx = lambda x: OX_R - x
    D.dim((rx(0), Z_SUP), (rx(I["cx2"]), Z_SUP), 8, txt="81.3", h=3.2)
    D.dim((rx(I["cx2"]), Z_SUP), (rx(I["cx1"]), Z_SUP), 8, txt="81.3", h=3.2)
    D.dim((rx(I["cx1"]), Z_SUP), (rx(ANCHO), Z_SUP), 8, txt="81.3", h=3.2)
    D.text("TEXTO", (rx(ANCHO / 2), Z_SUP + 15), 3, "(a ejes de montantes)", "center")
    D.dim((rx(ANCHO), Z_INF), (rx(ANCHO), I["zr"]), -10, txt="61")
    D.dim((rx(ANCHO), I["zr"]), (rx(ANCHO), Z_SUP), -10, txt="61")
    D.dim((rx(0), Z_INF), (rx(0), I["zc1"]), 10, txt="40.7")
    D.dim((rx(0), I["zc1"]), (rx(0), I["zc2"]), 10, txt="40.7")
    D.dim((rx(0), I["zc2"]), (rx(0), Z_SUP), 10, txt="40.7")
    D.text("TEXTO", (rx(-24), I["zc1"] - 2), 2.6, "(trav. centrales)", "center", 90)
    D.text("TEXTO", (rx(ANCHO + 22), I["zr"] - 2), 2.6, "(trav. laterales)", "center", 90)
    D.text("TEXTO", (rx(ANCHO / 2), 240), 7, "ALZADO POSTERIOR", "center")
    D.text("TEXTO", (rx(ANCHO / 2), 232), 3.5, "Bastidor visto por detras con cruz de soporte", "center")
    # etiquetas
    D.leader((rx(ANCHO * 0.25), Z_INF + ALTO * 0.25 + 3), (rx(ANCHO * 0.25) + 20, 60),
             "CRUZ TRASERA\n" + P["seccion"] + " acostada\nunion a media madera al centro")
    D.leader((rx(I["cx1"]), Z_INF + 12), (rx(I["cx1"]) - 5, 40), "MONTANTE " + P["seccion"])
    D.leader((rx(ANCHO - w / 2), 30), (rx(ANCHO) + 25, 60), "PATA LATERAL 210 cm")

    # ---------------- alzado lateral
    OX_S = 700.0
    D.lines(hidden_line(full, SIDE), lambda p: (p[0] + OX_S, p[1]))
    D.line("PISO", (OX_S - Lf / 2 - 20, 0), (OX_S + Lf / 2 + 30, 0))
    for i in range(7):
        x = OX_S - Lf / 2 - 17 + i * 18
        D.line("PISO", (x, 0), (x - 3, -3))
    sx = lambda y: OX_S + y
    D.dim((sx(yc - Lf / 2), 0), (sx(yc + Lf / 2), 0), -10)
    D.dim((sx(0), Z_INF), (sx(0), Z_SUP), 14, txt="122")
    D.dim((sx(0), 0), (sx(0), Z_INF), 14, txt="88")
    D.dim((sx(I["yx1"]), 0), (sx(I["yx1"]), Z_SUP), -30, txt="210")
    D.dim((sx(I["P2"][0]), 0), (sx(I["P2"][0]), zt), -(Lf / 2 + 8), fmt="{:.0f}")
    D.dim((sx(0), Z_SUP), (sx(I["yx1"]), Z_SUP), 6, fmt="{:.1f}", h=2.6)
    D.text("TEXTO", (sx(0), 240), 7, "ALZADO LATERAL", "center")
    D.text("TEXTO", (sx(0), 232), 3.5, "(visto desde la derecha)", "center")
    D.leader((sx(-T_TROV / 2), 180), (sx(-30), 195), "TROVISEL 6 mm\nPEGADO AL BASTIDOR")
    D.leader((sx(I["yx1"] - w / 2), 150), (sx(30), 165), "CRUZ TRASERA")
    D.leader((sx(yc), zt + 3), (sx(-35), 70), "TACO + PERNO\nPIVOTE TORNAPUNTA")
    D.leader((sx(I["P1"][0] - 3), 10), (sx(40), 40), "TORNAPUNTA\nTRASERA")
    D.leader((sx(yc - Lf / 2 + 5), d / 2), (sx(-45), 22), "PIE ABATIBLE " + "%.0f" % Lf + " cm")

    # ---------------- detalles isometricos
    details = []
    ISO_FL = view_basis((1, 1, -1))      # desde frente-izquierda-arriba
    ISO_BL = view_basis((1, -1, -1))     # desde atras-izquierda-arriba

    # D1 esquina superior: pata + travesano superior + trovisel + cruz
    reg = (-1, 32, -1, 30, 176, 211)
    off = {"trovisel": (0, -10, 0), "cruz": (0, 10, 0), "trav_sup": (6, 0, 0)}
    s1 = solids_from(M, ["trovisel", "pata_izq", "trav_sup", "cruz1"], reg, off)
    seg1 = hidden_line(s1, ISO_BL)
    lab1 = []
    pr = lambda p: project(p, ISO_BL)
    # pegamento sobre la cara trasera del trovisel
    glue = []
    for z in (Z_SUP - w / 2,):
        glue.append(((1.2, -10 + T_TROV, z), (31, -10 + T_TROV, z)))
    glue.append(((w / 2, -10 + T_TROV, Z_SUP - 1.2), (w / 2, -10 + T_TROV, 177)))
    ejes1 = [((-3, I["y0"] + d * 0.3, Z_SUP - w / 2), (6 + w + 5, I["y0"] + d * 0.3, Z_SUP - w / 2)),
             ((-3, I["y0"] + d * 0.7, Z_SUP - w / 2), (6 + w + 5, I["y0"] + d * 0.7, Z_SUP - w / 2)),
             ((3, -14, 200), (3, I["yx1"] + 14, 200)),
             ((14, -14, Z_SUP - w / 2), (14, -10 + T_TROV + 0.01, Z_SUP - w / 2))]
    lab1 = [((25, -10 + T_TROV, 190), (30, 25), "TROVISEL: adhesivo de montaje\n(poliuretano) en todo el contacto"),
            ((w / 2, I["y1"], 185), (-28, -10), "PATA " + P["seccion"]),
            ((25, I["y0"], Z_SUP), (-20, 26), "TRAVESANO SUPERIOR\na tope entre patas"),
            ((5, I["yx1"] + 10, 196), (-30, 28), "CRUZ TRASERA (separada)\natornillada a pata y travesano"),
            ((-3, I["y0"] + d * 0.3, Z_SUP - w / 2), (-34, 8), "2 tornillos " + P["tornillo"] + "\n+ pegamento blanco"),
            ((14, -14, Z_SUP - w / 2), (30, 22), "tornillo #8x1\" c/rondana\ncada 30 cm (perimetro)")]
    details.append(("DETALLE 1 - ESQUINA SUPERIOR (vista posterior, despiezada)",
                    seg1, ISO_BL, glue, ejes1, lab1))

    # D2 union en T montante / travesano central
    cx1, zc1 = I["cx1"], I["zc1"]
    reg = (cx1 - 14, cx1 + 18, I["y0"], I["y1"], zc1 - 16, zc1 + 16)
    s2 = solids_from(M, ["montante1", "trav_cen1"], reg, {"trav_cen1": (7, 0, 0)})
    seg2 = hidden_line(s2, ISO_FL)
    ejes2 = [((cx1 - w / 2 - 5, I["y0"] + d * f, zc1), (cx1 + w / 2 + 7 + 6, I["y0"] + d * f, zc1)) for f in (0.3, 0.7)]
    lab2 = [((cx1, I["y0"], zc1 + 12), (-30, 12), "MONTANTE"),
            ((cx1 + 15, I["y0"], zc1 + w / 2), (8, 22), "TRAVESANO INTERMEDIO\n(separado para ver la union)"),
            ((cx1 - w / 2 - 5, I["y0"] + d * 0.3, zc1), (-34, -18),
             "2 tornillos " + P["tornillo"] + "\ndesde el costado libre\ndel montante + pegamento")]
    details.append(("DETALLE 2 - UNION EN T MONTANTE / TRAVESANO", seg2, ISO_FL, [], ejes2, lab2))

    # D3 cruce a media madera de la cruz trasera (pieza 1 separada hacia atras)
    phi = 2 * math.atan2(ALTO, ANCHO)
    a1 = math.atan2(-ALTO, ANCHO)
    e1 = (math.cos(a1), 0, math.sin(a1))
    e2 = (-math.sin(a1), 0, math.cos(a1))
    e3 = (0, 1, 0)
    Lp, Wp, tp = 44.0, I["wx"], w
    cen = (ANCHO / 2, I["yx0"], Z_INF + ALTO / 2)
    o1 = sub(add(cen, (0, 8.0, 22.0)), mul(e1, Lp / 2))
    # cruz 1: caja hacia el frente (w=0) ; cruz 2: caja hacia atras (w=t)
    pA = notched_strip(o1, e1, e2, e3, Lp, Wp, tp, Lp / 2, phi, notch_top=False)
    a2 = math.atan2(ALTO, ANCHO)
    f1 = (math.cos(a2), 0, math.sin(a2))
    f2 = (-math.sin(a2), 0, math.cos(a2))
    o2 = sub(cen, mul(f1, Lp / 2))
    pB = notched_strip(o2, f1, f2, e3, Lp, Wp, tp, Lp / 2, -phi, notch_top=True)
    s3 = [Solid(pA), Solid(pB)]
    seg3 = hidden_line(s3, ISO_BL)
    ejes3 = [(add(cen, (0, -2, -5.5)), add(cen, (0, 8 + tp + 3, 22 + 3)))]
    lab3 = [(add(o1, mul(e1, 5)), (-25, 20), "CRUZ - PIEZA CONTINUA\n(caja hacia el frente)"),
            (add(o2, add(mul(f1, 6), (0, tp, 0))), (-34, -14), "CRUZ - PIEZA EN TRAMOS\no con caja hacia atras"),
            (add(cen, (0, tp, 0)), (30, -30),
             "caja a media madera (1/2 del grueso)\npegamento + 2 tornillos " + P["tornillo_x"])]
    details.append(("DETALLE 3 - CRUCE DE LA CRUZ A MEDIA MADERA", seg3, ISO_BL, [], ejes3, lab3))

    # D4 pie abatible + tornapunta (lado izquierdo, piezas separadas hacia afuera)
    reg = (-2 * w - 3, w + 3, -50, 60, 0, zt + 14)
    off = {"pie_izq": (-6, 0, 0), "taco_izq": (-6, 0, 0), "tornapunta_izq": (-12, 0, 0),
           "perno": (-22, 0, 0), "cabeza": (-22, 0, 0), "tuerca": (6, 0, 0)}
    names = ["pata_izq", "pie_izq", "taco_izq", "tornapunta_izq", "perno_pivote_izq", "perno_tp_sup_izq",
             "perno_tp_inf_izq", "cabeza_pivote_izq", "cabeza_tp_sup_izq", "cabeza_tp_inf_izq",
             "tuerca_pivote_izq", "tuerca_tp_sup_izq", "tuerca_tp_inf_izq"]
    s4 = solids_from(M, names, reg, off)
    seg4 = hidden_line(s4, ISO_FL)
    ejes4 = []
    for side, nm, py, pz in I["bolts"]:
        if side == "izq":
            ejes4.append(((-2 * w - 30, py, pz), (w + 8, py, pz)))
    P1, P2 = I["P1"], I["P2"]
    lab4 = [((w / 2, I["y0"], zt + 12), (14, 14), "PATA LATERAL"),
            ((-6 - w, yc - Lf / 2 + 6, d), (-12, -20), "PIE ABATIBLE %.0f cm (gira 90 grados\nsobre el perno para transporte)" % Lf),
            ((-6 - w, I["y0"], zt + 5), (-26, 16), "TACO SEPARADOR\n10 cm, pegado y\natornillado a la pata"),
            ((-12 - 2 * w, (P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2), (-50, 6), "TORNAPUNTA TRASERA\n(trabaja el pie a 90 grados)"),
            ((-2 * w - 22 - 0.5, yc, d / 2), (-24, -14),
             "PERNO COCHE " + P["perno"] + " c/ rondanas\ny tuerca mariposa (3 por lado)")]
    details.append(("DETALLE 4 - PIE ABATIBLE CON TORNAPUNTA (despiezado)", seg4, ISO_FL, [], ejes4, lab4))

    # colocar los detalles en una fila
    X0, Ytop = -20.0, -55.0
    slot = 280.0
    for k, (title, segs, view, glue, ejes, labs) in enumerate(details):
        xs = [c for _, p, q in segs for c in (p[0], q[0])]
        ys = [c for _, p, q in segs for c in (p[1], q[1])]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        sc = min(150.0 / bw, 150.0 / bh, 6.0)
        ox = X0 + k * slot + (slot - bw * sc) / 2 - min(xs) * sc
        oy = Ytop - 45 - (max(ys) * sc) + (150 - bh * sc) / 2 * 0
        T = lambda p, sc=sc, ox=ox, oy=oy: (p[0] * sc + ox, p[1] * sc + oy)
        D.lines(segs, T)
        for a, b in glue:
            D.line("PEGAMENTO", T(project(a, view)), T(project(b, view)))
        for a, b in ejes:
            D.line("EJES", T(project(a, view)), T(project(b, view)))
        for a3, (dx, dy), txt in labs:
            p = T(project(a3, view))
            D.leader(p, (p[0] + dx, p[1] + dy), txt, h=3.0)
        cxm = X0 + k * slot + slot / 2
        D.text("TEXTO", (cxm, Ytop - 2), 4.2, title, "center")
        D.text("TEXTO", (cxm, Ytop - 9), 3, "ISOMETRICO - SIN ESCALA", "center")
        D.line("TEXTO", (cxm - 105, Ytop - 4.5), (cxm + 105, Ytop - 4.5))

    # ---------------- lista de cortes y notas
    NX, NY = 820.0, 222.0
    rows = lista_cortes(P, I)
    D.text("TEXTO", (NX, NY), 5, "LISTA DE CORTES  -  madera " + P["seccion"], "left")
    D.line("TEXTO", (NX, NY - 3), (NX + 270, NY - 3))
    y = NY - 9
    D.text("TEXTO", (NX, y), 3.2, "PIEZA")
    D.text("TEXTO", (NX + 150, y), 3.2, "CANT.")
    D.text("TEXTO", (NX + 180, y), 3.2, "LARGO (cm)")
    D.text("TEXTO", (NX + 225, y), 3.2, "CORTE")
    y -= 3
    D.line("TEXTO", (NX, y), (NX + 270, y))
    total = 0.0
    for nm, n, L, corte in rows:
        y -= 6
        D.text("TEXTO", (NX, y), 3.2, nm)
        D.text("TEXTO", (NX + 155, y), 3.2, str(n))
        D.text("TEXTO", (NX + 185, y), 3.2, "%.1f" % L)
        D.text("TEXTO", (NX + 225, y), 3.2, corte)
        total += n * L
    y -= 4
    D.line("TEXTO", (NX, y), (NX + 270, y))
    y -= 6
    D.text("TEXTO", (NX, y), 3.2, "TOTAL LINEAL APROX.: %.1f m  (comprar %d tramos de 2.44 m o %d de 3.66 m incl. desperdicio)"
           % (total / 100, math.ceil(total * 1.12 / 244), math.ceil(total * 1.12 / 366)))
    y -= 14
    notas = [
        "NOTAS",
        "1. Cotas en centimetros. Medidas de madera nominales " + P["seccion"] + "; verificar la medida real",
        "   del polin y ajustar los largos (el bastidor siempre mide 244 x 122 al exterior).",
        "2. Trovisel (PVC espumado) de 122 x 244, 6 mm. Va PEGADO al frente del bastidor con adhesivo",
        "   de montaje / poliuretano en todos los miembros, mas tornillo #8 x 1\" con rondana cada 30 cm",
        "   en el perimetro (sin apretar de mas para no hundir el PVC).",
        "3. Bastidor: uniones a tope con pegamento blanco + 2 tornillos " + P["tornillo"] + " con barreno guia.",
        "   Los travesanos intermedios estan alternados (alturas distintas) para poder atornillar de frente.",
        "4. Cruz trasera: 2 diagonales acostadas detras del bastidor, unidas a media madera en el centro y",
        "   atornilladas (" + P["tornillo_x"] + ") a cada pata, travesano y montante que cruzan. Cortar las puntas",
        "   presentando la pieza sobre el bastidor armado.",
        "5. Patas en los costados = largueros laterales del bastidor, del piso a 210 cm.",
        "6. Pie abatible por lado: gira sobre un perno coche " + P["perno"] + " con tuerca mariposa (pivote). La tornapunta",
        "   trasera gira sobre el perno del taco y se fija al pie con otro perno: asi el pie queda a 90 grados.",
        "   Para transporte: quitar el perno inferior de la tornapunta, subirla y girar el pie.",
        "7. En exterior: lastrar o anclar los pies (costales de arena / taquetes) por efecto del viento.",
        "8. Sellar / pintar la madera antes de pegar el trovisel.",
    ]
    for i, t in enumerate(notas):
        D.text("TEXTO", (NX, y - i * 5.6), 4 if i == 0 else 3.0, t)

    # ---------------- marco y cuadro de titulo
    bx0, by0, bx1, by1 = D.bbox()
    bx0, by0, bx1, by1 = bx0 - 12, by0 - 40, max(bx1, NX + 280) + 12, by1 + 10
    D.rect("MARCO", bx0, by0, bx1, by1)
    D.rect("MARCO", bx0 + 3, by0 + 3, bx1 - 3, by1 - 3)
    tx0 = bx1 - 3 - 300
    D.rect("MARCO", tx0, by0 + 3, bx1 - 3, by0 + 33)
    D.text("TEXTO", (tx0 + 5, by0 + 23), 5.5, "ESTRUCTURA PARA TROVISEL 122 x 244")
    D.text("TEXTO", (tx0 + 5, by0 + 15), 4.2, P["nombre"])
    D.text("TEXTO", (tx0 + 5, by0 + 8), 3, "Inferior a 88 cm / superior a 210 cm del piso  -  Unidades: cm  -  Lamina %s" % key)
    D.text("TEXTO", (bx0 + 8, by0 + 8), 3, "Vistas generadas por generar_planos.py (modelo 3D con lineas ocultas eliminadas)")

    base = os.path.join(outdir, "trovisel_122x244_%s" % key)
    D.to_dxf(base + ".dxf")
    D.to_svg(base + ".svg")
    return base, rows


def lista_cortes(P, I):
    w = I["w"]
    cx1 = I["cx1"]
    wx = I["wx"]
    a1, b1 = (0.0, Z_SUP), (ANCHO, Z_INF)
    lx = poly_len(I["x1poly"], a1, b1)
    lb = poly_len(I["brace"], I["P2"], I["P1"])
    return [
        ("Pata lateral (larguero del bastidor)", 2, Z_SUP, "recto"),
        ("Travesano superior e inferior", 2, ANCHO - 2 * w, "recto"),
        ("Montante", 2, ALTO - 2 * w, "recto"),
        ("Travesano intermedio lateral", 2, cx1 - w / 2 - w, "recto"),
        ("Travesano intermedio central", 2, ANCHO / 3 - w, "recto"),
        ("Diagonal de la cruz (pieza continua)", 1, lx, "puntas a 26.6/63.4 grados"),
        ("Diagonal de la cruz (2 tramos)", 2, (lx - wx / math.sin(2 * math.atan2(ALTO, ANCHO))) / 2,
         "un extremo a inglete"),
        ("Pie abatible", 2, I["Lf"], "recto"),
        ("Tornapunta trasera", 2, lb, "puntas segun plantilla"),
        ("Taco separador", 2, 10.0, "recto"),
    ]


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(outdir, exist_ok=True)
    for key, P in VERSIONES.items():
        base, rows = make_sheet(key, P, outdir)
        print("generado:", base + ".dxf")
        for r in rows:
            print("   %-40s %d x %6.1f cm" % r[:3])


if __name__ == "__main__":
    main()
