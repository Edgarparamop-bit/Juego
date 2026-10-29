# Parque industrial - Lotificación DXF

Proyecto en Python (`ezdxf` + `shapely`) que reproduce la traza del plano de referencia `PROPUESTA_1.dwfx`: polígono irregular en "boomerang/V" dividido en dos macrolotes por la vialidad central, cada uno con una vialidad interna que remata en un retorno en "T" y lotes perpendiculares a la vialidad. Todas las coordenadas están en UTM, en metros, y se extrajeron directamente de las capas del DWFX (`POLIGONO`, `LOTES`, `VIAL-EJE`, `VIAL-DERECHO-VIA`, `DONACION-AREA-VERDE`). Ningún vértice, ángulo ni divisoria se desplazó.

## Ejecución

```bash
pip install -r requirements.txt && python main.py
```

Salidas:

- `out/plano_parque_industrial.dxf`: plano principal, con la traza exacta de la referencia.
- `out/plano_parque_industrial_frente25.dxf`: variante opcional con los lotes regenerados a frente fijo de 25.00 m (ver la nota de diseño).

## Tabla de metrados por macrolote

| Concepto | Macrolote 1 | Macrolote 2 | Total proyecto |
|---|---:|---:|---:|
| Área total del polígono (m2) | 14,125.23 | 17,972.54 | 32,097.77 |
| Área de donación verde (m2) | 1,516.67 | 1,791.48 | 3,308.15 |
| Donación respecto al macrolote (%) | 10.74 % | 9.97 % | 10.31 % |
| Área de vialidad y banquetas (m2) | 2,610.15 | 3,059.79 | 5,669.94 |
|   - arroyo asfáltico (m2) | 1,985.66 | 2,325.35 | 4,311.01 |
|   - banquetas (m2) | 624.49 | 734.45 | 1,358.93 |
| Área vendible / lotes (m2) | 9,998.32 | 13,121.22 | 23,119.55 |
| Número total de lotes | 12 | 14 | 26 |
| Longitud total de vialidad, eje dentro del predio (ml) | 183.89 | 218.76 | 402.65 |
| Punto más bajo de drenaje (X, Y) | 357,879.21, 2,285,124.47 | 357,879.21, 2,285,124.47 | común a ambos |
| Pendiente asumida | 0.5 % | 0.5 % |  |
| Recorrido hidráulico a la salida (m) | 195.98 | 461.71 |  |
| Cota de inicio (retorno en T) (m) | 100.98 | 102.31 |  |
| Cota mínima (salida de drenaje) (m) | 100.00 | 100.00 |  |

La cota mínima de 100.00 m es un banco de nivel local supuesto; la cota de inicio es `cota mínima + 0.5 % × recorrido`. El recorrido va del retorno en T al acceso por el eje y, desde el acceso, por la vialidad central hasta la salida en la esquina inferior izquierda (vértice suroeste del Macrolote 1).

## Justificación de accesos y retornos en "T"

**MACROLOTE 1.** Acceso único por el lindero sur, sobre la vialidad central que separa ambos macrolotes. El eje sube con una curva en S hacia el norte-noreste (tramo recto de ~68 m) y gira al oriente hasta rematar en el retorno en T. El cabezal de la T (20.0 x 29.8 m a límite de banqueta) permite la vuelta en U de vehículos de carga y remata a 13.7 m de la donación, sin requerir una glorieta; el arroyo no se acerca al lindero sureste: la franja de donación perimetral y la cuña verde del vértice oriente quedan íntegras. Los lotes 1-7 dan frente al lado poniente/norte de la vialidad y los lotes 8-12 al lado oriente; los lotes 6-9 también dan frente al propio cabezal de la T; ninguno depende de la donación para su acceso.

**MACROLOTE 2.** Acceso único por el lindero sur con radios de giro de 15.0 m (poniente) y 13.5 m (oriente) sobre la vialidad central. El eje corre recto ~155 m hacia el norte-noreste, paralelo al lindero poniente, y gira al oriente hasta el retorno en T (20.0 x 29.8 m). La T remata a 12.4 m de la franja de donación, de modo que el retorno resuelve la vuelta en U del extremo cerrado sin invadir la donación perimetral sureste y además genera frente para los lotes 20, 21 y 22, que rodean el cabezal. Los lotes 13-19 quedan al poniente/norte y los lotes 20-26 al oriente, entre la vialidad y la franja verde.

En ambos casos el retorno en T se resolvió con la sección completa: el arroyo de 9.00 m entra al cabezal y la banqueta de 1.50 m lo rodea. La validación comprueba que la intersección entre la vialidad y la donación es de 0.00 m2.

## Cuadro de lotes (plano principal)

| Lote | Macrolote | Lado | Área (m2) | Frente (m) | Ancho x fondo (m) |
|---:|---|---|---:|---:|---|
| 1 | MACROLOTE 1 | IZQ | 487.16 | 43.51 | 46.66 x 18.42 |
| 2 | MACROLOTE 1 | IZQ | 583.34 | 30.02 | 30.36 x 19.97 |
| 3 | MACROLOTE 1 | IZQ | 586.73 | 30.10 | 30.07 x 19.53 |
| 4 | MACROLOTE 1 | IZQ | 577.79 | 23.66 | 34.93 x 20.88 |
| 5 | MACROLOTE 1 | IZQ | 1,257.43 | 22.83 | 43.86 x 45.75 |
| 6 | MACROLOTE 1 | IZQ | 970.42 | 44.69 | 41.90 x 37.05 |
| 7 | MACROLOTE 1 | IZQ | 1,235.15 | 15.07 | 36.14 x 50.10 |
| 8 | MACROLOTE 1 | DER | 1,036.34 | 34.86 | 64.45 x 28.92 |
| 9 | MACROLOTE 1 | DER | 735.27 | 55.33 | 36.97 x 35.86 |
| 10 | MACROLOTE 1 | DER | 1,178.89 | 30.09 | 30.05 x 47.72 |
| 11 | MACROLOTE 1 | DER | 675.73 | 30.07 | 30.55 x 30.85 |
| 12 | MACROLOTE 1 | DER | 674.06 | 41.50 | 47.66 x 22.42 |
| 13 | MACROLOTE 2 | IZQ | 806.93 | 50.15 | 48.22 x 27.48 |
| 14 | MACROLOTE 2 | IZQ | 588.24 | 30.06 | 30.06 x 19.60 |
| 15 | MACROLOTE 2 | IZQ | 588.98 | 30.04 | 30.01 x 19.65 |
| 16 | MACROLOTE 2 | IZQ | 589.36 | 29.99 | 29.97 x 19.70 |
| 17 | MACROLOTE 2 | IZQ | 611.76 | 31.41 | 33.49 x 24.01 |
| 18 | MACROLOTE 2 | IZQ | 1,425.20 | 16.09 | 51.09 x 41.87 |
| 19 | MACROLOTE 2 | IZQ | 1,124.98 | 37.08 | 38.41 x 41.24 |
| 20 | MACROLOTE 2 | IZQ | 1,334.38 | 35.96 | 45.67 x 41.43 |
| 21 | MACROLOTE 2 | DER | 962.45 | 49.80 | 58.72 x 30.64 |
| 22 | MACROLOTE 2 | DER | 876.17 | 67.33 | 43.28 x 34.50 |
| 23 | MACROLOTE 2 | DER | 1,705.67 | 30.00 | 30.06 x 63.74 |
| 24 | MACROLOTE 2 | DER | 1,297.66 | 30.09 | 30.07 x 50.04 |
| 25 | MACROLOTE 2 | DER | 854.70 | 30.03 | 29.99 x 36.35 |
| 26 | MACROLOTE 2 | DER | 354.77 | 31.68 | 31.34 x 21.71 |

## Notas de diseño (regla de oro vs. parámetros)

- **Sección vial.** En la referencia el derecho de vía mide 11.0 m (arroyo de 8.0 m). El plano aplica la sección pedida de **12.00 m = 1.50 + 9.00 + 1.50** sobre el *mismo eje* del DWFX, sin moverlo. Así, el frente de los lotes recorre 0.50 m y las divisorias conservan su posición y su ángulo. El cabezal de la T se toma tal cual de la capa `VIAL-DERECHO-VIA` y su arroyo resulta de restar la banqueta de 1.50 m.
- **Frente de lote.** En la traza de referencia los frentes típicos miden **30 m**, no 25 m. Por la regla de oro, el plano principal respeta las divisorias originales (26 lotes). Para cumplir el parámetro de 25.00 m sin tocar polígono, eje, retornos ni donación se genera además `out/plano_parque_industrial_frente25.dxf`, con lotes perpendiculares a la banqueta cada 25.00 m (34 lotes; vendible 23,071.91 m2). El modo se elige con `MODO_LOTIFICACION` en `config.py`.
- **Donación.** Es la franja perimetral sureste más los remates verdes del dibujo, menos lo que ocupa la sección de 12 m.

## Validación

| Verificación | Resultado | Detalle |
|---|:---:|---|
| MACROLOTE 1: cierre de áreas | OK | total - (donación + vialidad + vendible) = +0.090 m2 |
| MACROLOTE 1: lotes sin traslape | OK | traslape acumulado = 0.0000 m2 |
| MACROLOTE 1: lotes no invaden vialidad ni donación | OK | invasión = 0.0000 m2 |
| MACROLOTE 1: vialidad y retorno T no invaden donación | OK | invasión = 0.0000 m2 |
| MACROLOTE 1: sección vial 1.50 | 9.00 | 1.50 | OK | arroyo 9.00 m / derecho de vía 12.00 m; arroyo 9.00 m / derecho de vía 12.00 m |
| MACROLOTE 1: todos los lotes con frente a vialidad | OK | sin frente: ninguno |
| MACROLOTE 2: cierre de áreas | OK | total - (donación + vialidad + vendible) = +0.039 m2 |
| MACROLOTE 2: lotes sin traslape | OK | traslape acumulado = 0.0000 m2 |
| MACROLOTE 2: lotes no invaden vialidad ni donación | OK | invasión = 0.0000 m2 |
| MACROLOTE 2: vialidad y retorno T no invaden donación | OK | invasión = 0.0000 m2 |
| MACROLOTE 2: sección vial 1.50 | 9.00 | 1.50 | OK | arroyo 9.00 m / derecho de vía 12.00 m; arroyo 9.00 m / derecho de vía 12.00 m |
| MACROLOTE 2: todos los lotes con frente a vialidad | OK | sin frente: ninguno |
| Proyecto: donación ~10 % | OK | 10.31 % |
| DXF: ezdxf.readfile | OK | /home/user/Juego/parque_industrial_dxf/out/plano_parque_industrial.dxf |
| DXF: auditoría sin errores | OK | 0 errores, 0 correcciones |
| DXF: $INSUNITS = 6 (metros) | OK | $INSUNITS = 6 |
| DXF: capa LOTES (color 2) | OK | 52 entidades |
| DXF: capa DONACION (color 3) | OK | 8 entidades |
| DXF: capa VIAL_ASFALTO (color 8) | OK | 10 entidades |
| DXF: capa VIAL_BANQUETA (color 9) | OK | 4 entidades |
| DXF: capa DRENAJE (color 1) | OK | 6 entidades |
| DXF: capa COTAS (color 6) | OK | 117 entidades |
| DXF: capa TEXTOS (color 7) | OK | 41 entidades |
| DXF: capa TABLA_CONTENIDOS (color 7) | OK | 2 entidades |

## Capas del DXF

| Capa | Color | Contenido |
|---|---:|---|
| `LOTES` | 2 | Polilíneas cerradas y relleno amarillo de cada lote |
| `DONACION` | 3 | Franja perimetral de donación (verde) |
| `VIAL_ASFALTO` | 8 | Arroyo de 9.00 m, retornos en T y eje (CENTER) |
| `VIAL_BANQUETA` | 9 | Límite de derecho de vía y banquetas de 1.50 m |
| `DRENAJE` | 1 | Símbolo y texto del punto más bajo / salida de drenaje |
| `COTAS` | 6 | Cotas alineadas de lados y frentes de cada predio y de la sección vial |
| `TEXTOS` | 7 | Número, área, frente y medidas de cada lote; rótulos de la sección |
| `TABLA_CONTENIDOS` | 7 | Bloques `TABLA_CONTENIDOS` (metrados) y `TABLA_CONTENIDOS_LOTES` |

## Estructura

```
parque_industrial_dxf/
  README.md          memoria y validación (generado por main.py)
  requirements.txt
  main.py            orquestación
  config.py          coordenadas de la traza y parámetros
  geometry.py        vialidad, donación y lotificación (shapely)
  dxf_writer.py      capas, rellenos, cotas, textos y tabla (ezdxf)
  validacion.py      verificaciones, drenaje y esta memoria
  out/plano_parque_industrial.dxf
```
