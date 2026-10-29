"""Geometría de las 3 opciones de lotificación (shapely)."""
import heapq
import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import config as C

HALF_ROW = C.SECCION / 2          # 6.00 m
HALF_ASF = C.ARROYO / 2           # 4.50 m
EPS = 1e-6


def envolvente():
    return box(0, 0, C.ANCHO, C.LARGO)


def _clean(g, e=1e-4):
    return g.buffer(e, join_style=2).buffer(-e, join_style=2)


def _polys(g):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 1e-3]


# ----------------------------------------------------------------------------------
# Trazos viales por opción. Cada calle: dict(nombre, pts, fondo, orden)
#   fondo = fondo máximo de los lotes que dan frente a esa calle
#   orden = prioridad de lotificación (menor primero)
# Todas las posiciones dependen del ancho de banda de donación b.
# ----------------------------------------------------------------------------------
def opcion_1(b):
    """Espina central recta + 3 calles transversales."""
    W, L = C.ANCHO, C.LARGO
    x0, x1, y0, y1 = b, W - b, b, L - b
    xc = W / 2
    D = ((y1 - y0) - 3 * C.SECCION) / 6.0          # fondo de lote: sencillo + doble + doble + sencillo
    calles = [dict(nombre="EJE CENTRAL", pts=[(xc, 0.0), (xc, L)], fondo=D, orden=9)]
    for k in range(3):
        y = y0 + D + HALF_ROW + k * (2 * D + C.SECCION)
        calles.append(dict(nombre=f"CALLE TRANSVERSAL T{k+1}", pts=[(x0, y), (x1, y)], fondo=D, orden=1))
    accesos = [dict(nombre="Acceso sur (eje central)", punto=(xc, 0.0), borde="SUR"),
               dict(nombre="Acceso norte (eje central)", punto=(xc, L), borde="NORTE")]
    punto_bajo = (xc, 0.0)
    return dict(calles=calles, accesos=accesos, punto_bajo=punto_bajo,
                notas=[f"Fondo de lote uniforme {D:.2f} m (bloques sencillos al norte y sur, dobles al centro).",
                       "Las 3 transversales cruzan el eje central y terminan contra la donación perimetral (calles cerradas de 70 m)."])


def opcion_2(b, Do=30.0, Ds=25.0):
    """Anillo central con cruce interno, eje de acceso sur y salida sureste."""
    W, L = C.ANCHO, C.LARGO
    x0, x1, y0, y1 = b, W - b, b, L - b
    xa = x0 + Do + HALF_ROW
    xb = x1 - Do - HALF_ROW
    ya = y0 + Ds + HALF_ROW
    yb = y1 - Ds - HALF_ROW
    ym = (ya + yb) / 2
    xc = W / 2
    din = ((xb - xa) - C.SECCION) / 2               # fondo interior (espalda con espalda)
    dcr = ((ym - ya) - C.SECCION) / 2               # fondo entre anillo y cruce
    calles = [
        dict(nombre="ANILLO CENTRAL", pts=[(xa, ya), (xb, ya), (xb, yb), (xa, yb), (xa, ya)], fondo=Do, orden=2),
        dict(nombre="CRUCE INTERNO", pts=[(xa, ym), (xb, ym)], fondo=dcr, orden=1),
        dict(nombre="EJE CENTRAL DE ACCESO", pts=[(xc, 0.0), (xc, ya)], fondo=Ds, orden=3),
        dict(nombre="SALIDA SURESTE", pts=[(xb, ya), (xb, 0.0)], fondo=Ds, orden=3),
    ]
    accesos = [dict(nombre="Acceso sur (eje central)", punto=(xc, 0.0), borde="SUR"),
               dict(nombre="Salida sureste (drenaje y acceso)", punto=(xb, 0.0), borde="SUR")]
    return dict(calles=calles, accesos=accesos, punto_bajo=(xb, 0.0), anillo_lado=(xa, ya),
                notas=[f"Anillo de {xb-xa:.2f} x {yb-ya:.2f} m a ejes; lotes exteriores de {Do:.2f} m de fondo.",
                       f"Interior del anillo dividido por un cruce E-O; lotes interiores de {dcr:.2f} m de fondo.",
                       "La esquina sureste del anillo baja por un tramo recto al borde sur: ahí está la salida de drenaje."])


def opcion_3(b, Dw=20.0, Dn=40.0):
    """Colector en T: colector longitudinal + barra norte + ramales en peine."""
    W, L = C.ANCHO, C.LARGO
    x0, x1, y0, y1 = b, W - b, b, L - b
    xc = W / 2
    yt = y1 - Dn - HALF_ROW                         # barra de la T
    xr_w = x0 + Dw + HALF_ROW                       # ramal poniente
    xr_e = x1 - Dw - HALF_ROW                       # ramal oriente
    db = ((xc - HALF_ROW) - (xr_w + HALF_ROW)) / 2  # fondo espalda con espalda ramal/colector
    calles = [
        dict(nombre="COLECTOR CENTRAL", pts=[(xc, 0.0), (xc, yt)], fondo=db, orden=2),
        dict(nombre="BARRA NORTE (T)", pts=[(x0, yt), (x1, yt)], fondo=Dn, orden=3),
        dict(nombre="RAMAL PONIENTE", pts=[(xr_w, yt), (xr_w, y0)], fondo=max(Dw, db), orden=1),
        dict(nombre="RAMAL ORIENTE", pts=[(xr_e, yt), (xr_e, y0)], fondo=max(Dw, db), orden=1),
    ]
    accesos = [dict(nombre="Acceso sur (colector)", punto=(xc, 0.0), borde="SUR")]
    return dict(calles=calles, accesos=accesos, punto_bajo=(xc, 0.0),
                fondos_lado={"RAMAL PONIENTE": {-1: db, 1: Dw}, "RAMAL ORIENTE": {1: db, -1: Dw}},
                notas=[f"Ramales a {Dw+HALF_ROW:.2f} m de la donación: lotes de {Dw:.2f} m hacia la donación y de {db:.2f} m hacia el colector.",
                       f"Barra norte con lotes de {Dn:.2f} m de fondo hacia el norte.",
                       "Los ramales terminan contra la donación sur (calles cerradas)."])


OPCIONES = [
    dict(clave="opcion_1", corto="Espina central recta", titulo="OPCIÓN 1 — ESPINA CENTRAL RECTA", fn=opcion_1),
    dict(clave="opcion_2", corto="Anillo central con cruces", titulo="OPCIÓN 2 — ANILLO CENTRAL CON CRUCES", fn=opcion_2),
    dict(clave="opcion_3", corto="Colector en T con ramales en peine", titulo="OPCIÓN 3 — COLECTOR EN T CON RAMALES EN PEINE", fn=opcion_3),
]


# ----------------------------------------------------------------------------------
def vialidad(calles):
    env = envolvente()
    lines = [LineString(c["pts"]) for c in calles]
    row = unary_union([ln.buffer(HALF_ROW, cap_style=2, join_style=2) for ln in lines]).intersection(env)
    asf = unary_union([ln.buffer(HALF_ASF, cap_style=2, join_style=2) for ln in lines]).intersection(env)
    row, asf = _clean(row), _clean(asf)
    banq = _clean(row.difference(asf))
    return row, asf, banq


def banda_donacion(b, row):
    env = envolvente()
    interior = box(b, b, C.ANCHO - b, C.LARGO - b)
    banda = env.difference(interior)
    return _clean(banda.difference(row)), interior


def resolver_banda(fn):
    """Ancho de banda b tal que la donación (descontando los gaps de acceso) = 10 % exacto."""
    env_a = C.ANCHO * C.LARGO
    lo, hi = 1.0, 15.0
    for _ in range(60):
        b = (lo + hi) / 2
        lay = fn(b)
        row, _, _ = vialidad(lay["calles"])
        don, _ = banda_donacion(b, row)
        if don.area / env_a < C.DONACION_OBJETIVO:
            lo = b
        else:
            hi = b
    return (lo + hi) / 2


# ----------------------------------------------------------------------------------
def _rect_lado(a, t, n, s0, s1, d):
    P = lambda s, w: (a[0] + t[0] * s + n[0] * w, a[1] + t[1] * s + n[1] * w)
    return Polygon([P(s0, HALF_ROW), P(s1, HALF_ROW), P(s1, HALF_ROW + d), P(s0, HALF_ROW + d)])


def lotificar(calles, row, interior, fondos_lado=None):
    """Lotes rectangulares de frente 25.00 m sobre el alineamiento exterior de banqueta."""
    disponible = _clean(interior.difference(row))
    lotes, remanentes_frente = [], []
    fondos_lado = fondos_lado or {}
    for c in sorted(calles, key=lambda c: c["orden"]):
        for a, bb in zip(c["pts"][:-1], c["pts"][1:]):
            Lseg = math.dist(a, bb)
            t = ((bb[0] - a[0]) / Lseg, (bb[1] - a[1]) / Lseg)
            for side in (1, -1):
                n = (-t[1] * side, t[0] * side)
                dmax = fondos_lado.get(c["nombre"], {}).get(side, c["fondo"])
                # alineamiento exterior de banqueta de este lado
                al = LineString([(a[0] + n[0] * HALF_ROW - t[0] * HALF_ROW, a[1] + n[1] * HALF_ROW - t[1] * HALF_ROW),
                                 (bb[0] + n[0] * HALF_ROW + t[0] * HALF_ROW, bb[1] + n[1] * HALF_ROW + t[1] * HALF_ROW)])
                # tramos del alineamiento que dan a terreno disponible (franja de 0.5 m)
                probe = al.buffer(0.25, cap_style=2).intersection(disponible.buffer(-1e-3))
                tramos = []
                for p in _polys(probe):
                    ss = [(q[0] - a[0]) * t[0] + (q[1] - a[1]) * t[1] for q in p.exterior.coords]
                    tramos.append((min(ss), max(ss)))
                for s0, s1 in sorted(tramos):
                    s = s0
                    while s + C.FRENTE_LOTE <= s1 + 1e-6:
                        # fondo: el mayor posible (<= dmax) que quede dentro del terreno disponible
                        lo_, hi_ = 0.0, dmax
                        for _ in range(40):
                            m = (lo_ + hi_) / 2
                            r = _rect_lado(a, t, n, s, s + C.FRENTE_LOTE, m)
                            if r.difference(disponible).area < 1e-3:
                                lo_ = m
                            else:
                                hi_ = m
                        d = math.floor(lo_ * 1000) / 1000   # truncar: nunca invadir la donación
                        if d >= C.FONDO_MINIMO:
                            r = _rect_lado(a, t, n, s, s + C.FRENTE_LOTE, d)
                            lotes.append(dict(geom=r, calle=c["nombre"], frente=C.FRENTE_LOTE, fondo=d))
                            disponible = _clean(disponible.difference(r))
                        s += C.FRENTE_LOTE
                    if s1 - s > 0.5:
                        remanentes_frente.append(dict(calle=c["nombre"], largo=round(s1 - s, 2)))
    remanentes = [p for p in _polys(disponible) if p.area > 1.0]
    return lotes, remanentes, remanentes_frente


# ----------------------------------------------------------------------------------
def drenaje(calles, punto_bajo):
    """Red de ejes -> distancias al punto bajo (Dijkstra) -> cotas con pendiente mínima."""
    segs = []
    for c in calles:
        for a, b in zip(c["pts"][:-1], c["pts"][1:]):
            segs.append(LineString([a, b]))
    red = unary_union(segs)   # nodifica en las intersecciones
    key = lambda p: (round(p[0], 3), round(p[1], 3))
    graf = {}
    aristas = []
    for ln in getattr(red, "geoms", [red]):
        cs = list(ln.coords)
        for a, b in zip(cs[:-1], cs[1:]):
            ka, kb = key(a), key(b)
            w = math.dist(a, b)
            if w < 1e-6:
                continue
            graf.setdefault(ka, []).append((kb, w))
            graf.setdefault(kb, []).append((ka, w))
            aristas.append((ka, kb))
    src = key(punto_bajo)
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18):
            continue
        for v, w in graf.get(u, []):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    cota = {k: C.COTA_PUNTO_BAJO + C.PENDIENTE_LONGITUDINAL * d for k, d in dist.items()}
    flechas = []
    for ka, kb in aristas:
        hi_, lo_ = (ka, kb) if dist[ka] > dist[kb] else (kb, ka)
        flechas.append((hi_, lo_))
    # mínimos locales: nodos sin ningún vecino más bajo
    minimos = [k for k in graf if all(dist[v] >= dist[k] for v, _ in graf[k])]
    return dict(nodos=cota, flechas=flechas, n_minimos=len(minimos), minimos=minimos,
                longitud=sum(s.length for s in segs))


# ----------------------------------------------------------------------------------
def construir(op):
    fn = op["fn"]
    b = resolver_banda(fn)
    lay = fn(b)
    row, asf, banq = vialidad(lay["calles"])
    don, interior = banda_donacion(b, row)
    lotes, remanentes, rem_frente = lotificar(lay["calles"], row, interior, lay.get("fondos_lado"))
    for i, L in enumerate(sorted(lotes, key=lambda L: (-round(L["geom"].centroid.y, 0), L["geom"].centroid.x))):
        L["id"] = f"L-{i+1:02d}"
    lotes.sort(key=lambda L: L["id"])
    dren = drenaje(lay["calles"], lay["punto_bajo"])
    # gaps de donación en cada acceso
    env = envolvente()
    banda_llena = env.difference(interior)
    gaps = []
    for acc in lay["accesos"]:
        g = banda_llena.intersection(row).intersection(Point(acc["punto"]).buffer(HALF_ROW + b + 0.5))
        gaps.append(dict(acceso=acc["nombre"], borde=acc["borde"], x=acc["punto"][0], y=acc["punto"][1],
                         ancho=C.SECCION, area=g.area))
    return dict(op=op, b=b, lay=lay, row=row, asf=asf, banq=banq, don=don, interior=interior,
                lotes=lotes, remanentes=remanentes, rem_frente=rem_frente, dren=dren, gaps=gaps,
                env=env)
