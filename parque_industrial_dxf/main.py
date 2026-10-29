"""Genera 3 opciones de lotificación industrial sobre el polígono irregular y
exporta un DXF por opción en out/.   Uso:  python main.py"""
import os
import sys
import warnings

import ezdxf

import config as C
import geometry as G
from dxf_writer import escribir
from validacion import validar

warnings.filterwarnings("ignore", category=RuntimeWarning)
BASE = os.path.dirname(os.path.abspath(__file__))


def metricas(r):
    A = r["area_total"]
    m = dict(area_total=A, area_donacion=r["don"].area, area_asfalto=r["asf"].area,
             area_banqueta=r["banq"].area, area_vial=r["row"].area,
             area_lotes=sum(L["geom"].area for L in r["lotes"]), n_lotes=len(r["lotes"]),
             long_vial=r["dren"]["longitud"], cota_min=min(r["dren"]["nodos"].values()),
             cota_max=max(r["dren"]["nodos"].values()), punto_bajo=r["punto_bajo"], banda=r["banda"])
    for k in ("donacion", "vial", "lotes"):
        m[f"pct_{k}"] = 100 * m[f"area_{k}"] / A
    m["cuadre"] = m["area_donacion"] + m["area_vial"] + m["area_lotes"]
    return m


def seccion_md(r, m, val):
    pb = m["punto_bajo"]
    fr = [L["frente_alineamiento"] for L in r["lotes"]]
    ar = [L["geom"].area for L in r["lotes"]]
    L = [f"### {r['op']['titulo']}\n", "| Concepto | Valor |", "|---|---|",
         f"| Área total del polígono (A + B) | {m['area_total']:,.2f} m² |",
         f"| Donación verde perimetral | {m['area_donacion']:,.2f} m² (**{m['pct_donacion']:.3f} %**); banda base de {m['banda']:.2f} m más remanentes de borde |",
         f"| Vialidad total | {m['area_vial']:,.2f} m² ({m['pct_vial']:.2f} %) |",
         f"| &nbsp;&nbsp;Asfalto 9.00 m (calles + retornos) | {m['area_asfalto']:,.2f} m² |",
         f"| &nbsp;&nbsp;Banquetas 1.50 m | {m['area_banqueta']:,.2f} m² |",
         f"| Área vendible (lotes) | {m['area_lotes']:,.2f} m² ({m['pct_lotes']:.2f} %) |",
         f"| Número de lotes | {m['n_lotes']} (frentes de {min(fr):.2f} a {max(fr):.2f} m; áreas de {min(ar):,.0f} a {max(ar):,.0f} m²) |",
         f"| Longitud total de vialidad (ejes, incluye brazos de retorno) | {m['long_vial']:,.2f} m |",
         f"| Punto más bajo / salida de drenaje | X = {pb[0]:.2f}, Y = {pb[1]:.2f} (UTM {pb[0]+C.ORIGEN_UTM[0]:.2f}, {pb[1]+C.ORIGEN_UTM[1]:.2f}) |",
         f"| Pendiente longitudinal asumida | {100*C.PENDIENTE_LONGITUDINAL:.1f} % hacia la salida |",
         f"| Cota de inicio (punto alto) / cota mínima | {m['cota_max']:.2f} m / {m['cota_min']:.2f} m |",
         f"| Cuadre (donación + vialidad + lotes) | {m['cuadre']:,.2f} m² |", "",
         "**Accesos y gaps de donación**\n"]
    for i, gp in enumerate(r["gaps"]):
        L.append(f"- Gap {i+1} en ({gp['x']:.2f}, {gp['y']:.2f}): la banda verde se interrumpe {C.SECCION:.2f} m para dejar pasar el colector ({gp['area']:.2f} m²).")
    L.append("- El colector cruza la calle municipal entre A y B. Ahí no se dibuja vialidad propia, solo el eje y el cruce pluvial.")
    L.append("")
    L.append("**Retornos**\n")
    for c in r["calles"]:
        tipo = "en T (dos brazos)" if len(c["brazos"]) == 2 else "en L (un brazo)"
        L.append(f"- {c['nombre']}: retorno rectangular {tipo}, cada brazo con {C.BRAZO_RETORNO:.2f} m de arroyo libre y ancho de 9.00 m.")
    L.append("")
    L.append("**Justificación**\n")
    for n in r["op"]["notas"]:
        L.append(f"- {n}")
    L.append("")
    L.append("**Validación**\n")
    for p, ok, d in val:
        L.append(f"- {'✅' if ok else '❌'} {p}: {d}")
    L.append("")
    return "\n".join(L)


README_HEAD = """# Parque industrial: 3 opciones de lotificación sobre polígono irregular

Proyecto en Python (shapely + ezdxf) que lotifica los dos macrolotes reales de `lotificaciones.dwfx`. Juntos forman un boomerang con cortes diagonales. El programa genera tres opciones y exporta un DXF por opción en `out/`.

## Ejecutar

```bash
pip install -r requirements.txt
python main.py
```

## Polígono base

- Coordenadas en `config.py`. El origen (0,0) está en la esquina surponiente de la envolvente, con escala 1:1 y unidades en metros (`$INSUNITS = 6`).
- Macrolote A: {AA:,.2f} m². Macrolote B: {AB:,.2f} m². Total: **{AT:,.2f} m²**.
- Para superponer sobre `lotificaciones.dwg`, mueve el dibujo de (0,0) a ({UX:.3f}, {UY:.3f}).

## Criterios

| Criterio | Valor |
|---|---|
| Colector principal | Paralelo al borde más bajo: la diagonal frente a Fraccionamiento La Espiga, que la memoria toma como la parte baja. Recorre B y A sin interrupción y cruza la calle municipal intermedia. Todo escurre hacia una sola salida en el extremo sur de A, sobre la avenida principal. |
| Calles internas | Nacen del colector y terminan en **retornos rectangulares en T o en L**. No hay glorietas ni anillos. |
| Retorno | Brazos de {BR:.2f} m de arroyo libre (≥ 15 m), con 9.00 m de ancho y banqueta de 1.50 m alrededor. El tractocamión entra, retrocede a un brazo y sale de frente. |
| Sección vial | 1.50 banqueta + 9.00 asfalto + 1.50 banqueta = **12.00 m** |
| Lotes | Frente mínimo de 25.00 m sobre el alineamiento exterior de banqueta. Los cortes son perpendiculares a la calle y en los quiebres del polígono quedan lotes trapezoidales. Área mínima de {AM:,.0f} m². |
| Donación | 10 % del total, en banda perimetral sobre los linderos que no ocupa el colector, más los remanentes de borde. El ancho de la banda se calcula para llegar al 10 %. |
| Drenaje | Sin topografía. Pendiente longitudinal de 0.5 % hacia la salida, con cota supuesta de {Z:.2f} m. Las cotas de los nodos salen de la ruta más corta sobre los ejes. |

## Cómo resuelven la topografía los retornos

Las calles internas son ramales sin salida. Su único punto de conexión es el colector, así que cada calle tiene un solo sentido de escurrimiento: del retorno (punto alto del ramal) hacia el colector. El agua de los lotes entra a la calle, corre hacia la boca del ramal y de ahí por el colector, que va paralelo al borde bajo, hasta la salida única. Con circuitos o glorietas aparecerían tramos con pendientes encontradas y puntos bajos intermedios. Los retornos rectangulares también ocupan menos área que una glorieta del mismo radio de maniobra y se acomodan contra los linderos inclinados.

## Memoria por opción

"""

README_TAIL = """
## Comparativo

| Opción | Lotes | Área vendible | Vialidad | Donación | Long. vial | Cota alta |
|---|---|---|---|---|---|---|
{filas}

## Limitaciones

- No hay levantamiento topográfico. El borde bajo y las cotas son supuestos (pendiente de 0.5 %) y hay que confirmarlos en campo.
- Las cotas son de rasante teórica sobre ejes; no incluyen diseño de tubería pluvial ni el cruce bajo la calle municipal.
- Las esquinas de las intersecciones no llevan radios de giro (aplica a calles y colector). Los retornos sí cumplen el brazo de 17 m.
- Los remanentes interiores sin frente propio se suman al lote vecino con el que comparten el lindero más largo. Así no se crean lotes nuevos con frente menor de 25 m.
"""


def main():
    out = os.path.join(BASE, C.OUT_DIR)
    os.makedirs(out, exist_ok=True)
    polys = G.poligonos()
    secc, filas, rutas, todo_ok = [], [], [], True
    for op in G.OPCIONES:
        r = G.construir(op)
        m = metricas(r)
        val = validar(r)
        todo_ok &= all(ok for _, ok, _ in val)
        ruta = os.path.join(out, f"{op['clave']}.dxf")
        escribir(r, m, ruta)
        rutas.append((op, ruta, m, val))
        secc.append(seccion_md(r, m, val))
        filas.append(f"| {op['clave'][-1]} · {op['corto']} | {m['n_lotes']} | {m['area_lotes']:,.2f} m² ({m['pct_lotes']:.2f} %) | {m['area_vial']:,.2f} m² ({m['pct_vial']:.2f} %) | {m['pct_donacion']:.3f} % | {m['long_vial']:,.2f} m | {m['cota_max']:.2f} m |")
    head = README_HEAD.format(AA=polys["A"].area, AB=polys["B"].area, AT=G.area_total(), UX=C.ORIGEN_UTM[0],
                              UY=C.ORIGEN_UTM[1], BR=C.BRAZO_RETORNO, AM=C.AREA_MIN_LOTE, Z=C.COTA_PUNTO_BAJO)
    with open(os.path.join(BASE, "README.md"), "w", encoding="utf-8") as f:
        f.write(head + "\n".join(secc) + README_TAIL.format(filas="\n".join(filas)))

    print("=" * 80)
    for op, ruta, m, val in rutas:
        doc = ezdxf.readfile(ruta)
        msp = doc.modelspace()
        print(op["titulo"])
        print(f"  DXF: {os.path.abspath(ruta)}")
        print(f"  Lotes {m['n_lotes']} | vendible {m['area_lotes']:,.2f} m2 ({m['pct_lotes']:.2f} %) | donación "
              f"{m['area_donacion']:,.2f} m2 ({m['pct_donacion']:.3f} %) | vialidad {m['area_vial']:,.2f} m2 ({m['pct_vial']:.2f} %)")
        print(f"  Long. vial {m['long_vial']:,.2f} m | salida ({m['punto_bajo'][0]:.2f}, {m['punto_bajo'][1]:.2f}) "
              f"Z {m['cota_min']:.2f} | punto alto Z {m['cota_max']:.2f}")
        print(f"  ezdxf.readfile OK: {len(msp)} entidades, $INSUNITS={doc.header['$INSUNITS']}, capas: "
              f"{', '.join(sorted({e.dxf.layer for e in msp}))}")
        for p, ok, d in val:
            print(f"    [{'OK' if ok else 'FALLA'}] {p}: {d}")
        print("-" * 80)
    faltan = [r for _, r, _, _ in rutas if not os.path.isfile(r)]
    print("Los 3 DXF existen y se abren con ezdxf.readfile." if not faltan else f"Faltan: {faltan}")
    print("Todas las validaciones OK." if todo_ok else "ATENCIÓN: hay validaciones con falla.")
    return 0 if todo_ok and not faltan else 1


if __name__ == "__main__":
    sys.exit(main())
