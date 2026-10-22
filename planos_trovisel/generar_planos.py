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
    "RELLENO": (7, "CONTINUOUS"),
    "MADERA": (7, "CONTINUOUS"),
    "TUBO": (8, "CONTINUOUS"),
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
# RGB aproximado de los colores ACI usados en rellenos (solo para la vista previa)
ACI_RGB = {150: "#007fff", 151: "#7fbfff", 140: "#00bfff", 141: "#7fdfff",
           41: "#ffdf7f", 43: "#ccb266", 51: "#ffff7f", 33: "#cca566",
           250: "#333333", 251: "#505050", 252: "#696969", 253: "#828282",
           30: "#ff7f00", 32: "#cc6600", 254: "#bebebe", 8: "#808080", 9: "#c0c0c0"}


def triangulate(poly):
    """Triangulacion por recorte de orejas (poligonos simples)."""
    pts = list(poly)
    if signed_area(pts) < 0:
        pts = pts[::-1]
    tris = []
    guard = 0
    while len(pts) > 3 and guard < 1000:
        guard += 1
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if cross2(sub2(b, a), sub2(c, b)) <= 1e-12:
                continue
            if any(point_in_poly_strict(p, [a, b, c]) for p in pts if p not in (a, b, c)):
                continue
            tris.append((a, b, c))
            pts.pop(i)
            break
        else:
            break
    if len(pts) >= 3:
        for i in range(1, len(pts) - 1):
            tris.append((pts[0], pts[i], pts[i + 1]))
    return tris


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

    def fill(self, pts, aci):
        self.items.append(("fill", "RELLENO", pts, aci))

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
            elif it[0] == "fill":
                xs += [p[0] for p in it[2]]
                ys += [p[1] for p in it[2]]
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
            elif it[0] == "fill":
                _, layer, pts, aci = it
                for a, b, c in triangulate(pts):
                    g(0, "SOLID"); g(8, layer); g(62, aci)
                    for k, p in enumerate((a, b, c, c)):
                        g(10 + k, float(p[0])); g(20 + k, float(p[1])); g(30 + k, 0.0)
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
            if it[0] == "fill":
                pts = " ".join("%.3f,%.3f" % T(p) for p in it[2])
                c = ACI_RGB.get(it[3], "#ccc")
                o.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.05"/>' % (pts, c, c))
            elif it[0] == "line":
                p, q = T(it[2]), T(it[3])
                sw = 0.35 if layer in ("MADERA", "TUBO", "TROVISEL", "HERRAJES", "MARCO") else 0.2
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
    "V1": dict(nombre='VERSION 1 - MADERA (POLIN DE 1" x 1 1/2")', material="madera",
               w=1.0 * IN, d=1.5 * IN, seccion='polin 1" x 1 1/2" (2.54 x 3.81 cm)',
               pie=60.0, zt=57.0, perno='1/4"', perno_r=0.3175, cabeza_r=0.95,
               tornillo='#8 x 2" (5 cm)', tramo=244.0),
    "V2": dict(nombre='VERSION 2 - TUBULAR NEGRO (PTR 1" x 1 1/2")', material="tubo",
               w=1.0 * IN, d=1.5 * IN, seccion='PTR 1" x 1 1/2" cal. 16 negro',
               pie=60.0, zt=57.0, perno='1/4"', perno_r=0.3175, cabeza_r=0.95,
               tornillo='-', tramo=610.0, pared=0.15),
}

PALETAS = {  # color ACI de relleno segun la orientacion de la cara (x, y, z)
    "trovisel": (140, 150, 151),
    "madera": (43, 41, 51),
    "tubo": (251, 250, 252),
    "herraje": (32, 30, 30),
}
MATERIAL_CAPA = {"TROVISEL": "trovisel", "MADERA": "madera", "TUBO": "tubo", "HERRAJES": "herraje"}


def tube_walls(b, axis, t):
    """Divide un prisma rectangular en las 4 paredes de un tubo (extremos abiertos)."""
    lo = [b[0], b[2], b[4]]
    hi = [b[1], b[3], b[5]]
    a = "xyz".index(axis)
    i, j = [k for k in range(3) if k != a]
    walls = []
    for lo_i, hi_i, lo_j, hi_j in ((lo[i], lo[i] + t, lo[j], hi[j]),
                                   (hi[i] - t, hi[i], lo[j], hi[j]),
                                   (lo[i] + t, hi[i] - t, lo[j], lo[j] + t),
                                   (lo[i] + t, hi[i] - t, hi[j] - t, hi[j])):
        l2, h2 = list(lo), list(hi)
        l2[i], h2[i], l2[j], h2[j] = lo_i, hi_i, lo_j, hi_j
        walls.append((l2[0], h2[0], l2[1], h2[1], l2[2], h2[2]))
    return walls


def build_model(P):
    """Devuelve lista de (nombre, capa, spec) y datos utiles."""
    w, d = P["w"], P["d"]
    tb = T_TROV
    tubo = P["material"] == "tubo"
    capa = "TUBO" if tubo else "MADERA"
    tw = P.get("pared", 0.15)
    y0, y1 = tb, tb + d
    yc = tb + d / 2
    Lf, zt = P["pie"], P["zt"]
    zr = Z_INF + ALTO / 2
    xc = ANCHO / 2
    M = []

    def member(name, b, axis):
        if tubo:
            for k, bb in enumerate(tube_walls(b, axis, tw)):
                M.append(("%s#%d" % (name, k), capa, box(*bb)))
        else:
            M.append((name, capa, box(*b)))

    M.append(("trovisel", "TROVISEL", box(0, ANCHO, 0, tb, Z_INF, Z_SUP)))
    # patas laterales = largueros del bastidor, del piso a 210
    member("pata_izq", (0, w, y0, y1, 0, Z_SUP), "z")
    member("pata_der", (ANCHO - w, ANCHO, y0, y1, 0, Z_SUP), "z")
    member("trav_sup", (w, ANCHO - w, y0, y1, Z_SUP - w, Z_SUP), "x")
    member("trav_inf", (w, ANCHO - w, y0, y1, Z_INF, Z_INF + w), "x")
    # cruz de soporte: travesano medio + montante central
    zr0, zr1 = zr - w / 2, zr + w / 2
    xs0, xs1 = xc - w / 2, xc + w / 2
    if tubo:
        member("trav_med", (w, ANCHO - w, y0, y1, zr0, zr1), "x")
        member("montante_inf", (xs0, xs1, y0, y1, Z_INF + w, zr0), "z")
        member("montante_sup", (xs0, xs1, y0, y1, zr1, Z_SUP - w), "z")
    else:
        # media madera: travesano continuo al frente, montante continuo atras
        M += [("trav_med", capa, box(w, ANCHO - w, y0, yc, zr0, zr1)),
              ("trav_med_b1", capa, box(w, xs0, yc, y1, zr0, zr1)),
              ("trav_med_b2", capa, box(xs1, ANCHO - w, yc, y1, zr0, zr1)),
              ("montante", capa, box(xs0, xs1, yc, y1, Z_INF + w, Z_SUP - w)),
              ("montante_f1", capa, box(xs0, xs1, y0, yc, Z_INF + w, zr0)),
              ("montante_f2", capa, box(xs0, xs1, y0, yc, zr1, Z_SUP - w))]
    # pie hacia atras + taco + tornapunta, del lado interior de cada pata
    P1 = (y0 + Lf - 6, d / 2)
    P2 = (yc, zt)
    ext = d * 0.9
    u = sub2(P1, P2)
    ul = math.hypot(*u)
    u = (u[0] / ul, u[1] / ul)
    e1 = (P2[0] - u[0] * ext, P2[1] - u[1] * ext)
    e2 = (P1[0] + u[0] * ext, P1[1] + u[1] * ext)
    brace = clip_rect(strip_poly(e1, e2, d, ext=0), -30, y0 + Lf, 0, 300)
    nrm = (-u[1], u[0])
    def brace_band(sg):     # franja de pared del tubo a lo largo de un canto
        c = -(nrm[0] * P2[0] + nrm[1] * P2[1])
        return clean_poly(clip_halfplane(brace, sg * nrm[0], sg * nrm[1], sg * c - (d / 2 - tw)))
    bolts = []
    r, rh = P["perno_r"], P["cabeza_r"]
    for side, xl, sg in (("izq", 0.0, 1), ("der", ANCHO, -1)):
        def X(a):
            return xl + sg * a
        def rng(a, b):
            return (min(X(a), X(b)), max(X(a), X(b)))
        fx, bx = rng(w, 2 * w), rng(2 * w, 3 * w)
        member("pie_" + side, (fx[0], fx[1], y0, y0 + Lf, 0, d), "y")
        member("taco_" + side, (fx[0], fx[1], y0, y1, zt - 4, zt + 4), "y")
        if tubo:
            M.append(("tornapunta_%s#0" % side, capa, ("pyz", brace, bx[0], bx[0] + tw)))
            M.append(("tornapunta_%s#1" % side, capa, ("pyz", brace, bx[1] - tw, bx[1])))
            M.append(("tornapunta_%s#2" % side, capa, ("pyz", brace_band(1), bx[0] + tw, bx[1] - tw)))
            M.append(("tornapunta_%s#3" % side, capa, ("pyz", brace_band(-1), bx[0] + tw, bx[1] - tw)))
        else:
            M.append(("tornapunta_" + side, capa, ("pyz", brace, bx[0], bx[1])))
        # pernos: (nombre, centro y-z, cara donde apoya la cabeza, cara donde va la tuerca)
        for nm, (py, pz), a_head, a_nut in (("pivote", (yc, d / 2), 0.0, 2 * w),
                                            ("tp_sup", P2, 0.0, 3 * w),
                                            ("tp_inf", P1, w, 3 * w)):
            c0, c1 = sorted((X(a_head - 0.5), X(a_nut + 1.2)))
            M.append(("perno_%s_%s" % (nm, side), "HERRAJES", ("cyl", "x", (0, py, pz), r, c0, c1, 16)))
            h0, h1 = sorted((X(a_head - 0.5), X(a_head)))
            M.append(("cabeza_%s_%s" % (nm, side), "HERRAJES", ("cyl", "x", (0, py, pz), rh, h0, h1, 16)))
            n0, n1 = sorted((X(a_nut + 0.2), X(a_nut + 0.9)))
            M.append(("tuerca_%s_%s" % (nm, side), "HERRAJES", ("cyl", "x", (0, py, pz), rh * 0.95, n0, n1, 6)))
            bolts.append((side, nm, py, pz))
    info = dict(w=w, d=d, yc=yc, y0=y0, y1=y1, Lf=Lf, zt=zt, zr=zr, xc=xc,
                brace=brace, P1=P1, P2=P2, bolts=bolts, tubo=tubo)
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
        s = Solid(polys, layer, smooth=(spec[0] == "cyl" and spec[6] > 8))
        s.material = MATERIAL_CAPA[layer]
        out.append(s)
    return out


def fills(solids, view):
    """Caras visibles con su color, ordenadas de atras hacia adelante (pintor)."""
    R, U, V = view
    items = []
    for s in solids:
        pal = PALETAS[getattr(s, "material", "madera")]
        for f in s.faces:
            if dot(f.n, V) > -1e-6:
                continue
            poly = [(dot(p, R), dot(p, U)) for p in f.pts]
            if abs(signed_area(poly)) < 1e-6:
                continue
            depth = sum(dot(p, V) for p in f.pts) / len(f.pts)
            ax = max(range(3), key=lambda i: abs(f.n[i]))
            items.append((depth, poly, pal[ax]))
    items.sort(key=lambda t: -t[0])
    return [(p, c) for _, p, c in items]


def add_view(D, solids, view, T):
    for poly, col in fills(solids, view):
        D.fill([T(p) for p in poly], col)
    D.lines(hidden_line(solids, view), T)


def poly_len(poly, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dz)
    pr = [((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L for p in poly]
    return max(pr) - min(pr)


# ------------------------------------------------- pieza a media madera
def notched_strip(o, e1, e2, e3, L, W, t, uc, notch_top=True):
    """Pieza recta (largo L, ancho W, grueso t) con caja a media madera de
    ancho W centrada en uc, en la cara w=t (notch_top) o en w=0."""
    def P(u, v, w):
        if not notch_top:
            w = t - w
        return add(o, add(mul(e1, u), add(mul(e2, v), mul(e3, w))))
    ua, ub = uc - W / 2, uc + W / 2
    h = t / 2
    m, M_ = -W / 2, W / 2
    return [
        [P(0, m, 0), P(L, m, 0), P(L, M_, 0), P(0, M_, 0)],
        [P(0, m, t), P(ua, m, t), P(ua, M_, t), P(0, M_, t)],
        [P(ub, m, t), P(L, m, t), P(L, M_, t), P(ub, M_, t)],
        [P(ua, m, h), P(ub, m, h), P(ub, M_, h), P(ua, M_, h)],
        [P(ua, m, h), P(ua, M_, h), P(ua, M_, t), P(ua, m, t)],
        [P(ub, m, h), P(ub, M_, h), P(ub, M_, t), P(ub, m, t)],
        [P(0, m, 0), P(L, m, 0), P(L, m, t), P(ub, m, t), P(ub, m, h), P(ua, m, h), P(ua, m, t), P(0, m, t)],
        [P(0, M_, 0), P(L, M_, 0), P(L, M_, t), P(ub, M_, t), P(ub, M_, h), P(ua, M_, h), P(ua, M_, t), P(0, M_, t)],
        [P(0, m, 0), P(0, M_, 0), P(0, M_, t), P(0, m, t)],
        [P(L, m, 0), P(L, M_, 0), P(L, M_, t), P(L, m, t)],
    ]


def solid_mat(polys, layer):
    s = Solid(polys, layer)
    s.material = MATERIAL_CAPA[layer]
    return s


# ------------------------------------------------------------- laminas
def piso(D, x0, x1):
    D.line("PISO", (x0, 0), (x1, 0))
    n = int((x1 - x0) / 21)
    for i in range(n + 1):
        x = x0 + 3 + i * 21
        D.line("PISO", (x, 0), (x - 3, -3))


def make_sheet(key, P, outdir):
    M, I = build_model(P)
    w, d, yc, Lf, zt, y0, y1 = I["w"], I["d"], I["yc"], I["Lf"], I["zt"], I["y0"], I["y1"]
    tubo = I["tubo"]
    D = Drawing()
    full = solids_from(M)
    FRONT = view_basis((0, 1, 0))
    REAR = view_basis((0, -1, 0))
    SIDE = view_basis((-1, 0, 0))
    estructura = "tubular negro" if tubo else "madera"

    # ---------------- alzado frontal
    add_view(D, full, FRONT, lambda p: p)
    piso(D, -25, ANCHO + 25)
    D.text("TEXTO", (ANCHO / 2, 152), 6, "TROVISEL 122 x 244", "center")
    D.text("TEXTO", (ANCHO / 2, 142), 3.5, "(PVC espumado 6 mm, color azul, pegado al bastidor)", "center")
    D.dim((0, Z_SUP), (ANCHO, Z_SUP), 10)
    D.dim((0, 0), (0, Z_INF), 12)
    D.dim((0, Z_INF), (0, Z_SUP), 12)
    D.dim((ANCHO, 0), (ANCHO, Z_SUP), -12)
    D.text("TEXTO", (ANCHO / 2, 240), 7, "ALZADO FRONTAL", "center")
    D.text("TEXTO", (ANCHO / 2, 232), 3.5, "Estructura total 244 x 210 cm", "center")

    # ---------------- alzado posterior
    OX_R = 330.0 + ANCHO
    rx = lambda x: OX_R - x
    add_view(D, full, REAR, lambda p: (p[0] + OX_R, p[1]))
    piso(D, rx(ANCHO) - 25, rx(0) + 25)
    D.dim((rx(ANCHO), Z_SUP), (rx(I["xc"]), Z_SUP), 10)
    D.dim((rx(I["xc"]), Z_SUP), (rx(0), Z_SUP), 10)
    D.dim((rx(ANCHO), Z_INF), (rx(ANCHO), I["zr"]), 10)
    D.dim((rx(ANCHO), I["zr"]), (rx(ANCHO), Z_SUP), 10)
    D.dim((rx(0), 0), (rx(0), Z_INF), -10)
    D.text("TEXTO", (rx(ANCHO / 2), 240), 7, "ALZADO POSTERIOR", "center")
    D.text("TEXTO", (rx(ANCHO / 2), 232), 3.5, "Bastidor visto por detras: perimetro + cruz de soporte", "center")
    D.leader((rx(ANCHO * 0.6), I["zr"]), (rx(ANCHO * 0.6) + 15, 62),
             "CRUZ DE SOPORTE\n(travesano medio + montante central)\n" + P["seccion"])
    D.leader((rx(I["xc"]), Z_INF + 15), (rx(I["xc"]) + 10, 22), "MONTANTE CENTRAL")
    D.leader((rx(ANCHO - w / 2), 30), (rx(ANCHO) + 30, 72), "PATA LATERAL 210 cm")
    D.leader((rx(2.5 * w), 25), (rx(-22), 50), "PIE + TORNAPUNTA\n(lado interior)")

    # ---------------- alzado lateral
    OX_S = 700.0
    sx = lambda y: OX_S + y
    add_view(D, full, SIDE, lambda p: (p[0] + OX_S, p[1]))
    piso(D, sx(-25), sx(Lf + 30))
    D.dim((sx(y0), 0), (sx(y0 + Lf), 0), -10)
    D.dim((sx(-3), 0), (sx(-3), Z_INF), 12)
    D.dim((sx(-3), Z_INF), (sx(-3), Z_SUP), 12)
    D.dim((sx(y0 + Lf), 0), (sx(y0 + Lf), Z_SUP), -14)
    D.dim((sx(yc), 0), (sx(yc), zt), -(Lf - 8), fmt="{:.0f}")
    D.dim((sx(0), Z_SUP), (sx(y1), Z_SUP), 6, h=2.6)
    D.text("TEXTO", (sx(Lf / 2 - 10), 240), 7, "ALZADO LATERAL", "center")
    D.text("TEXTO", (sx(Lf / 2 - 10), 232), 3.5, "(visto desde la derecha)", "center")
    D.leader((sx(T_TROV / 2), 180), (sx(25), 195), "TROVISEL 6 mm\nPEGADO AL BASTIDOR")
    D.leader((sx(yc), 130), (sx(25), 140), "PATA " + ("PTR" if tubo else "POLIN"))
    D.leader((sx(yc), zt), (sx(-38), 75), "PERNO PIVOTE\nTORNAPUNTA")
    D.leader((sx(yc), d / 2), (sx(-38), 25), "PERNO PIVOTE PIE")
    D.leader((sx(I["P1"][0] - 12), 18), (sx(Lf - 5), 45), "TORNAPUNTA")
    D.leader((sx(Lf - 15), d / 2), (sx(Lf - 5), 18), "PIE %.0f cm" % Lf)

    # ---------------- detalles isometricos
    ISO_BL = view_basis((1, -1, -1))     # desde atras-izquierda-arriba
    ISO_FRI = view_basis((-1, 1, -1))    # desde frente-derecha-arriba (cara interior pata izq.)
    details = []

    # D1 esquina superior
    reg = (-1, 32, -1, 12, 176, 211)
    s1 = solids_from(M, ["trovisel", "pata_izq", "trav_sup"], reg,
                     {"trovisel": (0, -10, 0), "trav_sup": (6, 0, 0)})
    yb = -10 + T_TROV
    glue = [((1.2, yb, Z_SUP - w / 2), (31, yb, Z_SUP - w / 2)),
            ((w / 2, yb, Z_SUP - 1.2), (w / 2, yb, 177))]
    ejes = [((14, -14, Z_SUP - w / 2), (14, yb + 0.01, Z_SUP - w / 2))]
    if tubo:
        lab = [((w + 3, y0, Z_SUP - w), (-30, 26), "SOLDADURA a tope en\ntodo el contorno (MIG)"),
               ((w / 2, y0, Z_SUP), (-45, -22), "TAPON PLASTICO\nen extremo abierto")]
        fij = "pija autoperforante c/rondana\ncada 30 cm (perimetro)"
    else:
        ejes += [((-3, y0 + d * f, Z_SUP - w / 2), (6 + w + 5, y0 + d * f, Z_SUP - w / 2)) for f in (0.3, 0.7)]
        lab = [((-3, y0 + d * 0.3, Z_SUP - w / 2), (-34, 8), "2 tornillos " + P["tornillo"] + "\n+ pegamento blanco"),
               ((25, y0, Z_SUP), (-20, 26), "TRAVESANO SUPERIOR\na tope entre patas")]
        fij = "tornillo #8x1\" c/rondana\ncada 30 cm (perimetro)"
    lab += [((25, yb, 190), (30, 25), "TROVISEL: adhesivo poliuretano\n(o cinta doble cara VHB) en todo el contacto"),
            ((w / 2, y1, 185), (-28, -10), "PATA " + P["seccion"]),
            ((14, -14, Z_SUP - w / 2), (30, 22), fij)]
    details.append(("DETALLE 1 - ESQUINA SUPERIOR (vista posterior, despiezada)", s1, ISO_BL, glue, ejes, lab))

    # D2 centro de la cruz
    xc, zr = I["xc"], I["zr"]
    L2 = 36.0
    capa = "TUBO" if tubo else "MADERA"
    if tubo:
        reg = (xc - L2 / 2, xc + L2 / 2, -1, 10, zr - L2 / 2, zr + L2 / 2)
        s2 = solids_from(M, ["trav_med", "montante"], reg,
                         {"montante_sup": (0, 0, 6), "montante_inf": (0, 0, -6)})
        ejes = []
        lab = [((xc + 14, y1, zr), (20, 22), "TRAVESANO MEDIO CONTINUO"),
               ((xc, y1, zr + 14), (-34, 16), "MONTANTE EN 2 TRAMOS\nsoldado arriba y abajo\ndel travesano"),
               ((xc + w / 2, y1, zr - w / 2), (18, -24), "cordon de soldadura\nen las 4 caras")]
    else:
        s2 = [solid_mat(notched_strip((xc - L2 / 2, y0, zr), X_, Z_, Y_, L2, w, d, L2 / 2, True), capa),
              solid_mat(notched_strip((xc, y0 + 22, zr - L2 / 2), Z_, X_, Y_, L2, w, d, L2 / 2, False), capa)]
        ejes = [((xc, y0 - 3, zr), (xc, y0 + 22 + d + 4, zr))]
        lab = [((xc + 14, y1, zr), (20, -22), "TRAVESANO MEDIO\n(caja atras, 1/2 del grueso)"),
               ((xc, y0 + 22 + d, zr + 14), (-34, 14), "MONTANTE CENTRAL\n(caja al frente, 1/2 del grueso)"),
               ((xc, y0 + 22 + d + 4, zr), (-30, -30), "pegamento + 2 tornillos\n#8 x 1 1/4\" en el cruce")]
    details.append(("DETALLE 2 - CENTRO DE LA CRUZ " + ("(soldado)" if tubo else "A MEDIA MADERA"),
                    s2, ISO_BL, [], ejes, lab))

    # D3 travesano medio contra la pata
    reg = (-1, 26, -1, 10, zr - 12, zr + 12)
    s3 = solids_from(M, ["pata_izq", "trav_med"], reg, {"trav_med": (6, 0, 0)})
    if tubo:
        ejes = []
        lab = [((w + 6, y1, zr), (20, 22), "SOLDADURA a tope\nen todo el contorno")]
    else:
        ejes = [((-4, y0 + d * f, zr), (w + 6 + 6, y0 + d * f, zr)) for f in (0.3, 0.7)]
        lab = [((-4, y0 + d * 0.3, zr), (-30, -16), "2 tornillos " + P["tornillo"] + "\ndesde el costado de la pata\n+ pegamento blanco")]
    lab += [((w / 2, y1, zr + 10), (30, 30), "PATA"),
            ((20, y1, zr + w / 2), (14, 20), "TRAVESANO MEDIO\n(separado para ver la union)")]
    details.append(("DETALLE 3 - TRAVESANO MEDIO CON PATA", s3, ISO_BL, [], ejes, lab))

    # D4 pie + tornapunta (pata izquierda, cara interior, piezas separadas)
    reg = (-2, 3 * w + 3, -20, Lf + 5, 0, zt + 12)
    names = ["pata_izq", "pie_izq", "taco_izq", "tornapunta_izq", "perno_", "cabeza_", "tuerca_"]
    off = {"pie_izq": (6, 0, 0), "taco_izq": (6, 0, 0), "tornapunta_izq": (12, 0, 0),
           "perno": (-14, 0, 0), "cabeza": (-14, 0, 0), "tuerca": (20, 0, 0)}
    s4 = solids_from(M, names, reg, off)
    s4 = [s for s in s4 if s.layer != "HERRAJES" or
          max(p[0] for f in s.faces for p in f.pts) < ANCHO / 2]
    ejes = [((-20, py, pz), (3 * w + 24, py, pz)) for side, nm, py, pz in I["bolts"] if side == "izq"]
    P1, P2 = I["P1"], I["P2"]
    lab = [((w / 2, y0, zt + 10), (-24, 10), "PATA LATERAL"),
           ((6 + 2 * w, y0 + Lf - 10, d), (10, -16), "PIE %.0f cm hacia atras\n(gira sobre el perno para guardar)" % Lf),
           ((6 + 2 * w, y0, zt + 4), (-34, 18), "TACO SEPARADOR 8 cm\n" + ("soldado a la pata" if tubo else "pegado y atornillado")),
           ((12 + 3 * w, (P1[0] + P2[0]) / 2, (P1[1] + P2[1]) / 2), (22, 12), "TORNAPUNTA"),
           ((-14.5, yc, d / 2), (-24, -14), "PERNO " + P["perno"] + " c/ rondanas y\ntuerca mariposa (3 por lado)")]
    details.append(("DETALLE 4 - PIE Y TORNAPUNTA (despiezado)", s4, ISO_FRI, [], ejes, lab))

    X0, Ytop = -20.0, -55.0
    slot = 280.0
    for k, (title, sol, view, glue, ejes, labs) in enumerate(details):
        segs = hidden_line(sol, view)
        xs = [c for _, p, q in segs for c in (p[0], q[0])]
        ys = [c for _, p, q in segs for c in (p[1], q[1])]
        bw, bh = max(xs) - min(xs), max(ys) - min(ys)
        sc = min(150.0 / bw, 150.0 / bh, 6.0)
        ox = X0 + k * slot + (slot - bw * sc) / 2 - min(xs) * sc
        oy = Ytop - 45 - max(ys) * sc
        T = lambda p, sc=sc, ox=ox, oy=oy: (p[0] * sc + ox, p[1] * sc + oy)
        for poly, col in fills(sol, view):
            D.fill([T(p) for p in poly], col)
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
        D.line("TEXTO", (cxm - 110, Ytop - 4.5), (cxm + 110, Ytop - 4.5))

    # ---------------- lista de cortes y notas
    NX, NY = 830.0, 222.0
    rows = lista_cortes(P, I)
    D.text("TEXTO", (NX, NY), 5, "LISTA DE CORTES - " + P["seccion"])
    D.line("TEXTO", (NX, NY - 3), (NX + 270, NY - 3))
    y = NY - 9
    for x, t in ((0, "PIEZA"), (150, "CANT."), (180, "LARGO (cm)"), (220, "NOTA")):
        D.text("TEXTO", (NX + x, y), 3.2, t)
    y -= 3
    D.line("TEXTO", (NX, y), (NX + 270, y))
    total = 0.0
    for nm, n, L, nota in rows:
        y -= 6
        D.text("TEXTO", (NX, y), 3.2, nm)
        D.text("TEXTO", (NX + 155, y), 3.2, str(n))
        D.text("TEXTO", (NX + 185, y), 3.2, "%.1f" % L)
        D.text("TEXTO", (NX + 220, y), 3.2, nota)
        total += n * L
    y -= 4
    D.line("TEXTO", (NX, y), (NX + 270, y))
    y -= 6
    D.text("TEXTO", (NX, y), 3.2, "TOTAL LINEAL APROX.: %.1f m  (%d tramos de %.2f m, con 10%% de desperdicio)"
           % (total / 100, math.ceil(total * 1.1 / P["tramo"]), P["tramo"] / 100))
    y -= 14
    if tubo:
        uniones = [
            "3. Bastidor soldado (MIG o electrodo 6013) a tope en todo el contorno; esmerilar y",
            "   pintar con primario + esmalte NEGRO. Tapones plasticos en extremos abiertos.",
            "4. Cruz de soporte: travesano medio continuo; montante central en 2 tramos soldados",
            "   arriba y abajo del travesano.",
            "5. Trovisel: adhesivo de poliuretano (o cinta VHB) sobre todo el bastidor + pija",
            "   autoperforante con rondana cada 30 cm en el perimetro.",
        ]
    else:
        uniones = [
            "3. Bastidor: uniones a tope con pegamento blanco + 2 tornillos " + P["tornillo"] + " con",
            "   barreno guia. Sellar/pintar la madera antes de pegar el trovisel.",
            "4. Cruz de soporte: travesano medio y montante central unidos a media madera al centro",
            "   (caja de la mitad del grueso en cada pieza) con pegamento + 2 tornillos.",
            "5. Trovisel: adhesivo de montaje/poliuretano sobre todo el bastidor + tornillo #8 x 1\"",
            "   con rondana cada 30 cm en el perimetro (sin apretar de mas).",
        ]
    notas = [
        "NOTAS",
        "1. Cotas en cm. Estructura total 244 x 210. Trovisel 122 x 244 de 88 a 210 cm del piso.",
        "2. Seccion: " + P["seccion"] + ". Verificar medida real y ajustar largos.",
    ] + uniones + [
        "6. Patas en los costados = largueros del bastidor, del piso a 210 cm.",
        "7. Pie por el lado interior de cada pata, hacia atras. Gira sobre perno " + P["perno"] + " (pivote);",
        "   la tornapunta va del taco al extremo del pie con pernos y tuerca mariposa.",
        "   Para guardar: quitar el perno inferior de la tornapunta y girar pie y tornapunta.",
        "8. El pie solo sale hacia atras: lastrar (costal de arena) o anclar al piso,",
        "   sobre todo en exterior por el viento.",
    ]
    for i, t in enumerate(notas):
        D.text("TEXTO", (NX, y - i * 5.6), 4 if i == 0 else 3.0, t)
    y -= len(notas) * 5.6 + 8
    D.text("TEXTO", (NX, y), 4, "COLORES")
    for i, (col, t) in enumerate(((150, "Trovisel (azul)"),
                                  (PALETAS["tubo" if tubo else "madera"][1], "Estructura (" + estructura + ")"),
                                  (30, "Pernos / herrajes"))):
        yy = y - 8 - i * 7
        D.fill([(NX, yy), (NX + 10, yy), (NX + 10, yy + 4.5), (NX, yy + 4.5)], col)
        D.rect("TEXTO", NX, yy, NX + 10, yy + 4.5)
        D.text("TEXTO", (NX + 14, yy + 0.8), 3.2, t)

    # ---------------- marco y cuadro de titulo
    bx0, by0, bx1, by1 = D.bbox()
    bx0, by0, bx1, by1 = bx0 - 12, by0 - 40, max(bx1, NX + 280) + 12, by1 + 10
    D.rect("MARCO", bx0, by0, bx1, by1)
    D.rect("MARCO", bx0 + 3, by0 + 3, bx1 - 3, by1 - 3)
    tx0 = bx1 - 3 - 300
    D.rect("MARCO", tx0, by0 + 3, bx1 - 3, by0 + 33)
    D.text("TEXTO", (tx0 + 5, by0 + 23), 5.5, "ESTRUCTURA PARA TROVISEL 122 x 244")
    D.text("TEXTO", (tx0 + 5, by0 + 15), 4.2, P["nombre"])
    D.text("TEXTO", (tx0 + 5, by0 + 8), 3, "Total 244 x 210 cm / trovisel de 88 a 210 cm  -  Unidades: cm  -  Lamina %s" % key)
    D.text("TEXTO", (bx0 + 8, by0 + 8), 3, "Vistas generadas por generar_planos.py (modelo 3D, lineas ocultas eliminadas)")

    base = os.path.join(outdir, "trovisel_122x244_%s" % key)
    D.to_dxf(base + ".dxf")
    D.to_svg(base + ".svg")
    return base, rows


def lista_cortes(P, I):
    w = I["w"]
    lb = poly_len(I["brace"], I["P2"], I["P1"])
    rows = [
        ("Pata lateral", 2, Z_SUP, "del piso a 210"),
        ("Travesano superior e inferior", 2, ANCHO - 2 * w, "entre patas"),
        ("Travesano medio (cruz)", 1, ANCHO - 2 * w, "entre patas"),
    ]
    if I["tubo"]:
        rows.append(("Montante central (cruz), 2 tramos", 2, (ALTO - 3 * w) / 2, "arriba/abajo del medio"))
    else:
        rows.append(("Montante central (cruz)", 1, ALTO - 2 * w, "media madera al centro"))
    rows += [
        ("Pie", 2, I["Lf"], "hacia atras"),
        ("Tornapunta", 2, lb, "puntas a inglete"),
        ("Taco separador", 2, 8.0, ""),
    ]
    return rows


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
