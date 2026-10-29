"""Construcción geométrica (shapely) de vialidades, donación y lotes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, polygonize, substring, unary_union

import config

MITRE = 2  # shapely join_style
FLAT = 2  # shapely cap_style


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def polygons(geom: BaseGeometry) -> list[Polygon]:
    """Devuelve los polígonos (con área) contenidos en cualquier geometría."""
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        return [p for g in geom.geoms for p in polygons(g)]
    return []


def lines(geom: BaseGeometry) -> list[LineString]:
    if geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if hasattr(geom, "geoms"):
        return [ln for g in geom.geoms for ln in lines(g)]
    return []


def clean(geom: BaseGeometry, min_area: float = 0.01) -> BaseGeometry:
    return unary_union([p for p in polygons(geom.buffer(0)) if p.area > min_area])


def unit(dx: float, dy: float) -> tuple[float, float]:
    n = math.hypot(dx, dy)
    return dx / n, dy / n


def tangent(line: LineString, s: float, h: float = 0.5) -> tuple[float, float]:
    a = line.interpolate(max(0.0, s - h))
    b = line.interpolate(min(line.length, s + h))
    return unit(b.x - a.x, b.y - a.y)


def prolongar_inicio(line: LineString, d: float) -> LineString:
    c = list(line.coords)
    ux, uy = unit(c[0][0] - c[1][0], c[0][1] - c[1][1])
    return LineString([(c[0][0] + ux * d, c[0][1] + uy * d), *c])


def extend(line: LineString, d: float) -> LineString:
    """Prolonga una polilínea ``d`` metros por ambos extremos."""
    c = list(line.coords)
    (x0, y0), (x1, y1) = c[0], c[1]
    ux, uy = unit(x0 - x1, y0 - y1)
    c[0] = (x0 + ux * d, y0 + uy * d)
    (x0, y0), (x1, y1) = c[-1], c[-2]
    ux, uy = unit(x0 - x1, y0 - y1)
    c[-1] = (x0 + ux * d, y0 + uy * d)
    return LineString(c)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
@dataclass
class Lote:
    numero: int
    poligono: Polygon
    frente: float
    frente_lineas: list[LineString]
    lado: str
    estacion: float

    @property
    def area(self) -> float:
        return self.poligono.area

    def ancho_fondo(self) -> tuple[float, float]:
        """Ancho (paralelo al frente) y fondo (perpendicular) del predio."""
        ref = max(self.frente_lineas, key=lambda ln: ln.length, default=None)
        if ref is None:
            rect = self.poligono.minimum_rotated_rectangle
            c = list(rect.exterior.coords)
            a, b = math.dist(c[0], c[1]), math.dist(c[1], c[2])
            return max(a, b), min(a, b)
        (x0, y0), (x1, y1) = ref.coords[0], ref.coords[-1]
        ux, uy = unit(x1 - x0, y1 - y0)
        pts = list(self.poligono.exterior.coords)
        along = [x * ux + y * uy for x, y in pts]
        across = [-x * uy + y * ux for x, y in pts]
        return max(along) - min(along), max(across) - min(across)


@dataclass
class Macrolote:
    nombre: str
    clave: str
    poligono: Polygon
    eje: LineString
    eje_completo: LineString
    derecho_via: BaseGeometry
    arroyo: BaseGeometry
    banqueta: BaseGeometry
    donacion: BaseGeometry
    retorno_t: Polygon
    lotes: list[Lote] = field(default_factory=list)
    divisorias: list[LineString] = field(default_factory=list)
    remanentes: float = 0.0

    @property
    def area_total(self) -> float:
        return self.poligono.area

    @property
    def area_donacion(self) -> float:
        return self.donacion.area

    @property
    def area_vialidad(self) -> float:
        return self.derecho_via.area

    @property
    def area_vendible(self) -> float:
        return sum(l.area for l in self.lotes)

    @property
    def longitud_vialidad(self) -> float:
        return self.eje.length

    @property
    def acceso(self) -> Point:
        """Punto donde el eje cruza el lindero (acceso al macrolote)."""
        return Point(self.eje.coords[0])


# ---------------------------------------------------------------------------
# Vialidad
# ---------------------------------------------------------------------------
def _curvas_acceso(poly: Polygon, eje: LineString,
                   radios: tuple[float, float]) -> BaseGeometry:
    """Radios de giro de la guarnición donde la vialidad toca el lindero.

    Para cada lado del acceso se traza el arco de radio ``r`` tangente a la
    orilla del derecho de vía y al lindero del predio.
    """
    semi = config.SECCION_TOTAL / 2
    eje = prolongar_inicio(eje, 60.0)
    cruce = eje.intersection(poly.exterior)
    acceso = min((g for g in getattr(cruce, "geoms", [cruce]) if isinstance(g, Point)),
                 key=eje.project)
    interior = poly.buffer(0)
    piezas = []
    for lado, r in zip((1, -1), radios):  # 1 = izquierda, -1 = derecha
        if r <= 0:
            continue
        orilla = eje.offset_curve(lado * semi)
        guia = eje.offset_curve(lado * (semi + r))
        esquinas = orilla.intersection(poly.exterior)
        esquinas = [g for g in getattr(esquinas, "geoms", [esquinas]) if isinstance(g, Point)]
        if not esquinas:
            continue
        x = min(esquinas, key=acceso.distance)
        # Lado del lindero que corta la orilla, prolongado y desplazado r hacia dentro.
        anillo = list(poly.exterior.coords)
        a, b = min(zip(anillo, anillo[1:]), key=lambda ab: LineString(ab).distance(x))
        lindero = extend(LineString([a, b]), 200.0)
        paralela = max((lindero.offset_curve(r), lindero.offset_curve(-r)),
                       key=lambda ln: interior.contains(ln.interpolate(ln.project(x))))
        centros = guia.intersection(paralela)
        centros = [g for g in getattr(centros, "geoms", [centros]) if isinstance(g, Point)]
        if not centros:
            continue
        c = min(centros, key=acceso.distance)
        t1 = orilla.interpolate(orilla.project(c))
        t2 = lindero.interpolate(lindero.project(c))
        # Zona entre la orilla real (curva) del derecho de vía, el lindero y el arco.
        sx, s1 = sorted((orilla.project(x), orilla.project(t1)))
        tramo = list(substring(orilla, sx, s1).coords)
        if Point(tramo[0]).distance(x) > Point(tramo[-1]).distance(x):
            tramo = tramo[::-1]
        tri = Polygon([*tramo, (t2.x, t2.y)]).buffer(0)
        piezas.append(tri.difference(c.buffer(r, quad_segs=32)).intersection(interior))
    return unary_union(piezas) if piezas else Polygon()


def construir_vialidad(poly: Polygon, eje: LineString, retorno: Polygon,
                       radios: tuple[float, float]):
    semi = config.SECCION_TOTAL / 2
    # El tronco llega al centro del cabezal en T; el cabezal define el remate.
    tronco = substring(eje, 0, eje.project(retorno.centroid))
    row = unary_union([
        tronco.buffer(semi, cap_style=FLAT, join_style=1, quad_segs=24),
        retorno,
        _curvas_acceso(poly, eje, radios),
    ]).buffer(0.02, join_style=MITRE).buffer(-0.02, join_style=MITRE)
    # Arroyo = derecho de vía menos la franja de banqueta (concéntrica),
    # sin recortar hacia el lindero de acceso, que continúa fuera del predio.
    fuera = poly.buffer(60).difference(poly)
    arroyo = unary_union([row, fuera]).buffer(-config.BANQUETA, join_style=MITRE)
    row = clean(row.intersection(poly))
    arroyo = clean(arroyo.intersection(row))
    banqueta = clean(row.difference(arroyo))
    return row, arroyo, banqueta


# ---------------------------------------------------------------------------
# Lotificación
# ---------------------------------------------------------------------------
def _caras(area: BaseGeometry, cortes: list[LineString]) -> list[Polygon]:
    bordes = [ln for p in polygons(area) for ln in [p.exterior, *p.interiors]]
    caras = polygonize(unary_union([LineString(b.coords) for b in bordes] + cortes))
    return [c for c in caras if area.contains(c.representative_point())]


def _frente(lote: Polygon, row: BaseGeometry) -> list[LineString]:
    contacto = lote.exterior.intersection(row.buffer(0.02))
    merged = linemerge(lines(contacto)) if lines(contacto) else LineString()
    return [ln for ln in lines(merged) if ln.length > 0.5]


def divisorias_frente_fijo(bloques: list[Polygon], row: BaseGeometry,
                           frente: float) -> list[LineString]:
    """Genera divisorias perpendiculares a la banqueta cada ``frente`` m."""
    cortes = []
    for b in bloques:
      for fr in _frente(b, row):
        n = int(fr.length // frente)
        if fr.length - n * frente >= frente / 2:
            n += 1
        for k in range(1, n):
            s = k * frente
            q = fr.interpolate(s)
            tx, ty = tangent(fr, s, 1.0)
            nx, ny = -ty, tx
            if not b.contains(Point(q.x + nx * 0.6, q.y + ny * 0.6)):
                nx, ny = -nx, -ny
            rayo = LineString([(q.x - nx, q.y - ny), (q.x + nx * 400, q.y + ny * 400)])
            tramos = lines(rayo.intersection(b))
            if not tramos:
                continue
            tramo = min(tramos, key=lambda ln: ln.distance(q))
            # El corte se detiene en el primer corte ya trazado (esquinas,
            # cabezales del retorno en T), para no atravesar otros lotes.
            cruces = [p for c in cortes for p in getattr(tramo.intersection(c), "geoms",
                                                        [tramo.intersection(c)])
                      if isinstance(p, Point) and p.distance(q) > 1.5]
            if cruces:
                tope = min(cruces, key=q.distance)
                tramo = substring(tramo, 0, tramo.project(tope) + 0.5)
            cortes.append(extend(tramo, 1.0))
    return cortes


def fusionar_sin_frente(caras: list[Polygon], row: BaseGeometry,
                        frente_min: float) -> list[Polygon]:
    """Integra al vecino con mayor lindero común las caras sin frente útil."""
    caras = list(caras)
    while True:
        malas = [c for c in caras if c.area < config.AREA_MINIMA_LOTE
                 or sum(f.length for f in _frente(c, row)) < frente_min]
        if not malas or len(caras) < 2:
            return caras
        c = min(malas, key=lambda p: p.area)
        otras = [o for o in caras if o is not c]
        vecino = max(otras, key=lambda o: c.boundary.intersection(o.boundary.buffer(0.01)).length)
        if c.boundary.intersection(vecino.boundary.buffer(0.01)).length < 0.5:
            return caras
        caras = [o for o in otras if o is not vecino] + [clean(unary_union([c, vecino]))]


def ajustar_divisoria(div: LineString, area: BaseGeometry, tol: float = 0.6,
                      d: float = 2.0) -> LineString:
    """Ajusta los extremos de una divisoria al borde del área vendible.

    Si un extremo coincide (± ``tol``) con un vértice del borde se fija a él;
    si no, se prolonga ``d`` metros para garantizar el corte (p. ej. contra la
    nueva orilla de banqueta de la sección de 12 m).
    """
    vertices = [Point(c) for p in polygons(area) for r in [p.exterior, *p.interiors]
                for c in r.coords]
    c = list(div.coords)
    for i, j in ((0, 1), (-1, -2)):
        p = Point(c[i])
        v = min(vertices, key=p.distance)
        if p.distance(v) <= tol:
            c[i] = (v.x, v.y)
        else:
            ux, uy = unit(c[i][0] - c[j][0], c[i][1] - c[j][1])
            c[i] = (c[i][0] + ux * d, c[i][1] + uy * d)
    return LineString(c)


def construir_macrolote(nombre: str, cfg: dict, modo: str) -> Macrolote:
    poly = Polygon(cfg["poligono"])
    eje_completo = LineString(cfg["eje"])
    retorno = Polygon(cfg["retorno_t"])
    row, arroyo, banqueta = construir_vialidad(poly, eje_completo, retorno,
                                               cfg["radios_acceso"])
    eje = max(lines(eje_completo.intersection(poly)), key=lambda ln: ln.length)

    donacion = clean(unary_union([Polygon(d).buffer(0) for d in cfg["donacion"]])
                     .intersection(poly).difference(row))
    vendible = clean(poly.difference(row).difference(donacion))
    # Apertura morfológica mínima: elimina agujas de ancho nulo entre linderos
    # colineales (p. ej. donación sobre el lindero sureste).
    vendible = clean(vendible.buffer(-0.005, join_style=MITRE).buffer(0.005, join_style=MITRE))

    if modo == "FRENTE_25":
        bloques = [b for b in polygons(vendible) if b.area >= config.AREA_MINIMA_LOTE]
        divisorias = divisorias_frente_fijo(bloques, row, config.FRENTE_LOTE)
    else:
        divisorias = [ajustar_divisoria(LineString(d), vendible) for d in cfg["divisorias"]]

    caras = _caras(vendible, divisorias)
    if modo == "FRENTE_25":
        caras = fusionar_sin_frente(caras, row, config.FRENTE_LOTE / 2)
    chicas = [c for c in caras if c.area < config.AREA_MINIMA_LOTE]
    caras = [c for c in caras if c.area >= config.AREA_MINIMA_LOTE]
    remanente = sum(c.area for c in chicas)
    if chicas:  # remanentes sin frente útil: se suman a la donación
        donacion = clean(unary_union([donacion, *chicas]))
    # Cierre exacto: cualquier residuo de la poligonización también es donación.
    residuo = clean(vendible.difference(unary_union(caras)), 0.0)
    if residuo.area > 0:
        donacion = clean(unary_union([donacion, residuo]))
        remanente += residuo.area

    m = Macrolote(nombre, cfg["clave"], poly, eje, eje_completo, row, arroyo,
                  banqueta, donacion, retorno, divisorias=divisorias,
                  remanentes=remanente)

    lotes = []
    for c in caras:
        c = c.simplify(0.0)
        p = c.representative_point()
        s = eje_completo.project(p)
        tx, ty = tangent(eje_completo, s)
        q = eje_completo.interpolate(s)
        lado = "IZQ" if tx * (p.y - q.y) - ty * (p.x - q.x) > 0 else "DER"
        fr = _frente(c, row)
        lotes.append(Lote(0, c, sum(f.length for f in fr), fr, lado, s))
    # Numeración en sentido antihorario: lado izquierdo de acceso a retorno,
    # luego lado derecho de retorno a acceso.
    izq = sorted((l for l in lotes if l.lado == "IZQ"), key=lambda l: l.estacion)
    der = sorted((l for l in lotes if l.lado == "DER"), key=lambda l: -l.estacion)
    m.lotes = izq + der
    return m


def construir_proyecto(modo: str | None = None) -> list[Macrolote]:
    modo = modo or config.MODO_LOTIFICACION
    macros = [construir_macrolote(n, c, modo) for n, c in config.MACROLOTES.items()]
    n = 1
    for m in macros:
        for l in m.lotes:
            l.numero = n
            n += 1
    return macros


def seccion_en(m: Macrolote, fraccion: float):
    """Punto del eje y vectores tangente/normal para rotular la sección."""
    s = m.eje.length * fraccion
    p = m.eje.interpolate(s)
    tx, ty = tangent(m.eje, s, 2.0)
    return (p.x, p.y), (tx, ty), (-ty, tx)
