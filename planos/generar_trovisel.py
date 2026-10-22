"""Genera los planos DXF del trovisel 122 x 244 cm (horizontal).

Dos versiones:
  - trovisel_madera.dxf : postes y bastidor de polín de madera
  - trovisel_metal.dxf  : postes y bastidor de PTR (tubular cuadrado) de acero

Cada archivo contiene alzado posterior, alzado lateral, detalles isométricos de
cada unión, notas, lista de materiales y cuadro de datos. Unidades: cm.

Uso:  python3 generar_trovisel.py [carpeta_salida]
"""
import math
import os
import sys

import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
import numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

from motor3d import Vista, caja, cilindro, prisma, dibujar, limites, unit

# ---------------------------------------------------------------- geometría base
ANCHO = 244.0      # ancho del tablero (eje x)
ALTO = 122.0       # alto del tablero (eje z)
Z_INF = 88.0       # borde inferior sobre el piso
Z_SUP = Z_INF + ALTO   # 210
E_TAB = 1.5        # espesor supuesto del tablero (verificar en obra)
X_POSTES = (61.0, 183.0)   # ejes de postes (a cuartos del ancho)

MADERA = (214, 172, 120)
TABLERO = (236, 236, 228)
CONCRETO = (196, 196, 196)
ACERO = (150, 166, 182)
HERRAJE = (105, 105, 110)
GRAVA = (170, 160, 140)

FECHA = "2026-10-22"

# ---------------------------------------------------------------- utilidades DXF


def nuevo_doc():
    doc = ezdxf.new("R2018", setup=True, units=5)  # 5 = centímetros
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 10
    doc.styles.add("ARIAL", font="arial.ttf")
    capas = [
        ("A-TABLERO", 7, 35), ("A-ESTRUCTURA", 7, 50), ("A-CIMENTACION", 7, 35),
        ("A-RELLENO", 8, 0), ("A-OCULTAS", 8, 25), ("A-EJES", 1, 18),
        ("A-COTAS", 3, 18), ("A-TEXTO", 7, 25), ("A-DETALLES", 7, 35),
        ("A-TERRENO", 7, 50), ("A-MARCO", 7, 70), ("A-HERRAJES", 7, 35),
    ]
    for nombre, col, lw in capas:
        ly = doc.layers.add(nombre, color=col)
        ly.dxf.lineweight = lw
    doc.layers.get("A-OCULTAS").dxf.linetype = "DASHED"
    doc.layers.get("A-EJES").dxf.linetype = "CENTER"
    ds = doc.dimstyles.new("COTAS_CM")
    ds.dxf.dimtxt = 4.0
    ds.dxf.dimasz = 2.8
    ds.dxf.dimexe = 2.0
    ds.dxf.dimexo = 1.5
    ds.dxf.dimgap = 1.0
    ds.dxf.dimdec = 1
    ds.dxf.dimzin = 8
    ds.dxf.dimtad = 1
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    ds.dxf.dimtxsty = "ARIAL"
    ds.dxf.dimclrd = 3
    ds.dxf.dimclre = 3
    ds.dxf.dimclrt = 7
    ds.dxf.dimblk = "ARCHTICK"
    ds.dxf.dimlunit = 2
    ds.dxf.dimdsep = ord(".")
    return doc


def texto(msp, s, x, y, h=4.0, alin=TextEntityAlignment.BOTTOM_LEFT, capa="A-TEXTO", rot=0):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": capa, "style": "ARIAL"})
    t.set_placement((x, y), align=alin)
    return t


def mtexto(msp, s, x, y, h=3.2, ancho=200, capa="A-TEXTO"):
    m = msp.add_mtext(s, dxfattribs={"layer": capa, "style": "ARIAL", "char_height": h,
                                      "width": ancho, "line_spacing_factor": 1.15})
    m.set_location((x, y), attachment_point=ezdxf.enums.MTextEntityAlignment.TOP_LEFT)
    return m


def cota(msp, p1, p2, base, vertical=False, texto_=None):
    d = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=90 if vertical else 0,
                           dimstyle="COTAS_CM", text=texto_ or "<>",
                           dxfattribs={"layer": "A-COTAS"})
    d.render()


def rect(msp, x0, y0, x1, y1, capa):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": capa})


def llamada(msp, etiqueta, punto, centro, r=7.0):
    """Burbuja de referencia a detalle con línea guía."""
    cx, cy = centro
    px, py = punto
    ang = math.atan2(py - cy, px - cx)
    msp.add_line((cx + r * math.cos(ang), cy + r * math.sin(ang)), (px, py),
                 dxfattribs={"layer": "A-TEXTO"})
    msp.add_circle((px, py), 0.9, dxfattribs={"layer": "A-TEXTO"})
    h = msp.add_hatch(dxfattribs={"layer": "A-TEXTO"})
    h.set_solid_fill(color=7)
    h.paths.add_edge_path().add_arc((px, py), 0.9, 0, 360)
    msp.add_circle((cx, cy), r, dxfattribs={"layer": "A-TEXTO"})
    texto(msp, etiqueta, cx, cy, 4.5, TextEntityAlignment.MIDDLE_CENTER)


def nota_guia(msp, s, punto, pos_texto, h=3.2):
    px, py = punto
    tx, ty = pos_texto
    codo = (tx - 2 if tx > px else tx + 2, ty + h * 0.5)
    msp.add_lwpolyline([(px, py), codo, (tx, ty + h * 0.5)], dxfattribs={"layer": "A-TEXTO"})
    msp.add_circle((px, py), 0.6, dxfattribs={"layer": "A-TEXTO"})
    al = TextEntityAlignment.BOTTOM_LEFT if tx > px else TextEntityAlignment.BOTTOM_RIGHT
    texto(msp, s, tx + (1 if tx > px else -1), ty, h, al)


def franja_terreno(msp, u0, u1, y0, huecos):
    """Línea de piso y franja de tierra, interrumpida por las cimentaciones."""
    msp.add_line((u0, y0), (u1, y0), dxfattribs={"layer": "A-TERRENO"})
    franja = sbox(u0, y0 - 7, u1, y0)
    for h in huecos:
        franja = franja.difference(h)
    geoms = [franja] if franja.geom_type == "Polygon" else list(franja.geoms)
    for g in geoms:
        if g.area < 1:
            continue
        hp = msp.add_hatch(dxfattribs={"layer": "A-RELLENO", "color": 8})
        hp.set_pattern_fill("EARTH", scale=0.35)
        hp.paths.add_polyline_path(list(g.exterior.coords)[:-1], is_closed=True)
    texto(msp, "NPT ±0.00", u1 - 2, y0 + 1.5, 3.2, TextEntityAlignment.BOTTOM_RIGHT)


def marco_y_cuadro(msp, version, ext):
    x0, y0, x1, y1 = ext
    rect(msp, x0, y0, x1, y1, "A-MARCO")
    rect(msp, x0 + 5, y0 + 5, x1 - 5, y1 - 5, "A-MARCO")
    # cuadro de datos
    cx0, cy0 = x1 - 295, y0 + 5
    cx1, cy1 = x1 - 5, y0 + 95
    rect(msp, cx0, cy0, cx1, cy1, "A-MARCO")
    for yy in (cy0 + 22, cy0 + 40, cy0 + 58, cy0 + 72):
        msp.add_line((cx0, yy), (cx1, yy), dxfattribs={"layer": "A-MARCO"})
    msp.add_line((cx0 + 145, cy0), (cx0 + 145, cy0 + 40), dxfattribs={"layer": "A-MARCO"})
    texto(msp, "ESTRUCTURA PARA TROVISEL 122 x 244 cm (HORIZONTAL)", cx0 + 4, cy0 + 79, 6.0)
    texto(msp, version, cx0 + 4, cy0 + 61, 6.0)
    texto(msp, "Contenido: alzado posterior, alzado lateral, detalles isométricos D1-D6,",
          cx0 + 4, cy0 + 51, 3.4)
    texto(msp, "notas y lista de materiales.", cx0 + 4, cy0 + 45, 3.4)
    texto(msp, "Unidades: cm", cx0 + 4, cy0 + 30, 3.6)
    texto(msp, "Alzados: 1 unidad = 1 cm (esc. 1:1 en modelo)", cx0 + 4, cy0 + 25, 2.8)
    texto(msp, "Detalles isométricos: sin escala (S/E)", cx0 + 4, cy0 + 9, 3.2)
    texto(msp, f"Fecha: {FECHA}", cx0 + 149, cy0 + 30, 3.6)
    texto(msp, "Hoja: 1 de 1", cx0 + 149, cy0 + 9, 3.6)


# ---------------------------------------------------------------- contraventeo


def poligono_contraventeo(p_sup, p_pie, y_corte, z_corte, ancho, z_min=None, z_max=None):
    """Polígono (y, z) de una pieza diagonal con corte vertical arriba y horizontal abajo."""
    d = unit(np.array(p_pie) - np.array(p_sup))
    n = np.array([-d[1], d[0]])
    esquinas = {}
    for s in (+1, -1):
        o = np.array(p_sup) + s * ancho / 2 * n
        t_sup = (y_corte - o[0]) / d[0]
        t_inf = (z_corte - o[1]) / d[1]
        esquinas[s] = (o + t_sup * d, o + t_inf * d)
    pts = [esquinas[1][0], esquinas[1][1], esquinas[-1][1], esquinas[-1][0]]
    pg = Polygon([tuple(p) for p in pts])
    if z_min is not None:
        pg = pg.intersection(sbox(-1e4, z_min, 1e4, 1e4))
    if z_max is not None:
        pg = pg.intersection(sbox(-1e4, -1e4, 1e4, z_max))
    return pg, d


def solido_yz(pg, x0, espesor, color, nombre="", tubo=None):
    coords = list(pg.exterior.coords)[:-1]
    s = prisma([(x0, y, z) for y, z in coords], (espesor, 0, 0), color, nombre)
    if tubo:
        # hueco del PTR visible en cortes del detalle
        pass
    return s


def tuerca(c, eje, r_rondana, r_tuerca, r_perno, largo_perno=1.4):
    """Rondana + tuerca hexagonal + punta del perno, saliendo en dirección eje."""
    c = np.asarray(c, dtype=float)
    a = unit(eje)
    out = [cilindro(c, a, r_rondana, 0.3, HERRAJE, "rondana", 16),
           cilindro(c + 0.3 * a, a, r_tuerca, 0.8 * r_perno * 2, HERRAJE, "tuerca", 6),
           cilindro(c + (0.3 + 1.6 * r_perno) * a, a, r_perno, largo_perno * 0.5, HERRAJE, "perno", 12)]
    return out


def cordon(p0, p1, n, t, a=0.5):
    """Cordón de soldadura visto sobre una junta a tope (cara de normal n, ancho en dirección t)."""
    p0, p1, n, t = (np.asarray(v, dtype=float) for v in (p0, p1, n, t))
    base = [p0 - a * t, p0 + a * t, p0 + 0.8 * a * n]
    return prisma(base, p1 - p0, (70, 70, 70), "soldadura")


def filete(p0, p1, d1, d2, a=0.6):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    base = [p0, p0 + a * unit(d1), p0 + a * unit(d2)]
    return prisma(base, p1 - p0, (70, 70, 70), "soldadura")


# ================================================================ VERSIÓN MADERA


def modelo_madera():
    m = {}
    yb0, yb1 = E_TAB, E_TAB + 5.0           # bastidor 2"x4" acostado (5 de fondo)
    yp0, yp1 = yb1, yb1 + 10.0              # postes 4"x4"
    m.update(yb=(yb0, yb1), yp=(yp0, yp1))
    sol = [caja(0, ANCHO, 0, E_TAB, Z_INF, Z_SUP, TABLERO, "tablero")]
    sol.append(caja(0, ANCHO, yb0, yb1, Z_SUP - 10, Z_SUP, MADERA, "larguero sup"))
    sol.append(caja(0, ANCHO, yb0, yb1, Z_INF, Z_INF + 10, MADERA, "larguero inf"))
    xs_v = [5.0, X_POSTES[0], ANCHO / 2, X_POSTES[1], ANCHO - 5.0]
    for xc in xs_v:
        sol.append(caja(xc - 5, xc + 5, yb0, yb1, Z_INF + 10, Z_SUP - 10, MADERA, "montante"))
    yc = (yp0 + yp1) / 2
    contra = []
    for xc, lado in zip(X_POSTES, (-1, 1)):
        sol.append(caja(xc - 5, xc + 5, yp0, yp1, 0, Z_SUP, MADERA, "poste"))
        sol.append(caja(xc - 15, xc + 15, yc - 15, yc + 15, -70, 0, CONCRETO, "dado",
                        patron=("AR-CONC", 0.25)))
        pg, d = poligono_contraventeo((yc, 160), (yc + 110, 0), yp0 + 1.0, 0, 10.0)
        x0 = xc + 5 if lado > 0 else xc - 10
        sol.append(solido_yz(pg, x0, 5.0, MADERA, "contraventeo"))
        xm = x0 + 2.5
        sol.append(caja(xm - 12.5, xm + 12.5, yc + 110 - 12.5, yc + 110 + 12.5, -40, 0,
                        CONCRETO, "dado contraventeo", patron=("AR-CONC", 0.25)))
        contra.append((x0, pg, d))
    m.update(sol=sol, xs_v=xs_v, yc=yc, contra=contra, largo_contra=_largo(contra[0][1]))
    return m


def _largo(pg):
    c = list(pg.exterior.coords)
    return max(math.dist(a, b) for a in c for b in c)


def detalles_madera(m):
    yb0, yb1 = m["yb"]
    yp0, yp1 = m["yp"]
    yc = m["yc"]
    D = []
    atras = (1, 1, 1)
    frente = (-1, -1, 1)

    # D1 tablero - bastidor (vista frontal)
    s = [caja(0, 45, yb0, yb1, Z_SUP - 10, Z_SUP, MADERA),
         caja(0, 10, yb0, yb1, Z_SUP - 40, Z_SUP - 10, MADERA),
         caja(0, 30, 0, E_TAB, Z_SUP - 30, Z_SUP, TABLERO)]
    for x, z in [(5, 205), (20, 205), (5, 190)]:
        s.append(cilindro((x, 0, z), (0, -1, 0), 0.9, 0.15, HERRAJE, lados=16))
        s.append(cilindro((x, -0.15, z), (0, -1, 0), 0.55, 0.25, HERRAJE, lados=12))
    D.append(("D1", "UNIÓN TABLERO - BASTIDOR", frente, s, [
        "1. Tablero trovisel 122x244 sobre bastidor.",
        "2. Tornillo para madera #10 x 1 1/4\" con rondana,",
        "   a cada 30 cm en perímetro y montantes,",
        "   a 2.5 cm mín. del borde del tablero.",
        "3. Bastidor de barrote 2\"x4\" (5x10) acostado."]))

    # D2 esquina del bastidor (vista posterior)
    s = [caja(ANCHO - 35, ANCHO, yb0, yb1, Z_SUP - 10, Z_SUP, MADERA),
         caja(ANCHO - 10, ANCHO, yb0, yb1, Z_SUP - 40, Z_SUP - 10, MADERA),
         caja(ANCHO - 38, ANCHO, 0, E_TAB, Z_SUP - 42, Z_SUP, TABLERO),
         caja(ANCHO - 8, ANCHO - 3, yb1, yb1 + 0.3, Z_SUP - 24, Z_SUP - 2, HERRAJE),
         caja(ANCHO - 20, ANCHO - 8, yb1, yb1 + 0.3, Z_SUP - 7, Z_SUP - 2, HERRAJE)]
    for x, z in [(ANCHO - 5.5, 206), (ANCHO - 5.5, 196), (ANCHO - 5.5, 188), (ANCHO - 16, 204.5)]:
        s.append(cilindro((x, yb1 + 0.3, z), (0, 1, 0), 0.6, 0.3, HERRAJE, lados=12))
    D.append(("D2", "ESQUINA DEL BASTIDOR", atras, s, [
        "1. Unión a tope: larguero corrido, montante entre",
        "   largueros; 2 clavos 3\" o tornillos 3\" por unión.",
        "2. Escuadra metálica en L 3\" (placa cal. 12)",
        "   por la cara posterior, 4 tornillos 1\".",
        "3. Igual en las 4 esquinas y en las uniones T",
        "   de montantes intermedios."]))

    # D3 bastidor - poste (vista posterior)
    xc = X_POSTES[1]
    s = [caja(xc - 5, xc + 5, yp0, yp1, Z_SUP - 32, Z_SUP, MADERA),
         caja(xc - 24, xc + 24, yb0, yb1, Z_SUP - 10, Z_SUP, MADERA),
         caja(xc - 5, xc + 5, yb0, yb1, Z_SUP - 32, Z_SUP - 10, MADERA),
         caja(xc - 26, xc + 26, 0, E_TAB, Z_SUP - 34, Z_SUP, TABLERO)]
    s += tuerca((xc, yp1, Z_SUP - 5), (0, 1, 0), 1.3, 1.0, 0.48)
    s += [cilindro((xc, yp1, Z_SUP - 22), (0, 1, 0), 1.3, 0.3, HERRAJE, lados=16),
          cilindro((xc, yp1 + 0.3, Z_SUP - 22), (0, 1, 0), 0.95, 0.6, HERRAJE, lados=6)]
    D.append(("D3", "UNIÓN BASTIDOR - POSTE", atras, s, [
        "1. Poste polín 4\"x4\" (10x10) detrás del bastidor.",
        "2. En largueros: perno coche 3/8\" x 7\" con",
        "   rondana y tuerca (2 por poste: sup. e inf.).",
        "3. En montante: 3 pijas (lag) 3/8\" x 5\" con",
        "   rondana, a cada 30 cm aprox.",
        "4. Pretaladrar; tuercas del lado posterior."]))

    # D4 contraventeo - poste (vista posterior)
    x0, pg, d = m["contra"][1]
    pgc = pg.intersection(sbox(-1e4, 128, 1e4, 1e4))
    s = [caja(xc - 5, xc + 5, yp0, yp1, 130, 185, MADERA),
         solido_yz(pgc, x0, 5.0, MADERA)]
    s += tuerca((x0 + 5, yc, 160), (1, 0, 0), 1.3, 1.0, 0.48)
    D.append(("D4", "UNIÓN CONTRAVENTEO - POSTE", atras, s, [
        "1. Contraventeo barrote 2\"x4\" (5x10) por la cara",
        "   exterior del poste, a ~55° con el piso.",
        "2. Perno 3/8\" x 7\" con rondanas y tuerca,",
        "   eje del perno a 160 cm del NPT.",
        "3. Corte vertical en el extremo superior."]))

    # D5 base del contraventeo
    pgb = pg.intersection(sbox(-1e4, -1, 1e4, 28))
    yf = yc + 110
    xm = x0 + 2.5
    s = [caja(xm - 12.5, xm + 12.5, yf - 12.5, yf + 12.5, -14, 0, CONCRETO),
         solido_yz(pgb, x0, 5.0, MADERA),
         caja(x0 + 5, x0 + 5.64, yf - 5, yf + 5, 0.64, 7.6, HERRAJE),
         caja(x0 + 5, x0 + 12.6, yf - 5, yf + 5, 0, 0.64, HERRAJE)]
    s += tuerca((x0 + 5.64, yf + 2.2, 4.2), (1, 0, 0), 1.2, 0.95, 0.48, 1.0)
    s += tuerca((x0 + 9.6, yf, 0.64), (0, 0, 1), 1.2, 0.95, 0.48, 1.0)
    D.append(("D5", "BASE DEL CONTRAVENTEO", atras, s, [
        "1. Dado de concreto 25x25x40 cm, f'c=150 kg/cm².",
        "2. Ángulo de acero 2\"x2\"x1/4\", L=10 cm.",
        "3. Taquete expansivo 3/8\" x 3\" al dado.",
        "4. Perno 3/8\" x 3 1/2\" ángulo-contraventeo.",
        "5. Madera sin contacto directo con el suelo."]))

    # D6 empotre del poste
    s = [caja(xc - 15, xc + 15, yc - 15, yc + 15, -70, 0, CONCRETO),
         caja(xc - 18, xc + 18, yc - 18, yc + 18, -80, -70, GRAVA),
         caja(xc - 5, xc + 5, yp0, yp1, 0, 40, MADERA)]
    D.append(("D6", "EMPOTRE DEL POSTE", atras, s, [
        "1. Dado de concreto 30x30x70 cm, f'c=150 kg/cm².",
        "2. Poste empotrado 60 cm, extremo con 2 clavos",
        "   de 4\" cruzados como anclaje.",
        "3. Plantilla de grava 10 cm para drenaje.",
        "4. Tramo empotrado con impermeabilizante",
        "   asfáltico; remate del dado con chaflán."]))
    return D


NOTAS_MADERA = [
    "NOTAS GENERALES",
    "1. Cotas en cm. Niveles referidos al nivel de piso terminado (NPT ±0.00).",
    "2. Tablero trovisel 122x244 cm en posición horizontal: borde inferior a",
    "   88 cm y borde superior a 210 cm del piso. Espesor supuesto 1.5 cm.",
    "3. Madera de pino de 1a, seca, tratada (sales CCA o equivalente).",
    "   Medidas nominales: polín 4\"x4\" = 10x10, barrote 2\"x4\" = 5x10.",
    "4. Bastidor con largueros corridos y 5 montantes a ejes 5, 61, 122,",
    "   183 y 239 cm. Postes a ejes 61 y 183 cm (cuartos del ancho).",
    "5. Herrajes galvanizados. Pretaladrar todos los pernos.",
    "6. Concreto f'c=150 kg/cm², agregado máx. 3/4\". Colar con el poste",
    "   aplomado y apuntalado; retirar puntales a los 7 días.",
    "7. Acabado: sellador y esmalte o barniz exterior en toda la madera.",
    "8. Verificar en obra el tipo de suelo y la exposición al viento.",
]


def materiales_madera(m):
    lc = m["largo_contra"]
    return [
        "LISTA DE MATERIALES",
        "Pza  Descripción",
        " 1   Tablero trovisel 122 x 244 cm",
        " 2   Poste polín 4\"x4\" L=270 cm (210 + 60 empotre)",
        " 2   Larguero barrote 2\"x4\" L=244 cm",
        f" 5   Montante barrote 2\"x4\" L=102 cm",
        f" 2   Contraventeo barrote 2\"x4\" L={lc:.0f} cm",
        " 4   Perno coche 3/8\" x 7\" c/rondana y tuerca",
        " 2   Perno 3/8\" x 7\" c/2 rondanas y tuerca",
        " 6   Pija (lag) 3/8\" x 5\" c/rondana",
        " 2   Ángulo 2\"x2\"x1/4\" L=10 cm",
        " 2   Taquete expansivo 3/8\" x 3\" + perno 3/8\" x 3 1/2\"",
        "10   Escuadra metálica 3\" (L o T)",
        "40   Tornillo madera #10 x 1 1/4\" c/rondana",
        " 2   Dado concreto 30x30x70 cm (poste)",
        " 2   Dado concreto 25x25x40 cm (contraventeo)",
        "      Concreto total aprox. 0.18 m³",
    ]


# ================================================================ VERSIÓN METAL

P3 = 7.62     # PTR 3"
P15 = 3.81    # PTR 1 1/2"
P2 = 5.08     # PTR 2"
E_PB = 0.95   # placa base 3/8"


def modelo_metal():
    m = {}
    yb0, yb1 = E_TAB, E_TAB + P15
    yp0, yp1 = yb1, yb1 + P3
    yc = (yp0 + yp1) / 2
    m.update(yb=(yb0, yb1), yp=(yp0, yp1), yc=yc)
    sol = [caja(0, ANCHO, 0, E_TAB, Z_INF, Z_SUP, TABLERO, "tablero")]
    sol.append(caja(0, ANCHO, yb0, yb1, Z_SUP - P15, Z_SUP, ACERO, "larguero sup"))
    sol.append(caja(0, ANCHO, yb0, yb1, Z_INF, Z_INF + P15, ACERO, "larguero inf"))
    xs_v = [P15 / 2, X_POSTES[0], ANCHO / 2, X_POSTES[1], ANCHO - P15 / 2]
    for xc in xs_v:
        sol.append(caja(xc - P15 / 2, xc + P15 / 2, yb0, yb1, Z_INF + P15, Z_SUP - P15, ACERO, "montante"))
    contra = []
    yf = yp1 + 100
    for xc in X_POSTES:
        sol.append(caja(xc - P3 / 2, xc + P3 / 2, yp0, yp1, E_PB, Z_SUP, ACERO, "poste"))
        sol.append(caja(xc - 12.5, xc + 12.5, yc - 12.5, yc + 12.5, 0, E_PB, ACERO, "placa base"))
        sol.append(caja(xc - 20, xc + 20, yc - 20, yc + 20, -80, 0, CONCRETO, "dado",
                        patron=("AR-CONC", 0.25)))
        pg, d = poligono_contraventeo((yp1, 150), (yf, 0.64), yp1, 0.64, P2)
        sol.append(solido_yz(pg, xc - P2 / 2, P2, ACERO, "contraventeo"))
        sol.append(caja(xc - 7.5, xc + 7.5, yf - 7.5, yf + 7.5, 0, 0.64, ACERO, "placa contraventeo"))
        sol.append(caja(xc - 15, xc + 15, yf - 15, yf + 15, -40, 0, CONCRETO, "dado contraventeo",
                        patron=("AR-CONC", 0.25)))
        contra.append((xc - P2 / 2, pg, d))
    m.update(sol=sol, xs_v=xs_v, contra=contra, yf=yf, largo_contra=_largo(contra[0][1]))
    return m


def detalles_metal(m):
    yb0, yb1 = m["yb"]
    yp0, yp1 = m["yp"]
    yc = m["yc"]
    yf = m["yf"]
    D = []
    atras = (1, 1, 1)
    frente = (-1, -1, 1)
    e = 0.19  # pared cal. 14 aprox.

    # D1 tablero - bastidor
    s = [caja(0, 40, yb0, yb1, Z_SUP - P15, Z_SUP, ACERO, tubo=("x", e)),
         caja(0, P15, yb0, yb1, Z_SUP - 32, Z_SUP - P15, ACERO, tubo=("z", e)),
         caja(0, 26, 0, E_TAB, Z_SUP - 24, Z_SUP, TABLERO)]
    for x, z in [(1.9, Z_SUP - 1.9), (14, Z_SUP - 1.9), (1.9, Z_SUP - 14)]:
        s.append(cilindro((x, 0, z), (0, -1, 0), 0.8, 0.2, (40, 40, 40), lados=16))
        s.append(cilindro((x, -0.2, z), (0, -1, 0), 0.5, 0.3, HERRAJE, lados=6))
    D.append(("D1", "UNIÓN TABLERO - BASTIDOR", frente, s, [
        "1. Tablero trovisel 122x244 sobre bastidor PTR.",
        "2. Pija autorroscante punta broca #10 x 1\" con",
        "   rondana de neopreno, a cada 30 cm en",
        "   perímetro y montantes, a 1.9 cm del borde.",
        "3. Bastidor PTR 1 1/2\"x1 1/2\" cal. 14."]))

    # D2 esquina del bastidor
    xh = ANCHO
    zj = Z_SUP - P15
    s = [caja(xh - 32, xh, yb0, yb1, zj, Z_SUP, ACERO, tubo=("x", e)),
         caja(xh - P15, xh, yb0, yb1, Z_SUP - 30, zj, ACERO),
         caja(xh - 34, xh, 0, E_TAB, Z_SUP - 33, Z_SUP, TABLERO),
         cordon((xh - P15, yb1, zj), (xh, yb1, zj), (0, 1, 0), (0, 0, 1), 0.45),
         cordon((xh, yb0, zj), (xh, yb1, zj), (1, 0, 0), (0, 0, 1), 0.45),
         filete((xh - P15, yb0, zj), (xh - P15, yb1, zj), (-1, 0, 0), (0, 0, -1), 0.5)]
    D.append(("D2", "ESQUINA DEL BASTIDOR", atras, s, [
        "1. Larguero corrido, montante a tope entre",
        "   largueros.",
        "2. Soldadura perimetral de filete 1/8\"",
        "   (electrodo E-6013), esmerilar cara frontal.",
        "3. Extremos abiertos del PTR con tapa de",
        "   lámina cal. 14 soldada."]))

    # D3 bastidor - poste
    xc = X_POSTES[1]
    x0, x1 = xc - P3 / 2, xc + P3 / 2
    s = [caja(x0, x1, yp0, yp1, Z_SUP - 30, Z_SUP, ACERO),
         caja(xc - 22, xc + 22, yb0, yb1, zj, Z_SUP, ACERO, tubo=("x", e)),
         caja(xc - P15 / 2, xc + P15 / 2, yb0, yb1, Z_SUP - 30, zj, ACERO),
         caja(xc - 24, xc + 24, 0, E_TAB, Z_SUP - 32, Z_SUP, TABLERO),
         filete((x1, yb1, zj), (x1, yb1, Z_SUP), (1, 0, 0), (0, 1, 0)),
         filete((x0, yb1, zj), (x0, yb1, Z_SUP), (-1, 0, 0), (0, 1, 0)),
         caja(x0, x1, yp0, yp1, Z_SUP, Z_SUP + 0.48, ACERO)]
    D.append(("D3", "UNIÓN BASTIDOR - POSTE", atras, s, [
        "1. Poste PTR 3\"x3\" cal. 11 detrás del bastidor,",
        "   tapa superior de placa 3/16\" soldada.",
        "2. Soldadura de filete 3/16\" en ambos lados del",
        "   poste contra largueros y montante (cordones",
        "   de 5 cm a cada 15 cm en el montante).",
        "3. Poste al ras del borde superior (210 cm)."]))

    # D4 contraventeo - poste
    xb, pg, d = m["contra"][1]
    pgc = pg.intersection(sbox(-1e4, 118, 1e4, 1e4))
    zs = [c[1] for c in pg.exterior.coords if abs(c[0] - yp1) < 1e-6]
    za, zb_ = min(zs), max(zs)
    nup = np.array([0, -d[1], d[0]])
    if nup[2] < 0:
        nup = -nup
    s = [caja(x0, x1, yp0, yp1, 115, 170, ACERO),
         solido_yz(pgc, xb, P2, ACERO),
         filete((xb + P2, yp1, za), (xb + P2, yp1, zb_), (1, 0, 0), (0, 1, 0), 0.5),
         filete((xb, yp1, zb_), (xb + P2, yp1, zb_), (0, 0, 1), (0, d[0], d[1]), 0.6)]
    D.append(("D4", "UNIÓN CONTRAVENTEO - POSTE", atras, s, [
        "1. Contraventeo PTR 2\"x2\" cal. 14 en la cara",
        "   posterior del poste, a ~55° con el piso.",
        "2. Extremo cortado a bisel, soldadura perimetral",
        "   de filete 3/16\" (E-7018).",
        "3. Eje del contraventeo a 150 cm del NPT."]))

    # D5 base del contraventeo
    pgb = pg.intersection(sbox(-1e4, -1, 1e4, 26))
    ys = [c[0] for c in pg.exterior.coords if abs(c[1] - 0.64) < 1e-6]
    ya, yb_ = min(ys), max(ys)
    s = [caja(xc - 15, xc + 15, yf - 15, yf + 15, -14, 0, CONCRETO),
         caja(xc - 7.5, xc + 7.5, yf - 7.5, yf + 7.5, 0, 0.64, ACERO),
         solido_yz(pgb, xb, P2, ACERO),
         filete((xb + P2, ya, 0.64), (xb + P2, yb_, 0.64), (1, 0, 0), (0, 0, 1), 0.5)]
    for yy in (yf - 5.5, yf + 5.5):
        s += tuerca((xc, yy, 0.64), (0, 0, 1), 1.2, 0.9, 0.48, 1.6)
    D.append(("D5", "BASE DEL CONTRAVENTEO", atras, s, [
        "1. Dado de concreto 30x30x40 cm, f'c=200 kg/cm².",
        "2. Placa 15x15x1/4\" con 2 anclas de redondo",
        "   3/8\" L=30 cm con gancho, tuerca y rondana.",
        "3. Contraventeo soldado a la placa con filete",
        "   3/16\" perimetral."]))

    # D6 base del poste
    yc0 = yc
    s = [caja(xc - 20, xc + 20, yc0 - 20, yc0 + 20, -16, 0, CONCRETO),
         caja(xc - 12.5, xc + 12.5, yc0 - 12.5, yc0 + 12.5, 0, E_PB, ACERO),
         caja(x0, x1, yp0, yp1, E_PB, 40, ACERO, tubo=("z", 0.30))]
    tc = 0.95
    for sx, sy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        if sx:
            xa = x1 if sx > 0 else x0
            tri = [(xa, yc0 - tc / 2, E_PB), (xa + 8 * sx, yc0 - tc / 2, E_PB), (xa, yc0 - tc / 2, E_PB + 12)]
            s.append(prisma(tri, (0, tc, 0), ACERO))
        else:
            ya_ = yp1 if sy > 0 else yp0
            tri = [(xc - tc / 2, ya_, E_PB), (xc - tc / 2, ya_ + 8 * sy, E_PB), (xc - tc / 2, ya_, E_PB + 12)]
            s.append(prisma(tri, (tc, 0, 0), ACERO))
    for yy0, yy1 in [(yp0, yc0 - tc / 2), (yc0 + tc / 2, yp1)]:
        s.append(filete((x1, yy0, E_PB), (x1, yy1, E_PB), (1, 0, 0), (0, 0, 1), 0.5))
    for xx0, xx1 in [(x0, xc - tc / 2), (xc + tc / 2, x1)]:
        s.append(filete((xx0, yp1, E_PB), (xx1, yp1, E_PB), (0, 1, 0), (0, 0, 1), 0.5))
    for dx in (-9, 9):
        for dy in (-9, 9):
            s += tuerca((xc + dx, yc0 + dy, E_PB), (0, 0, 1), 1.5, 1.15, 0.64, 2.0)
    D.append(("D6", "BASE DEL POSTE", atras, s, [
        "1. Placa base 25x25x3/8\" con 4 barrenos 5/8\".",
        "2. 4 anclas redondo 1/2\" L=45 cm con gancho,",
        "   tuerca y rondana, a 18 cm entre ejes.",
        "3. 4 cartabones placa 3/8\" de 8x12 cm.",
        "4. Filete 3/16\" perimetral poste-placa.",
        "5. Dado 40x40x80 cm, f'c=200 kg/cm²; nivelar con",
        "   mortero sin contracción (grout) 2 cm."]))
    return D


NOTAS_METAL = [
    "NOTAS GENERALES",
    "1. Cotas en cm. Niveles referidos al nivel de piso terminado (NPT ±0.00).",
    "2. Tablero trovisel 122x244 cm en posición horizontal: borde inferior a",
    "   88 cm y borde superior a 210 cm del piso. Espesor supuesto 1.5 cm.",
    "3. Acero ASTM A500 (PTR) y A36 (placas). Postes PTR 3\"x3\" cal. 11,",
    "   bastidor PTR 1 1/2\"x1 1/2\" cal. 14, contraventeos PTR 2\"x2\" cal. 14.",
    "4. Bastidor con largueros corridos y 5 montantes a ejes 1.9, 61, 122,",
    "   183 y 242.1 cm. Postes a ejes 61 y 183 cm (cuartos del ancho).",
    "5. Soldadura con electrodo E-7018 (estructural) y E-6013 (bastidor).",
    "   Limpiar escoria y esmerilar cordones visibles.",
    "6. Concreto f'c=200 kg/cm². Anclas colocadas con plantilla antes del",
    "   colado; montar la estructura a los 7 días.",
    "7. Acabado: primario anticorrosivo y 2 manos de esmalte alquidálico.",
    "8. Verificar en obra el tipo de suelo y la exposición al viento.",
]


def materiales_metal(m):
    lc = m["largo_contra"]
    return [
        "LISTA DE MATERIALES",
        "Pza  Descripción",
        " 1   Tablero trovisel 122 x 244 cm",
        " 2   Poste PTR 3\"x3\" cal. 11 L=209 cm",
        " 2   Larguero PTR 1 1/2\"x1 1/2\" cal. 14 L=244 cm",
        f" 5   Montante PTR 1 1/2\"x1 1/2\" cal. 14 L={ALTO - 2 * P15:.1f} cm",
        f" 2   Contraventeo PTR 2\"x2\" cal. 14 L={lc:.0f} cm",
        " 2   Placa base 25x25x3/8\"",
        " 8   Cartabón placa 3/8\" 8x12 cm",
        " 8   Ancla redondo 1/2\" L=45 cm c/tuerca y rondana",
        " 2   Placa 15x15x1/4\" (contraventeo)",
        " 4   Ancla redondo 3/8\" L=30 cm c/tuerca y rondana",
        " 2   Tapa placa 3/16\" 8x8 cm (remate de postes)",
        " 4   Tapa lámina cal. 14 (extremos de largueros)",
        "40   Pija autorroscante #10 x 1\" c/rondana neopreno",
        " 2   Dado concreto 40x40x80 cm (poste)",
        " 2   Dado concreto 30x30x40 cm (contraventeo)",
        "      Concreto total aprox. 0.33 m³",
    ]


# ================================================================ ARMADO DEL PLANO

OX, OY = 150.0, 130.0      # origen del alzado posterior (x=244 a la izquierda, piso)
SX = 545.0                # origen horizontal del alzado lateral (cara frontal del tablero)


def dibujar_alzados(msp, m, version):
    sol = m["sol"]
    yp0, yp1 = m["yp"]
    yb0, yb1 = m["yb"]
    madera = version == "madera"

    # ---------------- alzado posterior (visto desde atrás)
    vp = Vista((0, 1, 0), 1.0, (OX + ANCHO, OY))
    def ux(x):
        return OX + ANCHO - x
    res = dibujar(msp, sol, vp, "A-ESTRUCTURA", "A-RELLENO", plano=True)
    huecos = [pg for pg, s, n, _ in res if "dado" in s.nombre]
    franja_terreno(msp, OX - 45, OX + ANCHO + 45, OY, [unary_union(huecos).buffer(0.01)])
    for xc in X_POSTES:
        msp.add_line((ux(xc), OY - 95), (ux(xc), OY + Z_SUP + 12), dxfattribs={"layer": "A-EJES"})
        if madera:
            rect(msp, ux(xc) - 5, OY - 60, ux(xc) + 5, OY, "A-OCULTAS")
            for z in (Z_INF + 5, Z_SUP - 5):
                msp.add_circle((ux(xc), OY + z), 1.3, dxfattribs={"layer": "A-HERRAJES"})
            for z in (120, 150, 180):
                msp.add_circle((ux(xc), OY + z), 1.0, dxfattribs={"layer": "A-HERRAJES"})
        else:
            for dx in (-9, 9):
                msp.add_line((ux(xc) + dx, OY), (ux(xc) + dx, OY - 45), dxfattribs={"layer": "A-OCULTAS"})
    msp.add_line((ux(ANCHO / 2), OY + Z_INF - 6), (ux(ANCHO / 2), OY + Z_SUP + 6),
                 dxfattribs={"layer": "A-EJES"})
    # cotas
    zt = OY + Z_SUP
    cota(msp, (ux(ANCHO), zt), (ux(0), zt), (0, zt + 30))
    cadena = [ANCHO, X_POSTES[1], X_POSTES[0], 0]
    for a, b in zip(cadena, cadena[1:]):
        cota(msp, (ux(a), zt), (ux(b), zt), (0, zt + 17))
    xi = ux(ANCHO)
    cota(msp, (xi, OY), (xi, OY + Z_INF), (xi - 18, 0), vertical=True)
    cota(msp, (xi, OY + Z_INF), (xi, zt), (xi - 18, 0), vertical=True)
    cota(msp, (xi, OY), (xi, zt), (xi - 34, 0), vertical=True)
    xd = ux(0)
    if madera:
        prof, ancho_d, emp = 70, 30, 60
    else:
        prof, ancho_d, emp = 80, 40, 45
    cota(msp, (ux(X_POSTES[0]) + ancho_d / 2, OY), (ux(X_POSTES[0]) + ancho_d / 2, OY - prof),
         (xd + 22, 0), vertical=True)
    cota(msp, (ux(X_POSTES[0]) - ancho_d / 2, OY - prof), (ux(X_POSTES[0]) + ancho_d / 2, OY - prof),
         (0, OY - prof - 12))
    if madera:
        cota(msp, (ux(X_POSTES[0]) - 5, OY - 60), (ux(X_POSTES[0]) - 5, OY), (xd + 36, 0),
             vertical=True, texto_="<> empotre")
    # textos
    texto(msp, "ALZADO POSTERIOR", OX + ANCHO / 2, OY - 120, 7, TextEntityAlignment.BOTTOM_CENTER)
    texto(msp, "(visto desde atrás)  Cotas en cm", OX + ANCHO / 2, OY - 128, 3.6,
          TextEntityAlignment.BOTTOM_CENTER)
    if madera:
        nota_guia(msp, "Poste polín 4\"x4\" (10x10)", (ux(X_POSTES[1]), OY + 60), (OX - 40, OY + 40))
        nota_guia(msp, "Larguero 2\"x4\" (5x10)", (ux(100), OY + Z_INF + 5), (ux(100) + 12, OY + 60))
        nota_guia(msp, "Montante 2\"x4\"", (ux(ANCHO / 2), OY + 150), (ux(ANCHO / 2) + 15, OY + 140))
        nota_guia(msp, "Contraventeo 2\"x4\"", (ux(X_POSTES[0]) + 8, OY + 40), (ux(X_POSTES[0]) + 30, OY + 25))
        nota_guia(msp, "Dado 30x30x70", (ux(X_POSTES[1]) + 10, OY - 50), (OX - 40, OY - 95))
    else:
        nota_guia(msp, "Poste PTR 3\"x3\" cal. 11", (ux(X_POSTES[1]) + 2, OY + 60), (OX - 40, OY + 40))
        nota_guia(msp, "Larguero PTR 1 1/2\"", (ux(100), OY + Z_INF + 2), (ux(100) + 12, OY + 60))
        nota_guia(msp, "Montante PTR 1 1/2\"", (ux(ANCHO / 2), OY + 150), (ux(ANCHO / 2) + 15, OY + 140))
        nota_guia(msp, "Contraventeo PTR 2\"x2\"", (ux(X_POSTES[0]), OY + 30), (ux(X_POSTES[0]) + 30, OY + 15))
        nota_guia(msp, "Dado 40x40x80", (ux(X_POSTES[1]) + 10, OY - 50), (OX - 40, OY - 95))
        nota_guia(msp, "Placa base 25x25x3/8\"", (ux(X_POSTES[0]) - 11, OY + 0.5), (ux(X_POSTES[0]) - 45, OY + 20))
    nota_guia(msp, "Tablero trovisel 122x244", (ux(100), OY + 175), (ux(100) + 12, OY + 190))
    # llamadas a detalles
    llamada(msp, "D2", (ux(ANCHO) + 3, zt - 3), (ux(ANCHO) + 22, zt + 2 - 30 + 30 - 13))
    llamada(msp, "D3", (ux(X_POSTES[1]), zt - 5), (ux(X_POSTES[1]) - 20, zt - 30))
    llamada(msp, "D6", (ux(X_POSTES[0]), OY - 3), (ux(X_POSTES[0]) - 28, OY - 25))
    llamada(msp, "D1", (ux(0) - 3, zt - 3), (ux(0) - 22, zt - 16))

    # ---------------- alzado lateral (visto desde la derecha)
    vl = Vista((1, 0, 0), 1.0, (SX, OY))
    res = dibujar(msp, sol, vl, "A-ESTRUCTURA", "A-RELLENO", plano=True)
    huecos = [pg for pg, s, n, _ in res if "dado" in s.nombre]
    yfin = SX + (m["contra"][0][1].bounds[2]) + 40
    franja_terreno(msp, SX - 50, yfin, OY, [unary_union(huecos).buffer(0.01)])
    yc = m["yc"]
    def uy(y):
        return SX + y
    msp.add_line((uy(yc), OY - 95), (uy(yc), OY + Z_SUP + 12), dxfattribs={"layer": "A-EJES"})
    pg = m["contra"][0][1]
    if madera:
        rect(msp, uy(yp0), OY - 60, uy(yp1), OY, "A-OCULTAS")
        msp.add_circle((uy(yc), OY + 160), 1.3, dxfattribs={"layer": "A-HERRAJES"})
        yfoot = yc + 110
    else:
        for dy in (-9, 9):
            msp.add_line((uy(yc) + dy, OY), (uy(yc) + dy, OY - 45), dxfattribs={"layer": "A-OCULTAS"})
        yfoot = m["yf"]
    msp.add_line((uy(yfoot), OY - 50), (uy(yfoot), OY + 20), dxfattribs={"layer": "A-EJES"})
    # cotas laterales
    zt = OY + Z_SUP
    cota(msp, (uy(0), zt), (uy(yb0), zt), (0, zt + 8), texto_="<> tablero")
    cota(msp, (uy(yb0), zt), (uy(yb1), zt), (0, zt + 17), texto_="<> bastidor")
    cota(msp, (uy(yp0), zt), (uy(yp1), zt), (0, zt + 26), texto_="<> poste")
    cota(msp, (uy(0), zt), (uy(yp1), zt), (0, zt + 36))
    cota(msp, (uy(yc), OY), (uy(yfoot), OY), (0, OY - 100 if madera else OY - 108))
    cota(msp, (uy(0), OY), (uy(0), OY + Z_INF), (uy(0) - 18, 0), vertical=True)
    cota(msp, (uy(0), OY + Z_INF), (uy(0), zt), (uy(0) - 18, 0), vertical=True)
    cota(msp, (uy(0), OY), (uy(0), zt), (uy(0) - 34, 0), vertical=True)
    z_ap = 160 if madera else 150
    cota(msp, (uy(yc), OY), (uy(yc), OY + z_ap), (uy(yfoot) + 25, 0), vertical=True,
         texto_="<> eje contraventeo")
    texto(msp, "ALZADO LATERAL", SX + 60, OY - 120, 7, TextEntityAlignment.BOTTOM_CENTER)
    texto(msp, "(visto desde la derecha)  Cotas en cm", SX + 60, OY - 128, 3.6,
          TextEntityAlignment.BOTTOM_CENTER)
    nota_guia(msp, "Frente (cara de anuncio)", (uy(0), OY + 180), (uy(0) - 15, OY + 228))
    llamada(msp, "D4", (uy(yc) + 4, OY + z_ap), (uy(yc) + 30, OY + z_ap + 25))
    llamada(msp, "D5", (uy(yfoot), OY + 3), (uy(yfoot) + 22, OY + 30))
    texto(msp, f"Ángulo del contraventeo ≈ {math.degrees(math.atan2(z_ap, yfoot - yc)):.0f}°",
          uy(yc) + 20, OY + 20, 3.2)


def dibujar_detalles(msp, D, x0, y0, ancho_celda=228, alto_fig=150, alto_celda=245, cols=3):
    for i, (clave, titulo, V, sol, notas) in enumerate(D):
        col, fila = i % cols, i // cols
        cx = x0 + col * ancho_celda
        cy = y0 - fila * alto_celda
        rect(msp, cx, cy - alto_celda + 5, cx + ancho_celda - 6, cy, "A-MARCO")
        v = Vista(V, 1.0, (0, 0))
        bx0, by0, bx1, by1 = limites(sol, v)
        k = min((ancho_celda - 30) / (bx1 - bx0), (alto_fig - 20) / (by1 - by0))
        ox = cx + (ancho_celda - 6) / 2 - k * (bx0 + bx1) / 2
        oy = cy - 18 - alto_fig / 2 - k * (by0 + by1) / 2 + 6
        v = Vista(V, k, (ox, oy))
        dibujar(msp, sol, v, "A-DETALLES", "A-RELLENO")
        msp.add_circle((cx + 11, cy - 10), 7, dxfattribs={"layer": "A-TEXTO"})
        texto(msp, clave, cx + 11, cy - 10, 4.5, TextEntityAlignment.MIDDLE_CENTER)
        texto(msp, titulo, cx + 22, cy - 9, 4.6)
        texto(msp, "Isométrico  S/E", cx + 22, cy - 15, 3.0)
        mtexto(msp, "\\P".join(notas), cx + 6, cy - alto_fig - 18, 3.1, ancho_celda - 14)


def generar(version, salida):
    doc = nuevo_doc()
    msp = doc.modelspace()
    if version == "madera":
        m = modelo_madera()
        D = detalles_madera(m)
        notas, mats = NOTAS_MADERA, materiales_madera(m)
        rotulo = "VERSIÓN 1: POLINES DE MADERA"
    else:
        m = modelo_metal()
        D = detalles_metal(m)
        notas, mats = NOTAS_METAL, materiales_metal(m)
        rotulo = "VERSIÓN 2: ESTRUCTURA TUBULAR CUADRADA (PTR)"
    dibujar_alzados(msp, m, version)
    dibujar_detalles(msp, D, 10, -15)
    # columna derecha
    xc = 770
    mtexto(msp, "\\P".join(notas), xc, OY + 255, 3.6, 248)
    mtexto(msp, "\\P".join(mats), xc, OY + 255 - 18 - 6.6 * len(notas), 3.6, 248)
    marco_y_cuadro(msp, rotulo, (0, -515, 1025, 400))
    doc.header["$EXTMIN"] = (0, -515, 0)
    doc.header["$EXTMAX"] = (1025, 400, 0)
    doc.set_modelspace_vport(height=930, center=(512, -57))
    nombre = os.path.join(salida, f"trovisel_{version}.dxf")
    doc.saveas(nombre)
    return nombre, doc


def vista_previa(doc, ruta_pdf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy

    fig = plt.figure(figsize=(16.5, 14.9))
    ax = fig.add_axes([0, 0, 1, 1])
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.COLOR, lineweight_scaling=0.6)
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace())
    ax.set_xlim(-2, 1027)
    ax.set_ylim(-517, 402)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.set_size_inches(22, 19.7)
    fig.savefig(ruta_pdf, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(salida, exist_ok=True)
    for ver in ("madera", "metal"):
        nombre, doc = generar(ver, salida)
        print("DXF:", nombre)
        if "--pdf" in sys.argv or "--png" in sys.argv:
            ext = "png" if "--png" in sys.argv else "pdf"
            vista_previa(doc, os.path.join(salida, f"trovisel_{ver}_vista_previa.{ext}"))
