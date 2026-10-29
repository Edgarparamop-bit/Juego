"""Parámetros de diseño del parque industrial (unidades: metros, escala 1:1).

Polígono base: los dos macrolotes reales de `lotificaciones.dwfx` (forma de
boomerang con cortes diagonales), trasladados para que la esquina surponiente de
su envolvente quede en el origen (0,0). La orientación es la original (norte = +Y).
"""

# Traslado al sistema original (UTM) para superponer sobre lotificaciones.dwg:
#   X_utm = x + ORIGEN_UTM[0] ;  Y_utm = y + ORIGEN_UTM[1]
ORIGEN_UTM = (357879.275, 2285119.682)

# Macrolotes (vértices en sentido antihorario). Entre A y B pasa una calle municipal.
MACROLOTES = {
    "A": [(0.000, 4.887), (62.346, 169.391), (181.034, 142.883), (182.984, 142.093),
          (184.653, 140.662), (185.845, 138.874), (186.370, 136.609), (186.238, 134.463),
          (184.671, 131.483), (31.232, 2.742), (26.187, 0.238), (22.053, 0.000)],
    "B": [(167.725, 158.186), (238.296, 345.457), (354.762, 319.470), (328.059, 262.490),
          (258.561, 193.590), (210.878, 153.417), (207.302, 151.272), (203.249, 150.556),
          (200.269, 150.914)],
}
# Borde más bajo (frente al fraccionamiento La Espiga, en diagonal): índices de
# vértices de sur a norte. El colector principal corre paralelo a ese borde.
BORDE_BAJO = {"A": [9, 8], "B": [5, 4, 3, 2]}
# Linderos con calle municipal (donde se abren los accesos): sur de A = avenida
# principal; norte de A y sur de B = calle intermedia; norte de B = calle norte.

# Sección vial obligatoria: 1.50 + 9.00 + 1.50 = 12.00 m
BANQUETA = 1.50
ARROYO = 9.00
SECCION = BANQUETA + ARROYO + BANQUETA
assert abs(SECCION - 12.00) < 1e-9

# Retorno rectangular en T (o en L si un brazo no cabe), sin glorietas.
# Cada brazo deja 17.00 m de arroyo libre fuera del arroyo de la calle
# (> 15 m mínimo; un tractocamión T3-S2 mide ~16.5 m): el vehículo entra,
# retrocede a un brazo y sale de frente.
BRAZO_RETORNO = 17.00

# Lotes
FRENTE_LOTE = 25.00          # mínimo, sobre el alineamiento exterior de banqueta
FONDO_LIBRE_TRAS_RETORNO = 25.00
AREA_MIN_LOTE = 600.00       # lote industrial mínimo; piezas menores se unen a la vecina

# Donación municipal perimetral
DONACION_OBJETIVO = 0.100
DONACION_TOLERANCIA = 0.001

# Drenaje (sin topografía)
PENDIENTE_LONGITUDINAL = 0.005   # 0.5 %
COTA_PUNTO_BAJO = 100.00         # cota supuesta en la salida (m)

# Textos DXF (1.5 a 2.5 m)
H_TITULO = 2.5
H_TEXTO = 2.0
H_NOTA = 1.5

OUT_DIR = "out"
