# Lotificación en 6 lotes - 3 propuestas

Base: `lotificaciones.dwfx`. Los polígonos de los dos macrolotes y la avenida lateral diagonal se tomaron en coordenadas UTM (m), sin modificar. Cada macrolote se divide en **3 lotes de igual área** con frente a la avenida lateral diagonal y deja **10.00 % de donación al fondo**. En total son **6 lotes**.

```bash
pip install -r requirements.txt && python main_6lotes.py
```

## Archivos

- `out/6_lotes/propuesta_1_6_lotes.dxf`: PROPUESTA 1 - DONACIÓN AL FONDO, CORTES PARALELOS A LAS CABECERAS
- `out/6_lotes/propuesta_2_6_lotes.dxf`: PROPUESTA 2 - DONACIÓN EN EL EXTREMO NORTE, CORTES PARALELOS A LAS CABECERAS
- `out/6_lotes/propuesta_3_6_lotes.dxf`: PROPUESTA 3 - DONACIÓN AL FONDO, CORTES PERPENDICULARES A LA AVENIDA
- `out/6_lotes/comparativo_3_propuestas.dxf`: Las 3 propuestas lado a lado (desplazadas 450 m en X)

## Comparativo de propuestas

| Concepto | Propuesta 1 | Propuesta 2 | Propuesta 3 |
|---|---:|---:|---:|
| Donación | Franja al fondo (lindero poniente) | Extremo norte | Franja al fondo (lindero poniente) |
| Cortes | Paralelos a cabeceras | Paralelos a cabeceras | Perpendiculares a la avenida |
| MACROLOTE 1: área total (m2) | 14,113.74 | 14,113.74 | 14,113.74 |
| MACROLOTE 1: donación (m2) | 1,411.37 (10.00 %) | 1,411.38 (10.00 %) | 1,411.37 (10.00 %) |
| MACROLOTE 1: área de cada lote (m2) | 4,234.12 | 4,234.12 | 4,234.12 |
| MACROLOTE 1: frentes a avenida (m) | 107.56 / 59.54 / 32.52 | 96.13 / 58.17 / 45.33 | 82.69 / 49.81 / 67.08 |
| MACROLOTE 2: área total (m2) | 17,978.43 | 17,978.43 | 17,978.43 |
| MACROLOTE 2: donación (m2) | 1,797.84 (10.00 %) | 1,797.85 (10.00 %) | 1,797.84 (10.00 %) |
| MACROLOTE 2: área de cada lote (m2) | 5,393.52 | 5,393.52 | 5,393.53 |
| MACROLOTE 2: frentes a avenida (m) | 108.13 / 64.42 / 51.10 | 97.05 / 63.50 / 78.61 | 87.12 / 59.03 / 77.48 |
| Total vendible (m2) | 28,882.96 | 28,882.95 | 28,882.96 |
| Total donación (m2) | 3,209.21 | 3,209.22 | 3,209.21 |
| Total de lotes | 6 | 6 | 6 |

## PROPUESTA 1 - DONACIÓN AL FONDO, CORTES PARALELOS A LAS CABECERAS

Donación del 10 % como franja continua sobre el lindero poniente (fondo de los lotes). Tres lotes de igual área con cortes paralelos a las cabeceras norte y sur, como en el esquema; cada lote va de la donación a la avenida.

| Lote | Macrolote | Área (m2) | % del macrolote | Frente a avenida (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,234.12 | 30.00 % | 107.56 |
| 2 | MACROLOTE 1 | 4,234.12 | 30.00 % | 59.54 |
| 3 | MACROLOTE 1 | 4,234.13 | 30.00 % | 32.52 |
| 4 | MACROLOTE 2 | 5,393.52 | 30.00 % | 108.13 |
| 5 | MACROLOTE 2 | 5,393.53 | 30.00 % | 64.42 |
| 6 | MACROLOTE 2 | 5,393.53 | 30.00 % | 51.10 |

## PROPUESTA 2 - DONACIÓN EN EL EXTREMO NORTE, CORTES PARALELOS A LAS CABECERAS

Donación del 10 % concentrada en el extremo norte (fondo del macrolote) como una sola área verde con frente a la avenida. Tres lotes de igual área de lindero a lindero, con cortes paralelos a las cabeceras.

| Lote | Macrolote | Área (m2) | % del macrolote | Frente a avenida (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,234.12 | 30.00 % | 96.13 |
| 2 | MACROLOTE 1 | 4,234.13 | 30.00 % | 58.17 |
| 3 | MACROLOTE 1 | 4,234.12 | 30.00 % | 45.33 |
| 4 | MACROLOTE 2 | 5,393.52 | 30.00 % | 97.05 |
| 5 | MACROLOTE 2 | 5,393.53 | 30.00 % | 63.50 |
| 6 | MACROLOTE 2 | 5,393.53 | 30.00 % | 78.61 |

## PROPUESTA 3 - DONACIÓN AL FONDO, CORTES PERPENDICULARES A LA AVENIDA

Donación del 10 % como franja sobre el lindero poniente (fondo). Tres lotes de igual área con linderos perpendiculares a la avenida lateral, para que cada predio quede ortogonal a su frente.

| Lote | Macrolote | Área (m2) | % del macrolote | Frente a avenida (m) |
|---:|---|---:|---:|---:|
| 1 | MACROLOTE 1 | 4,234.12 | 30.00 % | 82.69 |
| 2 | MACROLOTE 1 | 4,234.13 | 30.00 % | 49.81 |
| 3 | MACROLOTE 1 | 4,234.13 | 30.00 % | 67.08 |
| 4 | MACROLOTE 2 | 5,393.53 | 30.00 % | 87.12 |
| 5 | MACROLOTE 2 | 5,393.53 | 30.00 % | 59.03 |
| 6 | MACROLOTE 2 | 5,393.53 | 30.00 % | 77.48 |

## Drenaje

Punto más bajo / salida: X = 357,879.29, Y = 2,285,124.59, en el vértice suroeste del Macrolote 1. Se asume una pendiente de 0.5 % y una cota mínima de 100.00 m (banco de nivel local supuesto).

- MACROLOTE 1: punto más lejano a 229.11 m, cota de inicio 101.15 m.
- MACROLOTE 2: punto más lejano a 474.18 m, cota de inicio 102.37 m.

## Validación

| Verificación | Resultado | Detalle |
|---|:---:|---|
| P1 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P1 - MACROLOTE 1: 3 lotes de igual área | OK | 4,234.12, 4,234.12, 4,234.13 m2 (dif. 0.003 m2) |
| P1 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 107.56 m, L2 59.54 m, L3 32.52 m |
| P1 - MACROLOTE 1: cierre de áreas | OK | -0.000 m2 |
| P1 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P1 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P1 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P1 - MACROLOTE 2: 3 lotes de igual área | OK | 5,393.52, 5,393.53, 5,393.53 m2 (dif. 0.006 m2) |
| P1 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 108.13 m, L5 64.42 m, L6 51.10 m |
| P1 - MACROLOTE 2: cierre de áreas | OK | -0.000 m2 |
| P1 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P1 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P1 - DXF abre con ezdxf.readfile | OK | propuesta_1_6_lotes.dxf |
| P1 - DXF auditoría | OK | 0 errores |
| P1 - DXF $INSUNITS = 6 | OK | metros |
| P1 - DXF capa LOTES | OK | 12 entidades |
| P1 - DXF capa DONACION | OK | 4 entidades |
| P1 - DXF capa VIAL_ASFALTO | OK | 23 entidades |
| P1 - DXF capa VIAL_BANQUETA | OK | 6 entidades |
| P1 - DXF capa DRENAJE | OK | 4 entidades |
| P1 - DXF capa COTAS | OK | 23 entidades |
| P1 - DXF capa TEXTOS | OK | 30 entidades |
| P1 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
| P2 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P2 - MACROLOTE 1: 3 lotes de igual área | OK | 4,234.12, 4,234.13, 4,234.12 m2 (dif. 0.008 m2) |
| P2 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 96.13 m, L2 58.17 m, L3 45.33 m |
| P2 - MACROLOTE 1: cierre de áreas | OK | +0.000 m2 |
| P2 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P2 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P2 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P2 - MACROLOTE 2: 3 lotes de igual área | OK | 5,393.52, 5,393.53, 5,393.53 m2 (dif. 0.005 m2) |
| P2 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 97.05 m, L5 63.50 m, L6 78.61 m |
| P2 - MACROLOTE 2: cierre de áreas | OK | +0.000 m2 |
| P2 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P2 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P2 - DXF abre con ezdxf.readfile | OK | propuesta_2_6_lotes.dxf |
| P2 - DXF auditoría | OK | 0 errores |
| P2 - DXF $INSUNITS = 6 | OK | metros |
| P2 - DXF capa LOTES | OK | 12 entidades |
| P2 - DXF capa DONACION | OK | 4 entidades |
| P2 - DXF capa VIAL_ASFALTO | OK | 23 entidades |
| P2 - DXF capa VIAL_BANQUETA | OK | 6 entidades |
| P2 - DXF capa DRENAJE | OK | 4 entidades |
| P2 - DXF capa COTAS | OK | 24 entidades |
| P2 - DXF capa TEXTOS | OK | 30 entidades |
| P2 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
| P3 - MACROLOTE 1: donación 10 % | OK | 10.000 % |
| P3 - MACROLOTE 1: 3 lotes de igual área | OK | 4,234.12, 4,234.13, 4,234.13 m2 (dif. 0.002 m2) |
| P3 - MACROLOTE 1: todos los lotes con frente a la avenida | OK | L1 82.69 m, L2 49.81 m, L3 67.08 m |
| P3 - MACROLOTE 1: cierre de áreas | OK | -0.000 m2 |
| P3 - MACROLOTE 1: sin traslapes | OK | 0.0000 m2 |
| P3 - MACROLOTE 1: cada lote es un solo polígono | OK |  |
| P3 - MACROLOTE 2: donación 10 % | OK | 10.000 % |
| P3 - MACROLOTE 2: 3 lotes de igual área | OK | 5,393.53, 5,393.53, 5,393.53 m2 (dif. 0.006 m2) |
| P3 - MACROLOTE 2: todos los lotes con frente a la avenida | OK | L4 87.12 m, L5 59.03 m, L6 77.48 m |
| P3 - MACROLOTE 2: cierre de áreas | OK | +0.000 m2 |
| P3 - MACROLOTE 2: sin traslapes | OK | 0.0000 m2 |
| P3 - MACROLOTE 2: cada lote es un solo polígono | OK |  |
| P3 - DXF abre con ezdxf.readfile | OK | propuesta_3_6_lotes.dxf |
| P3 - DXF auditoría | OK | 0 errores |
| P3 - DXF $INSUNITS = 6 | OK | metros |
| P3 - DXF capa LOTES | OK | 12 entidades |
| P3 - DXF capa DONACION | OK | 4 entidades |
| P3 - DXF capa VIAL_ASFALTO | OK | 23 entidades |
| P3 - DXF capa VIAL_BANQUETA | OK | 6 entidades |
| P3 - DXF capa DRENAJE | OK | 4 entidades |
| P3 - DXF capa COTAS | OK | 22 entidades |
| P3 - DXF capa TEXTOS | OK | 30 entidades |
| P3 - DXF capa TABLA_CONTENIDOS | OK | 2 entidades |
