"""Lotificación de 6 lotes con la vialidad de proyecto de ``referencia/Drawing1.dxf``.

La vialidad diagonal de proyecto (12 m en el Macrolote 2) entra a los predios de
ambos macrolotes (al poniente colindan las parcelas 60 y 49). Cada macrolote
neto queda limitado por el paramento de esa vialidad. La
traza se extrae con ``extraer_drawing1.py`` y está en ``traza_carretera.py``.
"""

from pathlib import Path

import traza_carretera as T

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out" / "carretera"
README_PATH = BASE_DIR / "README_CARRETERA.md"
REFERENCIA_DXF = BASE_DIR / "referencia" / "Drawing1.dxf"

DONACION_PCT = 0.10  # 10 % del área neta de cada macrolote
LOTES_POR_MACROLOTE = 3
PENDIENTE_DRENAJE = 0.005
COTA_MINIMA = 100.00
PUNTO_DRENAJE = (357879.36, 2285124.60)  # vértice suroeste del Macrolote 1

# Capas del plano de referencia que se importan como contexto (cuadrícula UTM,
# norte, rótulos catastrales, anillo vial, superficies afectadas, etc.).
# Las vialidades se redibujan en VIAL_ASFALTO / VIAL_BANQUETA y los rellenos de
# las parcelas se omiten para no tapar los lotes.
CONTEXTO_EXCLUIR_CAPAS = {"ASFALTO", "CUNETA", "Proy_Guarnición", "001 PROY ACCESO"}

NOMBRE_VIALIDAD = "VIALIDAD DE PROYECTO (DIAGONAL)"
TEXTO_FRENTE = "FRENTE A VIALIDAD"
TABLAS_APILADAS = True  # cuadro de lotes debajo del cuadro de áreas
VIALIDADES = T.VIALIDADES
EJE_VIALIDAD = T.EJE_VIALIDAD

MACROLOTES = {
    "MACROLOTE 1": {
        "clave": "A",
        "poligono": T.NETO_A,
        "vialidad_en_parcela": T.VIALIDAD_EN_PARCELA_A,
        "superficie_afectada_plano": 1103.172,
        "lindero_fondo": [(357879.36, 2285124.60), (357941.73, 2285289.09)],
        "lindero_avenida": T.LINDERO_AVENIDA_A,
        "lindero_cabecera": [(357941.73, 2285289.09), (358071.21, 2285260.23)],
        "rotulo": (357880.0, 2285250.0),
        "secciones": [0.30, 0.65],
    },
    "MACROLOTE 2": {
        "clave": "B",
        "poligono": T.NETO_B,
        "vialidad_en_parcela": T.VIALIDAD_EN_PARCELA_B,
        "superficie_afectada_plano": 1145.612,
        "lindero_fondo": [(358047.08, 2285277.90), (358117.60, 2285465.16)],
        "lindero_avenida": T.LINDERO_AVENIDA_B,
        "lindero_cabecera": [(358117.60, 2285465.16), (358234.11, 2285439.19)],
        "rotulo": (358170.0, 2285482.0),
        "secciones": [0.35, 0.70],
    },
}

# Posición de títulos y cuadros (espacio libre al poniente del Macrolote 2,
# a la derecha de la rosa de los vientos del plano de referencia).
TABLA_ORIGEN = (357887.0, 2285468.0)
TABLA_ANCHOS = (50.0, 26.0)
TABLA_LOTES_ANCHOS = (31.0, 37.0)
TITULO_ORIGEN = (357892.0, 2285522.0)

PROPUESTAS = {
    1: {
        "nombre": "PROPUESTA 1 - DONACIÓN AL FONDO, CORTES PARALELOS A LAS CABECERAS",
        "donacion": "fondo",
        "cortes": "cabecera",
        "descripcion": (
            "Vialidad de proyecto según Drawing1. Donación del 10 % del área neta como "
            "franja sobre el lindero poniente (fondo). Tres lotes de igual área por "
            "macrolote, con cortes paralelos a las cabeceras y frente a la vialidad."
        ),
    },
    2: {
        "nombre": "PROPUESTA 2 - DONACIÓN EN EL EXTREMO NORTE, CORTES PARALELOS A LAS CABECERAS",
        "donacion": "extremo",
        "cortes": "cabecera",
        "descripcion": (
            "Vialidad de proyecto según Drawing1. Donación del 10 % del área neta "
            "concentrada en el extremo norte de cada macrolote. Tres lotes de igual área "
            "con cortes paralelos a las cabeceras."
        ),
    },
    3: {
        "nombre": "PROPUESTA 3 - DONACIÓN AL FONDO, CORTES PERPENDICULARES A LA VIALIDAD",
        "donacion": "fondo",
        "cortes": "avenida",
        "descripcion": (
            "Vialidad de proyecto según Drawing1. Donación del 10 % del área neta al "
            "fondo (lindero poniente). Tres lotes de igual área con linderos "
            "perpendiculares a la vialidad diagonal."
        ),
    },
}
