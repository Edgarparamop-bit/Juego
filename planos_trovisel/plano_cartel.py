#!/usr/bin/env python3
"""
Plano tecnico DXF - Estructura de cartel publicitario de madera.

Instalacion:
    pip install ezdxf

Uso:
    python3 plano_cartel.py            -> genera plano_cartel.dxf junto a este script

Unidades: milimetros. Toda la geometria sale de un modelo 3D (cajas de polin)
y se proyecta en cada vista; el modelo se dibuja a 1:1.

Hojas (Layouts de 900 x 600 mm):
  01_VISTAS        alzado frontal, posterior, lateral y vista superior  (ventana 1:10)
  02_ISOMETRICOS   isometrico frontal y posterior acotados             (ventana 1:10)
  03_DETALLES      detalles de uniones: escuadra (perfil, frente e isometrico
                   despiezado), esquina superior y cruz                (ventana 1:5)

Necesita generar_planos.py (en la misma carpeta) para eliminar lineas ocultas.
"""
import datetime
import math
import os
import sys

import ezdxf
from ezdxf import bbox, units
from ezdxf.enums import TextEntityAlignment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar_planos as gp   # noqa: E402  (solidos 3D + lineas ocultas)

# ------------------------------------------------------------------ parametros (mm)
ANCHO = 2440.0                 # ancho total del marco del cartel
ALTO_PANEL = 1237.3            # altura del panel (zona azul)
Z_PANEL = 880.0                # del piso a la base del panel
LUZ_POSTES = 1490.0            # entre caras internas de los postes
PW, PD = 25.4, 12.7            # polin 1" x 1/2": ancho visto de frente x grueso
T_PANEL = 6.0                  # espesor del panel (trovisel)

Z_TOP = Z_PANEL + ALTO_PANEL   # 2117.3: los postes llegan al canto superior del marco
ALTO_POSTE = Z_TOP
MITAD = ALTO_PANEL / 2         # 618.65
X_POSTE_IZQ = (ANCHO - LUZ_POSTES) / 2 - PW      # 449.6 (se acota como 450)
X_POSTE_DER = ANCHO - X_POSTE_IZQ - PW           # 1965.0
Y0, Y1 = T_PANEL, T_PANEL + PD                   # profundidad del bastidor

# escuadra de cada pata (pie hacia atras + taco + diagonal), lado interior del poste
L_PIE = 550.0
Z_TACO = 570.0                 # centro del perno superior de la diagonal
H_TACO = 50.0
Y_INF = 496.0                  # perno diagonal-pie, medido desde el frente del poste
EXT = 30.0                     # la diagonal sobresale de cada perno
R_TORNILLO = 3.0               # perno 1/4" ~ 6 mm
R_CABEZA = 9.0

CAPAS = {  # nombre -> (color ACI, tipo de linea)
    "01_MADERA": (4, "Continuous"),      # cian
    "02_TORNILLOS": (1, "Continuous"),   # rojo
    "03_COTAS": (2, "Continuous"),       # amarillo
    "04_TEXTO": (7, "Continuous"),       # blanco
    "05_PANEL": (5, "Continuous"),       # azul
    "06_EJES": (6, "CENTER"),
    "07_VENTANAS": (8, "Continuous"),    # no se imprime
    "08_RELLENOS": (9, "Continuous"),    # sombreado de color (se puede apagar)
}
COLOR = {"01_MADERA": (226, 204, 160), "05_PANEL": (36, 125, 190), "02_TORNILLOS": (60, 60, 60)}
LUZ = gp.unit((-0.35, -0.55, 0.76))

# regiones del espacio modelo
O_ORTO = (0.0, 0.0)            # hoja 1, 1:10
O_ISO = (0.0, -7000.0)         # hoja 2, 1:10
O_DET = (0.0, -12000.0)        # hoja 3, 1:5
ISO_K = math.sqrt(2.0 / 3.0)   # escorzo isometrico (0.8165)


# ================================================================== modelo 3D
def diagonal_perfil():
    """Contorno (y, z) de la diagonal (y desde la cara frontal del poste)."""
    p2 = (PD / 2, Z_TACO)
    p1 = (Y_INF, PW / 2)
    ux, uz = p1[0] - p2[0], p1[1] - p2[1]
    L = math.hypot(ux, uz)
    ux, uz = ux / L, uz / L
    a = (p2[0] - ux * EXT, p2[1] - uz * EXT)
    b = (p1[0] + ux * EXT, p1[1] + uz * EXT)
    pts = gp.clip_rect(gp.strip_poly(a, b, PW, ext=0), -200, L_PIE, 0, 5000)
    return pts, p1, p2, L + 2 * EXT


def modelo():
    """Lista de (nombre, capa, spec) en mm. x: ancho, y: profundidad (frente=0), z: altura."""
    M = []
    def caja(n, x0, x1, y0, y1, z0, z1, capa="01_MADERA"):
        M.append((n, capa, gp.box(x0, x1, y0, y1, z0, z1)))
    caja("panel", 0, ANCHO, 0, T_PANEL, Z_PANEL, Z_TOP, "05_PANEL")
    xl0, xl1 = X_POSTE_IZQ, X_POSTE_IZQ + PW
    xr0, xr1 = X_POSTE_DER, X_POSTE_DER + PW
    caja("poste_izq", xl0, xl1, Y0, Y1, 0, ALTO_POSTE)
    caja("poste_der", xr0, xr1, Y0, Y1, 0, ALTO_POSTE)
    caja("larguero_izq", 0, PW, Y0, Y1, Z_PANEL, Z_TOP)
    caja("larguero_der", ANCHO - PW, ANCHO, Y0, Y1, Z_PANEL, Z_TOP)
    for nombre, zc in (("trav_sup", Z_TOP - PW / 2), ("trav_med", Z_PANEL + MITAD), ("trav_inf", Z_PANEL + PW / 2)):
        for k, (a, b) in enumerate(((PW, xl0), (xl1, xr0), (xr1, ANCHO - PW))):
            caja("%s_%d" % (nombre, k), a, b, Y0, Y1, zc - PW / 2, zc + PW / 2)
    prof, p1, p2, _ = diagonal_perfil()
    prof = [(Y0 + y, z) for y, z in prof]
    pernos = []
    for lado, x_in, sg in (("izq", xl1, 1), ("der", xr0, -1)):
        X = lambda a, x_in=x_in, sg=sg: x_in + sg * a
        r = lambda a, b: (min(X(a), X(b)), max(X(a), X(b)))
        f, d = r(0, PD), r(PD, 2 * PD)
        caja("pie_" + lado, f[0], f[1], Y0, Y0 + L_PIE, 0, PW)
        caja("taco_" + lado, f[0], f[1], Y0, Y1, Z_TACO - H_TACO / 2, Z_TACO + H_TACO / 2)
        M.append(("diagonal_" + lado, "01_MADERA", ("pyz", prof, d[0], d[1])))
        # pernos: (nombre, y, z, cara de la cabeza, cara de la tuerca) en coordenada local X()
        for nm, py, pz, a0, a1 in (("pivote", Y0 + PD / 2, PW / 2, -PW, PD),
                                   ("superior", Y0 + PD / 2, Z_TACO, -PW, 2 * PD),
                                   ("inferior", Y0 + p1[0], PW / 2, 0, 2 * PD)):
            c0, c1 = sorted((X(a0 - 5), X(a1 + 12)))
            M.append(("perno_%s_%s" % (nm, lado), "02_TORNILLOS", ("cyl", "x", (0, py, pz), R_TORNILLO, c0, c1, 16)))
            h0, h1 = sorted((X(a0 - 5), X(a0)))
            M.append(("cabeza_%s_%s" % (nm, lado), "02_TORNILLOS", ("cyl", "x", (0, py, pz), R_CABEZA, h0, h1, 16)))
            n0, n1 = sorted((X(a1 + 1), X(a1 + 7)))
            M.append(("tuerca_%s_%s" % (nm, lado), "02_TORNILLOS", ("cyl", "x", (0, py, pz), R_CABEZA * 0.95, n0, n1, 6)))
            pernos.append((lado, nm, py, pz, c0, c1))
    return M, pernos, p1, p2


def solidos(M, nombres=None, region=None, desplaz=None, sin=()):
    out = []
    for n, capa, spec in M:
        if nombres is not None and not any(n.startswith(p) for p in nombres):
            continue
        if any(n.startswith(p) for p in sin):
            continue
        if region is not None:
            spec = gp.clip_spec(spec, region)
            if spec is None:
                continue
        polys = gp.spec_polys(spec)
        if desplaz:
            for p, v in desplaz.items():
                if n.startswith(p):
                    polys = gp.translate_polys(polys, v)
        s = gp.Solid(polys, capa, smooth=(spec[0] == "cyl" and spec[6] > 8))
        s.nombre = n
        out.append(s)
    return out


# ================================================================== DXF
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
    for esc in (10, 5):
        ds = doc.dimstyles.new("COTAS_1_%d" % esc)
        ds.dxf.dimtxsty = "PLANO"
        ds.dxf.dimtxt = 2.5 * esc
        ds.dxf.dimasz = 2.5 * esc
        ds.dxf.dimexe = 1.5 * esc
        ds.dxf.dimexo = 1.0 * esc
        ds.dxf.dimgap = 0.8 * esc
        ds.dxf.dimtad = 1
        ds.dxf.dimdec = 1
        ds.dxf.dimzin = 8
        ds.dxf.dimdsep = ord(".")
        ds.dxf.dimblk = ""                 # flecha cerrada rellena (estandar AutoCAD)
        ds.dxf.dimclrd = 256
        ds.dxf.dimclre = 256
        ds.dxf.dimclrt = 256
        ds.dxf.dimtih = 0
        ds.dxf.dimtoh = 0
    blk = doc.blocks.new("CABEZA_TORNILLO")       # circulo r=3 con cruz
    blk.add_circle((0, 0), R_TORNILLO, dxfattribs={"layer": "0"})
    c = R_TORNILLO * 0.7
    blk.add_line((-c, -c), (c, c), dxfattribs={"layer": "0"})
    blk.add_line((-c, c), (c, -c), dxfattribs={"layer": "0"})
    return doc


class Hoja:
    """Dibuja una vista con un origen en el modelo y tamanos de texto para su escala."""
    def __init__(self, msp, origen, esc, f=1.0):
        self.msp, self.o, self.esc, self.f = msp, origen, esc, f
        self.txt = 2.5 * esc
        self.tit = 5.0 * esc
        self.dimstyle = "COTAS_1_%d" % esc

    def P(self, p):
        return (self.o[0] + p[0] * self.f, self.o[1] + p[1] * self.f)

    def texto(self, s, p, h=None, align=TextEntityAlignment.MIDDLE_CENTER, rot=0.0, capa="04_TEXTO"):
        t = self.msp.add_text(s, height=h or self.txt, rotation=rot,
                              dxfattribs={"layer": capa, "style": "PLANO"})
        t.set_placement(self.P(p), align=align)

    def titulo(self, s, sub, p):
        self.texto(s, p, h=self.tit)
        self.texto(sub, (p[0], p[1] - 1.8 * self.tit))

    def nota(self, s, anchor, ptxt):
        self.msp.add_leader([self.P(ptxt), self.P(anchor)], dimstyle=self.dimstyle,
                            dxfattribs={"layer": "04_TEXTO"})
        der = ptxt[0] >= anchor[0]
        dx = self.txt * 0.4 * (1 if der else -1)
        if "\n" in s:
            mt = self.msp.add_mtext(s.replace("\n", "\\P"), dxfattribs={
                "layer": "04_TEXTO", "style": "PLANO", "char_height": self.txt})
            mt.set_location(self.P((ptxt[0] + dx, ptxt[1])), attachment_point=4 if der else 6)
        else:
            self.texto(s, (ptxt[0] + dx, ptxt[1]),
                       align=TextEntityAlignment.MIDDLE_LEFT if der else TextEntityAlignment.MIDDLE_RIGHT)

    def cota(self, p1, p2, base, angle=0, dec=None):
        over = {} if dec is None else {"dimdec": dec}
        self.msp.add_linear_dim(base=self.P(base), p1=self.P(p1), p2=self.P(p2), angle=angle,
                                dimstyle=self.dimstyle, override=over,
                                dxfattribs={"layer": "03_COTAS"}).render()

    def tornillo(self, p):
        self.msp.add_blockref("CABEZA_TORNILLO", self.P(p), dxfattribs={"layer": "02_TORNILLOS"})

    def rect(self, x0, y0, x1, y1, capa):
        self.msp.add_lwpolyline([self.P(q) for q in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))],
                                close=True, dxfattribs={"layer": capa})

    def piso(self, x0, x1):
        paso = 15 * self.esc
        self.msp.add_line(self.P((x0, 0)), self.P((x1, 0)), dxfattribs={"layer": "04_TEXTO"})
        for i in range(int((x1 - x0) / paso) + 1):
            x = x0 + 4 * self.esc + i * paso
            self.msp.add_line(self.P((x, 0)), self.P((x - 4 * self.esc, -4 * self.esc)),
                              dxfattribs={"layer": "04_TEXTO"})


def sombra(capa, n):
    base = COLOR.get(capa, (200, 200, 200))
    f = 0.62 + 0.38 * max(0.0, gp.dot(n, LUZ))
    return tuple(int(min(255, c * f)) for c in base)


def relleno(msp, pts, rgb):
    h = msp.add_hatch(dxfattribs={"layer": "08_RELLENOS"})
    h.rgb = rgb
    h.paths.add_polyline_path(pts, is_closed=True)


def caras_visibles(sols, view, tile=None):
    """Caras orientadas al observador, ordenadas de atras hacia adelante (pintor)."""
    R, U, V = view
    out = []
    for s in sols:
        for f in s.faces:
            if gp.dot(f.n, V) > -1e-6:
                continue
            pieces = [f.pts]
            if tile and len(f.pts) == 4:
                a, b, c, d = f.pts
                nu = max(1, int(math.ceil(gp.length(gp.sub(b, a)) / tile)))
                nv = max(1, int(math.ceil(gp.length(gp.sub(d, a)) / tile)))
                def B(u, v, a=a, b=b, d=d):
                    return gp.add(gp.add(a, gp.mul(gp.sub(b, a), u)), gp.mul(gp.sub(d, a), v))
                pieces = [[B(i / nu, j / nv), B((i + 1) / nu, j / nv), B((i + 1) / nu, (j + 1) / nv),
                           B(i / nu, (j + 1) / nv)] for i in range(nu) for j in range(nv)]
            for pc in pieces:
                poly = [(gp.dot(p, R), gp.dot(p, U)) for p in pc]
                if abs(gp.signed_area(poly)) < 1e-6:
                    continue
                depth = sum(gp.dot(p, V) for p in pc) / len(pc)
                out.append((depth, poly, s.layer, f.n))
    out.sort(key=lambda t: -t[0])
    return out


def vista_orto(H, sols, view):
    """Vista ortogonal: por cada cara visible, relleno + rectangulo cerrado (de atras hacia adelante)."""
    for _, poly, capa, n in caras_visibles(sols, view):
        pts = [H.P(p) for p in poly]
        relleno(H.msp, pts, sombra(capa, n))
        H.msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": capa})


def vista_iso(H, sols, view, tile=120.0):
    """Isometrico: rellenos sombreados (pintor) + aristas exactas sin lineas ocultas.
    El panel es una placa delgada: se pinta al final si la camara lo ve de frente
    y al principio si lo ve por detras; el resto se ordena por mosaicos."""
    panel = [s for s in sols if s.layer == "05_PANEL"]
    resto = [s for s in sols if s.layer != "05_PANEL"]
    capas = [caras_visibles(resto, view, tile=tile), caras_visibles(panel, view)]
    if view[2][1] < 0:          # camara detras del panel
        capas.reverse()
    for grupo in capas:
        for _, poly, capa, n in grupo:
            relleno(H.msp, [H.P(p) for p in poly], sombra(capa, n))
    for capa, p, q in gp.hidden_line(sols, view):
        H.msp.add_line(H.P(p), H.P(q), dxfattribs={"layer": capa})


def flecha(msp, tip, ang, size):
    a1, a2 = ang + math.radians(165), ang - math.radians(165)
    pts = [tip, (tip[0] + size * math.cos(a1), tip[1] + size * math.sin(a1)),
           (tip[0] + size * math.cos(a2), tip[1] + size * math.sin(a2))]
    h = msp.add_hatch(color=256, dxfattribs={"layer": "03_COTAS"})
    h.paths.add_polyline_path(pts, is_closed=True)


def cota_iso(H, view, A, B, dir_ext, dist, dec=1, txt=None):
    """Cota isometrica: linea de cota paralela a A-B y lineas de extension a lo largo
    del eje dir_ext (estilo isometrico). Muestra la verdadera magnitud."""
    pr = lambda p: H.P(gp.project(p, view))
    a, b = pr(A), pr(B)
    e = gp.project(dir_ext, view)
    el = math.hypot(*e)
    e = (e[0] / el, e[1] / el)
    s = dist * ISO_K
    a2 = (a[0] + e[0] * s, a[1] + e[1] * s)
    b2 = (b[0] + e[0] * s, b[1] + e[1] * s)
    sg = 1 if dist >= 0 else -1
    gap, over = 0.8 * H.esc * sg, 1.5 * H.esc * sg
    for p, q in ((a, a2), (b, b2)):
        H.msp.add_line((p[0] + e[0] * gap, p[1] + e[1] * gap), (q[0] + e[0] * over, q[1] + e[1] * over),
                       dxfattribs={"layer": "03_COTAS"})
    H.msp.add_line(a2, b2, dxfattribs={"layer": "03_COTAS"})
    ang = math.atan2(b2[1] - a2[1], b2[0] - a2[0])
    flecha(H.msp, a2, ang + math.pi, 2.5 * H.esc)
    flecha(H.msp, b2, ang, 2.5 * H.esc)
    if txt is None:
        L = gp.length(gp.sub(B, A))
        txt = "%.*f" % (dec, L)
        if "." in txt:
            txt = txt.rstrip("0").rstrip(".")
    deg = math.degrees(ang)
    if deg > 90.01 or deg < -89.99:
        deg += 180
    m = ((a2[0] + b2[0]) / 2, (a2[1] + b2[1]) / 2)
    nr = math.radians(deg + 90)
    p = (m[0] + math.cos(nr) * H.txt * 0.4, m[1] + math.sin(nr) * H.txt * 0.4)
    t = H.msp.add_text(txt, height=H.txt, rotation=deg, dxfattribs={"layer": "03_COTAS", "style": "PLANO"})
    t.set_placement(p, align=TextEntityAlignment.BOTTOM_CENTER)


# ================================================================== hoja 1: vistas 1:10
def hoja_vistas(msp, M, pernos, p1, p2):
    sols = solidos(M, sin=("perno", "cabeza", "tuerca"))
    xl0, xl1, xr0, xr1 = X_POSTE_IZQ, X_POSTE_IZQ + PW, X_POSTE_DER, X_POSTE_DER + PW
    zm = Z_PANEL + MITAD

    # ---- alzado frontal (x, z)
    H = Hoja(msp, O_ORTO, 10)
    vista_orto(H, sols, gp.view_basis((0, 1, 0)))
    for lado, nm, py, pz, a, b in pernos:
        H.rect(a, pz - R_TORNILLO, b, pz + R_TORNILLO, "02_TORNILLOS")
    H.piso(-300, ANCHO + 300)
    H.texto("PANEL", (ANCHO / 2, zm + MITAD / 2), h=H.tit)
    H.texto("(zona azul 2440 x 1237.3, pegada al marco)", (ANCHO / 2, zm + MITAD / 2 - 70))
    H.nota('POLIN 1"x1/2" (25.4 x 12.7 mm)', (xl0 + PW / 2, 420), (xl0 + 280, 650))
    H.nota("ESCUADRA: pie + taco + diagonal", (xr0 - PD, 300), (xr0 - 280, 700))
    H.nota('PERNOS 1/4"', (xr0 - 2 * PD - 10, Z_TACO), (xr0 - 280, 500))
    H.titulo("VISTA FRONTAL (ALZADO)", "Esc. 1:10", (ANCHO / 2, -330))
    H.cota((0, Z_TOP), (ANCHO, Z_TOP), (0, Z_TOP + 330))
    H.cota((0, Z_TOP), (xl0, Z_TOP), (0, Z_TOP + 170), dec=0)
    H.cota((xl1, Z_TOP), (xr0, Z_TOP), (0, Z_TOP + 170))
    H.cota((xr1, Z_TOP), (ANCHO, Z_TOP), (0, Z_TOP + 170), dec=0)
    H.cota((0, Z_PANEL), (0, Z_TOP), (-330, 0), angle=90)
    H.cota((0, Z_PANEL), (0, zm), (-170, 0), angle=90, dec=2)
    H.cota((0, zm), (0, Z_TOP), (-170, 0), angle=90, dec=2)
    H.cota((xl0, 0), (xl0, Z_PANEL), (-170, 0), angle=90)
    H.cota((ANCHO, 0), (ANCHO, Z_TOP), (ANCHO + 200, 0), angle=90)
    H.cota((xl1 + 2 * PD, 0), (xl1 + 2 * PD, Z_TACO), (xl1 + 170, 0), angle=90)

    # ---- alzado posterior (sx = -x)
    H = Hoja(msp, (O_ORTO[0] + 3300.0 + ANCHO, O_ORTO[1]), 10)
    vista_orto(H, sols, gp.view_basis((0, -1, 0)))
    for lado, nm, py, pz, a, b in pernos:
        H.rect(-b, pz - R_TORNILLO, -a, pz + R_TORNILLO, "02_TORNILLOS")
    for zc in (Z_TOP - PW / 2, zm, Z_PANEL + PW / 2):      # tornillos del marco
        for xa in (PW / 2, xl0 + PW / 2, xr0 + PW / 2, ANCHO - PW / 2):
            H.tornillo((-xa, zc))
    H.piso(-ANCHO - 300, 300)
    H.nota("TORNILLOS (poste / travesanos)", (-(xl0 + PW / 2), zm), (-(xl0 - 260), zm + 260))
    H.nota("CRUZ: travesano medio", (-ANCHO / 2, zm), (-ANCHO / 2 - 250, zm + 330))
    H.nota("PIE + DIAGONAL (lado interior)", (-(xr0 - 1.5 * PD), 300), (-(xr0 - 330), 650))
    H.titulo("VISTA POSTERIOR", "Esc. 1:10 - marco visto por detras", (-ANCHO / 2, -330))
    H.cota((-ANCHO, Z_TOP), (-xr1, Z_TOP), (0, Z_TOP + 170), dec=0)
    H.cota((-xr0, Z_TOP), (-xl1, Z_TOP), (0, Z_TOP + 170))
    H.cota((-xl0, Z_TOP), (0, Z_TOP), (0, Z_TOP + 170), dec=0)
    H.cota((-ANCHO, Z_TOP), (0, Z_TOP), (0, Z_TOP + 330))
    H.cota((0, Z_PANEL), (0, zm), (200, 0), angle=90, dec=2)
    H.cota((0, zm), (0, Z_TOP), (200, 0), angle=90, dec=2)
    H.cota((0, 0), (0, Z_PANEL), (200, 0), angle=90)

    # ---- vista lateral (desde la derecha: frente a la izquierda)
    H = Hoja(msp, (O_ORTO[0] + 6500.0, O_ORTO[1]), 10)
    vista_orto(H, sols, gp.view_basis((-1, 0, 0)))
    for lado, nm, py, pz, a, b in pernos:
        if lado == "der":
            H.tornillo((py, pz))
    H.piso(-250, L_PIE + 300)
    H.nota("PANEL", (T_PANEL / 2, 1700), (-280, 1850))
    H.nota("DIAGONAL", (Y0 + (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2), (420, 700))
    H.nota("PIE", (Y0 + 380, PW / 2), (440, 190))
    H.titulo("VISTA LATERAL", "Esc. 1:10 - desde la derecha", (L_PIE / 2 - 50, -330))
    H.cota((Y0, 0), (Y0 + L_PIE, 0), (0, -170))
    H.cota((0, 0), (0, Z_PANEL), (-220, 0), angle=90)
    H.cota((0, Z_PANEL), (0, Z_TOP), (-220, 0), angle=90)
    H.cota((Y1, 0), (Y1, Z_TOP), (L_PIE + 170, 0), angle=90)
    H.cota((Y1, 0), (Y1, Z_TACO), (300, 0), angle=90)
    H.cota((0, Z_TOP), (Y1, Z_TOP), (0, Z_TOP + 130))

    # ---- vista superior (planta): x a la derecha, y (hacia atras) hacia arriba
    H = Hoja(msp, (O_ORTO[0], O_ORTO[1] + 2950.0), 10)
    vista_orto(H, sols, gp.view_basis((0, 0, -1)))
    for lado, nm, py, pz, a, b in pernos:
        if nm == "inferior":
            H.rect(a, py - R_TORNILLO, b, py + R_TORNILLO, "02_TORNILLOS")
    H.nota("PIE", (xl1 + PD / 2, 380), (xl1 + 280, 450))
    H.nota("PANEL (frente)", (900, T_PANEL / 2), (1100, -170))
    H.titulo("VISTA SUPERIOR (PLANTA)", "Esc. 1:10", (ANCHO / 2, 830))
    H.cota((0, 0), (ANCHO, 0), (0, -330))
    H.cota((xl1, Y0 + L_PIE), (xr0, Y0 + L_PIE), (0, Y0 + L_PIE + 120))
    H.cota((xr0, 0), (xr0, Y0 + L_PIE), (xr0 - 200, 0), angle=90)
    H.cota((ANCHO, 0), (ANCHO, Y1), (ANCHO + 150, 0), angle=90)


# ================================================================== hoja 2: isometricos 1:10
def hoja_isometricos(msp, M):
    sols = solidos(M)
    zm = Z_PANEL + MITAD
    xl0, xl1, xr0, xr1 = X_POSTE_IZQ, X_POSTE_IZQ + PW, X_POSTE_DER, X_POSTE_DER + PW
    Xd, Yd, Zd = (1, 0, 0), (0, 1, 0), (0, 0, 1)

    # ---- isometrico frontal (camara: frente-izquierda-arriba)
    V1 = gp.view_basis((1, 1, -1))
    H = Hoja(msp, O_ISO, 10)
    vista_iso(H, sols, V1)
    cota_iso(H, V1, (0, 0, Z_TOP), (ANCHO, 0, Z_TOP), Zd, 400, dec=0)
    cota_iso(H, V1, (0, 0, Z_TOP), (xl0, 0, Z_TOP), Zd, 200, txt="450")
    cota_iso(H, V1, (xl1, 0, Z_TOP), (xr0, 0, Z_TOP), Zd, 200, dec=0)
    cota_iso(H, V1, (xr1, 0, Z_TOP), (ANCHO, 0, Z_TOP), Zd, 200, txt="450")
    cota_iso(H, V1, (ANCHO, Y1, Z_PANEL), (ANCHO, Y1, zm), Xd, 250, dec=2)
    cota_iso(H, V1, (ANCHO, Y1, zm), (ANCHO, Y1, Z_TOP), Xd, 250, dec=2)
    cota_iso(H, V1, (ANCHO, Y1, Z_PANEL), (ANCHO, Y1, Z_TOP), Xd, 550)
    cota_iso(H, V1, (xr1, Y1, 0), (xr1, Y1, Z_PANEL), Xd, 1025, dec=0)
    ax = gp.project(Xd, V1)
    c = gp.project((ANCHO / 2, 0, zm), V1)
    H.texto("PANEL", c, h=H.tit * 1.5, rot=math.degrees(math.atan2(ax[1], ax[0])))
    bb = gp.project((ANCHO / 2, 0, 0), V1)
    H.titulo("ISOMETRICO FRONTAL", "Esc. 1:10 - cotas en verdadera magnitud", (bb[0] - 200, bb[1] - 700))

    # ---- isometrico posterior (camara: atras-izquierda-arriba)
    V2 = gp.view_basis((1, -1, -1))
    H = Hoja(msp, (O_ISO[0] + 4300.0, O_ISO[1]), 10)
    vista_iso(H, sols, V2)
    pr = lambda q: gp.project(q, V2)
    cota_iso(H, V2, (0, Y1, Z_TOP), (ANCHO, Y1, Z_TOP), Zd, 400, dec=0)
    cota_iso(H, V2, (0, Y1, Z_TOP), (xl0, Y1, Z_TOP), Zd, 200, txt="450")
    cota_iso(H, V2, (xl1, Y1, Z_TOP), (xr0, Y1, Z_TOP), Zd, 200, dec=0)
    cota_iso(H, V2, (xr1, Y1, Z_TOP), (ANCHO, Y1, Z_TOP), Zd, 200, txt="450")
    cota_iso(H, V2, (0, Y1, Z_PANEL), (0, Y1, zm), Yd, 250, dec=2)
    cota_iso(H, V2, (0, Y1, zm), (0, Y1, Z_TOP), Yd, 250, dec=2)
    cota_iso(H, V2, (0, Y1, Z_PANEL), (0, Y1, Z_TOP), Yd, 550)
    cota_iso(H, V2, (xl0, Y1, 0), (xl0, Y1, Z_PANEL), Yd, 900, dec=0)
    cota_iso(H, V2, (xr0 - 2 * PD, Y0, 0), (xr0 - 2 * PD, Y0 + L_PIE, 0), Xd, -300, dec=0)
    a = pr((ANCHO * 0.72, Y1, zm))
    H.nota("CRUZ (travesano medio)", a, (a[0] + 250, a[1] + 450))
    a = pr((xr0 - 1.5 * PD, Y0 + 260, 330))
    H.nota("DIAGONAL / ESCUADRA", a, (a[0] + 400, a[1] - 150))
    a = pr((xl0 + PW / 2, Y1, 600))
    H.nota('POSTE POLIN 1"x1/2"', a, (a[0] - 450, a[1] + 100))
    bb = gp.project((ANCHO / 2, Y1, 0), V2)
    H.titulo("ISOMETRICO POSTERIOR", "Esc. 1:10 - cotas en verdadera magnitud", (bb[0] + 200, bb[1] - 750))


# ================================================================== hoja 2: detalles 1:5
def hoja_detalles(msp, M, pernos, p1, p2):
    k = 5
    # ---- detalle A: perfil de la escuadra (pata derecha vista desde la derecha)
    H = Hoja(msp, O_DET, k)
    reg = (X_POSTE_DER - 2 * PD - 1, ANCHO, -100, 2000, 0, 650)
    vista_orto(H, solidos(M, ["poste_der", "pie_der", "taco_der", "diagonal_der"], reg), gp.view_basis((-1, 0, 0)))
    for lado, nm, py, pz, a, b in pernos:
        if lado == "der":
            H.tornillo((py, pz))
    H.piso(-120, L_PIE + 120)
    H.nota('PERNO 1/4" PASANTE (pivote del pie)', (Y0 + PD / 2, PW / 2), (170, 160))
    H.nota('PERNO 1/4" diagonal-taco-poste', (Y0 + PD / 2, Z_TACO), (150, 650))
    H.nota('PERNO 1/4" diagonal-pie', (Y0 + p1[0], PW / 2), (430, 260))
    H.nota("TACO 50 mm", (Y1, Z_TACO + H_TACO / 2 - 5), (-140, 690))
    H.titulo("DETALLE A - ESCUADRA (perfil)", "Esc. 1:5", (L_PIE / 2, -110))
    H.cota((Y0, 0), (Y1, 0), (0, -40))
    H.cota((0, 0), (0, PW), (-40, 0), angle=90)
    H.cota((Y0, 0), (Y0, Z_TACO), (-90, 0), angle=90)
    H.cota((Y0 + PD / 2, PW / 2), (Y0 + p1[0], PW / 2), (0, -70), dec=0)
    H.cota((Y0, Z_TACO - H_TACO / 2), (Y0, Z_TACO + H_TACO / 2), (-40, 0), angle=90)

    # ---- detalle B: misma union vista de frente (pata izquierda)
    xo = X_POSTE_IZQ
    H = Hoja(msp, (O_DET[0] + 1000.0 - xo, O_DET[1]), k)
    reg = (-1, xo + PW + 2 * PD + 1, -100, 2000, 0, 650)
    vista_orto(H, solidos(M, ["poste_izq", "pie_izq", "taco_izq", "diagonal_izq"], reg), gp.view_basis((0, 1, 0)))
    for lado, nm, py, pz, a, b in pernos:
        if lado == "izq" and nm != "inferior":
            H.msp.add_line(H.P((a - 20, pz)), H.P((b + 20, pz)), dxfattribs={"layer": "06_EJES"})
            H.rect(a, pz - R_TORNILLO, b, pz + R_TORNILLO, "02_TORNILLOS")
            H.rect(a, pz - R_CABEZA, a + 5, pz + R_CABEZA, "02_TORNILLOS")
            H.rect(b - 11, pz - R_CABEZA, b - 5, pz + R_CABEZA, "02_TORNILLOS")
    H.piso(xo - 60, xo + PW + 2 * PD + 60)
    H.nota("POSTE", (xo + PW / 2, 420), (xo - 120, 450))
    H.nota("PIE / TACO", (xo + PW + PD / 2, Z_TACO + 10), (xo + 150, 650))
    H.nota("DIAGONAL", (xo + PW + 1.5 * PD, 300), (xo + 150, 330))
    H.nota("TORNILLOS", (xo + PW + 2 * PD + 8, PW / 2), (xo + 150, 140))
    H.titulo("DETALLE B - UNION (frente)", "Esc. 1:5", (xo + PW + PD, -110))
    H.cota((xo, 0), (xo + PW, 0), (0, -40))
    H.cota((xo + PW, 0), (xo + PW + 2 * PD, 0), (0, -70))

    # ---- detalle C: isometrico despiezado de la escuadra (pata izquierda, cara interior)
    reg = (xo - 30, xo + PW + 2 * PD + 30, -100, 2000, 0, 700)
    off = {"pie_izq": (60, 0, 0), "taco_izq": (60, 0, 0), "diagonal_izq": (120, 0, 0),
           "perno": (-90, 0, 0), "cabeza": (-90, 0, 0), "tuerca": (200, 0, 0)}
    sols = solidos(M, ["poste_izq", "pie_izq", "taco_izq", "diagonal_izq", "perno_", "cabeza_", "tuerca_"], reg, off)
    sols = [s for s in sols if s.layer != "02_TORNILLOS" or s.nombre.endswith("_izq")]
    V = gp.view_basis((-1, 1, -1))
    o = gp.project((xo, 0, 0), V)
    H = Hoja(msp, (O_DET[0] + 1750.0 - o[0], O_DET[1] - o[1]), k)
    vista_iso(H, sols, V, tile=60.0)
    pr = lambda q: gp.project(q, V)
    for lado, nm, py, pz, a, b in pernos:
        if lado == "izq":
            H.msp.add_line(H.P(pr((a - 110, py, pz))), H.P(pr((b + 220, py, pz))), dxfattribs={"layer": "06_EJES"})
    def nota3(s, q, d):
        a = pr(q)
        H.nota(s, a, (a[0] + d[0], a[1] + d[1]))
    nota3("POSTE", (xo + PW / 2, Y0, 650), (-160, 60))
    nota3("PIE (gira sobre el perno)", (xo + PW + 60, Y0 + 420, PW), (160, -110))
    nota3("TACO 50 mm", (xo + PW + 60, Y0, Z_TACO + H_TACO / 2), (-250, 90))
    nota3("DIAGONAL", (xo + PW + PD + 120, Y0 + 250, 330), (200, 110))
    nota3('PERNO 1/4" + rondanas + tuerca', (xo - 95, Y0 + PD / 2, PW / 2), (-200, -100))
    tb = pr((xo, Y0 + L_PIE / 2, 0))
    H.titulo("DETALLE C - ESCUADRA DESPIEZADA", "Isometrico, Esc. 1:5", (tb[0] + 60, tb[1] - 280))


def detalles_marco(msp, M):
    k = 5
    xl0, xl1 = X_POSTE_IZQ, X_POSTE_IZQ + PW
    zm = Z_PANEL + MITAD
    V = gp.view_basis((1, -1, -1))          # camara: atras-izquierda-arriba
    pr = lambda q: gp.project(q, V)
    oy = O_DET[1] - 1150.0
    AMPL = 2.0                              # detalle E al doble -> 1:2.5 en la hoja de 1:5

    # ---- detalle D: esquina superior (larguero + travesano + poste + panel), despiezado
    reg = (-1, xl1 + 220, -1, 60, Z_TOP - 280, Z_TOP + 1)
    off = {"panel": (0, -90, 0), "trav_sup_0": (0, 0, 60), "trav_sup_1": (0, 0, 60)}
    sols = solidos(M, ["panel", "larguero_izq", "trav_sup_0", "trav_sup_1", "poste_izq"], reg, off)
    o = pr((0, 0, Z_TOP - 280))
    H = Hoja(msp, (O_DET[0] + 100 - o[0], oy - o[1]), k)
    vista_iso(H, sols, V, tile=50.0)
    zc = Z_TOP - PW / 2 + 60
    for x0_, x1_ in ((-70, PW + 70), (xl0 - 70, xl1 + 70)):
        for f in (0.3, 0.7):
            H.msp.add_line(H.P(pr((x0_, Y0 + PD * f, zc))), H.P(pr((x1_, Y0 + PD * f, zc))),
                           dxfattribs={"layer": "06_EJES"})
    yb = -90 + T_PANEL
    for a, b in (((PW / 2, yb, Z_TOP - 270), (PW / 2, yb, Z_TOP - 15)),
                 ((15, yb, Z_TOP - PW / 2), (xl1 + 200, yb, Z_TOP - PW / 2)),
                 ((xl0 + PW / 2, yb, Z_TOP - 270), (xl0 + PW / 2, yb, Z_TOP - 15))):
        H.msp.add_line(H.P(pr(a)), H.P(pr(b)), dxfattribs={"layer": "02_TORNILLOS", "linetype": "DASHED"})
    def n3(s, q, d):
        a = pr(q)
        H.nota(s, a, (a[0] + d[0], a[1] + d[1]))
    n3("LARGUERO EXTREMO", (PW / 2, Y1, Z_TOP - 220), (150, -60))
    n3("TRAVESANO SUPERIOR (separado)", (150, Y0, Z_TOP + 60), (-80, 110))
    n3("POSTE (continuo hasta el piso)", (xl0 + PW / 2, Y1, Z_TOP - 230), (-120, -80))
    n3('2 tornillos #8 x 1 1/2" por extremo\n+ pegamento blanco', (-70, Y0 + PD * 0.3, zc), (180, 140))
    n3("PANEL: adhesivo de montaje en todo\nel contacto (linea punteada)", (330, yb, Z_TOP - 200), (200, -60))
    t = pr((xl1 / 2, 0, Z_TOP - 280))
    H.titulo("DETALLE D - ESQUINA SUPERIOR", "Isometrico posterior despiezado, Esc. %s" % ("1:5" if H.f == 1 else "1:2.5"), (t[0], t[1] - 130))

    # ---- detalle E: cruz (travesano medio contra el poste), despiezado
    reg = (xl0 - 150, xl1 + 150, -1, 60, zm - 120, zm + 120)
    off = {"trav_med_0": (-50, 0, 0), "trav_med_1": (50, 0, 0)}
    sols = solidos(M, ["poste_izq", "trav_med_0", "trav_med_1"], reg, off)
    o = pr((xl0 - 150, 0, zm - 120))
    H = Hoja(msp, (O_DET[0] + 1450.0 - AMPL * o[0], oy - AMPL * o[1]), k, AMPL)
    vista_iso(H, sols, V, tile=50.0)
    yc = Y0 + PD / 2
    for sg, xr in ((-1, xl0 - 50), (1, xl1 + 50)):
        a = (xr + sg * 50, yc, zm + PW / 2 + 35)
        b = (xr - sg * 55, yc, zm - 5)
        H.msp.add_line(H.P(pr(a)), H.P(pr(b)), dxfattribs={"layer": "06_EJES"})
    def n3(s, q, d):
        a = pr(q)
        H.nota(s, a, (a[0] + d[0], a[1] + d[1]))
    n3("POSTE", (xl0 + PW / 2, Y1, zm + 100), (50, 30))
    n3("TRAVESANO MEDIO (cruz)", (xl1 + 160, Y1, zm + PW / 2), (30, 45))
    n3('tornillo #8 x 1 1/2" en diagonal\n(lancero), 2 por lado + pegamento', (xl0 - 100, yc, zm + PW / 2 + 35), (-40, 50))
    t = pr((xl0, 0, zm - 120))
    H.titulo("DETALLE E - CRUZ / POSTE", "Isometrico posterior despiezado, Esc. %s" % ("1:5" if H.f == 1 else "1:2.5"), (t[0], t[1] - 130))


# ================================================================== hojas 900 x 600
def extents(msp, region):
    x0, y0, x1, y1 = region
    box = bbox.BoundingBox()
    for e in msp:
        b = bbox.extents([e], fast=True)
        if b.has_data and x0 <= b.center.x <= x1 and y0 <= b.center.y <= y1:
            box.extend(b)
    return box


def marco_hoja(psp, titulo, num, escala):
    att = {"layer": "04_TEXTO"}
    psp.page_setup(size=(900, 600), margins=(0, 0, 0, 0), units="mm", scale=(1, 1))
    psp.add_lwpolyline([(0, 0), (900, 0), (900, 600), (0, 600)], close=True, dxfattribs=att)
    psp.add_lwpolyline([(10, 10), (890, 10), (890, 590), (10, 590)], close=True, dxfattribs=att)
    x0, y0, x1, y1 = 690, 10, 890, 70
    psp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs=att)
    psp.add_line((x0, 45), (x1, 45), dxfattribs=att)
    psp.add_line((x0, 27), (x1, 27), dxfattribs=att)
    psp.add_line((790, y0), (790, 45), dxfattribs=att)
    def t(s, p, h):
        e = psp.add_text(s, height=h, dxfattribs={"layer": "04_TEXTO", "style": "PLANO"})
        e.set_placement(p, align=TextEntityAlignment.MIDDLE_LEFT)
    t("Estructura Cartel Madera", (x0 + 5, 61), 5.5)
    t(titulo, (x0 + 5, 50.5), 3)
    t("ESCALA: " + escala, (x0 + 5, 36), 3)
    t("FECHA: " + datetime.date.today().strftime("%d/%m/%Y"), (795, 36), 3)
    t("UNIDADES: mm", (x0 + 5, 18.5), 3)
    t("HOJA %d/3 - 900 x 600 mm" % num, (795, 18.5), 3)
    return t


def ventana(psp, box, centro, tam, esc):
    c = box.center
    vp = psp.add_viewport(center=centro, size=tam, view_center_point=(c.x, c.y),
                          view_height=tam[1] * esc, dxfattribs={"layer": "07_VENTANAS"})
    vp.dxf.status = 1
    return (box.size.x / esc, box.size.y / esc)


def hojas(doc):
    msp = doc.modelspace()
    doc.layouts.rename("Layout1", "01_VISTAS")
    h1 = doc.layouts.get("01_VISTAS")
    t = marco_hoja(h1, "Vistas frontal, posterior, lateral y superior", 1, "1:10")
    t('Polin 1" x 1/2" (25.4 x 12.7 mm): seccion indicada por el cliente, verificar resistencia.', (20, 18), 3)
    s1 = ventana(h1, extents(msp, (-1e5, -3000, 1e5, 1e5)), (450, 330), (870, 505), 10)

    h2 = doc.layouts.new("02_ISOMETRICOS")
    t = marco_hoja(h2, "Isometricos frontal y posterior", 2, "1:10")
    t("Rellenos de color en capa 08_RELLENOS (apagarla para imprimir solo lineas).", (20, 18), 3)
    s2 = ventana(h2, extents(msp, (-1e5, -10000, 1e5, -3000)), (450, 330), (870, 505), 10)

    h3 = doc.layouts.new("03_DETALLES")
    t = marco_hoja(h3, "Detalles de uniones", 3, "1:5")
    t("Pernos 1/4\" con rondanas y tuerca; tornillos para madera #8 con barreno guia.", (20, 18), 3)
    s3 = ventana(h3, extents(msp, (-1e5, -1e5, 1e5, -10000)), (450, 330), (870, 505), 5)
    return s1, s2, s3


def main():
    doc = setup_document()
    msp = doc.modelspace()
    M, pernos, p1, p2 = modelo()
    hoja_vistas(msp, M, pernos, p1, p2)
    hoja_isometricos(msp, M)
    hoja_detalles(msp, M, pernos, p1, p2)
    detalles_marco(msp, M)
    s1, s2, s3 = hojas(doc)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plano_cartel.dxf")
    doc.saveas(out)
    print("Generado:", out)
    print("Hoja 1, vistas 1:10:      %.0f x %.0f mm (ventana 870 x 505)" % s1)
    print("Hoja 2, isometricos 1:10: %.0f x %.0f mm (ventana 870 x 505)" % s2)
    print("Hoja 3, detalles 1:5:     %.0f x %.0f mm (ventana 870 x 505)" % s3)


if __name__ == "__main__":
    main()
