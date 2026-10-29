"""Validaciones geométricas de cada opción."""
import config as C

try:
    from shapely.geometry import Point, box
    from shapely.ops import unary_union
    HAY_SHAPELY = True
except ImportError:  # pragma: no cover
    HAY_SHAPELY = False

TOL_A = 0.01   # m² de traslape tolerado (redondeo numérico)


def validar(res):
    """Devuelve lista de (prueba, ok, detalle)."""
    out = []
    A = C.ANCHO * C.LARGO
    if not HAY_SHAPELY:
        suma = sum(L["frente"] * L["fondo"] for L in res["lotes"])
        out.append(("Validación básica por áreas (sin shapely)", suma < A, f"lotes {suma:.2f} < total {A:.2f}"))
        out.append(("Limitación", True, "Sin shapely no se verifican traslapes ni frentes."))
        return out
    lotes = [L["geom"] for L in res["lotes"]]
    row, don = res["row"], res["don"]

    # 1. traslapes
    tl = 0.0
    for i in range(len(lotes)):
        for j in range(i + 1, len(lotes)):
            tl += lotes[i].intersection(lotes[j]).area
    out.append(("Sin traslape lote-lote", tl < TOL_A, f"{tl:.4f} m2"))
    u = unary_union(lotes)
    a1, a2, a3 = u.intersection(row).area, u.intersection(don).area, row.intersection(don).area
    out.append(("Sin traslape lotes-vialidad/banqueta", a1 < TOL_A, f"{a1:.4f} m2"))
    out.append(("Sin traslape lotes-donación", a2 < TOL_A, f"{a2:.4f} m2"))
    out.append(("Sin traslape vialidad-donación", a3 < TOL_A, f"{a3:.4f} m2"))

    # 2. frente >= 25.00 sobre alineamiento exterior de banqueta
    borde_row = row.boundary
    malos = []
    for L in res["lotes"]:
        fr = L["geom"].boundary.intersection(borde_row.buffer(0.005)).length
        # el frente contiguo más largo es el lado sobre la calle; las esquinas pueden sumar 2 lados
        if fr < C.FRENTE_LOTE - 0.01:
            malos.append(f"{L['id']} ({fr:.2f} m)")
    out.append(("Todos los lotes con frente >= 25.00 m a vialidad", not malos, ", ".join(malos) or f"{len(lotes)} lotes OK"))

    # 3. donación perimetral y 9.9 % - 10.1 %
    pct = don.area / A
    out.append(("Donación entre 9.9 % y 10.1 %", 0.099 <= pct <= 0.101, f"{100*pct:.3f} %"))
    env = box(0, 0, C.ANCHO, C.LARGO)
    nucleo = env.buffer(-(res["b"] + 0.01))
    fuera = don.intersection(nucleo).area
    toca = all(g.intersects(env.exterior) for g in getattr(don, "geoms", [don]))
    out.append(("Donación perimetral (solo banda de borde, toca el límite)", fuera < TOL_A and toca,
                f"ancho de banda {res['b']:.3f} m; área fuera de banda {fuera:.4f} m2"))

    # 4. punto bajo único, en borde accesible (sobre un eje que llega al límite)
    pb = Point(res["lay"]["punto_bajo"])
    en_borde = pb.distance(env.exterior) < 1e-6
    en_eje = any(pb.distance(_ls(c["pts"])) < 1e-6 for c in res["lay"]["calles"])
    out.append(("Punto bajo único", res["dren"]["n_minimos"] == 1, f"mínimos = {res['dren']['n_minimos']}"))
    out.append(("Punto bajo en borde accesible (eje vial en el límite)", en_borde and en_eje,
                f"({pb.x:.2f}, {pb.y:.2f})"))

    # 5. cada lote con acceso (toca vialidad)
    ciegos = [L["id"] for L in res["lotes"] if not L["geom"].buffer(0.01).intersects(row)]
    out.append(("Ningún lote ciego", not ciegos, ", ".join(ciegos) or "OK"))
    return out


def _ls(pts):
    from shapely.geometry import LineString
    return LineString(pts)
