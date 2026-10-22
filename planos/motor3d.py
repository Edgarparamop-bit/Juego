"""Motor mínimo de proyección con eliminación de líneas ocultas para DXF.

Los sólidos son poliedros convexos (prismas). Cada vista proyecta las caras
visibles, resta las porciones tapadas por caras más cercanas y dibuja en el
DXF los rellenos (HATCH) y los contornos (LWPOLYLINE) resultantes.
"""
import math

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, Point
from shapely.ops import unary_union

EPS_AREA = 1e-7


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


class Solido:
    def __init__(self, caras, color, nombre="", patron=None, decor=None):
        self.caras = [np.asarray(c, dtype=float) for c in caras]
        self.color = color
        self.nombre = nombre
        self.patron = patron
        # decor: lista de (indice_cara, poligono3d) dibujada dentro de la cara
        self.decor = decor or []
        centro = np.mean(np.vstack(self.caras), axis=0)
        self.normales = []
        for c in self.caras:
            n = np.zeros(3)
            for i in range(len(c)):
                a, b = c[i], c[(i + 1) % len(c)]
                n += np.cross(a, b)
            n = unit(n)
            if np.dot(n, c.mean(axis=0) - centro) < 0:
                n = -n
            self.normales.append(n)


def prisma(base, vec, color, nombre="", patron=None):
    base = [np.asarray(p, dtype=float) for p in base]
    vec = np.asarray(vec, dtype=float)
    tapa = [p + vec for p in base]
    caras = [base, tapa]
    n = len(base)
    for i in range(n):
        j = (i + 1) % n
        caras.append([base[i], base[j], tapa[j], tapa[i]])
    return Solido(caras, color, nombre, patron)


def caja(x0, x1, y0, y1, z0, z1, color, nombre="", patron=None, tubo=None):
    """Caja alineada a ejes. tubo=(eje, espesor) agrega el hueco del PTR en los extremos."""
    s = prisma([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
               (0, 0, z1 - z0), color, nombre, patron)
    if tubo:
        eje, e = tubo
        lim = {"x": (x0, x1), "y": (y0, y1), "z": (z0, z1)}
        for idx, (c, n) in enumerate(zip(s.caras, s.normales)):
            k = "xyz".index(eje)
            if abs(abs(n[k]) - 1) < 1e-9:
                pos = c[0][k]
                otros = [a for a in "xyz" if a != eje]
                (a0, a1), (b0, b1) = lim[otros[0]], lim[otros[1]]
                pts = []
                for a, b in [(a0 + e, b0 + e), (a1 - e, b0 + e), (a1 - e, b1 - e), (a0 + e, b1 - e)]:
                    p = [0, 0, 0]
                    p[k] = pos
                    p["xyz".index(otros[0])] = a
                    p["xyz".index(otros[1])] = b
                    pts.append(p)
                s.decor.append((idx, np.array(pts, dtype=float)))
    return s


def cilindro(c, eje, r, largo, color, nombre="", lados=12):
    c = np.asarray(c, dtype=float)
    a = unit(eje)
    tmp = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = unit(np.cross(a, tmp))
    e2 = np.cross(a, e1)
    base = [c + r * (math.cos(2 * math.pi * i / lados) * e1 + math.sin(2 * math.pi * i / lados) * e2)
            for i in range(lados)]
    return prisma(base, a * largo, color, nombre)


def soldadura(p0, p1, d1, d2, cateto, color=(70, 70, 70)):
    """Cordón de filete triangular a lo largo de p0-p1, catetos en direcciones d1 y d2."""
    p0 = np.asarray(p0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    base = [p0, p0 + cateto * unit(d1), p0 + cateto * unit(d2)]
    return prisma(base, p1 - p0, color, "soldadura")


class Vista:
    def __init__(self, V, escala=1.0, origen=(0, 0)):
        self.V = unit(V)
        f = -self.V
        z = np.array([0, 0, 1.0])
        if abs(np.dot(f, z)) > 0.999:
            z = np.array([0, 1.0, 0])
        self.R = unit(np.cross(f, z))
        self.U = np.cross(self.R, f)
        self.k = escala
        self.o = np.asarray(origen, dtype=float)

    def p2(self, P):
        P = np.asarray(P, dtype=float)
        return (self.k * np.dot(P, self.R) + self.o[0], self.k * np.dot(P, self.U) + self.o[1])

    def prof(self, n, d, uv):
        u = (uv[0] - self.o[0]) / self.k
        v = (uv[1] - self.o[1]) / self.k
        return (d - u * np.dot(n, self.R) - v * np.dot(n, self.U)) / np.dot(n, self.V)


def _polis(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g] if g.area > EPS_AREA else []
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        out = []
        for h in g.geoms:
            out += _polis(h)
        return out
    return []


def resolver(solidos, vista):
    """Devuelve lista de (poligono_visible, solido, normal, decor_visibles)."""
    caras = []
    for s in solidos:
        for idx, (c, n) in enumerate(zip(s.caras, s.normales)):
            if np.dot(n, vista.V) <= 1e-9:
                continue
            pg = Polygon([vista.p2(p) for p in c])
            if not pg.is_valid:
                pg = pg.buffer(0)
            if pg.area <= EPS_AREA:
                continue
            caras.append(dict(pg=pg, s=s, n=n, d=float(np.dot(n, c[0])), idx=idx))
    for i, A in enumerate(caras):
        tapas = []
        for j, B in enumerate(caras):
            if i == j or A["s"] is B["s"]:
                continue
            if not A["pg"].intersects(B["pg"]):
                continue
            inter = A["pg"].intersection(B["pg"])
            for q in _polis(inter):
                p = q.representative_point()
                ta = vista.prof(A["n"], A["d"], (p.x, p.y))
                tb = vista.prof(B["n"], B["d"], (p.x, p.y))
                if tb > ta + 1e-6:
                    tapas.append(q)
        vis = A["pg"]
        if tapas:
            vis = vis.difference(unary_union(tapas).buffer(1e-7))
        A["vis"] = _polis(vis)
    out = []
    for A in caras:
        decs = []
        for idx, poly3 in A["s"].decor:
            if idx == A["idx"]:
                dp = Polygon([vista.p2(p) for p in poly3])
                for v in A["vis"]:
                    decs += _polis(v.intersection(dp))
        for v in A["vis"]:
            out.append((v, A["s"], A["n"], decs))
    return out


def sombra(color, n, vista, plano=False):
    if plano:
        f = 1.0
    else:
        f = 0.72 + 0.28 * float(np.dot(n, vista.U)) + 0.10 * float(np.dot(n, vista.R))
        f = max(0.45, min(1.08, f))
    return tuple(int(max(0, min(255, c * f))) for c in color)


def dibujar(msp, solidos, vista, capa_linea, capa_relleno, plano=False, contorno=True):
    res = resolver(solidos, vista)
    for pg, s, n, decs in res:
        col = sombra(s.color, n, vista, plano)
        h = msp.add_hatch(dxfattribs={"layer": capa_relleno})
        h.set_solid_fill(rgb=col)
        _rutas(h, pg)
        if s.patron:
            hp = msp.add_hatch(dxfattribs={"layer": capa_relleno, "color": 8})
            hp.set_pattern_fill(s.patron[0], scale=s.patron[1])
            _rutas(hp, pg)
        for d in decs:
            hd = msp.add_hatch(dxfattribs={"layer": capa_relleno})
            hd.set_solid_fill(rgb=tuple(int(c * 0.45) for c in s.color))
            _rutas(hd, d)
    if contorno:
        for pg, s, n, decs in res:
            for g in [pg] + decs:
                anillos = [g.exterior] + list(g.interiors)
                for r in anillos:
                    msp.add_lwpolyline(list(r.coords), close=True, dxfattribs={"layer": capa_linea})
    return res


def _rutas(h, pg):
    h.paths.add_polyline_path(list(pg.exterior.coords)[:-1], is_closed=True, flags=1)
    for r in pg.interiors:
        h.paths.add_polyline_path(list(r.coords)[:-1], is_closed=True, flags=0)


def limites(solidos, vista):
    pts = [vista.p2(p) for s in solidos for c in s.caras for p in c]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)
