"""Escritura DXF (solo ezdxf, entidades nativas, unidades en metros)."""
import math

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

import config as C

CAPAS = [
    ("VIAL_ASFALTO", 1, "Arroyo asfáltico 9.00 m"),
    ("VIAL_BANQUETA", 3, "Banquetas 1.50 m"),
    ("LOTES", 7, "Lotes industriales, frente 25.00 m"),
    ("DONACION_VERDE", 4, "Donación municipal perimetral 10 %"),
    ("EJES_VIALES", 2, "Ejes de vialidad"),
    ("COTAS", 6, "Cotas de sección y frentes"),
    ("DRENAJE", 5, "Punto bajo, escurrimiento y cotas"),
    ("LIMITE", 8, "Límite del polígono"),
    ("TEXTO", 7, "Títulos y notas"),
]


def _rings(poly):
    yield list(poly.exterior.coords)
    for r in poly.interiors:
        yield list(r.coords)


def _pl(msp, poly, layer):
    for g in getattr(poly, "geoms", [poly]):
        if g.geom_type != "Polygon" or g.area < 1e-3:
            continue
        for ring in _rings(g):
            msp.add_lwpolyline([(x, y) for x, y in ring[:-1]], close=True, dxfattribs={"layer": layer})


def _txt(msp, s, p, h, layer="TEXTO", rot=0.0, align=TA.MIDDLE_CENTER):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer, "style": "Standard"})
    t.set_placement(p, align=align)
    return t


def _flecha(msp, a, b, layer="DRENAJE", head=2.5):
    msp.add_line(a, b, dxfattribs={"layer": layer})
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (math.radians(150), math.radians(-150)):
        msp.add_line(b, (b[0] + head * math.cos(ang + da), b[1] + head * math.sin(ang + da)), dxfattribs={"layer": layer})


def escribir(res, metr, ruta):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6          # metros
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    for nombre, color, _ in CAPAS:
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()
    W, L = C.ANCHO, C.LARGO

    # límite, donación, vialidad
    _pl(msp, res["env"], "LIMITE")
    _pl(msp, res["don"], "DONACION_VERDE")
    _pl(msp, res["asf"], "VIAL_ASFALTO")
    _pl(msp, res["banq"], "VIAL_BANQUETA")
    for c in res["lay"]["calles"]:
        msp.add_lwpolyline(c["pts"], dxfattribs={"layer": "EJES_VIALES", "linetype": "CENTER", "ltscale": 0.5})

    # etiquetas de calle y cotas de sección (en el tramo más largo de cada calle)
    for c in res["lay"]["calles"]:
        segs = list(zip(c["pts"][:-1], c["pts"][1:]))
        a, b = max(segs, key=lambda s: math.dist(*s))
        Ls = math.dist(a, b)
        t = ((b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls)
        n = (-t[1], t[0])
        rot = math.degrees(math.atan2(t[1], t[0]))
        if rot > 90 or rot <= -90:
            rot -= 180 if rot > 0 else -180
        P = lambda s, w: (a[0] + t[0] * s + n[0] * w, a[1] + t[1] * s + n[1] * w)
        s_lab = Ls * 0.30
        _txt(msp, c["nombre"], P(s_lab, 2.6), C.H_NOTA, "COTAS", rot)
        _txt(msp, "SECCIÓN VIAL 12.00 m", P(s_lab, 0.0 - 0.0), C.H_NOTA, "COTAS", rot)
        _txt(msp, "= 1.50 + 9.00 + 1.50", P(s_lab, -2.4), C.H_NOTA, "COTAS", rot)
        # cota transversal
        s_c = Ls * 0.72
        msp.add_line(P(s_c, -6.0), P(s_c, 6.0), dxfattribs={"layer": "COTAS"})
        for w in (-6.0, -4.5, 4.5, 6.0):
            msp.add_line(P(s_c - 0.8, w), P(s_c + 0.8, w), dxfattribs={"layer": "COTAS"})
        for w, s_ in ((-5.25, "1.50"), (0.0, "9.00"), (5.25, "1.50")):
            _txt(msp, s_, P(s_c + 2.6, w), C.H_NOTA, "COTAS", rot + 90 if abs(rot) < 1e-6 or True else rot)
        _txt(msp, "12.00 m", P(s_c - 3.2, 0.0), C.H_NOTA, "COTAS", rot + 90)

    # lotes
    for Lt in res["lotes"]:
        g = Lt["geom"]
        _pl(msp, g, "LOTES")
        c = g.centroid
        _txt(msp, Lt["id"], (c.x, c.y + 2.6), C.H_TEXTO, "TEXTO")
        _txt(msp, "FRENTE 25.00 m", (c.x, c.y), C.H_NOTA, "COTAS")
        _txt(msp, f"{g.area:,.2f} m2", (c.x, c.y - 2.3), C.H_NOTA, "TEXTO")

    # drenaje: flechas de escurrimiento sobre los ejes y cotas en nodos
    dren = res["dren"]
    for hi, lo in dren["flechas"]:
        Ls = math.dist(hi, lo)
        if Ls < 8:
            continue
        t = ((lo[0] - hi[0]) / Ls, (lo[1] - hi[1]) / Ls)
        m = ((hi[0] + lo[0]) / 2, (hi[1] + lo[1]) / 2)
        _flecha(msp, (m[0] - t[0] * 4, m[1] - t[1] * 4), (m[0] + t[0] * 4, m[1] + t[1] * 4))
    for k, z in dren["nodos"].items():
        _txt(msp, f"Z={z:.2f}", (k[0] + 2.2, k[1] + 1.4), C.H_NOTA, "DRENAJE", align=TA.LEFT)
    pb = res["lay"]["punto_bajo"]
    msp.add_circle(pb, radius=3.0, dxfattribs={"layer": "DRENAJE"})
    msp.add_circle(pb, radius=1.5, dxfattribs={"layer": "DRENAJE"})
    msp.add_line((pb[0] - 4, pb[1]), (pb[0] + 4, pb[1]), dxfattribs={"layer": "DRENAJE"})
    msp.add_line((pb[0], pb[1] - 4), (pb[0], pb[1] + 4), dxfattribs={"layer": "DRENAJE"})
    _flecha(msp, (pb[0], pb[1] - 4), (pb[0], pb[1] - 12), head=3.0)
    _txt(msp, "PUNTO MÁS BAJO / SALIDA DE DRENAJE", (pb[0] + 6, pb[1] - 6), C.H_TEXTO, "DRENAJE", align=TA.LEFT)
    _txt(msp, f"X={pb[0]:.2f}  Y={pb[1]:.2f}  Z={C.COTA_PUNTO_BAJO:.2f} (supuesta)", (pb[0] + 6, pb[1] - 9), C.H_NOTA, "DRENAJE", align=TA.LEFT)
    _txt(msp, "Descarga a red municipal", (pb[0] + 6, pb[1] - 11.5), C.H_NOTA, "DRENAJE", align=TA.LEFT)

    # gaps de donación
    for i, gp in enumerate(res["gaps"]):
        dy = -(16 + 3 * i) if gp["borde"] == "SUR" else 8
        _txt(msp, f"GAP DONACIÓN {gp['ancho']:.2f} m - {gp['acceso']}", (gp["x"], gp["y"] + dy), C.H_NOTA, "DONACION_VERDE")

    # título y notas
    _txt(msp, res["op"]["titulo"], (W / 2, L + 22), C.H_TITULO, "TEXTO")
    _txt(msp, f"PARQUE INDUSTRIAL - ENVOLVENTE {W:.2f} x {L:.2f} m = {W*L:,.2f} m2 - ESCALA 1:1 - UNIDADES: METROS", (W / 2, L + 18), C.H_NOTA, "TEXTO")
    _txt(msp, "SECCIÓN VIAL 12.00 m = 1.50 + 9.00 + 1.50", (W / 2, L + 14.5), C.H_TEXTO, "COTAS")

    # leyenda y cuadro de áreas (al oriente del polígono)
    x0, y = W + 15, L
    _txt(msp, "LEYENDA DE CAPAS", (x0, y), C.H_TEXTO, "TEXTO", align=TA.LEFT)
    y -= 5
    for nombre, _, desc in CAPAS:
        msp.add_line((x0, y), (x0 + 8, y), dxfattribs={"layer": nombre})
        _txt(msp, f"{nombre}: {desc}", (x0 + 10, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_LEFT)
        y -= 3.5
    y -= 4
    _txt(msp, "CUADRO DE ÁREAS", (x0, y), C.H_TEXTO, "TEXTO", align=TA.LEFT)
    y -= 4.5
    filas = [
        ("Área total del polígono", f"{metr['area_total']:,.2f} m2", "100.00 %"),
        ("Donación verde perimetral", f"{metr['area_donacion']:,.2f} m2", f"{metr['pct_donacion']:.2f} %"),
        ("Vialidad (asfalto + banquetas)", f"{metr['area_vial']:,.2f} m2", f"{metr['pct_vial']:.2f} %"),
        ("  Asfalto 9.00 m", f"{metr['area_asfalto']:,.2f} m2", ""),
        ("  Banquetas 1.50 m", f"{metr['area_banqueta']:,.2f} m2", ""),
        ("Lotes vendibles", f"{metr['area_lotes']:,.2f} m2", f"{metr['pct_lotes']:.2f} %"),
        ("Área verde interna (remanentes)", f"{metr['area_remanente']:,.2f} m2", f"{metr['pct_remanente']:.2f} %"),
        ("Número de lotes", f"{metr['n_lotes']}", ""),
        ("Longitud de vialidad (ejes)", f"{metr['long_vial']:,.2f} m", ""),
        ("Pendiente longitudinal supuesta", f"{100*C.PENDIENTE_LONGITUDINAL:.1f} %", ""),
        ("Cota inicio / cota mínima", f"{metr['cota_max']:.2f} / {metr['cota_min']:.2f} m", ""),
    ]
    for a, b, c in filas:
        _txt(msp, a, (x0, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_LEFT)
        _txt(msp, b, (x0 + 62, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_RIGHT)
        if c:
            _txt(msp, c, (x0 + 76, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_RIGHT)
        y -= 3.2
    y -= 3
    _txt(msp, "NOTAS", (x0, y), C.H_TEXTO, "TEXTO", align=TA.LEFT)
    y -= 4
    notas = res["lay"]["notas"] + [
        "Lotes medidos desde el alineamiento exterior de banqueta; no invaden arroyo ni banqueta.",
        "Remanentes con frente < 25.00 m se dejan como área verde interna (no se crean lotes irregulares).",
        f"Sin topografía: pendiente {100*C.PENDIENTE_LONGITUDINAL:.1f} % hacia el punto bajo; cota supuesta {C.COTA_PUNTO_BAJO:.2f} m.",
    ]
    for nt in notas:
        _txt(msp, "- " + nt, (x0, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_LEFT)
        y -= 3.2

    doc.header["$EXTMIN"] = (-5.0, min(-25.0, y - 5), 0.0)
    doc.header["$EXTMAX"] = (W + 180.0, L + 28.0, 0.0)
    doc.saveas(ruta)
    return ruta
