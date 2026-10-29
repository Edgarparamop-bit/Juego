# Parque industrial: 3 opciones de lotificación en DXF

Proyecto en Python que genera tres opciones de lotificación industrial sobre la misma envolvente rectangular y exporta un DXF por opción en `out/`.

## Ejecutar

```bash
pip install -r requirements.txt
python main.py
```

Al terminar, `out/opcion_1.dxf`, `out/opcion_2.dxf` y `out/opcion_3.dxf` quedan listos para abrir en AutoCAD, BricsCAD o QCAD (unidades en metros, `$INSUNITS = 6`, escala 1:1, origen en la esquina surponiente).

## Criterios de diseño

| Criterio | Valor |
|---|---|
| Envolvente | 172.00 × 186.61 m = 32,096.92 m². Es la misma área total de los macrolotes A + B de `lotificaciones.dwfx` (32,096.50 m²). |
| Sección vial | 1.50 banqueta + 9.00 asfalto + 1.50 banqueta = **12.00 m** |
| Frente de lote | 25.00 m sobre el alineamiento exterior de banqueta; el lote nunca invade banqueta ni arroyo. |
| Fondo mínimo de lote | 15.00 m |
| Donación | 10 % del área total, en banda perimetral. El ancho de la banda se calcula para que, después de abrir los gaps de acceso, dé 10.000 %. |
| Remanentes | Tramos de frente menores de 25.00 m: área verde interna. No se crean lotes irregulares. |
| Drenaje | Sin topografía. Pendiente longitudinal mínima de 0.5 % hacia un único punto bajo en el borde. Cota supuesta en la salida: 100.00 m. |

## Archivos

| Archivo | Contenido |
|---|---|
| `config.py` | Parámetros: envolvente, sección, frente, donación y pendiente. |
| `geometry.py` | Trazo vial de cada opción, banda de donación, lotificación y red de drenaje. |
| `dxf_writer.py` | Capas y entidades DXF nativas con ezdxf. |
| `validacion.py` | Traslapes, frentes, donación perimetral, punto bajo único y lotes sin acceso. |
| `main.py` | Orquesta todo, escribe este README y relee cada DXF con `ezdxf.readfile`. |

## Capas DXF

| Capa | Color | Contenido |
|---|---|---|
| VIAL_ASFALTO | 1 | Polilíneas cerradas del arroyo de 9.00 m |
| VIAL_BANQUETA | 3 | Banquetas de 1.50 m |
| LOTES | 7 | Contornos de lotes (frente 25.00 m) |
| DONACION_VERDE | 4 | Banda perimetral de donación |
| EJES_VIALES | 2 | Ejes de vialidad |
| COTAS | 6 | 1.50 / 9.00 / 1.50 / 12.00 m / FRENTE 25.00 m y etiqueta de sección de cada calle |
| DRENAJE | 5 | Punto más bajo, flechas de escurrimiento y cotas de rasante |
| LIMITE | 8 | Límite del polígono |
| TEXTO | 7 | Título, leyenda, cuadro de áreas y notas |

## Memoria por opción

### OPCIÓN 1 — ESPINA CENTRAL RECTA

| Concepto | Valor |
|---|---|
| Área total del polígono | 32,096.92 m² (100.00 %) |
| Donación verde perimetral | 3,209.69 m² (**10.000 %**), banda de 4.761 m |
| Vialidad total (asfalto + banquetas) | 7,656.53 m² (23.85 %) |
| &nbsp;&nbsp;Asfalto 9.00 m | 5,823.40 m² |
| &nbsp;&nbsp;Banquetas 2 × 1.50 m | 1,833.13 m² |
| Área vendible (lotes) | 21,162.60 m² (65.93 %) |
| Área verde interna (remanentes sin frente de 25 m) | 68.09 m² (0.21 %) |
| Número de lotes | 36 (frente 25.00 m; fondos 23.51 m) |
| Longitud total de vialidad (ejes) | 674.04 m |
| Punto más bajo de drenaje | X = 86.00, Y = 0.00 (borde sur) |
| Pendiente longitudinal asumida | 0.5 % hacia el punto bajo |
| Cota inicio (punto alto) / cota mínima | 101.17 m / 100.00 m (supuesta) |
| Cuadre de áreas | 32,096.92 m² |

**Accesos y gaps de donación**

- Acceso sur (eje central) en borde sur (X = 86.00, Y = 0.00): gap de 12.00 m en la banda verde (57.13 m² descontados; la banda se ensanchó para compensar y mantener el 10 %).
- Acceso norte (eje central) en borde norte (X = 86.00, Y = 186.61): gap de 12.00 m en la banda verde (57.13 m² descontados; la banda se ensanchó para compensar y mantener el 10 %).

**Justificación del arreglo**

- Fondo de lote uniforme 23.51 m (bloques sencillos al norte y sur, dobles al centro).
- Las 3 transversales cruzan el eje central y terminan contra la donación perimetral (calles cerradas de 70 m).
- Remanentes de frente < 25.00 m: 4 tramos (91.08 m de alineamiento) en esquinas e intersecciones; quedan como área verde interna y no se crearon lotes irregulares.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banqueta: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Todos los lotes con frente >= 25.00 m a vialidad: 36 lotes OK
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (solo banda de borde, toca el límite): ancho de banda 4.761 m; área fuera de banda 0.0000 m2
- ✅ Punto bajo único: mínimos = 1
- ✅ Punto bajo en borde accesible (eje vial en el límite): (86.00, 0.00)
- ✅ Ningún lote ciego: OK

### OPCIÓN 2 — ANILLO CENTRAL CON CRUCES

| Concepto | Valor |
|---|---|
| Área total del polígono | 32,096.92 m² (100.00 %) |
| Donación verde perimetral | 3,209.69 m² (**10.000 %**), banda de 4.761 m |
| Vialidad total (asfalto + banquetas) | 6,589.59 m² (20.53 %) |
| &nbsp;&nbsp;Asfalto 9.00 m | 4,996.19 m² |
| &nbsp;&nbsp;Banquetas 2 × 1.50 m | 1,593.40 m² |
| Área vendible (lotes) | 18,081.35 m² (56.33 %) |
| Área verde interna (remanentes sin frente de 25 m) | 4,216.29 m² (13.14 %) |
| Número de lotes | 28 (frente 25.00 m; fondos 22.77, 25.00, 30.00 m) |
| Longitud total de vialidad (ejes) | 573.13 m |
| Punto más bajo de drenaje | X = 131.24, Y = 0.00 (borde sur) |
| Pendiente longitudinal asumida | 0.5 % hacia el punto bajo |
| Cota inicio (punto alto) / cota mínima | 101.21 m / 100.00 m (supuesta) |
| Cuadre de áreas | 32,096.92 m² |

**Accesos y gaps de donación**

- Acceso sur (eje central) en borde sur (X = 86.00, Y = 0.00): gap de 12.00 m en la banda verde (57.13 m² descontados; la banda se ensanchó para compensar y mantener el 10 %).
- Salida sureste (drenaje y acceso) en borde sur (X = 131.24, Y = 0.00): gap de 12.00 m en la banda verde (57.13 m² descontados; la banda se ensanchó para compensar y mantener el 10 %).

**Justificación del arreglo**

- Anillo de 90.48 x 115.09 m a ejes; lotes exteriores de 30.00 m de fondo.
- Interior del anillo dividido por un cruce E-O; lotes interiores de 22.77 m de fondo.
- La esquina sureste del anillo baja por un tramo recto al borde sur: ahí está la salida de drenaje.
- Remanentes de frente < 25.00 m: 15 tramos (187.91 m de alineamiento) en esquinas e intersecciones; quedan como área verde interna y no se crearon lotes irregulares.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banqueta: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Todos los lotes con frente >= 25.00 m a vialidad: 28 lotes OK
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (solo banda de borde, toca el límite): ancho de banda 4.761 m; área fuera de banda 0.0000 m2
- ✅ Punto bajo único: mínimos = 1
- ✅ Punto bajo en borde accesible (eje vial en el límite): (131.24, 0.00)
- ✅ Ningún lote ciego: OK

### OPCIÓN 3 — COLECTOR EN T CON RAMALES EN PEINE

| Concepto | Valor |
|---|---|
| Área total del polígono | 32,096.92 m² (100.00 %) |
| Donación verde perimetral | 3,209.69 m² (**10.000 %**), banda de 4.675 m |
| Vialidad total (asfalto + banquetas) | 6,517.23 m² (20.30 %) |
| &nbsp;&nbsp;Asfalto 9.00 m | 4,928.43 m² |
| &nbsp;&nbsp;Banquetas 2 × 1.50 m | 1,588.81 m² |
| Área vendible (lotes) | 21,415.10 m² (66.72 %) |
| Área verde interna (remanentes sin frente de 25 m) | 954.85 m² (2.97 %) |
| Número de lotes | 36 (frente 25.00 m; fondos 20.00, 21.66, 40.00 m) |
| Longitud total de vialidad (ejes) | 561.10 m |
| Punto más bajo de drenaje | X = 86.00, Y = 0.00 (borde sur) |
| Pendiente longitudinal asumida | 0.5 % hacia el punto bajo |
| Cota inicio (punto alto) / cota mínima | 101.61 m / 100.00 m (supuesta) |
| Cuadre de áreas | 32,096.88 m² |

**Accesos y gaps de donación**

- Acceso sur (colector) en borde sur (X = 86.00, Y = 0.00): gap de 12.00 m en la banda verde (56.10 m² descontados; la banda se ensanchó para compensar y mantener el 10 %).

**Justificación del arreglo**

- Ramales a 26.00 m de la donación: lotes de 20.00 m hacia la donación y de 21.66 m hacia el colector.
- Barra norte con lotes de 40.00 m de fondo hacia el norte.
- Los ramales terminan contra la donación sur (calles cerradas).
- Remanentes de frente < 25.00 m: 3 tramos (59.29 m de alineamiento) en esquinas e intersecciones; quedan como área verde interna y no se crearon lotes irregulares.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banqueta: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Todos los lotes con frente >= 25.00 m a vialidad: 36 lotes OK
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (solo banda de borde, toca el límite): ancho de banda 4.675 m; área fuera de banda 0.0000 m2
- ✅ Punto bajo único: mínimos = 1
- ✅ Punto bajo en borde accesible (eje vial en el límite): (86.00, 0.00)
- ✅ Ningún lote ciego: OK

## Comparativo

| Opción | Lotes | Área vendible | Vialidad | Donación | Verde interno | Longitud vial | Punto bajo |
|---|---|---|---|---|---|---|---|
| 1 · Espina central recta | 36 | 21,162.60 m² (65.93 %) | 7,656.53 m² (23.85 %) | 10.000 % | 68.09 m² | 674.04 m | (86.00, 0.00) |
| 2 · Anillo central con cruces | 28 | 18,081.35 m² (56.33 %) | 6,589.59 m² (20.53 %) | 10.000 % | 4,216.29 m² | 573.13 m | (131.24, 0.00) |
| 3 · Colector en T con ramales en peine | 36 | 21,415.10 m² (66.72 %) | 6,517.23 m² (20.30 %) | 10.000 % | 954.85 m² | 561.10 m | (86.00, 0.00) |

## Limitaciones y supuestos

- La envolvente es un rectángulo equivalente en área al terreno real, como pidió el encargo, para comparar las opciones en igualdad. Para el proyecto ejecutivo hay que llevar el trazo elegido a la poligonal real.
- No hay topografía. Las cotas de rasante son teóricas: salida en 100.00 m y pendiente de 0.5 % sobre la ruta más corta de cada punto hacia la salida. Hay que ajustarlas con un levantamiento.
- Las calles cerradas (transversales de la opción 1 y ramales de la opción 3) no llevan retorno. Si el reglamento lo exige para tractocamión, hay que agregar un retorno de radio ≥ 15 m en su extremo, a costa de los lotes vecinos.
- El área verde interna proviene de remanentes sin frente de 25 m. Es independiente de la donación municipal perimetral y no se suma a ella.
