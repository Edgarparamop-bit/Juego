"""Validaciones geométricas de cada opción (shapely)."""
from shapely.geometry import Point
from shapely.ops import unary_union

import config as C

TOL_A = 0.01


def validar(res):
    out = []
    At = res["area_total"]
    lotes = [L["geom"] for L in res["lotes"]]
    row, don = res["row"], res["don"]

    tl = sum(lotes[i].intersection(lotes[j]).area for i in range(len(lotes)) for j in range(i + 1, len(lotes)))
    out.append(("Sin traslape lote-lote", tl < TOL_A, f"{tl:.4f} m2"))
    u = unary_union(lotes)
    a1, a2, a3 = u.intersection(row).area, u.intersection(don).area, row.intersection(don).area
    out.append(("Sin traslape lotes-vialidad/banquetas", a1 < TOL_A, f"{a1:.4f} m2"))
    out.append(("Sin traslape lotes-donación", a2 < TOL_A, f"{a2:.4f} m2"))
    out.append(("Sin traslape vialidad-donación", a3 < TOL_A, f"{a3:.4f} m2"))

    malos = [f"{L['id']} ({L['frente_alineamiento']:.2f})" for L in res["lotes"] if L["frente_alineamiento"] < C.FRENTE_LOTE - 0.01]
    out.append(("Frente >= 25.00 m sobre alineamiento exterior de banqueta", not malos,
                ", ".join(malos) or f"{len(lotes)} lotes; mínimo {min(L['frente_alineamiento'] for L in res['lotes']):.2f} m"))

    pct = don.area / At
    out.append(("Donación entre 9.9 % y 10.1 %", 0.099 <= pct <= 0.101, f"{100*pct:.3f} %"))
    perim = unary_union([P.exterior for P in res["polys"].values()])
    partes = list(getattr(don, "geoms", [don]))
    out.append(("Donación perimetral (cada parte toca el lindero)", all(p.buffer(0.01).intersects(perim) for p in partes),
                f"{len(partes)} partes; banda base {res['banda']:.3f} m"))

    pb = Point(res["punto_bajo"])
    en_borde = pb.distance(perim) < 0.05
    en_colector = pb.distance(Point(res["cols"]["A"][0])) < 1e-6
    out.append(("Punto bajo único en la red", res["dren"]["n_minimos"] == 1, f"mínimos locales = {res['dren']['n_minimos']}"))
    out.append(("Punto bajo en el borde accesible del colector", en_borde and en_colector, f"({pb.x:.2f}, {pb.y:.2f})"))

    cortos = [c["nombre"] for c in res["calles"] if not c["brazos"]]
    out.append((f"Retornos con brazo >= 15 m ({C.BRAZO_RETORNO:.2f} m)", not cortos and C.BRAZO_RETORNO >= 15.0,
                ", ".join(f"{c['nombre']}: {'T' if len(c['brazos']) == 2 else 'L'}" for c in res["calles"])))
    ciegos = [L["id"] for L in res["lotes"] if not L["geom"].buffer(0.02).intersects(row)]
    out.append(("Ningún lote ciego", not ciegos, ", ".join(ciegos) or "OK"))
    return out
