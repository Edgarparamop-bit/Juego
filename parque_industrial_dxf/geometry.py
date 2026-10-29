"""Geometría: colector por el borde bajo, calles con retornos rectangulares,
donación perimetral, lotificación por frentes de 25 m y red de drenaje."""
import heapq
import math

import shapely
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union

import config as C

H_ROW = C.SECCION / 2          # 6.00
H_ASF = C.ARROYO / 2           # 4.50


# ---------------------------------------------------------------- utilidades
def _polys(g):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 1e-3]


def _clean(g, e=1e-3):
    return g.buffer(e, join_style=2).buffer(-2 * e, join_style=2).buffer(e, join_style=2)


def _unit(a, b):
    d = (b[0] - a[0], b[1] - a[1])
    n = math.hypot(*d)
    return (d[0] / n, d[1] / n)


def _rect(c, t, s0, s1, w0, w1):
    """Rectángulo en el marco (t a lo largo, n = t rotado 90° izq.)."""
    n = (-t[1], t[0])
    P = lambda s, w: (c[0] + t[0] * s + n[0] * w, c[1] + t[1] * s + n[1] * w)
    return Polygon([P(s0, w0), P(s1, w0), P(s1, w1), P(s0, w1)])


def poligonos():
    return {k: Polygon(v) for k, v in C.MACROLOTES.items()}


def area_total():
    return sum(p.area for p in poligonos().values())


# ---------------------------------------------------------------- colector
def colector(k):
    P = Polygon(C.MACROLOTES[k])
    chain = LineString([C.MACROLOTES[k][i] for i in C.BORDE_BAJO[k]])
    best = None
    for d in (H_ROW, -H_ROW):
        off = chain.offset_curve(d, join_style=2, mitre_limit=5)
        if P.contains(off.interpolate(0.5, normalized=True)):
            best = off
    cs = list(best.coords)
    if math.dist(cs[0], chain.coords[0]) > math.dist(cs[-1], chain.coords[0]):
        cs = cs[::-1]
    t0 = _unit(cs[1], cs[0])
    t1 = _unit(cs[-2], cs[-1])
    cs = [(cs[0][0] + t0[0] * 60, cs[0][1] + t0[1] * 60)] + cs[1:-1] + [(cs[-1][0] + t1[0] * 60, cs[-1][1] + t1[1] * 60)]
    ln = LineString(cs).intersection(P)
    ln = max([g for g in getattr(ln, "geoms", [ln]) if g.geom_type == "LineString"], key=lambda g: g.length)
    cs = list(ln.coords)
    if cs[0][1] > cs[-1][1]:
        cs = cs[::-1]
    return cs   # de sur (bajo) a norte (alto)


def _punto_en(cs, s):
    ln = LineString(cs)
    p = ln.interpolate(s)
    p2 = ln.interpolate(min(s + 0.5, ln.length))
    p1 = ln.interpolate(max(s - 0.5, 0))
    return (p.x, p.y), _unit((p1.x, p1.y), (p2.x, p2.y))


# ---------------------------------------------------------------- calles con retorno
def _dir(k, nombre, t_col):
    V = C.MACROLOTES[k]
    if nombre == "perp":                       # perpendicular al colector, hacia el interior
        return (-t_col[1], t_col[0])
    if nombre == "poniente":                   # perpendicular a la colindancia poniente, hacia ella
        u = _unit(V[0], V[1])
        return (-u[1], u[0])
    if nombre == "norte":                      # paralela a la colindancia poniente
        return _unit(V[0], V[1])
    if nombre == "este":                       # paralela al lindero norte
        return _unit(V[1], V[2])
    raise ValueError(nombre)


def _dist_linea(p, a, b):
    """Distancia con signo a la recta a-b (positiva hacia el interior del macrolote)."""
    t = _unit(a, b)
    d = (p[0] - a[0]) * t[1] - (p[1] - a[1]) * t[0]
    return d if Polygon_orient_cw else -d


Polygon_orient_cw = True   # los vértices de config.MACROLOTES van en sentido horario


def retorno(end, t, brazos):
    """ROW y arroyo del retorno rectangular (T o L) al final de una calle."""
    row, asf = [], []
    A = C.BRAZO_RETORNO
    for sg in brazos:
        if sg > 0:
            row.append(_rect(end, t, -H_ROW, H_ROW, 0, H_ASF + A + C.BANQUETA))
            asf.append(_rect(end, t, -H_ASF, H_ASF, 0, H_ASF + A))
        else:
            row.append(_rect(end, t, -H_ROW, H_ROW, -(H_ASF + A + C.BANQUETA), 0))
            asf.append(_rect(end, t, -H_ASF, H_ASF, -(H_ASF + A), 0))
    row.append(_rect(end, t, -H_ROW, H_ROW, -H_ROW, H_ROW))
    asf.append(_rect(end, t, -H_ASF, H_ASF, -H_ASF, H_ASF))
    return unary_union(row), unary_union(asf)


def calle(k, col, spec, permitido):
    """spec = dict(s=..., tramos=[(dir, largo)]); largo: número, ('oeste', d), ('norte_lim', d) o 'max'."""
    V = C.MACROLOTES[k]
    s_ini = spec["s"]
    if isinstance(s_ini, str):          # "auto": primer punto del colector donde el primer tramo mide >= 20 m
        d_obj = spec["tramos"][0][1][1]
        for s_ in range(0, int(LineString(col).length)):
            p_, t_ = _punto_en(col, s_)
            tt = (-t_[1], t_[0])
            if not Polygon(V).contains(Point(p_[0] + tt[0] * 20, p_[1] + tt[1] * 20)):
                tt = (-tt[0], -tt[1])
            dw = _dist_linea(p_, V[0], V[1])
            ang = abs(tt[0] * _unit(V[0], V[1])[1] - tt[1] * _unit(V[0], V[1])[0])
            if (dw - d_obj) / max(ang, 1e-6) >= 20:
                s_ini = s_
                break
    p0, t_col = _punto_en(col, s_ini)
    pts = [p0]
    t = None
    for dname, largo in spec["tramos"]:
        t = _dir(k, dname, t_col)
        a = pts[-1]
        if dname == "perp" and not Polygon(V).contains(Point(a[0] + t[0] * 20, a[1] + t[1] * 20)):
            t = (-t[0], -t[1])
        if isinstance(largo, (int, float)):
            L = largo
        elif largo == "max":
            L = None
        else:
            ref, d = largo
            seg = (V[0], V[1]) if ref == "oeste" else (V[1], V[2])
            # avanzar hasta quedar a distancia d de esa colindancia
            lo, hi = 0.0, 400.0
            d0 = _dist_linea(a, *seg)
            for _ in range(50):
                m = (lo + hi) / 2
                q = (a[0] + t[0] * m, a[1] + t[1] * m)
                if (_dist_linea(q, *seg) > d) == (d0 > d):
                    lo = m
                else:
                    hi = m
            L = (lo + hi) / 2
        if L is None:
            # el mayor largo con retorno dentro del terreno permitido, dejando fondo para lotes
            best = None
            for L_ in [x * 1.0 for x in range(10, 400)]:
                e = (a[0] + t[0] * L_, a[1] + t[1] * L_)
                a2 = (a[0] + t[0] * (H_ROW + 1), a[1] + t[1] * (H_ROW + 1)) if len(pts) == 1 else a
                cuerpo = LineString([a2, e]).buffer(H_ROW, cap_style=2)
                if not permitido.contains(cuerpo):
                    break
                br = [sg for sg in (1, -1) if permitido.contains(retorno(e, t, [sg])[0])]
                if br:
                    best = (L_, br)
            if best is None:
                raise RuntimeError(f"No cabe la calle {spec}")
            L_max = best[0]
            L = L_max
            for L_ in [L_max - x for x in range(0, int(L_max))]:
                if L_ <= 10:
                    break
                e = (a[0] + t[0] * L_, a[1] + t[1] * L_)
                br = [sg for sg in (1, -1) if permitido.contains(retorno(e, t, [sg])[0])]
                if br and L_max - L_ >= C.FONDO_LIBRE_TRAS_RETORNO:
                    L = L_
                    break
        pts.append((a[0] + t[0] * L, a[1] + t[1] * L))
    end = pts[-1]
    brazos = [sg for sg in (1, -1) if permitido.contains(retorno(end, t, [sg])[0])]
    return dict(nombre=spec["nombre"], macro=k, pts=pts, t_fin=t, brazos=brazos)


# ---------------------------------------------------------------- opciones
PEINE_A = (70, 150)
PEINE_B = (70, 150)
OPCIONES = [
    dict(clave="opcion_1", corto="Colector inferior con peines y retornos",
         titulo="OPCIÓN 1 — COLECTOR INFERIOR CON PEINES Y RETORNOS",
         calles={"A": [dict(nombre="PEINE A1", s=PEINE_A[0], tramos=[("poniente", "max")]),
                       dict(nombre="PEINE A2", s=PEINE_A[1], tramos=[("poniente", "max")])],
                 "B": [dict(nombre="PEINE B1", s=PEINE_B[0], tramos=[("poniente", "max")]),
                       dict(nombre="PEINE B2", s=PEINE_B[1], tramos=[("poniente", "max")])]},
         notas=["Calles en peine que salen del colector y corren perpendiculares a la colindancia poniente",
                "(lotes rectangulares espalda con espalda entre peines); cada una termina en retorno rectangular en T."]),
    dict(clave="opcion_2", corto="Colector diagonal con ramales",
         titulo="OPCIÓN 2 — COLECTOR DIAGONAL CON RAMALES",
         calles={"A": [dict(nombre="RAMAL A", s="auto", tramos=[("perp", ("oeste", 36.0)), ("norte", ("norte_lim", 36.0)), ("este", "max")])],
                 "B": [dict(nombre="RAMAL B", s="auto", tramos=[("perp", ("oeste", 36.0)), ("norte", ("norte_lim", 36.0)), ("este", "max")])]},
         notas=["Ramal en J por macrolote (como el plano de referencia): sale del colector en la parte baja,",
                "sube paralelo a la colindancia poniente y gira al oriente paralelo al lindero norte;",
                "termina en retorno rectangular cerca del colector, sin conectarse a él."]),
    dict(clave="opcion_3", corto="Retornos profundos optimizados",
         titulo="OPCIÓN 3 — RETORNOS PROFUNDOS OPTIMIZADOS",
         calles={"A": [dict(nombre="CALLE PROFUNDA A", s="auto", tramos=[("perp", ("oeste", 36.0)), ("norte", "max")])],
                 "B": [dict(nombre="CALLE PROFUNDA B", s="auto", tramos=[("perp", ("oeste", 36.0)), ("norte", "max")])]},
         notas=["Una sola calle profunda por macrolote: nace en el extremo bajo del colector, sube paralela a",
                "la colindancia poniente y termina en un retorno rectangular al norte. Es la menor vialidad interna."]),
]


# ---------------------------------------------------------------- lotificación
def _frentes(segs, edif):
    """Líneas de alineamiento exterior de banqueta (a 6.00 m del eje) por segmento y lado."""
    out = []
    for j, sg in enumerate(segs):
        a, b = sg["ls"].coords[0], sg["ls"].coords[-1]
        t = sg["t"]
        for lado in (1, -1):
            n = (-t[1] * lado, t[0] * lado)
            fl = LineString([(a[0] + n[0] * H_ROW, a[1] + n[1] * H_ROW), (b[0] + n[0] * H_ROW, b[1] + n[1] * H_ROW)])
            util = fl.intersection(edif.buffer(0.05))
            if util.length > 1.0:
                out.append(dict(j=j, lado=lado, linea=fl, util=util))
    return out


def lotificar(polys, row, banda):
    """Divide el terreno edificable en lotes con frente >= 25.00 m sobre su alineamiento."""
    lotes, rem = [], []
    for k, P in polys.items():
        edif = _clean(P.difference(banda).difference(row))
        segs = _SEGMENTOS[k]
        frentes = _frentes(segs, edif)
        pts, lab, vistos = [], [], set()
        for gi, f in enumerate(frentes):
            for g in getattr(f["util"], "geoms", [f["util"]]):
                if g.geom_type != "LineString":
                    continue
                n = max(2, int(g.length / 0.5))
                for i in range(n + 1):
                    p = g.interpolate(i * g.length / n)
                    kp = (round(p.x, 2), round(p.y, 2))
                    if kp in vistos:
                        continue
                    vistos.add(kp)
                    pts.append(p)
                    lab.append(gi)
        vor = shapely.voronoi_polygons(MultiPoint(pts), extend_to=P.buffer(80), ordered=True)
        celdas = {}
        for cell, gi in zip(vor.geoms, lab):
            celdas.setdefault(gi, []).append(cell)
        for gi, cs in celdas.items():
            f = frentes[gi]
            sg = segs[f["j"]]
            a, t = sg["ls"].coords[0], sg["t"]
            region = _clean(unary_union([c.buffer(0) for c in cs]).buffer(0).intersection(edif))
            for comp in _polys(region):
                fl = comp.boundary.intersection(f["linea"].buffer(0.05))
                if fl.is_empty or fl.length < 1.0:
                    rem.append(dict(geom=comp, macro=k))
                    continue
                cc = [c for g in getattr(fl, "geoms", [fl]) for c in (g.exterior.coords if g.geom_type == "Polygon" else g.coords)]
                ss = [(x - a[0]) * t[0] + (y - a[1]) * t[1] for x, y in cc]
                s0, s1 = min(ss), max(ss)
                n = int((s1 - s0) / C.FRENTE_LOTE + 1e-6)
                if n == 0:
                    rem.append(dict(geom=comp, macro=k))
                    continue
                cortes = [-1e4] + [s0 + C.FRENTE_LOTE * i for i in range(1, n)] + [1e4]
                piezas = []
                for c0, c1 in zip(cortes[:-1], cortes[1:]):
                    q = comp.intersection(_rect(a, t, c0, c1, -1e4, 1e4))
                    partes = sorted(_polys(q), key=lambda z: -z.boundary.intersection(f["linea"].buffer(0.05)).length)
                    if partes:
                        piezas.append(partes[0])
                        rem += [dict(geom=z, macro=k) for z in partes[1:]]
                # una pieza menor al lote mínimo se une UNA vez a su vecina del mismo frente
                unidas = [False] * len(piezas)
                i = 0
                while i < len(piezas):
                    if piezas[i].area < C.AREA_MIN_LOTE and not unidas[i]:
                        vec = [j for j in (i - 1, i + 1) if 0 <= j < len(piezas) and not unidas[j]]
                        if vec:
                            j = min(vec, key=lambda j: piezas[j].area)
                            u = _clean(unary_union([piezas[i], piezas[j]]))
                            if u.geom_type == "Polygon":
                                lo_, hi_ = min(i, j), max(i, j)
                                piezas[lo_] = u
                                unidas[lo_] = True
                                piezas.pop(hi_)
                                unidas.pop(hi_)
                                continue
                    i += 1
                for q in piezas:
                    if q.area >= C.AREA_MIN_LOTE:
                        lotes.append(dict(geom=q, macro=k, calle=sg["calle"]))
                    else:
                        rem.append(dict(geom=q, macro=k))
    return lotes, rem


# ---------------------------------------------------------------- vialidad completa
_SEGMENTOS = {}


def vialidad(op, permitido):
    polys = poligonos()
    cols = {k: colector(k) for k in polys}
    calles = []
    for k in polys:
        for sp in op["calles"][k]:
            calles.append(calle(k, cols[k], sp, permitido[k]))
    row_l, asf_l = [], []
    for k, cs in cols.items():
        ln = LineString(cs)
        row_l.append(ln.buffer(H_ROW, cap_style=2, join_style=2).intersection(polys[k]))
        asf_l.append(ln.buffer(H_ASF, cap_style=2, join_style=2).intersection(polys[k]))
    for c in calles:
        ln = LineString(c["pts"])
        r, a = retorno(c["pts"][-1], c["t_fin"], c["brazos"])
        row_l += [ln.buffer(H_ROW, cap_style=2, join_style=2), r]
        asf_l += [ln.buffer(H_ASF, cap_style=2, join_style=2), a]
    allp = unary_union(list(polys.values()))
    row = _clean(unary_union(row_l).intersection(allp))
    asf = _clean(unary_union(asf_l).intersection(allp))
    # segmentos de frente (colector, tramos de calle y barra de retorno)
    for k in polys:
        segs = []
        cs = cols[k]
        for a, b in zip(cs[:-1], cs[1:]):
            segs.append(dict(ls=LineString([a, b]), t=_unit(a, b), calle=f"COLECTOR {k}"))
        for c in [c for c in calles if c["macro"] == k]:
            for a, b in zip(c["pts"][:-1], c["pts"][1:]):
                segs.append(dict(ls=LineString([a, b]), t=_unit(a, b), calle=c["nombre"]))
            e, t = c["pts"][-1], c["t_fin"]
            n = (-t[1], t[0])
            w1 = (H_ASF + C.BRAZO_RETORNO) if 1 in c["brazos"] else 0.0
            w0 = -(H_ASF + C.BRAZO_RETORNO) if -1 in c["brazos"] else 0.0
            p0 = (e[0] + n[0] * w0, e[1] + n[1] * w0)
            p1 = (e[0] + n[0] * w1, e[1] + n[1] * w1)
            segs.append(dict(ls=LineString([p0, p1]), t=_unit(p0, p1), calle=c["nombre"] + " (RETORNO)"))
        _SEGMENTOS[k] = segs
    # cruce del colector bajo la calle municipal entre A y B (solo eje / tubería pluvial)
    cruce = [cols["A"][-1], cols["B"][0]]
    return cols, calles, row, asf, cruce


# ---------------------------------------------------------------- donación
def _bordes_perimetrales(k):
    V = C.MACROLOTES[k]
    n = len(V)
    bajo = C.BORDE_BAJO[k]
    excl = {tuple(sorted((bajo[i], bajo[i + 1]))) for i in range(len(bajo) - 1)}
    segs = []
    for i in range(n):
        j = (i + 1) % n
        if tuple(sorted((i, j))) in excl:
            continue
        segs.append(LineString([V[i], V[j]]))
    return unary_union(segs)


def banda(w, row):
    polys = poligonos()
    out = []
    for k, P in polys.items():
        b = P.intersection(_bordes_perimetrales(k).buffer(w, cap_style=2, join_style=2))
        out.append(b)
    full = _clean(unary_union(out))
    return full, _clean(full.difference(row))


def construir(op):
    polys = poligonos()
    At = area_total()
    permitido = {k: P.buffer(-6.0, join_style=2) for k, P in polys.items()}
    cols, calles, row, asf, cruce = vialidad(op, permitido)

    def evaluar(w):
        full, bnd = banda(w, row)
        lotes, rem = lotificar(polys, row, bnd)
        don_extra, vial_extra, merge = [], [], []
        perim = unary_union([P.exterior for P in polys.values()])
        presupuesto = C.DONACION_OBJETIVO * At - bnd.area
        for r in sorted(rem, key=lambda r: r["geom"].area):
            g = r["geom"]
            if (g.buffer(0.05).intersects(bnd) or g.buffer(0.05).intersects(perim)) and g.area <= presupuesto + 1.0:
                don_extra.append(g)
                presupuesto -= g.area
            else:
                merge.append(g)   # si ya no cabe en la donación, se integra al lote vecino
        for g in merge:   # remanente interior sin frente propio: se integra al lote vecino
            j = max(range(len(lotes)), key=lambda j: g.boundary.intersection(lotes[j]["geom"].buffer(0.05)).length) if lotes else None
            u = _clean(unary_union([lotes[j]["geom"], g])) if j is not None else None
            if u is not None and u.geom_type == "Polygon" and g.boundary.intersection(lotes[j]["geom"].buffer(0.05)).length > 0.5:
                lotes[j]["geom"] = u
            elif g.buffer(0.05).intersects(bnd) or g.buffer(0.05).intersects(perim):
                don_extra.append(g)
            else:
                vial_extra.append(g)
        don = _clean(unary_union([bnd] + don_extra))
        return dict(full=full, don=don, lotes=lotes, vial_extra=vial_extra, w=w)

    lo, hi = 0.5, 15.0
    ev = None
    for _ in range(26):
        m = (lo + hi) / 2
        ev = evaluar(m)
        if ev["don"].area / At < C.DONACION_OBJETIVO:
            lo = m
        else:
            hi = m
    # elegir la evaluación más cercana al 10 % entre los extremos
    cands = [evaluar(lo), evaluar(hi)]
    ev = min(cands, key=lambda e: abs(e["don"].area / At - C.DONACION_OBJETIVO))

    row_total = _clean(unary_union([row] + ev["vial_extra"]))
    asf_total = asf
    banq = _clean(row_total.difference(asf_total))
    lotes = ev["lotes"]
    for L in lotes:
        L["frente_alineamiento"] = L["geom"].boundary.intersection(row_total.boundary.buffer(0.02)).length
    lotes.sort(key=lambda L: (L["macro"], -round(L["geom"].centroid.y), L["geom"].centroid.x))
    for i, L in enumerate(lotes):
        L["id"] = f"{L['macro']}-{i+1:02d}" if L["macro"] == "A" else f"{L['macro']}-{i+1-sum(1 for x in lotes if x['macro']=='A'):02d}"
    pb = cols["A"][0]
    dren = drenaje(cols, calles, cruce, pb)
    gaps = []
    for g in _polys(ev["full"].intersection(row_total)):
        c = g.centroid
        gaps.append(dict(x=c.x, y=c.y, area=g.area))
    return dict(op=op, polys=polys, cols=cols, calles=calles, row=row_total, asf=asf_total, banq=banq,
                don=ev["don"], banda=ev["w"], lotes=lotes, vial_extra=ev["vial_extra"], dren=dren,
                punto_bajo=pb, gaps=gaps, cruce=cruce, area_total=At)


# ---------------------------------------------------------------- drenaje
def drenaje(cols, calles, cruce, punto_bajo):
    segs = []
    for cs in cols.values():
        segs += [LineString([a, b]) for a, b in zip(cs[:-1], cs[1:])]
    segs.append(LineString(cruce))
    for c in calles:
        segs += [LineString([a, b]) for a, b in zip(c["pts"][:-1], c["pts"][1:])]
        e, t = c["pts"][-1], c["t_fin"]
        n = (-t[1], t[0])
        for sg in c["brazos"]:
            segs.append(LineString([e, (e[0] + n[0] * sg * (H_ASF + C.BRAZO_RETORNO), e[1] + n[1] * sg * (H_ASF + C.BRAZO_RETORNO))]))
    segs = [s for s in segs if s.length > 1e-6]
    # partir cada segmento en los extremos de otros que caen sobre él (uniones en T)
    ends = [Point(c) for s in segs for c in (s.coords[0], s.coords[-1])]
    partidos = []
    for s in segs:
        cuts = sorted({round(s.project(p), 4) for p in ends if s.distance(p) < 0.05 and 0.05 < s.project(p) < s.length - 0.05})
        ds = [0.0] + cuts + [s.length]
        for d0, d1 in zip(ds[:-1], ds[1:]):
            p0, p1 = s.interpolate(d0), s.interpolate(d1)
            partidos.append(LineString([(p0.x, p0.y), (p1.x, p1.y)]))
    red = unary_union([]) if False else None
    from shapely.geometry import MultiLineString
    red = MultiLineString(partidos)
    nodos_ = []

    def key(p):
        for q in nodos_:
            if math.dist(p, q) < 0.05:
                return q
        q = (round(p[0], 3), round(p[1], 3))
        nodos_.append(q)
        return q
    graf, aristas = {}, []
    for ln in getattr(red, "geoms", [red]):
        cs = list(ln.coords)
        for a, b in zip(cs[:-1], cs[1:]):
            w = math.dist(a, b)
            if w < 1e-6:
                continue
            ka, kb = key(a), key(b)
            graf.setdefault(ka, []).append((kb, w))
            graf.setdefault(kb, []).append((ka, w))
            aristas.append((ka, kb))
    src = min(graf, key=lambda k: math.dist(k, punto_bajo))
    dist = {src: 0.0}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18):
            continue
        for v, w in graf[u]:
            if d + w < dist.get(v, 1e18):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    cota = {k: C.COTA_PUNTO_BAJO + C.PENDIENTE_LONGITUDINAL * d for k, d in dist.items()}
    minimos = [k for k in graf if all(dist[v] >= dist[k] for v, _ in graf[k])]
    flechas = [((ka, kb) if dist[ka] > dist[kb] else (kb, ka)) for ka, kb in aristas]
    return dict(nodos=cota, flechas=flechas, minimos=minimos, n_minimos=len(minimos),
                longitud=sum(s.length for s in segs), src=src)
