"""Escritura del plano DXF con ezdxf."""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import LineString, Point, Polygon

import config
from geometry import Macrolote, polygons, seccion_en

CAPAS = {
    "LOTES": 2,
    "DONACION": 3,
    "VIAL_ASFALTO": 8,
    "VIAL_BANQUETA": 9,
    "DRENAJE": 1,
    "COTAS": 6,
    "TEXTOS": 7,
    "TABLA_CONTENIDOS": 7,
}

DIMSTYLE = "COTAS_M"
H_TEXTO_LOTE = 1.6
H_COTA = 0.9


def m2(v: float) -> str:
    return f"{v:,.2f} m2"


def _rotacion(dx: float, dy: float) -> float:
    """Ángulo legible (texto nunca de cabeza) en grados."""
    a = math.degrees(math.atan2(dy, dx))
    if a > 90:
        a -= 180
    elif a <= -90:
        a += 180
    return a


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------
def nuevo_documento() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 6  # metros
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    doc.header["$LUPREC"] = 2
    doc.header["$LTSCALE"] = 0.5
    for nombre, color in CAPAS.items():
        doc.layers.add(nombre, color=color)
    doc.layers.get("VIAL_BANQUETA").dxf.linetype = "CONTINUOUS"

    ds = doc.dimstyles.duplicate_entry("EZDXF", DIMSTYLE)
    ds.dxf.dimtxt = H_COTA
    ds.dxf.dimasz = 0.6
    ds.dxf.dimexe = 0.4
    ds.dxf.dimexo = 0.3
    ds.dxf.dimgap = 0.2
    ds.dxf.dimlfac = 1.0
    ds.dxf.dimdec = 2
    ds.dxf.dimlunit = 2
    ds.dxf.dimtad = 1
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    ds.dxf.dimclrd = 256  # BYLAYER
    ds.dxf.dimclre = 256
    ds.dxf.dimclrt = 256
    ds.dxf.dimpost = "<> m"
    return doc


def _polilinea(msp, coords, capa: str, **dxfattribs):
    pts = list(coords)
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    return msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": capa, **dxfattribs})


def _contorno(msp, geom, capa: str):
    for p in polygons(geom):
        _polilinea(msp, p.exterior.coords, capa)
        for r in p.interiors:
            _polilinea(msp, r.coords, capa)


def _relleno(msp, geom, capa: str, color: int, transparencia: float):
    for p in polygons(geom):
        h = msp.add_hatch(color=color, dxfattribs={"layer": capa})
        h.paths.add_polyline_path(list(p.exterior.coords)[:-1], is_closed=True, flags=1)
        for r in p.interiors:
            h.paths.add_polyline_path(list(r.coords)[:-1], is_closed=True, flags=0)
        h.transparency = transparencia


# ---------------------------------------------------------------------------
# Elementos del plano
# ---------------------------------------------------------------------------
def _cotas_lote(msp, lote, vistos: set, row):
    poly: Polygon = lote.poligono.simplify(0.05)
    coords = list(poly.exterior.coords)
    for a, b in zip(coords, coords[1:]):
        largo = math.dist(a, b)
        if largo < 5.0:
            continue
        clave = frozenset((tuple(round(v, 1) for v in a), tuple(round(v, 1) for v in b)))
        if clave in vistos:
            continue
        vistos.add(clave)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ux, uy = (b[0] - a[0]) / largo, (b[1] - a[1]) / largo
        nx, ny = -uy, ux
        es_frente = row.buffer(0.05).contains(LineString([a, b]))
        # Línea de cota hacia el interior del lote.
        signo = 1 if poly.contains(Point(mx + nx * 1.5, my + ny * 1.5)) else -1
        texto = "FRENTE <>" if es_frente else "<>"
        dim = msp.add_aligned_dim(p1=a, p2=b, distance=signo * 1.8, dimstyle=DIMSTYLE,
                                  text=texto, dxfattribs={"layer": "COTAS"})
        dim.render()


def _textos_lote(msp, lote):
    p = lote.poligono.representative_point()
    if lote.poligono.buffer(-4).contains(lote.poligono.centroid):
        p = lote.poligono.centroid
    ancho, fondo = lote.ancho_fondo()
    texto = (f"LOTE {lote.numero}\\P{m2(lote.area)}\\P"
             f"FRENTE {lote.frente:,.2f} m\\P{ancho:,.2f} x {fondo:,.2f} m")
    mt = msp.add_mtext(texto, dxfattribs={"layer": "TEXTOS", "char_height": H_TEXTO_LOTE,
                                          "style": "OpenSans"})
    mt.set_location((p.x, p.y), attachment_point=5)


def _seccion_vial(msp, m: Macrolote, fraccion: float):
    (x, y), (tx, ty), (nx, ny) = seccion_en(m, fraccion)
    semi = config.SECCION_TOTAL / 2
    offs = [-semi, -semi + config.BANQUETA, semi - config.BANQUETA, semi]
    pts = [(x + nx * o, y + ny * o) for o in offs]
    # Línea de sección y cotas parciales 1.50 | 9.00 | 1.50
    msp.add_line(pts[0], pts[-1], dxfattribs={"layer": "VIAL_ASFALTO", "linetype": "DASHED"})
    for a, b in zip(pts, pts[1:]):
        dim = msp.add_aligned_dim(p1=a, p2=b, distance=2.5, dimstyle=DIMSTYLE,
                                  dxfattribs={"layer": "COTAS"})
        dim.render()
    rot = _rotacion(tx, ty)
    msp.add_text("1.50m | 9.00m | 1.50m", height=1.0,
                 dxfattribs={"layer": "TEXTOS", "rotation": _rotacion(nx, ny)}).set_placement(
        (x + tx * 4.5, y + ty * 4.5), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("BANQUETA 1.5m - ARROYO 9.0m - BANQUETA 1.5m", height=0.9,
                 dxfattribs={"layer": "TEXTOS", "rotation": rot}).set_placement(
        (x - tx * 14, y - ty * 14), align=TextEntityAlignment.MIDDLE_CENTER)


def _drenaje(msp, cota_min: float):
    x, y = config.PUNTO_DRENAJE
    msp.add_circle((x, y), 2.0, dxfattribs={"layer": "DRENAJE"})
    msp.add_line((x - 3, y), (x + 3, y), dxfattribs={"layer": "DRENAJE"})
    msp.add_line((x, y - 3), (x, y + 3), dxfattribs={"layer": "DRENAJE"})
    h = msp.add_hatch(color=1, dxfattribs={"layer": "DRENAJE"})
    h.paths.add_polyline_path([(x - 9, y - 6), (x - 4.5, y - 3.5), (x - 6.5, y - 2.0)],
                              is_closed=True)
    msp.add_line((x - 2, y - 1.3), (x - 7, y - 4.5), dxfattribs={"layer": "DRENAJE"})
    msp.add_mtext(
        "PUNTO MÁS BAJO / SALIDA DE DRENAJE\\P"
        f"X = {x:,.2f}  Y = {y:,.2f}\\P"
        f"COTA MÍNIMA = {cota_min:.2f} m  -  PENDIENTE {config.PENDIENTE_DRENAJE * 100:.1f} %",
        dxfattribs={"layer": "DRENAJE", "char_height": 1.8},
    ).set_location((x - 10, y - 7), attachment_point=3)


def _tabla(doc, msp, macros: list[Macrolote], nombre: str, origen):
    """Bloque del cuadro de metrados (TOC) e inserción en el espacio libre."""
    blk = doc.blocks.new(nombre)
    cap = {"layer": "TABLA_CONTENIDOS"}
    w1, w2, h = 62.0, 30.0, 3.6
    filas: list[tuple[str, str, str]] = [("T", "CUADRO DE METRADOS - PARQUE INDUSTRIAL", "")]
    tot = sum(m.area_total for m in macros)
    don = sum(m.area_donacion for m in macros)
    for m in macros:
        filas += [
            ("S", f"{m.nombre}  ({m.clave})", ""),
            ("R", "Área total", m2(m.area_total)),
            ("R", f"Área de donación ({100 * m.area_donacion / m.area_total:.2f} %)",
             m2(m.area_donacion)),
            ("R", "Área de vialidad (arroyo + banquetas)", m2(m.area_vialidad)),
            ("R", "Área vendible (lotes)", m2(m.area_vendible)),
            ("R", "Número de lotes", f"{len(m.lotes)}"),
        ]
    filas += [
        ("S", "TOTALES DEL PROYECTO", ""),
        ("R", "Área total", m2(tot)),
        ("R", "Área de donación", m2(don)),
        ("R", "Porcentaje de donación", f"{100 * don / tot:.2f} %"),
        ("R", "Área de vialidad", m2(sum(m.area_vialidad for m in macros))),
        ("R", "Área vendible", m2(sum(m.area_vendible for m in macros))),
        ("R", "Total de lotes", f"{sum(len(m.lotes) for m in macros)}"),
    ]
    _dibujar_tabla(blk, filas, w1, w2, h, cap)
    msp.add_blockref(nombre, origen, dxfattribs=cap)

    # Cuadro de lotes (número, macrolote, área, frente) a la derecha.
    lotes = [("T", "CUADRO DE LOTES", "")]
    lotes += [("H", "LOTE / MACROLOTE", "ÁREA / FRENTE")]
    for m in macros:
        for l in m.lotes:
            lotes.append(("R", f"LOTE {l.numero}  ({m.nombre})",
                          f"{l.area:,.2f} m2 / {l.frente:,.2f} m"))
    blk2 = doc.blocks.new(nombre + "_LOTES")
    _dibujar_tabla(blk2, lotes, 36.0, 32.0, 2.8, cap)
    msp.add_blockref(nombre + "_LOTES", (origen[0] + w1 + w2 + 6, origen[1]), dxfattribs=cap)


def _dibujar_tabla(blk, filas, w1, w2, h, cap):
    w = w1 + w2
    y = 0.0
    for tipo, a, b in filas:
        alto = h * (1.3 if tipo == "T" else 1.0)
        blk.add_lwpolyline([(0, y), (w, y), (w, y - alto), (0, y - alto)], close=True,
                           dxfattribs=cap)
        th = alto * (0.42 if tipo == "T" else 0.38)
        if tipo in ("T", "S"):
            if tipo == "S":
                hh = blk.add_hatch(color=8, dxfattribs=cap)
                hh.paths.add_polyline_path([(0, y), (w, y), (w, y - alto), (0, y - alto)])
                hh.transparency = 0.7
            blk.add_text(a, height=th, dxfattribs=cap).set_placement(
                (w / 2, y - alto / 2), align=TextEntityAlignment.MIDDLE_CENTER)
        else:
            blk.add_line((w1, y), (w1, y - alto), dxfattribs=cap)
            blk.add_text(a, height=th, dxfattribs=cap).set_placement(
                (1.0, y - alto / 2), align=TextEntityAlignment.MIDDLE_LEFT)
            blk.add_text(b, height=th, dxfattribs=cap).set_placement(
                (w - 1.0, y - alto / 2), align=TextEntityAlignment.MIDDLE_RIGHT)
        y -= alto


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
def escribir_dxf(macros: list[Macrolote], ruta: Path, cota_min: float,
                 titulo: str = "") -> Path:
    doc = nuevo_documento()
    msp = doc.modelspace()

    for m in macros:
        # Vialidad
        _relleno(msp, m.arroyo, "VIAL_ASFALTO", 8, 0.55)
        _contorno(msp, m.arroyo, "VIAL_ASFALTO")
        _relleno(msp, m.banqueta, "VIAL_BANQUETA", 9, 0.4)
        _contorno(msp, m.derecho_via, "VIAL_BANQUETA")
        eje = m.eje_completo.intersection(m.derecho_via)
        for ln in getattr(eje, "geoms", [eje]):
            if ln.length > 1:
                msp.add_lwpolyline(list(ln.coords), dxfattribs={
                    "layer": "VIAL_ASFALTO", "linetype": "CENTER", "color": 1})
        # Donación
        _relleno(msp, m.donacion, "DONACION", 3, 0.6)
        _contorno(msp, m.donacion, "DONACION")
        for p in polygons(m.donacion):
            if p.area > 200:
                c = p.representative_point()
                msp.add_mtext(f"DONACIÓN\\P{m2(p.area)}", dxfattribs={
                    "layer": "TEXTOS", "char_height": 1.6}).set_location((c.x, c.y),
                                                                       attachment_point=5)
        # Lotes
        vistos: set = set()
        for l in m.lotes:
            _relleno(msp, l.poligono, "LOTES", 2, 0.65)
            _polilinea(msp, l.poligono.exterior.coords, "LOTES")
            _textos_lote(msp, l)
            _cotas_lote(msp, l, vistos, m.derecho_via)
        # Secciones viales rotuladas en varios tramos
        for f in (0.25, 0.55):
            _seccion_vial(msp, m, f)
        # Nombre del macrolote y acceso
        a = m.acceso
        msp.add_text(f"ACCESO {m.nombre}", height=1.8, dxfattribs={
            "layer": "TEXTOS"}).set_placement((a.x, a.y - 4.5),
                                              align=TextEntityAlignment.TOP_CENTER)
        c = m.poligono.centroid
        msp.add_text(f"{m.nombre}", height=4.0, dxfattribs={
            "layer": "TEXTOS", "color": 4}).set_placement(
            config.MACROLOTES[m.nombre].get("rotulo", (c.x, c.y)),
            align=TextEntityAlignment.MIDDLE_CENTER)

    _drenaje(msp, cota_min)
    _tabla(doc, msp, macros, "TABLA_CONTENIDOS", config.TABLA_ORIGEN)
    if titulo:
        msp.add_text(titulo, height=4.0, dxfattribs={"layer": "TEXTOS"}).set_placement(
            (config.TABLA_ORIGEN[0], config.TABLA_ORIGEN[1] + 12),
            align=TextEntityAlignment.BOTTOM_LEFT)

    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc.set_modelspace_vport(height=420, center=(358056, 2285300))
    doc.saveas(ruta)
    return ruta
