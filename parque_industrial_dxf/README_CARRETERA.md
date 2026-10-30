# Lotificación en 6 lotes con la vialidad de proyecto (Drawing1.dxf)

Base: `referencia/Drawing1.dxf`, que traza la **vialidad de proyecto diagonal** dentro de los dos macrolotes y marca las superficies afectadas. `extraer_drawing1.py` toma de ese plano, sin moverlos, los paramentos de la vialidad (capa `ASFALTO`), el predio del Macrolote 2 (capa `Polígono`) y los linderos poniente y sur del Macrolote 1, y escribe `traza_carretera.py`. El plano de referencia (cuadrícula UTM, norte, rótulos catastrales, parcelas vecinas 60 y 49, anillo vial y leyendas de superficie afectada) se importa tal cual como contexto, en sus mismas coordenadas.

En cada macrolote **neto** (predio menos vialidad) se deja una **donación del 10 %** y el resto se divide en **3 lotes de igual área**, todos con frente a la vialidad de proyecto. En total son 6 lotes.

```bash
pip install -r requirements.txt && python main_carretera.py
```

## Áreas de partida

| Concepto | Macrolote 1 | Macrolote 2 | Total |
|---|---:|---:|---:|
| Área bruta del predio (m2) | 18,181.82 | 20,713.11 | 38,894.92 |
| Vialidad de proyecto dentro del predio (m2) | 2,433.55 | 2,745.01 | 5,178.56 |
| Superficie afectada, leyenda del plano (m2) | 1,103.17 | 1,145.61 | 2,248.78 |
| Área neta del macrolote (m2) | 15,748.27 | 17,968.10 | 33,716.37 |
| Donación 10 % del área neta (m2) | 1,574.83 | 1,796.81 | 3,371.63 |
| Área vendible (m2) | 14,173.45 | 16,171.29 | 30,344.74 |

La sección real de la vialidad se acota en el plano en dos puntos por macrolote. En el Macrolote 2 mide 1.50 + 8.98 + 1.50 = 12.0 m. En el Macrolote 1 el arroyo se abre hacia el anillo vial, tal como está dibujado.

## Archivos

- `out/carretera/propuesta_1_carretera.dxf`: PROPUESTA 1 - DONACIÓN AL FONDO, CORTES PARALELOS A LAS CABECERAS
- `out/carretera/propuesta_2_carretera.dxf`: PROPUESTA 2 - DONACIÓN EN EL EXTREMO NORTE, CORTES PARALELOS A LAS CABECERAS
- `out/carretera/propuesta_3_carretera.dxf`: PROPUESTA 3 - DONACIÓN AL FONDO, CORTES PERPENDICULARES A LA VIALIDAD
- `out/carretera/comparativo_3_propuestas_carretera.dxf`: Las 3 propuestas lado a lado (desplazadas 650 m en X)

## Comparativo de propuestas

| Concepto | Propuesta 1 | Propuesta 2 | Propuesta 3 |
|---|---:|---:|---:|
| MACROLOTE 1: área de cada lote (m2) | 4,724.48 | 4,724.48 | 4,724.48 |
| MACROLOTE 1: frentes a la vialidad (m) | 106.48 / 61.71 / 36.36 | 95.20 / 59.84 / 47.34 | 79.49 / 51.61 / 73.40 |
| MACROLOTE 2: área de cada lote (m2) | 5,390.43 | 5,390.43 | 5,390.43 |
| MACROLOTE 2: frentes a la vialidad (m) | 110.89 / 64.28 / 51.10 | 99.81 / 63.10 / 78.86 | 89.86 / 59.01 / 77.37 |

## PROPUESTA 1 - DONACIÓN AL FONDO, CORTES PARALELOS A LAS CABECERAS

Vialidad de proyecto según Drawing1. Donación del 10 % del área neta como franja sobre el lindero poniente (fondo). Tres lotes de igual área por macrolote, con cortes paralelos a las cabeceras y frente a la vialidad.

| Lote | Macrolote | Área (m2) | % del área neta | Frente a vialidad (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,724.48 | 30.00 % | 106.48 |
| 2 | MACROLOTE 1 | 4,724.48 | 30.00 % | 61.71 |
| 3 | MACROLOTE 1 | 4,724.48 | 30.00 % | 36.36 |
| 4 | MACROLOTE 2 | 5,390.43 | 30.00 % | 110.89 |
| 5 | MACROLOTE 2 | 5,390.43 | 30.00 % | 64.28 |
| 6 | MACROLOTE 2 | 5,390.43 | 30.00 % | 51.10 |

## PROPUESTA 2 - DONACIÓN EN EL EXTREMO NORTE, CORTES PARALELOS A LAS CABECERAS

Vialidad de proyecto según Drawing1. Donación del 10 % del área neta concentrada en el extremo norte de cada macrolote. Tres lotes de igual área con cortes paralelos a las cabeceras.

| Lote | Macrolote | Área (m2) | % del área neta | Frente a vialidad (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,724.48 | 30.00 % | 95.20 |
| 2 | MACROLOTE 1 | 4,724.49 | 30.00 % | 59.84 |
| 3 | MACROLOTE 1 | 4,724.48 | 30.00 % | 47.34 |
| 4 | MACROLOTE 2 | 5,390.43 | 30.00 % | 99.81 |
| 5 | MACROLOTE 2 | 5,390.43 | 30.00 % | 63.10 |
| 6 | MACROLOTE 2 | 5,390.43 | 30.00 % | 78.86 |

## PROPUESTA 3 - DONACIÓN AL FONDO, CORTES PERPENDICULARES A LA VIALIDAD

Vialidad de proyecto según Drawing1. Donación del 10 % del área neta al fondo (lindero poniente). Tres lotes de igual área con linderos perpendiculares a la vialidad diagonal.

| Lote | Macrolote | Área (m2) | % del área neta | Frente a vialidad (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,724.48 | 30.00 % | 79.49 |
| 2 | MACROLOTE 1 | 4,724.48 | 30.00 % | 51.61 |
| 3 | MACROLOTE 1 | 4,724.49 | 30.00 % | 73.40 |
| 4 | MACROLOTE 2 | 5,390.43 | 30.00 % | 89.86 |
| 5 | MACROLOTE 2 | 5,390.43 | 30.00 % | 59.01 |
| 6 | MACROLOTE 2 | 5,390.43 | 30.00 % | 77.37 |

## Drenaje

Punto más bajo / salida: X = 357,879.36, Y = 2,285,124.60 (vértice suroeste del Macrolote 1). Pendiente asumida 0.5 %, cota mínima 100.00 m (banco de nivel local supuesto).

- MACROLOTE 1: punto más lejano a 236.53 m, cota de inicio 101.18 m.
- MACROLOTE 2: punto más lejano a 474.15 m, cota de inicio 102.37 m.

## Supuestos a confirmar

- **Lindero del Macrolote 1:** es la línea de `ASFALTO` que arranca sobre el lindero sur. La línea paralela que corre 1.50 m hacia dentro del predio se dibuja como referencia de guarnición y no se descuenta. Si es banqueta dentro del predio, el área neta baja unos 530 m2.
- **Base de la donación:** el 10 % se calcula sobre el área neta (predio menos vialidad de proyecto).
- **Superficie afectada:** la cifra de la leyenda del plano se reporta tal cual. La vialidad medida dentro de cada predio aparece en su propio renglón.

## Validación

| Verificación | Resultado | Detalle |
|---|:---:|---|
| P1 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P1 - MACROLOTE 1: 3 lotes de igual área | OK | 4,724.48, 4,724.48, 4,724.48 m2 (dif. 0.005 m2) |
| P1 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 106.48 m, L2 61.71 m, L3 36.36 m |
| P1 - MACROLOTE 1: cierre de áreas | OK | -0.000 m2 |
| P1 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P1 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P1 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P1 - MACROLOTE 2: 3 lotes de igual área | OK | 5,390.43, 5,390.43, 5,390.43 m2 (dif. 0.005 m2) |
| P1 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 110.89 m, L5 64.28 m, L6 51.10 m |
| P1 - MACROLOTE 2: cierre de áreas | OK | -0.000 m2 |
| P1 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P1 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P1 - DXF abre con ezdxf.readfile | OK | propuesta_1_carretera.dxf |
| P1 - DXF auditoría | OK | 0 errores |
| P1 - DXF $INSUNITS = 6 | OK | metros |
| P1 - DXF capa LOTES | OK | 12 entidades |
| P1 - DXF capa DONACION | OK | 4 entidades |
| P1 - DXF capa VIAL_ASFALTO | OK | 17 entidades |
| P1 - DXF capa VIAL_BANQUETA | OK | 2 entidades |
| P1 - DXF capa DRENAJE | OK | 4 entidades |
| P1 - DXF capa COTAS | OK | 35 entidades |
| P1 - DXF capa TEXTOS | OK | 36 entidades |
| P1 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
| P2 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P2 - MACROLOTE 1: 3 lotes de igual área | OK | 4,724.48, 4,724.49, 4,724.48 m2 (dif. 0.009 m2) |
| P2 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 95.20 m, L2 59.84 m, L3 47.34 m |
| P2 - MACROLOTE 1: cierre de áreas | OK | -0.000 m2 |
| P2 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P2 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P2 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P2 - MACROLOTE 2: 3 lotes de igual área | OK | 5,390.43, 5,390.43, 5,390.43 m2 (dif. 0.004 m2) |
| P2 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 99.81 m, L5 63.10 m, L6 78.86 m |
| P2 - MACROLOTE 2: cierre de áreas | OK | +0.000 m2 |
| P2 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P2 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P2 - DXF abre con ezdxf.readfile | OK | propuesta_2_carretera.dxf |
| P2 - DXF auditoría | OK | 0 errores |
| P2 - DXF $INSUNITS = 6 | OK | metros |
| P2 - DXF capa LOTES | OK | 12 entidades |
| P2 - DXF capa DONACION | OK | 4 entidades |
| P2 - DXF capa VIAL_ASFALTO | OK | 17 entidades |
| P2 - DXF capa VIAL_BANQUETA | OK | 2 entidades |
| P2 - DXF capa DRENAJE | OK | 4 entidades |
| P2 - DXF capa COTAS | OK | 35 entidades |
| P2 - DXF capa TEXTOS | OK | 36 entidades |
| P2 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
| P3 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P3 - MACROLOTE 1: 3 lotes de igual área | OK | 4,724.48, 4,724.48, 4,724.49 m2 (dif. 0.005 m2) |
| P3 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 79.49 m, L2 51.61 m, L3 73.40 m |
| P3 - MACROLOTE 1: cierre de áreas | OK | -0.000 m2 |
| P3 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P3 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P3 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P3 - MACROLOTE 2: 3 lotes de igual área | OK | 5,390.43, 5,390.43, 5,390.43 m2 (dif. 0.005 m2) |
| P3 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 89.86 m, L5 59.01 m, L6 77.37 m |
| P3 - MACROLOTE 2: cierre de áreas | OK | -0.000 m2 |
| P3 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P3 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P3 - DXF abre con ezdxf.readfile | OK | propuesta_3_carretera.dxf |
| P3 - DXF auditoría | OK | 0 errores |
| P3 - DXF $INSUNITS = 6 | OK | metros |
| P3 - DXF capa LOTES | OK | 12 entidades |
| P3 - DXF capa DONACION | OK | 4 entidades |
| P3 - DXF capa VIAL_ASFALTO | OK | 17 entidades |
| P3 - DXF capa VIAL_BANQUETA | OK | 2 entidades |
| P3 - DXF capa DRENAJE | OK | 4 entidades |
| P3 - DXF capa COTAS | OK | 34 entidades |
| P3 - DXF capa TEXTOS | OK | 36 entidades |
| P3 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
