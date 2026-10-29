"""Parámetros de diseño del parque industrial (unidades: metros)."""

# Envolvente rectangular común a las 3 opciones.
# El área de referencia es la suma de los macrolotes A + B de lotificaciones.dwfx
# (14,131.29 + 17,965.21 m²); el rectángulo conserva esa misma área total.
AREA_REFERENCIA = 32096.50
ANCHO = 172.00                                  # eje X (poniente -> oriente)
LARGO = round(AREA_REFERENCIA / ANCHO, 2)       # eje Y (sur -> norte) = 186.61 m
ORIGEN = (0.0, 0.0)                             # esquina surponiente

# Sección vial obligatoria: 1.50 + 9.00 + 1.50 = 12.00 m
BANQUETA = 1.50
ARROYO = 9.00
SECCION = BANQUETA + ARROYO + BANQUETA          # 12.00 m
assert abs(SECCION - 12.00) < 1e-9

# Lotes
FRENTE_LOTE = 25.00          # medido sobre el alineamiento exterior de banqueta
FONDO_MINIMO = 15.00         # fondo mínimo aceptable para un lote industrial

# Donación municipal perimetral (áreas verdes)
DONACION_OBJETIVO = 0.100
DONACION_TOLERANCIA = 0.001  # ±0.1 %

# Drenaje pluvial (sin topografía: pendiente longitudinal mínima supuesta)
PENDIENTE_LONGITUDINAL = 0.005   # 0.5 %
COTA_PUNTO_BAJO = 100.00         # cota supuesta en la salida de drenaje (m)

# Textos DXF (altura entre 1.5 y 2.5 m)
H_TITULO = 2.5
H_TEXTO = 2.0
H_NOTA = 1.5

OUT_DIR = "out"
