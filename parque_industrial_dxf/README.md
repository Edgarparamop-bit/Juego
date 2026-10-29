# Parque industrial: 3 opciones de lotificación sobre polígono irregular

Proyecto en Python (shapely + ezdxf) que lotifica los dos macrolotes reales de `lotificaciones.dwfx`. Juntos forman un boomerang con cortes diagonales. El programa genera tres opciones y exporta un DXF por opción en `out/`.

## Ejecutar

```bash
pip install -r requirements.txt
python main.py
```

## Polígono base

- Coordenadas en `config.py`. El origen (0,0) está en la esquina surponiente de la envolvente, con escala 1:1 y unidades en metros (`$INSUNITS = 6`).
- Macrolote A: 14,131.25 m². Macrolote B: 17,965.15 m². Total: **32,096.41 m²**.
- Para superponer sobre `lotificaciones.dwg`, mueve el dibujo de (0,0) a (357879.275, 2285119.682).

## Criterios

| Criterio | Valor |
|---|---|
| Colector principal | Paralelo al borde más bajo: la diagonal frente a Fraccionamiento La Espiga, que la memoria toma como la parte baja. Recorre B y A sin interrupción y cruza la calle municipal intermedia. Todo escurre hacia una sola salida en el extremo sur de A, sobre la avenida principal. |
| Calles internas | Nacen del colector y terminan en **retornos rectangulares en T o en L**. No hay glorietas ni anillos. |
| Retorno | Brazos de 17.00 m de arroyo libre (≥ 15 m), con 9.00 m de ancho y banqueta de 1.50 m alrededor. El tractocamión entra, retrocede a un brazo y sale de frente. |
| Sección vial | 1.50 banqueta + 9.00 asfalto + 1.50 banqueta = **12.00 m** |
| Lotes | Frente mínimo de 25.00 m sobre el alineamiento exterior de banqueta. Los cortes son perpendiculares a la calle y en los quiebres del polígono quedan lotes trapezoidales. Área mínima de 400 m². |
| Donación | 10 % del total, en banda perimetral sobre los linderos que no ocupa el colector, más los remanentes de borde. El ancho de la banda se calcula para llegar al 10 %. |
| Drenaje | Sin topografía. Pendiente longitudinal de 0.5 % hacia la salida, con cota supuesta de 100.00 m. Las cotas de los nodos salen de la ruta más corta sobre los ejes. |

## Cómo resuelven la topografía los retornos

Las calles internas son ramales sin salida. Su único punto de conexión es el colector, así que cada calle tiene un solo sentido de escurrimiento: del retorno (punto alto del ramal) hacia el colector. El agua de los lotes entra a la calle, corre hacia la boca del ramal y de ahí por el colector, que va paralelo al borde bajo, hasta la salida única. Con circuitos o glorietas aparecerían tramos con pendientes encontradas y puntos bajos intermedios. Los retornos rectangulares también ocupan menos área que una glorieta del mismo radio de maniobra y se acomodan contra los linderos inclinados.

## Memoria por opción

### OPCIÓN 1 — COLECTOR INFERIOR CON PEINES Y RETORNOS

| Concepto | Valor |
|---|---|
| Área total del polígono (A + B) | 32,096.41 m² |
| Donación verde perimetral | 3,209.64 m² (**10.000 %**); banda base de 5.12 m más remanentes de borde |
| Vialidad total | 8,619.88 m² (26.86 %) |
| &nbsp;&nbsp;Asfalto 9.00 m (calles + retornos) | 6,489.17 m² |
| &nbsp;&nbsp;Banquetas 1.50 m | 2,130.71 m² |
| Área vendible (lotes) | 20,266.89 m² (63.14 %) |
| Número de lotes | 15 (frentes de 25.01 a 158.06 m; áreas de 426 a 3,507 m²) |
| Longitud total de vialidad (ejes, incluye brazos de retorno) | 775.63 m |
| Punto más bajo / salida de drenaje | X = 19.34, Y = 0.60 (UTM 357898.62, 2285120.28) |
| Pendiente longitudinal asumida | 0.5 % hacia la salida |
| Cota de inicio (punto alto) / cota mínima | 102.34 m / 100.00 m |
| Cuadre (donación + vialidad + lotes) | 32,096.41 m² |

**Accesos y gaps de donación**

- Gap 1 en (347.32, 318.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (58.92 m²).
- Gap 2 en (203.25, 153.92): la banda verde se interrumpe 12.00 m para dejar pasar el colector (69.59 m²).
- Gap 3 en (182.05, 137.85): la banda verde se interrumpe 12.00 m para dejar pasar el colector (64.80 m²).
- Gap 4 en (23.68, 3.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (70.08 m²).
- El colector cruza la calle municipal entre A y B. Ahí no se dibuja vialidad propia, solo el eje y el cruce pluvial.

**Retornos**

- PEINE A1: retorno rectangular en L (un brazo), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.
- PEINE A2: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.
- PEINE B1: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.
- PEINE B2: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.

**Justificación**

- Calles en peine que salen del colector y corren perpendiculares a la colindancia poniente
- (lotes rectangulares espalda con espalda entre peines); cada una termina en retorno rectangular en T.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banquetas: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Frente >= 25.00 m sobre alineamiento exterior de banqueta: 15 lotes; mínimo 25.01 m
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (cada parte toca el lindero): 4 partes; banda base 5.118 m
- ✅ Punto bajo único en la red: mínimos locales = 1
- ✅ Punto bajo en el borde accesible del colector: (19.34, 0.60)
- ✅ Retornos con brazo >= 15 m (17.00 m): PEINE A1: L, PEINE A2: T, PEINE B1: T, PEINE B2: T
- ✅ Ningún lote ciego: OK

### OPCIÓN 2 — COLECTOR DIAGONAL CON RAMALES

| Concepto | Valor |
|---|---|
| Área total del polígono (A + B) | 32,096.41 m² |
| Donación verde perimetral | 3,209.64 m² (**10.000 %**); banda base de 5.12 m más remanentes de borde |
| Vialidad total | 9,723.04 m² (30.29 %) |
| &nbsp;&nbsp;Asfalto 9.00 m (calles + retornos) | 7,309.31 m² |
| &nbsp;&nbsp;Banquetas 1.50 m | 2,413.73 m² |
| Área vendible (lotes) | 19,163.73 m² (59.71 %) |
| Número de lotes | 22 (frentes de 25.01 a 108.08 m; áreas de 457 a 1,539 m²) |
| Longitud total de vialidad (ejes, incluye brazos de retorno) | 850.84 m |
| Punto más bajo / salida de drenaje | X = 19.34, Y = 0.60 (UTM 357898.62, 2285120.28) |
| Pendiente longitudinal asumida | 0.5 % hacia la salida |
| Cota de inicio (punto alto) / cota mínima | 102.39 m / 100.00 m |
| Cuadre (donación + vialidad + lotes) | 32,096.41 m² |

**Accesos y gaps de donación**

- Gap 1 en (347.32, 318.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (58.92 m²).
- Gap 2 en (203.25, 153.92): la banda verde se interrumpe 12.00 m para dejar pasar el colector (69.59 m²).
- Gap 3 en (182.05, 137.85): la banda verde se interrumpe 12.00 m para dejar pasar el colector (64.80 m²).
- Gap 4 en (23.68, 3.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (70.08 m²).
- El colector cruza la calle municipal entre A y B. Ahí no se dibuja vialidad propia, solo el eje y el cruce pluvial.

**Retornos**

- RAMAL A: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.
- RAMAL B: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.

**Justificación**

- Ramal en J por macrolote (como el plano de referencia): sale del colector en la parte baja,
- sube paralelo a la colindancia poniente y gira al oriente paralelo al lindero norte;
- termina en retorno rectangular cerca del colector, sin conectarse a él.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banquetas: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Frente >= 25.00 m sobre alineamiento exterior de banqueta: 22 lotes; mínimo 25.01 m
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (cada parte toca el lindero): 4 partes; banda base 5.118 m
- ✅ Punto bajo único en la red: mínimos locales = 1
- ✅ Punto bajo en el borde accesible del colector: (19.34, 0.60)
- ✅ Retornos con brazo >= 15 m (17.00 m): RAMAL A: T, RAMAL B: T
- ✅ Ningún lote ciego: OK

### OPCIÓN 3 — RETORNOS PROFUNDOS OPTIMIZADOS

| Concepto | Valor |
|---|---|
| Área total del polígono (A + B) | 32,096.41 m² |
| Donación verde perimetral | 3,209.64 m² (**10.000 %**); banda base de 5.12 m más remanentes de borde |
| Vialidad total | 8,786.22 m² (27.37 %) |
| &nbsp;&nbsp;Asfalto 9.00 m (calles + retornos) | 6,606.73 m² |
| &nbsp;&nbsp;Banquetas 1.50 m | 2,179.49 m² |
| Área vendible (lotes) | 20,100.55 m² (62.63 %) |
| Número de lotes | 21 (frentes de 25.01 a 82.77 m; áreas de 501 a 2,191 m²) |
| Longitud total de vialidad (ejes, incluye brazos de retorno) | 772.77 m |
| Punto más bajo / salida de drenaje | X = 19.34, Y = 0.60 (UTM 357898.62, 2285120.28) |
| Pendiente longitudinal asumida | 0.5 % hacia la salida |
| Cota de inicio (punto alto) / cota mínima | 102.32 m / 100.00 m |
| Cuadre (donación + vialidad + lotes) | 32,096.41 m² |

**Accesos y gaps de donación**

- Gap 1 en (347.32, 318.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (58.92 m²).
- Gap 2 en (203.25, 153.92): la banda verde se interrumpe 12.00 m para dejar pasar el colector (69.59 m²).
- Gap 3 en (182.05, 137.85): la banda verde se interrumpe 12.00 m para dejar pasar el colector (64.80 m²).
- Gap 4 en (23.68, 3.36): la banda verde se interrumpe 12.00 m para dejar pasar el colector (70.08 m²).
- El colector cruza la calle municipal entre A y B. Ahí no se dibuja vialidad propia, solo el eje y el cruce pluvial.

**Retornos**

- CALLE PROFUNDA A: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.
- CALLE PROFUNDA B: retorno rectangular en T (dos brazos), cada brazo con 17.00 m de arroyo libre y ancho de 9.00 m.

**Justificación**

- Una sola calle profunda por macrolote: nace en el extremo bajo del colector, sube paralela a
- la colindancia poniente y termina en un retorno rectangular al norte. Es la menor vialidad interna.

**Validación**

- ✅ Sin traslape lote-lote: 0.0000 m2
- ✅ Sin traslape lotes-vialidad/banquetas: 0.0000 m2
- ✅ Sin traslape lotes-donación: 0.0000 m2
- ✅ Sin traslape vialidad-donación: 0.0000 m2
- ✅ Frente >= 25.00 m sobre alineamiento exterior de banqueta: 21 lotes; mínimo 25.01 m
- ✅ Donación entre 9.9 % y 10.1 %: 10.000 %
- ✅ Donación perimetral (cada parte toca el lindero): 4 partes; banda base 5.118 m
- ✅ Punto bajo único en la red: mínimos locales = 1
- ✅ Punto bajo en el borde accesible del colector: (19.34, 0.60)
- ✅ Retornos con brazo >= 15 m (17.00 m): CALLE PROFUNDA A: T, CALLE PROFUNDA B: T
- ✅ Ningún lote ciego: OK

## Comparativo

| Opción | Lotes | Área vendible | Vialidad | Donación | Long. vial | Cota alta |
|---|---|---|---|---|---|---|
| 1 · Colector inferior con peines y retornos | 15 | 20,266.89 m² (63.14 %) | 8,619.88 m² (26.86 %) | 10.000 % | 775.63 m | 102.34 m |
| 2 · Colector diagonal con ramales | 22 | 19,163.73 m² (59.71 %) | 9,723.04 m² (30.29 %) | 10.000 % | 850.84 m | 102.39 m |
| 3 · Retornos profundos optimizados | 21 | 20,100.55 m² (62.63 %) | 8,786.22 m² (27.37 %) | 10.000 % | 772.77 m | 102.32 m |

## Limitaciones

- No hay levantamiento topográfico. El borde bajo y las cotas son supuestos (pendiente de 0.5 %) y hay que confirmarlos en campo.
- Las cotas son de rasante teórica sobre ejes; no incluyen diseño de tubería pluvial ni el cruce bajo la calle municipal.
- Las esquinas de las intersecciones no llevan radios de giro (aplica a calles y colector). Los retornos sí cumplen el brazo de 17 m.
- Los remanentes interiores sin frente propio se suman al lote vecino con el que comparten el lindero más largo. Así no se crean lotes nuevos con frente menor de 25 m.
