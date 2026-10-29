"""Lotificación de 6 lotes (3 por macrolote) con 10 % de donación al fondo.

Cada macrolote se divide en tres lotes de **igual área** que dan frente a la
avenida lateral diagonal. La donación es exactamente el 10 % del macrolote. Las
posiciones de los cortes se obtienen por bisección sobre el área.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.affinity import translate
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import config_6lotes as cfg
from dxf_writer import (CAPAS, DIMSTYLE, _dibujar_tabla, _polilinea, _relleno,
                        _rotacion, m2, nuevo_documento)
from geometry import lines, polygons, unit

GRANDE = 5000.0  # semiplanos de corte (m)


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------
def semiplano(origen, d, t: float) -> Polygon:
    """Semiplano {p : n·(p - origen) <= t}, con n normal izquierda de ``d``."""
    dx, dy = d
    nx, ny = -dy, dx
    ox, oy = origen[0] + nx * t, origen[1] + ny * t
    a = (ox - dx * GRANDE, oy - dy * GRANDE)
    b = (ox + dx * GRANDE, oy + dy * GRANDE)
    return Polygon([a, b, (b[0] - nx * GRANDE, b[1] - ny * GRANDE),
                    (a[0] - nx * GRANDE, a[1] - ny * GRANDE)])


def biseccion(f, objetivo: float, lo: float, hi: float, tol: float = 1e-4) -> float:
    """Raíz de f(t) = objetivo, con f creciente en [lo, hi]."""
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) < objetivo:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def _rango(geom, origen, d):
    nx, ny = -d[1], d[0]
    ts = [nx * (x - origen[0]) + ny * (y - origen[1])
          for p in polygons(geom) for x, y in p.exterior.coords]
    return min(ts) - 1, max(ts) + 1


def cortar_por_area(geom, origen, d, area: float):
    """Parte ``geom`` con una línea de dirección ``d`` dejando ``area`` del lado -n."""
    lo, hi = _rango(geom, origen, d)
    t = biseccion(lambda s: geom.intersection(semiplano(origen, d, s)).area, area, lo, hi)
    corte = semiplano(origen, d, t)
    return geom.intersection(corte), geom.difference(corte), t


def franja_fondo(poly: Polygon, p0, p1, area: float) -> Polygon:
    """Franja a lo largo del lindero p0-p1, hacia el interior, con el área dada."""
    d = unit(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -d[1], d[0]
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    if not poly.contains(Point(mx + nx, my + ny)):  # interior hacia -n
        d = (-d[0], -d[1])
        p0, p1 = p1, p0
    # Interior hacia +n: la franja es {n·(p - p0) <= w}.
    w = biseccion(lambda s: poly.intersection(semiplano(p0, d, s)).area, area, 0.0, 300.0)
    return poly.intersection(semiplano(p0, d, w)), w


def _limpio(g):
    return unary_union([p for p in polygons(g.buffer(0)) if p.area > 0.01])


@dataclass
class Lote6:
    numero: int
    poligono: Polygon
    frente: float
    fondo: float

    @property
    def area(self) -> float:
        return self.poligono.area


@dataclass
class Macro6:
    nombre: str
    clave: str
    poligono: Polygon
    donacion: Polygon
    avenida: LineString
    lotes: list[Lote6] = field(default_factory=list)
    ancho_donacion: float = 0.0

    @property
    def area_total(self) -> float:
        return self.poligono.area

    @property
    def area_donacion(self) -> float:
        return self.donacion.area

    @property
    def area_vendible(self) -> float:
        return sum(l.area for l in self.lotes)


def construir_macro(nombre: str, c: dict, prop: dict) -> Macro6:
    poly = Polygon(c["poligono"]).buffer(0)
    av = LineString(c["lindero_avenida"])
    area_don = cfg.DONACION_PCT * poly.area
    (h0, h1) = c["lindero_cabecera"]
    d_cab = unit(h1[0] - h0[0], h1[1] - h0[1])  # dirección de las cabeceras
    # Normal izquierda de las cabeceras apuntando al norte.
    if d_cab[0] < 0:
        d_cab = (-d_cab[0], -d_cab[1])
    ancho = 0.0
    if prop["donacion"] == "fondo":
        (p0, p1) = c["lindero_fondo"]
        donacion, ancho = franja_fondo(poly, p0, p1, area_don)
    else:  # extremo norte
        sur, donacion, _ = cortar_por_area(poly, h0, d_cab, poly.area - area_don)
    donacion = _limpio(donacion)
    vendible = _limpio(poly.difference(donacion))

    if prop["cortes"] == "cabecera":
        d = d_cab
    else:  # perpendiculares a la avenida
        a0, a1 = av.coords[0], av.coords[-1]
        ux, uy = unit(a1[0] - a0[0], a1[1] - a0[1])
        d = (-uy, ux)
    # Orientar d para que -n quede al sur (el primer lote es el más al sur).
    nx, ny = -d[1], d[0]
    if ny < 0:
        d = (-d[0], -d[1])

    objetivo = vendible.area / cfg.LOTES_POR_MACROLOTE
    resto = vendible
    piezas = []
    for _ in range(cfg.LOTES_POR_MACROLOTE - 1):
        pieza, resto, _t = cortar_por_area(resto, h0, d, objetivo)
        piezas.append(_limpio(pieza))
    piezas.append(_limpio(resto))

    m = Macro6(nombre, c["clave"], poly, donacion, av, ancho_donacion=ancho)
    for p in piezas:
        frente = p.boundary.intersection(av.buffer(0.05)).length
        rect = p.minimum_rotated_rectangle
        cc = list(rect.exterior.coords)
        lados = sorted([math.dist(cc[0], cc[1]), math.dist(cc[1], cc[2])])
        m.lotes.append(Lote6(0, p, frente, lados[1] if frente < lados[0] else lados[0]))
    return m


def construir_propuesta(n: int) -> list[Macro6]:
    prop = cfg.PROPUESTAS[n]
    macros = [construir_macro(nom, c, prop) for nom, c in cfg.MACROLOTES.items()]
    k = 1
    for m in macros:
        for l in m.lotes:
            l.numero = k
            k += 1
    return macros


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------
def validar(macros: list[Macro6]) -> list[tuple[str, bool, str]]:
    res = []
    for m in macros:
        pct = 100 * m.area_donacion / m.area_total
        res.append((f"{m.nombre}: donación 10 %", abs(pct - 10) < 0.01, f"{pct:.3f} %"))
        areas = [l.area for l in m.lotes]
        dif = max(areas) - min(areas)
        res.append((f"{m.nombre}: 3 lotes de igual área", len(areas) == 3 and dif < 0.05,
                    f"{', '.join(f'{a:,.2f}' for a in areas)} m2 (dif. {dif:.3f} m2)"))
        sin = [l.numero for l in m.lotes if l.frente < 5]
        res.append((f"{m.nombre}: todos los lotes con frente a la avenida", not sin,
                    ", ".join(f"L{l.numero} {l.frente:.2f} m" for l in m.lotes)))
        cierre = m.area_total - m.area_donacion - m.area_vendible
        res.append((f"{m.nombre}: cierre de áreas", abs(cierre) < 0.05, f"{cierre:+.3f} m2"))
        tras = sum(a.poligono.intersection(b.poligono).area
                   for i, a in enumerate(m.lotes) for b in m.lotes[i + 1:])
        tras += sum(l.poligono.intersection(m.donacion).area for l in m.lotes)
        res.append((f"{m.nombre}: sin traslapes", tras < 0.01, f"{tras:.4f} m2"))
        conexo = all(len(polygons(l.poligono)) == 1 for l in m.lotes)
        res.append((f"{m.nombre}: cada lote es un solo polígono", conexo, ""))
    return res


# ---------------------------------------------------------------------------
# DXF
# ---------------------------------------------------------------------------
def _cotas(msp, poly: Polygon, av: LineString, vistos: set):
    p = poly.simplify(0.05)
    c = list(p.exterior.coords)
    for a, b in zip(c, c[1:]):
        largo = math.dist(a, b)
        if largo < 5:
            continue
        k = frozenset((tuple(round(v, 1) for v in a), tuple(round(v, 1) for v in b)))
        if k in vistos:
            continue
        vistos.add(k)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        nx, ny = -(b[1] - a[1]) / largo, (b[0] - a[0]) / largo
        signo = 1 if p.contains(Point(mx + nx * 2, my + ny * 2)) else -1
        frente = av.buffer(0.1).contains(LineString([a, b]))
        msp.add_aligned_dim(p1=a, p2=b, distance=signo * 2.5, dimstyle=DIMSTYLE,
                            text="FRENTE <>" if frente else "<>",
                            dxfattribs={"layer": "COTAS"}).render()


def _flecha_acceso(msp, lote: Lote6, av: LineString, poly: Polygon):
    tramo = lote.poligono.boundary.intersection(av.buffer(0.05))
    ls = lines(tramo)
    if not ls:
        return
    t = max(ls, key=lambda x: x.length)
    q = t.interpolate(0.5, normalized=True)
    (x0, y0), (x1, y1) = t.coords[0], t.coords[-1]
    ux, uy = unit(x1 - x0, y1 - y0)
    nx, ny = -uy, ux
    if not poly.contains(Point(q.x + nx * 2, q.y + ny * 2)):
        nx, ny = -nx, -ny
    s = (q.x - nx * 7, q.y - ny * 7)  # desde la avenida hacia el lote
    e = (q.x + nx * 3, q.y + ny * 3)
    msp.add_line(s, e, dxfattribs={"layer": "TEXTOS", "color": 1})
    h = msp.add_hatch(color=1, dxfattribs={"layer": "TEXTOS"})
    h.paths.add_polyline_path([(e[0] + nx * 2.5, e[1] + ny * 2.5),
                               (e[0] + ux * 1.2, e[1] + uy * 1.2),
                               (e[0] - ux * 1.2, e[1] - uy * 1.2)], is_closed=True)
    msp.add_text(f"ACCESO LOTE {lote.numero}", height=1.4,
                 dxfattribs={"layer": "TEXTOS", "color": 1,
                             "rotation": _rotacion(ux, uy)}).set_placement(
        (q.x - nx * 4, q.y - ny * 4), align=TextEntityAlignment.MIDDLE_CENTER)


def dibujar_propuesta(doc, msp, n: int, macros: list[Macro6], dx: float = 0.0):
    prop = cfg.PROPUESTAS[n]
    T = (lambda g: translate(g, dx, 0)) if dx else (lambda g: g)
    predios = unary_union([m.poligono for m in macros])
    for v in cfg.VIALIDADES:
        # Guarniciones/banquetas pegadas al predio (< 2 m) en VIAL_BANQUETA.
        capa = ("VIAL_BANQUETA" if max(predios.boundary.distance(Point(p)) for p in v) < 2.0
                else "VIAL_ASFALTO")
        msp.add_lwpolyline([(x + dx, y) for x, y in v], dxfattribs={"layer": capa})
    for m in macros:
        av = T(m.avenida)
        poly = T(m.poligono)
        don = T(m.donacion)
        _relleno(msp, don, "DONACION", 3, 0.55)
        for p in polygons(don):
            _polilinea(msp, p.exterior.coords, "DONACION")
        c = don.representative_point()
        pct = 100 * m.area_donacion / m.area_total
        txt = f"DONACIÓN {pct:.2f} %\\P{m2(m.area_donacion)}"
        if m.ancho_donacion:
            txt += f"\\PANCHO {m.ancho_donacion:.2f} m"
        rot = 0.0
        if prop["donacion"] == "fondo":
            (p0, p1) = cfg.MACROLOTES[m.nombre]["lindero_fondo"]
            rot = _rotacion(p1[0] - p0[0], p1[1] - p0[1])
        msp.add_mtext(txt, dxfattribs={"layer": "TEXTOS", "char_height": 1.6,
                                       "rotation": rot}).set_location((c.x, c.y),
                                                                      attachment_point=5)
        vistos: set = set()
        for l in m.lotes:
            lp = T(l.poligono)
            _relleno(msp, lp, "LOTES", 2, 0.6)
            _polilinea(msp, lp.exterior.coords, "LOTES")
            q = lp.centroid if lp.buffer(-6).contains(lp.centroid) else lp.representative_point()
            msp.add_mtext(
                f"LOTE {l.numero}\\P{m2(l.area)}\\P{100 * l.area / m.area_total:.2f} % DEL "
                f"{m.nombre}\\PFRENTE A AVENIDA {l.frente:,.2f} m",
                dxfattribs={"layer": "TEXTOS", "char_height": 2.2}).set_location(
                (q.x, q.y), attachment_point=5)
            _cotas(msp, lp, av, vistos)
            _flecha_acceso(msp, l, av, poly)
        r = cfg.MACROLOTES[m.nombre]["rotulo"]
        msp.add_text(m.nombre, height=4.0, dxfattribs={"layer": "TEXTOS", "color": 4}) \
            .set_placement((r[0] + dx, r[1]), align=TextEntityAlignment.MIDDLE_CENTER)
    # Rótulo de la avenida lateral (diagonal), a media sección.
    av = macros[0].avenida
    q = av.interpolate(0.62, normalized=True)
    (x0, y0), (x1, y1) = av.coords[0], av.coords[-1]
    ux, uy = unit(x1 - x0, y1 - y0)
    msp.add_text("AVENIDA LATERAL (DIAGONAL)", height=3.0,
                 dxfattribs={"layer": "VIAL_ASFALTO", "rotation": _rotacion(ux, uy)}) \
        .set_placement((q.x + uy * 7 + dx, q.y - ux * 7), align=TextEntityAlignment.MIDDLE_CENTER)
    # Drenaje
    x, y = cfg.PUNTO_DRENAJE
    x += dx
    msp.add_circle((x, y), 2.0, dxfattribs={"layer": "DRENAJE"})
    msp.add_line((x - 3, y), (x + 3, y), dxfattribs={"layer": "DRENAJE"})
    msp.add_line((x, y - 3), (x, y + 3), dxfattribs={"layer": "DRENAJE"})
    msp.add_mtext("PUNTO MÁS BAJO / SALIDA DE DRENAJE\\P"
                  f"X = {cfg.PUNTO_DRENAJE[0]:,.2f}  Y = {y:,.2f}\\P"
                  f"COTA {cfg.COTA_MINIMA:.2f} m - PENDIENTE {cfg.PENDIENTE_DRENAJE * 100:.1f} %",
                  dxfattribs={"layer": "DRENAJE", "char_height": 1.8}).set_location(
        (x - 4, y - 4), attachment_point=3)
    # Tablas
    _tablas(doc, msp, n, macros, (357880.0 + dx, 2285470.0))
    msp.add_text(prop["nombre"], height=4.5, dxfattribs={"layer": "TEXTOS"}).set_placement(
        (357880.0 + dx, 2285500.0), align=TextEntityAlignment.BOTTOM_LEFT)
    msp.add_mtext(prop["descripcion"], dxfattribs={
        "layer": "TEXTOS", "char_height": 2.0, "width": 160.0}).set_location(
        (357880.0 + dx, 2285497.0), attachment_point=1)


def _tablas(doc, msp, n: int, macros: list[Macro6], origen):
    cap = {"layer": "TABLA_CONTENIDOS"}
    filas = [("T", f"CUADRO DE ÁREAS - PROPUESTA {n}", "")]
    tot = sum(m.area_total for m in macros)
    don = sum(m.area_donacion for m in macros)
    for m in macros:
        filas += [
            ("S", m.nombre, ""),
            ("R", "Área total", m2(m.area_total)),
            ("R", f"Donación ({100 * m.area_donacion / m.area_total:.2f} %)", m2(m.area_donacion)),
            ("R", "Área vendible", m2(m.area_vendible)),
            ("R", "Número de lotes", str(len(m.lotes))),
            ("R", "Área por lote (iguales)", m2(m.lotes[0].area)),
        ]
    filas += [
        ("S", "TOTALES DEL PROYECTO", ""),
        ("R", "Área total", m2(tot)),
        ("R", "Donación", m2(don)),
        ("R", "Porcentaje de donación", f"{100 * don / tot:.2f} %"),
        ("R", "Área vendible", m2(sum(m.area_vendible for m in macros))),
        ("R", "Total de lotes", str(sum(len(m.lotes) for m in macros))),
    ]
    nombre = f"TABLA_CONTENIDOS_P{n}"
    blk = doc.blocks.new(nombre)
    _dibujar_tabla(blk, filas, 58.0, 30.0, 3.6, cap)
    msp.add_blockref(nombre, origen, dxfattribs=cap)

    lotes = [("T", "CUADRO DE LOTES", ""), ("H", "LOTE / MACROLOTE", "ÁREA / FRENTE / %")]
    for m in macros:
        for l in m.lotes:
            lotes.append(("R", f"LOTE {l.numero}  ({m.nombre})",
                          f"{l.area:,.2f} m2 / {l.frente:,.2f} m / "
                          f"{100 * l.area / m.area_total:.2f} %"))
    blk2 = doc.blocks.new(nombre + "_LOTES")
    _dibujar_tabla(blk2, lotes, 36.0, 40.0, 3.4, cap)
    msp.add_blockref(nombre + "_LOTES", (origen[0] + 94, origen[1]), dxfattribs=cap)


def escribir(ruta: Path, items: list[tuple[int, list[Macro6], float]]) -> Path:
    doc = nuevo_documento()
    msp = doc.modelspace()
    for n, macros, dx in items:
        dibujar_propuesta(doc, msp, n, macros, dx)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ancho = 450 * len(items)
    doc.set_modelspace_vport(height=440, center=(357870 + ancho / 2, 2285300))
    doc.saveas(ruta)
    return ruta


def verificar_dxf(ruta: Path) -> list[tuple[str, bool, str]]:
    doc = ezdxf.readfile(ruta)
    aud = doc.audit()
    msp = doc.modelspace()
    res = [("DXF abre con ezdxf.readfile", True, ruta.name),
           ("DXF auditoría", not aud.has_errors, f"{len(aud.errors)} errores"),
           ("DXF $INSUNITS = 6", doc.header.get("$INSUNITS") == 6, "metros")]
    for capa, color in CAPAS.items():
        k = len(msp.query(f'*[layer=="{capa}"]'))
        res.append((f"DXF capa {capa}", capa in doc.layers and k > 0, f"{k} entidades"))
    return res
