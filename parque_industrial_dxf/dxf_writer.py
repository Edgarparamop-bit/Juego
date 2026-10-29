"""Escritura DXF (solo ezdxf, entidades nativas, unidades en metros)."""
import math

import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

import config as C

CAPAS = [
    ("VIAL_ASFALTO", 1, "Arroyo asfáltico 9.00 m (incluye retornos rectangulares)"),
    ("VIAL_BANQUETA", 3, "Banquetas 1.50 m"),
    ("LOTES", 7, "Lotes industriales, frente >= 25.00 m"),
    ("DONACION_VERDE", 4, "Donación municipal perimetral 10 %"),
    ("EJES_VIALES", 2, "Ejes de colector, calles y retornos"),
    ("COTAS", 6, "Cotas de sección y frentes"),
    ("DRENAJE", 5, "Punto bajo, escurrimiento y cotas de rasante"),
    ("LIMITE", 8, "Límite del polígono original"),
    ("TEXTO", 7, "Títulos y notas"),
]


def _rings(poly):
    yield list(poly.exterior.coords)
    for r in poly.interiors:
        yield list(r.coords)


def _pl(msp, geom, layer):
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.area < 1e-3:
            continue
        for ring in _rings(g):
            msp.add_lwpolyline([(x, y) for x, y in ring[:-1]], close=True, dxfattribs={"layer": layer})


def _txt(msp, s, p, h, layer="TEXTO", rot=0.0, align=TA.MIDDLE_CENTER):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": layer, "style": "Standard"})
    t.set_placement(p, align=align)


def _flecha(msp, a, b, layer="DRENAJE", head=2.5):
    msp.add_line(a, b, dxfattribs={"layer": layer})
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (math.radians(150), math.radians(-150)):
        msp.add_line(b, (b[0] + head * math.cos(ang + da), b[1] + head * math.sin(ang + da)), dxfattribs={"layer": layer})


def _rot_legible(t):
    rot = math.degrees(math.atan2(t[1], t[0]))
    if rot > 90:
        rot -= 180
    if rot <= -90:
        rot += 180
    return rot


def _etiqueta_calle(msp, nombre, a, b):
    Ls = math.dist(a, b)
    t = ((b[0] - a[0]) / Ls, (b[1] - a[1]) / Ls)
    n = (-t[1], t[0])
    rot = _rot_legible(t)
    P = lambda s, w: (a[0] + t[0] * s + n[0] * w, a[1] + t[1] * s + n[1] * w)
    s_lab = Ls * 0.35
    _txt(msp, nombre, P(s_lab, 2.6), C.H_NOTA, "COTAS", rot)
    _txt(msp, "SECCIÓN VIAL 12.00 m", P(s_lab, 0.0), C.H_NOTA, "COTAS", rot)
    _txt(msp, "= 1.50 + 9.00 + 1.50", P(s_lab, -2.4), C.H_NOTA, "COTAS", rot)
    s_c = Ls * 0.75
    msp.add_line(P(s_c, -6.0), P(s_c, 6.0), dxfattribs={"layer": "COTAS"})
    for w in (-6.0, -4.5, 4.5, 6.0):
        msp.add_line(P(s_c - 0.8, w), P(s_c + 0.8, w), dxfattribs={"layer": "COTAS"})
    for w, s_ in ((-5.25, "1.50"), (0.0, "9.00"), (5.25, "1.50")):
        _txt(msp, s_, P(s_c + 2.4, w), C.H_NOTA, "COTAS", rot + 90)
    _txt(msp, "12.00 m", P(s_c - 3.0, 0.0), C.H_NOTA, "COTAS", rot + 90)


def escribir(res, metr, ruta):
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6
    doc.header["$MEASUREMENT"] = 1
    for nombre, color, _ in CAPAS:
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()

    for P in res["polys"].values():
        msp.add_lwpolyline(list(P.exterior.coords)[:-1], close=True, dxfattribs={"layer": "LIMITE"})
    _pl(msp, res["don"], "DONACION_VERDE")
    _pl(msp, res["asf"], "VIAL_ASFALTO")
    _pl(msp, res["banq"], "VIAL_BANQUETA")

    # ejes
    for k, cs in res["cols"].items():
        msp.add_lwpolyline(cs, dxfattribs={"layer": "EJES_VIALES", "linetype": "CENTER"})
        a, b = max(zip(cs[:-1], cs[1:]), key=lambda s: math.dist(*s))
        _etiqueta_calle(msp, f"COLECTOR PRINCIPAL {k}", a, b)
    msp.add_lwpolyline(res["cruce"], dxfattribs={"layer": "EJES_VIALES", "linetype": "DASHED"})
    m = ((res["cruce"][0][0] + res["cruce"][1][0]) / 2, (res["cruce"][0][1] + res["cruce"][1][1]) / 2)
    _txt(msp, "CRUCE PLUVIAL BAJO CALLE MUNICIPAL", (m[0] + 4, m[1]), C.H_NOTA, "DRENAJE", align=TA.MIDDLE_LEFT)
    for c in res["calles"]:
        msp.add_lwpolyline(c["pts"], dxfattribs={"layer": "EJES_VIALES", "linetype": "CENTER"})
        a, b = max(zip(c["pts"][:-1], c["pts"][1:]), key=lambda s: math.dist(*s))
        _etiqueta_calle(msp, c["nombre"], a, b)
        e, t = c["pts"][-1], c["t_fin"]
        n = (-t[1], t[0])
        for sg in c["brazos"]:
            fin = (e[0] + n[0] * sg * (4.5 + C.BRAZO_RETORNO), e[1] + n[1] * sg * (4.5 + C.BRAZO_RETORNO))
            msp.add_line(e, fin, dxfattribs={"layer": "EJES_VIALES", "linetype": "CENTER"})
        tipo = "T" if len(c["brazos"]) == 2 else "L"
        _txt(msp, f"RETORNO RECTANGULAR EN {tipo}", (e[0] + t[0] * 9, e[1] + t[1] * 9), C.H_NOTA, "COTAS", _rot_legible(n))
        _txt(msp, f"BRAZO {C.BRAZO_RETORNO:.2f} m + ARROYO 9.00", (e[0] + t[0] * 11.2, e[1] + t[1] * 11.2), C.H_NOTA, "COTAS", _rot_legible(n))

    # lotes
    for L in res["lotes"]:
        g = L["geom"]
        _pl(msp, g, "LOTES")
        c = g.representative_point()
        _txt(msp, L["id"], (c.x, c.y + 2.4), C.H_TEXTO, "TEXTO")
        _txt(msp, f"FRENTE {L['frente_alineamiento']:.2f} m", (c.x, c.y), C.H_NOTA, "COTAS")
        _txt(msp, f"{g.area:,.2f} m2", (c.x, c.y - 2.2), C.H_NOTA, "TEXTO")

    # drenaje
    dren = res["dren"]
    for hi, lo in dren["flechas"]:
        Ls = math.dist(hi, lo)
        if Ls < 10:
            continue
        t = ((lo[0] - hi[0]) / Ls, (lo[1] - hi[1]) / Ls)
        m = ((hi[0] + lo[0]) / 2, (hi[1] + lo[1]) / 2)
        _flecha(msp, (m[0] - t[0] * 4, m[1] - t[1] * 4), (m[0] + t[0] * 4, m[1] + t[1] * 4))
    for k, z in dren["nodos"].items():
        _txt(msp, f"Z={z:.2f}", (k[0] + 2.0, k[1] + 1.4), C.H_NOTA, "DRENAJE", align=TA.LEFT)
    pb = res["punto_bajo"]
    msp.add_circle(pb, radius=3.0, dxfattribs={"layer": "DRENAJE"})
    msp.add_circle(pb, radius=1.5, dxfattribs={"layer": "DRENAJE"})
    msp.add_line((pb[0] - 4, pb[1]), (pb[0] + 4, pb[1]), dxfattribs={"layer": "DRENAJE"})
    msp.add_line((pb[0], pb[1] - 4), (pb[0], pb[1] + 4), dxfattribs={"layer": "DRENAJE"})
    _flecha(msp, (pb[0], pb[1] - 3), (pb[0], pb[1] - 11), head=3.0)
    _txt(msp, "PUNTO MÁS BAJO / SALIDA DE DRENAJE", (pb[0] + 6, pb[1] - 6), C.H_TEXTO, "DRENAJE", align=TA.LEFT)
    _txt(msp, f"X={pb[0]:.2f}  Y={pb[1]:.2f}  Z={C.COTA_PUNTO_BAJO:.2f} m (supuesta)", (pb[0] + 6, pb[1] - 9), C.H_NOTA, "DRENAJE", align=TA.LEFT)
    _txt(msp, f"UTM X={pb[0]+C.ORIGEN_UTM[0]:.2f}  Y={pb[1]+C.ORIGEN_UTM[1]:.2f}", (pb[0] + 6, pb[1] - 11.5), C.H_NOTA, "DRENAJE", align=TA.LEFT)
    _txt(msp, "Descarga a red municipal sobre avenida principal", (pb[0] + 6, pb[1] - 14), C.H_NOTA, "DRENAJE", align=TA.LEFT)

    for i, gp in enumerate(res["gaps"]):
        _txt(msp, f"GAP {i+1}: ACCESO VIAL {C.SECCION:.2f} m", (gp["x"] + 8, gp["y"] + 3), C.H_NOTA, "DONACION_VERDE", align=TA.LEFT)

    # título, leyenda, cuadro de áreas, notas
    x0 = max(P.bounds[2] for P in res["polys"].values()) + 20
    ytop = max(P.bounds[3] for P in res["polys"].values())
    _txt(msp, res["op"]["titulo"], (x0, ytop + 18), C.H_TITULO, "TEXTO", align=TA.LEFT)
    _txt(msp, "PARQUE INDUSTRIAL - MACROLOTES A Y B - ESCALA 1:1 - UNIDADES: METROS - ORIGEN (0,0)", (x0, ytop + 14), C.H_NOTA, "TEXTO", align=TA.LEFT)
    _txt(msp, f"Para superponer en lotificaciones.dwg: mover de (0,0) a ({C.ORIGEN_UTM[0]:.3f}, {C.ORIGEN_UTM[1]:.3f})", (x0, ytop + 11), C.H_NOTA, "TEXTO", align=TA.LEFT)
    _txt(msp, "SECCIÓN VIAL 12.00 m = 1.50 + 9.00 + 1.50", (x0, ytop + 7), C.H_TEXTO, "COTAS", align=TA.LEFT)
    y = ytop
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
        ("Área total del polígono (A + B)", f"{metr['area_total']:,.2f} m2", "100.00 %"),
        ("Donación verde perimetral", f"{metr['area_donacion']:,.2f} m2", f"{metr['pct_donacion']:.2f} %"),
        ("Vialidad (asfalto + banquetas)", f"{metr['area_vial']:,.2f} m2", f"{metr['pct_vial']:.2f} %"),
        ("  Asfalto 9.00 m + retornos", f"{metr['area_asfalto']:,.2f} m2", ""),
        ("  Banquetas 1.50 m", f"{metr['area_banqueta']:,.2f} m2", ""),
        ("Lotes vendibles", f"{metr['area_lotes']:,.2f} m2", f"{metr['pct_lotes']:.2f} %"),
        ("Número de lotes", f"{metr['n_lotes']}", ""),
        ("Longitud de vialidad (ejes)", f"{metr['long_vial']:,.2f} m", ""),
        ("Pendiente longitudinal supuesta", f"{100*C.PENDIENTE_LONGITUDINAL:.1f} %", ""),
        ("Cota inicio / cota mínima", f"{metr['cota_max']:.2f} / {metr['cota_min']:.2f} m", ""),
    ]
    for a, b, c in filas:
        _txt(msp, a, (x0, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_LEFT)
        _txt(msp, b, (x0 + 66, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_RIGHT)
        if c:
            _txt(msp, c, (x0 + 80, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_RIGHT)
        y -= 3.2
    y -= 3
    _txt(msp, "NOTAS", (x0, y), C.H_TEXTO, "TEXTO", align=TA.LEFT)
    y -= 4
    notas = res["op"]["notas"] + [
        "Colector principal paralelo al borde más bajo (diagonal), continuo de B hacia A; salida única al sur.",
        "Retornos rectangulares (T o L) con brazos de 17.00 m de arroyo: el camión entra, retrocede y sale de frente.",
        "Lotes desde el alineamiento exterior de banqueta; frentes >= 25.00 m, trapezoidales en los quiebres.",
        "Remanentes sin frente de 25.00 m o < 600 m2 se integran a la donación perimetral.",
        f"Sin topografía: pendiente {100*C.PENDIENTE_LONGITUDINAL:.1f} % hacia la salida; cota supuesta {C.COTA_PUNTO_BAJO:.2f} m.",
    ]
    for nt in notas:
        _txt(msp, "- " + nt, (x0, y), C.H_NOTA, "TEXTO", align=TA.MIDDLE_LEFT)
        y -= 3.2

    xs = [P.bounds for P in res["polys"].values()]
    doc.header["$EXTMIN"] = (min(b[0] for b in xs) - 10, min(min(b[1] for b in xs) - 25, y - 5), 0.0)
    doc.header["$EXTMAX"] = (x0 + 190, ytop + 25, 0.0)
    doc.saveas(ruta)
    return ruta
