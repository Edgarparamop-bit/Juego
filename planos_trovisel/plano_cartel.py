#!/usr/bin/env python3
"""
Plano tecnico DXF - Estructura de cartel publicitario de madera.

Instalacion:
    pip install ezdxf

Uso:
    python3 plano_cartel.py            -> genera plano_cartel.dxf junto a este script

Unidades: milimetros. Modelo dibujado a 1:1; el Layout "PLANO_90x60" (hoja 900 x 600 mm)
muestra todas las vistas en una ventana grafica a escala 1:10.
"""
import datetime
import math
import os

import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment

# ------------------------------------------------------------------ parametros (mm)
ANCHO = 2440.0                 # ancho total del marco del cartel
ALTO_PANEL = 1237.3            # altura del panel (zona azul)
Z_PANEL = 880.0                # del piso a la base del panel
LUZ_POSTES = 1490.0            # entre caras internas de los postes
VOLADIZO = 450.0               # del borde exterior del marco al poste (nominal)
PW, PD = 25.4, 12.7            # polin 1" x 1/2": ancho en alzado x grueso (profundidad)
T_PANEL = 6.0                  # espesor del panel (trovisel)

Z_TOP = Z_PANEL + ALTO_PANEL   # 2117.3: los postes llegan al canto superior del marco
ALTO_POSTE = Z_TOP
MITAD = ALTO_PANEL / 2         # 618.65
# posicion real de los postes: se respeta la luz interior de 1490 y la simetria
X_POSTE_IZQ = (ANCHO - LUZ_POSTES) / 2 - PW      # 449.6 (se acota como 450)
X_POSTE_DER = ANCHO - X_POSTE_IZQ - PW           # 1965.0

# escuadra de cada pata (pie hacia atras + diagonal + taco), por el lado interior del poste
L_PIE = 550.0
Z_TACO = 570.0                 # centro del perno superior de la diagonal
H_TACO = 50.0
Y_INF = 496.0                  # posicion del perno diagonal-pie (desde el frente)
EXT = 30.0                     # la diagonal sobresale de cada perno
R_TORNILLO = 3.0

ESCALA = 10                    # 1:10 en el layout
TXT = 2.5 * ESCALA             # 2.5 mm en papel
TIT = 5.0 * ESCALA             # 5 mm en papel

# capas: nombre -> (color ACI, tipo de linea)
CAPAS = {
    "01_MADERA": (4, "Continuous"),      # cian
    "02_TORNILLOS": (1, "Continuous"),   # rojo
    "03_COTAS": (2, "Continuous"),       # amarillo
    "04_TEXTO": (7, "Continuous"),       # blanco
    "05_PANEL": (5, "Continuous"),       # azul (contorno del panel)
    "06_EJES": (6, "CENTER"),            # ejes de pernos
    "07_VENTANAS": (8, "Continuous"),    # marco de la ventana grafica (no se imprime)
}

# origenes de cada vista en el espacio modelo
O_FRONT = (0.0, 0.0)
O_SIDE = (3300.0, 0.0)
O_DET_A = (4400.0, 150.0)
K_DET = 2.0                    # detalles ampliados x2 -> 1:5 en la hoja
O_DET_B = (6050.0, 150.0)


# ------------------------------------------------------------------ utilidades
def setup_document():
    doc = ezdxf.new("R2018", setup=True)
    doc.units = units.MM
    doc.header["$INSUNITS"] = units.MM
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LUNITS"] = 2
    doc.header["$LTSCALE"] = 10
    doc.header["$PSLTSCALE"] = 1
    for name, (color, lt) in CAPAS.items():
        layer = doc.layers.add(name, color=color, linetype=lt)
        if name == "07_VENTANAS":
            layer.dxf.plot = 0
    doc.styles.add("PLANO", font="arial.ttf")

    ds = doc.dimstyles.new("COTAS_1_10")
    ds.dxf.dimtxsty = "PLANO"
    ds.dxf.dimtxt = 2.5 * ESCALA
    ds.dxf.dimasz = 2.5 * ESCALA
    ds.dxf.dimexe = 1.5 * ESCALA
    ds.dxf.dimexo = 1.0 * ESCALA
    ds.dxf.dimgap = 0.8 * ESCALA
    ds.dxf.dimtad = 1                  # texto sobre la linea de cota
    ds.dxf.dimdec = 1
    ds.dxf.dimzin = 8                  # sin ceros a la derecha
    ds.dxf.dimdsep = ord(".")
    ds.dxf.dimblk = ""                 # flecha cerrada rellena (estandar AutoCAD)
    ds.dxf.dimclrd = 256
    ds.dxf.dimclre = 256
    ds.dxf.dimclrt = 256
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0

    # bloque cabeza de tornillo: circulo r=3 con una cruz dentro
    blk = doc.blocks.new("CABEZA_TORNILLO")
    blk.add_circle((0, 0), R_TORNILLO, dxfattribs={"layer": "0"})
    c = R_TORNILLO * 0.7
    blk.add_line((-c, -c), (c, c), dxfattribs={"layer": "0"})
    blk.add_line((-c, c), (c, -c), dxfattribs={"layer": "0"})
    return doc


def rect(msp, x0, y0, x1, y1, layer="01_MADERA"):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": layer})


def poly(msp, pts, layer="01_MADERA"):
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


def tornillo(msp, p, k=1.0, simbolo=True):
    """Circulo r=3 en 02_TORNILLOS y, si se pide, el bloque cruz-en-circulo."""
    if simbolo:
        msp.add_blockref("CABEZA_TORNILLO", p, dxfattribs={
            "layer": "02_TORNILLOS", "xscale": k, "yscale": k})
    else:
        msp.add_circle(p, R_TORNILLO * k, dxfattribs={"layer": "02_TORNILLOS"})


def texto(msp, s, p, h=TXT, align=TextEntityAlignment.MIDDLE_CENTER, rot=0):
    t = msp.add_text(s, height=h, rotation=rot, dxfattribs={"layer": "04_TEXTO", "style": "PLANO"})
    t.set_placement(p, align=align)
    return t


def nota(msp, s, anchor, p_texto):
    """Llamada con flecha (LEADER) + texto."""
    msp.add_leader([p_texto, anchor], dimstyle="COTAS_1_10",
                   dxfattribs={"layer": "04_TEXTO"})
    al = TextEntityAlignment.MIDDLE_LEFT if p_texto[0] >= anchor[0] else TextEntityAlignment.MIDDLE_RIGHT
    dx = TXT * 0.4 if p_texto[0] >= anchor[0] else -TXT * 0.4
    if "\n" in s:
        mt = msp.add_mtext(s.replace("\n", "\\P"), dxfattribs={
            "layer": "04_TEXTO", "style": "PLANO", "char_height": TXT})
        mt.set_location((p_texto[0] + dx, p_texto[1]),
                        attachment_point=4 if dx > 0 else 6)   # medio-izq / medio-der
    else:
        texto(msp, s, (p_texto[0] + dx, p_texto[1]), align=al)


def cota(msp, p1, p2, base, angle=0, dec=None, lfac=None):
    over = {}
    if dec is not None:
        over["dimdec"] = dec
    if lfac is not None:
        over["dimlfac"] = lfac
    dim = msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle="COTAS_1_10",
                             override=over, dxfattribs={"layer": "03_COTAS"})
    dim.render()


def diagonal_perfil():
    """Contorno (y, z) de la diagonal en vista lateral, recortado al piso y al pie."""
    p2 = (PD / 2, Z_TACO)                # perno superior (eje del poste)
    p1 = (Y_INF, PW / 2)                 # perno inferior (eje del pie)
    ux, uz = p1[0] - p2[0], p1[1] - p2[1]
    L = math.hypot(ux, uz)
    ux, uz = ux / L, uz / L
    nx, nz = -uz * PW / 2, ux * PW / 2
    a = (p2[0] - ux * EXT, p2[1] - uz * EXT)
    b = (p1[0] + ux * EXT, p1[1] + uz * EXT)
    pts = [(a[0] - nx, a[1] - nz), (b[0] - nx, b[1] - nz), (b[0] + nx, b[1] + nz), (a[0] + nx, a[1] + nz)]
    # recorte contra z >= 0 e y <= L_PIE
    for (A, B, C) in ((0, 1, 0), (-1, 0, L_PIE)):
        out = []
        for i in range(len(pts)):
            P, Q = pts[i], pts[(i + 1) % len(pts)]
            fp, fq = A * P[0] + B * P[1] + C, A * Q[0] + B * Q[1] + C
            if fp >= 0:
                out.append(P)
            if (fp >= 0) != (fq >= 0):
                t = fp / (fp - fq)
                out.append((P[0] + t * (Q[0] - P[0]), P[1] + t * (Q[1] - P[1])))
        pts = out
    return pts, p1, p2, L + 2 * EXT


# ------------------------------------------------------------------ vistas
def vista_frontal(msp):
    ox, oy = O_FRONT
    T = lambda x, z: (ox + x, oy + z)
    def R(x0, z0, x1, z1, layer="01_MADERA"):
        rect(msp, *T(x0, z0), *T(x1, z1), layer=layer)

    xl0, xl1 = X_POSTE_IZQ, X_POSTE_IZQ + PW
    xr0, xr1 = X_POSTE_DER, X_POSTE_DER + PW
    # panel (zona azul) = contorno exterior del marco
    R(0, Z_PANEL, ANCHO, Z_TOP, layer="05_PANEL")
    # postes (continuos del piso al canto superior)
    R(xl0, 0, xl1, ALTO_POSTE)
    R(xr0, 0, xr1, ALTO_POSTE)
    # largueros extremos del marco
    R(0, Z_PANEL, PW, Z_TOP)
    R(ANCHO - PW, Z_PANEL, ANCHO, Z_TOP)
    # travesanos: superior, medio, inferior (a tope contra postes y largueros)
    z_med = Z_PANEL + MITAD
    tramos = [(PW, xl0), (xl1, xr0), (xr1, ANCHO - PW)]
    for zc in (Z_TOP - PW / 2, z_med, Z_PANEL + PW / 2):
        for a, b in tramos:
            R(a, zc - PW / 2, b, zc + PW / 2)
            # tornillos en los dos extremos de cada tramo
            tornillo(msp, T(a + PW / 2 if a == PW else a - PW / 2, zc), simbolo=True)
            tornillo(msp, T(b - PW / 2 if b == ANCHO - PW else b + PW / 2, zc), simbolo=True)
    # escuadras (pie + taco + diagonal) por el lado interior de cada poste
    pts, p1, p2, _ = diagonal_perfil()
    z_diag_max = max(p[1] for p in pts)
    for x_in, sg in ((xl1, 1), (xr0, -1)):
        def X(a):
            return x_in + sg * a
        R(min(X(0), X(PD)), 0, max(X(0), X(PD)), PW)                                   # pie (de canto)
        R(min(X(0), X(PD)), Z_TACO - H_TACO / 2, max(X(0), X(PD)), Z_TACO + H_TACO / 2)  # taco
        R(min(X(PD), X(2 * PD)), 0, max(X(PD), X(2 * PD)), z_diag_max)                   # diagonal (de punta)
        # pernos pasantes (vista de costado): eje + vastago
        for zc, prof in ((PW / 2, PD), (Z_TACO, 2 * PD)):
            x_ext = x_in - sg * PW
            msp.add_line(T(x_ext - sg * 15, zc), T(X(prof) + sg * 15, zc), dxfattribs={"layer": "06_EJES"})
            rect(msp, *T(min(x_ext - sg * 6, X(prof) + sg * 8), zc - R_TORNILLO),
                 *T(max(x_ext - sg * 6, X(prof) + sg * 8), zc + R_TORNILLO), layer="02_TORNILLOS")
    # piso
    msp.add_line(T(-300, 0), T(ANCHO + 300, 0), dxfattribs={"layer": "04_TEXTO"})

    # textos
    texto(msp, "PANEL", T(ANCHO / 2, Z_PANEL + MITAD + MITAD / 2), h=TIT)
    texto(msp, "(zona azul 2440 x 1237.3)", T(ANCHO / 2, Z_PANEL + MITAD + MITAD / 2 - 70))
    nota(msp, 'POLIN 1"x1/2" (25.4 x 12.7 mm)', T(xl0 + PW / 2, 450), T(xl0 + 260, 650))
    nota(msp, "TORNILLOS", T(xl1 + PW / 2, Z_TOP - PW / 2), T(xl1 + 260, Z_TOP + 120))
    nota(msp, "ESCUADRA (pie + diagonal)", T(xr0 - PD, 300), T(xr0 - 300, 700))
    texto(msp, "VISTA FRONTAL (ALZADO)", T(ANCHO / 2, -330), h=TIT)
    texto(msp, "Esc. 1:10", T(ANCHO / 2, -410))

    # cotas
    cota(msp, T(0, Z_TOP), T(ANCHO, Z_TOP), T(0, Z_TOP + 330))
    cota(msp, T(0, Z_TOP), T(xl0, Z_TOP), T(0, Z_TOP + 170), dec=0)
    cota(msp, T(xl1, Z_TOP), T(xr0, Z_TOP), T(0, Z_TOP + 170))
    cota(msp, T(xr1, Z_TOP), T(ANCHO, Z_TOP), T(0, Z_TOP + 170), dec=0)
    cota(msp, T(0, Z_PANEL), T(0, Z_TOP), T(-330, 0), angle=90)
    cota(msp, T(0, Z_PANEL), T(0, Z_PANEL + MITAD), T(-170, 0), angle=90, dec=2)
    cota(msp, T(0, Z_PANEL + MITAD), T(0, Z_TOP), T(-170, 0), angle=90, dec=2)
    cota(msp, T(xl0, 0), T(xl0, Z_PANEL), T(-170, 0), angle=90)
    cota(msp, T(ANCHO, 0), T(ANCHO, Z_TOP), T(ANCHO + 200, 0), angle=90)


def vista_lateral(msp):
    ox, oy = O_SIDE
    T = lambda y, z: (ox + y, oy + z)
    # panel + marco/poste (vista desde la derecha: frente a la izquierda)
    rect(msp, *T(-T_PANEL, Z_PANEL), *T(0, Z_TOP), layer="05_PANEL")
    rect(msp, *T(0, 0), *T(PD, ALTO_POSTE))                         # poste
    rect(msp, *T(0, Z_PANEL), *T(PD, Z_TOP))                        # larguero extremo del marco
    for zc in (Z_TOP - PW / 2, Z_PANEL + MITAD, Z_PANEL + PW / 2):  # travesanos de punta
        rect(msp, *T(0, zc - PW / 2), *T(PD, zc + PW / 2))
    rect(msp, *T(0, 0), *T(L_PIE, PW))                              # pie
    rect(msp, *T(0, Z_TACO - H_TACO / 2), *T(PD, Z_TACO + H_TACO / 2))  # taco
    pts, p1, p2, _ = diagonal_perfil()
    poly(msp, [T(*p) for p in pts])                                 # diagonal
    for p in ((PD / 2, PW / 2), p2, p1):
        tornillo(msp, T(*p))
    msp.add_line(T(-200, 0), T(L_PIE + 250, 0), dxfattribs={"layer": "04_TEXTO"})

    texto(msp, "VISTA LATERAL (PERFIL)", T(L_PIE / 2 - 50, -330), h=TIT)
    texto(msp, "Esc. 1:10 - vista desde la derecha", T(L_PIE / 2 - 50, -410))
    nota(msp, "PANEL", T(-T_PANEL / 2, 1700), T(-250, 1850))
    nota(msp, "DIAGONAL", T((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2), T(380, 650))

    cota(msp, T(0, 0), T(L_PIE, 0), T(0, -170))
    cota(msp, T(0, 0), T(0, Z_PANEL), T(-200, 0), angle=90)
    cota(msp, T(0, Z_PANEL), T(0, Z_TOP), T(-200, 0), angle=90)
    cota(msp, T(PD, 0), T(PD, Z_TOP), T(L_PIE + 150, 0), angle=90)
    cota(msp, T(PD, 0), T(PD, Z_TACO), T(250, 0), angle=90)
    cota(msp, T(0, Z_TOP), T(PD, Z_TOP), T(0, Z_TOP + 120))


def detalle_a(msp):
    """Zoom x2 de la escuadra en perfil: pata + taco + diagonal + pie."""
    ox, oy = O_DET_A
    k = K_DET
    T = lambda y, z: (ox + y * k, oy + z * k)
    z_corte = 660.0
    rect(msp, *T(0, 0), *T(PD, z_corte))
    # linea de corte (zigzag) en la pata
    msp.add_lwpolyline([T(-10, z_corte), T(PD * 0.3, z_corte + 8), T(PD * 0.7, z_corte - 8), T(PD + 10, z_corte)],
                       dxfattribs={"layer": "04_TEXTO"})
    rect(msp, *T(0, 0), *T(L_PIE, PW))
    rect(msp, *T(0, Z_TACO - H_TACO / 2), *T(PD, Z_TACO + H_TACO / 2))
    pts, p1, p2, Ld = diagonal_perfil()
    poly(msp, [T(*p) for p in pts])
    for p in ((PD / 2, PW / 2), p2, p1):
        tornillo(msp, T(*p), k=k)
    msp.add_line(T(-60, 0), T(L_PIE + 60, 0), dxfattribs={"layer": "04_TEXTO"})

    nota(msp, "PERNO 1/4\" PASANTE\n(pivote del pie)", T(PD / 2, PW / 2), T(180, 200))
    nota(msp, "PERNO 1/4\" (diagonal - pata\na traves del taco)", T(*p2), T(150, 700))
    nota(msp, "PERNO 1/4\" (diagonal - pie)", T(*p1), T(420, 330))
    nota(msp, "TACO 50 mm", T(PD, Z_TACO + H_TACO / 2 - 5), T(-200, 720))
    nota(msp, 'POLIN 1"x1/2"', T(PD / 2, 400), T(-200, 450))
    texto(msp, "DETALLE A", T(L_PIE / 2, -110), h=TIT)
    texto(msp, "Union pata / escuadra (perfil)", T(L_PIE / 2, -190))
    texto(msp, "Esc. 1:%g" % (ESCALA / k), T(L_PIE / 2, -230))

    lf = 1 / k
    cota(msp, T(0, 0), T(PD, 0), T(0, -35), lfac=lf)
    cota(msp, T(0, 0), T(0, PW), T(-40, 0), angle=90, lfac=lf)
    cota(msp, T(PD / 2, 0), T(PD / 2, Z_TACO), T(-90, 0), angle=90, lfac=lf)
    cota(msp, T(PD / 2, PW / 2), T(p1[0], PW / 2), T(0, -70), lfac=lf, dec=0)
    cota(msp, T(0, Z_TACO - H_TACO / 2), T(0, Z_TACO + H_TACO / 2), T(-40, 0), angle=90, lfac=lf)


def detalle_b(msp):
    """Zoom x2 de la misma union vista de frente (poste izquierdo): capas de piezas y pernos."""
    ox, oy = O_DET_B
    k = K_DET
    T = lambda x, z: (ox + x * k, oy + z * k)
    z_corte = 660.0
    # x local: 0 = cara exterior del poste; poste [0,PW], pie/taco [PW, PW+PD], diagonal [PW+PD, PW+2PD]
    rect(msp, *T(0, 0), *T(PW, z_corte))
    msp.add_lwpolyline([T(-10, z_corte), T(PW * 0.3, z_corte + 8), T(PW * 0.7, z_corte - 8), T(PW + 10, z_corte)],
                       dxfattribs={"layer": "04_TEXTO"})
    rect(msp, *T(PW, 0), *T(PW + PD, PW))
    rect(msp, *T(PW, Z_TACO - H_TACO / 2), *T(PW + PD, Z_TACO + H_TACO / 2))
    pts, p1, p2, _ = diagonal_perfil()
    zmax = max(p[1] for p in pts)
    rect(msp, *T(PW + PD, 0), *T(PW + 2 * PD, zmax))
    for zc, x_fin in ((PW / 2, PW + PD), (Z_TACO, PW + 2 * PD)):
        msp.add_line(T(-20, zc), T(x_fin + 20, zc), dxfattribs={"layer": "06_EJES"})
        rect(msp, *T(-6, zc - R_TORNILLO), *T(x_fin + 8, zc + R_TORNILLO), layer="02_TORNILLOS")
        rect(msp, *T(-6, zc - 3 * R_TORNILLO), *T(0, zc + 3 * R_TORNILLO), layer="02_TORNILLOS")         # cabeza
        rect(msp, *T(x_fin, zc - 3 * R_TORNILLO), *T(x_fin + 5, zc + 3 * R_TORNILLO), layer="02_TORNILLOS")  # tuerca
    msp.add_line(T(-40, 0), T(PW + 2 * PD + 40, 0), dxfattribs={"layer": "04_TEXTO"})
    nota(msp, "POSTE", T(PW / 2, 400), T(-130, 430))
    nota(msp, "PIE / TACO", T(PW + PD / 2, Z_TACO + 10), T(160, 640))
    nota(msp, "DIAGONAL", T(PW + 1.5 * PD, 300), T(160, 330))
    nota(msp, "TORNILLOS", T(PW + 2 * PD + 4, PW / 2), T(160, 150))
    texto(msp, "DETALLE B", T(PW + PD, -110), h=TIT)
    texto(msp, "Misma union (frente)", T(PW + PD, -190))
    texto(msp, "Esc. 1:%g" % (ESCALA / k), T(PW + PD, -230))
    lf = 1 / k
    cota(msp, T(0, 0), T(PW, 0), T(0, -35), lfac=lf)
    cota(msp, T(PW, 0), T(PW + 2 * PD, 0), T(0, -60), lfac=lf)


# ------------------------------------------------------------------ layout 900 x 600
def layout(doc):
    msp = doc.modelspace()
    ext_min, ext_max = model_extents(msp)
    doc.layouts.rename("Layout1", "PLANO_90x60")
    psp = doc.layouts.get("PLANO_90x60")
    psp.page_setup(size=(900, 600), margins=(0, 0, 0, 0), units="mm", scale=(1, 1))
    att = {"layer": "04_TEXTO"}
    psp.add_lwpolyline([(0, 0), (900, 0), (900, 600), (0, 600)], close=True, dxfattribs=att)
    psp.add_lwpolyline([(10, 10), (890, 10), (890, 590), (10, 590)], close=True, dxfattribs=att)

    # cuadro de titulo (esquina inferior derecha)
    x0, y0, x1, y1 = 690, 10, 890, 70
    psp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=att)
    psp.add_line((x0, 45), (x1, 45), dxfattribs=att)
    psp.add_line((x0, 27), (x1, 27), dxfattribs=att)
    psp.add_line((790, y0), (790, 45), dxfattribs=att)
    def ptxt(s, p, h, al=TextEntityAlignment.MIDDLE_LEFT):
        t = psp.add_text(s, height=h, dxfattribs={"layer": "04_TEXTO", "style": "PLANO"})
        t.set_placement(p, align=al)
    ptxt("Estructura Cartel Madera", (x0 + 5, 57.5), 6)
    ptxt("ESCALA: 1:10 (detalles 1:%g)" % (ESCALA / K_DET), (x0 + 5, 36), 3)
    ptxt("FECHA: " + datetime.date.today().strftime("%d/%m/%Y"), (795, 36), 3)
    ptxt("UNIDADES: mm", (x0 + 5, 18.5), 3)
    ptxt("HOJA: 900 x 600 mm", (795, 18.5), 3)
    ptxt('Polin 1" x 1/2" (25.4 x 12.7 mm): seccion indicada por el cliente, verificar resistencia.',
         (20, 18), 3)

    # ventana grafica 1:10 centrada en la hoja (sobre el cuadro de titulo)
    vp_w, vp_h = 870, 505
    cx, cy = 450, 75 + vp_h / 2
    mc = ((ext_min[0] + ext_max[0]) / 2, (ext_min[1] + ext_max[1]) / 2)
    vp = psp.add_viewport(center=(cx, cy), size=(vp_w, vp_h), view_center_point=mc,
                          view_height=vp_h * ESCALA, dxfattribs={"layer": "07_VENTANAS"})
    vp.dxf.status = 1
    return (ext_max[0] - ext_min[0]) / ESCALA, (ext_max[1] - ext_min[1]) / ESCALA


def model_extents(msp):
    from ezdxf import bbox
    box = bbox.extents(msp, fast=True)
    return box.extmin, box.extmax


def main():
    doc = setup_document()
    msp = doc.modelspace()
    vista_frontal(msp)
    vista_lateral(msp)
    detalle_a(msp)
    detalle_b(msp)
    w, h = layout(doc)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plano_cartel.dxf")
    doc.saveas(out)
    print("Generado:", out)
    print("Vistas a 1:10 ocupan %.0f x %.0f mm de la hoja (ventana 870 x 505)" % (w, h))
    print("Postes: X = %.1f y %.1f mm, alto %.1f mm" % (X_POSTE_IZQ, X_POSTE_DER, ALTO_POSTE))


if __name__ == "__main__":
    main()
