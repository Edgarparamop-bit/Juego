"""Extrae de ``referencia/Drawing1.dxf`` la traza con la nueva vialidad de proyecto
y escribe ``traza_carretera.py`` (coordenadas UTM, m). Se ejecuta una vez:

    python extraer_drawing1.py
"""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf import path as dxfpath
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, polygonize, unary_union

BASE = Path(__file__).resolve().parent
SRC = BASE / "referencia" / "Drawing1.dxf"
DST = BASE / "traza_carretera.py"


def plano(e) -> LineString:
    return LineString([(v.x, v.y) for v in dxfpath.make_path(e).flattening(0.02)])


def prolongar(l: LineString, d: float) -> LineString:
    c = list(l.coords)

    def e(a, b):
        dx, dy = a[0] - b[0], a[1] - b[1]
        n = math.hypot(dx, dy)
        return (a[0] + dx / n * d, a[1] + dy / n * d)

    c[0], c[-1] = e(c[0], c[1]), e(c[-1], c[-2])
    return LineString(c)


def cara(lineas, cerca) -> list:
    caras = [f for f in polygonize(unary_union(lineas)) if f.area > 50]
    f = min(caras, key=lambda f: f.distance(Point(cerca)))
    return [(round(x, 2), round(y, 2)) for x, y in f.exterior.simplify(0.02).coords]


def tramo(l: LineString, a, b) -> list:
    sa, sb = sorted((l.project(Point(a)), l.project(Point(b))))
    from shapely.ops import substring
    t = substring(l, sa, sb).simplify(0.02)
    return [(round(x, 2), round(y, 2)) for x, y in t.coords]


def main():
    doc = ezdxf.readfile(SRC)
    msp = doc.modelspace()
    AS = [plano(e) for e in msp.query('LWPOLYLINE[layer=="ASFALTO"]')]
    X0, Y0 = 357000.0, 2285000.0
    P = lambda x, y: (X0 + x, Y0 + y)  # noqa: E731
    # Identificación de líneas de la vialidad de proyecto (diagonal), por posición.
    ref_a, ref_b = Point(P(995.87, 184.48)), Point(P(1137.87, 313.26))
    lindero_a = min(AS, key=lambda l: l.distance(ref_a))          # paramento Macrolote 1
    lindero_b = min(AS, key=lambda l: l.distance(ref_b))          # paramento Macrolote 2
    otros = [l for l in AS if l is not lindero_a and l is not lindero_b]
    lejos = sorted(otros, key=lambda l: abs(l.distance(ref_b) - 12.0))[0]  # paramento opuesto
    sur = [plano(e) for e in msp.query('LINE[layer=="0"]')]
    nw_a = LineString([P(941.73, 289.09), P(879.89, 126.01)])
    poligono_b = plano(msp.query('LWPOLYLINE[layer=="Polígono"]').first)
    tope_a = LineString([P(943.22, 288.76), P(1071.21, 260.23)])

    neto_a = cara([prolongar(lindero_a, 3), prolongar(nw_a, 6), *[prolongar(s, 80) for s in sur]],
                  P(966, 212))
    neto_b = cara([lindero_b, prolongar(poligono_b, 3)], P(1135, 375))
    via_a = cara([prolongar(lindero_a, 3), prolongar(lejos, 5), prolongar(nw_a, 6),
                  *[prolongar(s, 80) for s in sur], prolongar(tope_a, 60)], P(1004, 184))
    via_b = cara([lindero_b, prolongar(poligono_b, 3)], P(1174, 347))

    # Eje: punto medio entre paramentos (derecho de vía).
    eje = []
    for i in range(0, int(lejos.length) + 1):
        p = lejos.interpolate(i)
        q = nearest_points(unary_union([lindero_a, lindero_b]), p)[0]
        if p.distance(q) < 14:
            eje.append(((p.x + q.x) / 2, (p.y + q.y) / 2))
    eje = [(round(x, 2), round(y, 2)) for x, y in LineString(eje).simplify(0.05).coords]

    av_a = tramo(lindero_a, P(917.27, 118.6), P(1073.76, 249.77))
    av_b = tramo(lindero_b, P(1087.95, 271.21), P(1234.11, 439.19))
    vialidades = [[(round(x, 2), round(y, 2)) for x, y in l.simplify(0.02).coords] for l in AS]
    cuneta = [[(round(x, 2), round(y, 2)) for x, y in plano(e).coords]
              for e in msp.query('LWPOLYLINE[layer=="CUNETA"]')]

    f = lambda pts: "[\n" + "".join(f"    ({x:.2f}, {y:.2f}),\n" for x, y in pts) + "]"  # noqa
    out = ['"""Traza generada por extraer_drawing1.py desde referencia/Drawing1.dxf (no editar)."""',
           "", f"NETO_A = {f(neto_a)}", f"NETO_B = {f(neto_b)}",
           f"VIALIDAD_EN_PARCELA_A = {f(via_a)}", f"VIALIDAD_EN_PARCELA_B = {f(via_b)}",
           f"EJE_VIALIDAD = {f(eje)}", f"LINDERO_AVENIDA_A = {f(av_a)}",
           f"LINDERO_AVENIDA_B = {f(av_b)}",
           "VIALIDADES = [\n" + "".join(f"    {v},\n" for v in vialidades) + "]",
           "CUNETA = [\n" + "".join(f"    {v},\n" for v in cuneta) + "]", ""]
    DST.write_text("\n".join(out), encoding="utf-8")
    print(DST)


if __name__ == "__main__":
    main()
