"""Genera las 3 opciones de lotificación industrial y exporta un DXF por opción.

Uso:  python main.py
"""
import os
import sys

import ezdxf

import config as C
import geometry as G
from dxf_writer import escribir
from validacion import validar

BASE = os.path.dirname(os.path.abspath(__file__))


def metricas(r):
    A = C.ANCHO * C.LARGO
    m = dict(
        area_total=A,
        area_donacion=r["don"].area,
        area_asfalto=r["asf"].area,
        area_banqueta=r["banq"].area,
        area_vial=r["row"].area,
        area_lotes=sum(L["geom"].area for L in r["lotes"]),
        area_remanente=sum(p.area for p in r["remanentes"]),
        n_lotes=len(r["lotes"]),
        long_vial=r["dren"]["longitud"],
        cota_min=min(r["dren"]["nodos"].values()),
        cota_max=max(r["dren"]["nodos"].values()),
        punto_bajo=r["lay"]["punto_bajo"],
        banda=r["b"],
    )
    for k in ("donacion", "vial", "lotes", "remanente"):
        m[f"pct_{k}"] = 100 * m[f"area_{k}"] / A
    m["cuadre"] = m["area_donacion"] + m["area_vial"] + m["area_lotes"] + m["area_remanente"]
    return m


def tabla_md(r, m, val):
    pb = m["punto_bajo"]
    L = []
    L.append(f"### {r['op']['titulo']}\n")
    L.append("| Concepto | Valor |")
    L.append("|---|---|")
    L.append(f"| Área total del polígono | {m['area_total']:,.2f} m² (100.00 %) |")
    L.append(f"| Donación verde perimetral | {m['area_donacion']:,.2f} m² (**{m['pct_donacion']:.3f} %**), banda de {m['banda']:.3f} m |")
    L.append(f"| Vialidad total (asfalto + banquetas) | {m['area_vial']:,.2f} m² ({m['pct_vial']:.2f} %) |")
    L.append(f"| &nbsp;&nbsp;Asfalto 9.00 m | {m['area_asfalto']:,.2f} m² |")
    L.append(f"| &nbsp;&nbsp;Banquetas 2 × 1.50 m | {m['area_banqueta']:,.2f} m² |")
    L.append(f"| Área vendible (lotes) | {m['area_lotes']:,.2f} m² ({m['pct_lotes']:.2f} %) |")
    L.append(f"| Área verde interna (remanentes sin frente de 25 m) | {m['area_remanente']:,.2f} m² ({m['pct_remanente']:.2f} %) |")
    L.append(f"| Número de lotes | {m['n_lotes']} (frente 25.00 m; fondos {', '.join(sorted({f'{x['fondo']:.2f}' for x in r['lotes']}))} m) |")
    L.append(f"| Longitud total de vialidad (ejes) | {m['long_vial']:,.2f} m |")
    L.append(f"| Punto más bajo de drenaje | X = {pb[0]:.2f}, Y = {pb[1]:.2f} (borde {'sur' if pb[1] == 0 else 'perimetral'}) |")
    L.append(f"| Pendiente longitudinal asumida | {100*C.PENDIENTE_LONGITUDINAL:.1f} % hacia el punto bajo |")
    L.append(f"| Cota inicio (punto alto) / cota mínima | {m['cota_max']:.2f} m / {m['cota_min']:.2f} m (supuesta) |")
    L.append(f"| Cuadre de áreas | {m['cuadre']:,.2f} m² |")
    L.append("")
    L.append("**Accesos y gaps de donación**\n")
    for gp in r["gaps"]:
        L.append(f"- {gp['acceso']} en borde {gp['borde'].lower()} (X = {gp['x']:.2f}, Y = {gp['y']:.2f}): gap de {gp['ancho']:.2f} m en la banda verde ({gp['area']:.2f} m² descontados; la banda se ensanchó para compensar y mantener el 10 %).")
    L.append("")
    L.append("**Justificación del arreglo**\n")
    for n in r["lay"]["notas"]:
        L.append(f"- {n}")
    if r["rem_frente"]:
        tot = sum(x["largo"] for x in r["rem_frente"])
        L.append(f"- Remanentes de frente < 25.00 m: {len(r['rem_frente'])} tramos ({tot:.2f} m de alineamiento) en esquinas e intersecciones; quedan como área verde interna y no se crearon lotes irregulares.")
    L.append("")
    L.append("**Validación**\n")
    for p, ok, d in val:
        L.append(f"- {'✅' if ok else '❌'} {p}: {d}")
    L.append("")
    return "\n".join(L)


README_HEAD = """# Parque industrial: 3 opciones de lotificación en DXF

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
| Envolvente | {W:.2f} × {L:.2f} m = {A:,.2f} m². Es la misma área total de los macrolotes A + B de `lotificaciones.dwfx` (32,096.50 m²). |
| Sección vial | 1.50 banqueta + 9.00 asfalto + 1.50 banqueta = **12.00 m** |
| Frente de lote | 25.00 m sobre el alineamiento exterior de banqueta; el lote nunca invade banqueta ni arroyo. |
| Fondo mínimo de lote | {FM:.2f} m |
| Donación | 10 % del área total, en banda perimetral. El ancho de la banda se calcula para que, después de abrir los gaps de acceso, dé 10.000 %. |
| Remanentes | Tramos de frente menores de 25.00 m: área verde interna. No se crean lotes irregulares. |
| Drenaje | Sin topografía. Pendiente longitudinal mínima de 0.5 % hacia un único punto bajo en el borde. Cota supuesta en la salida: {Z:.2f} m. |

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

"""

README_TAIL = """
## Comparativo

| Opción | Lotes | Área vendible | Vialidad | Donación | Verde interno | Longitud vial | Punto bajo |
|---|---|---|---|---|---|---|---|
{filas}

## Limitaciones y supuestos

- La envolvente es un rectángulo equivalente en área al terreno real, como pidió el encargo, para comparar las opciones en igualdad. Para el proyecto ejecutivo hay que llevar el trazo elegido a la poligonal real.
- No hay topografía. Las cotas de rasante son teóricas: salida en {Z:.2f} m y pendiente de 0.5 % sobre la ruta más corta de cada punto hacia la salida. Hay que ajustarlas con un levantamiento.
- Las calles cerradas (transversales de la opción 1 y ramales de la opción 3) no llevan retorno. Si el reglamento lo exige para tractocamión, hay que agregar un retorno de radio ≥ 15 m en su extremo, a costa de los lotes vecinos.
- El área verde interna proviene de remanentes sin frente de 25 m. Es independiente de la donación municipal perimetral y no se suma a ella.
"""


def main():
    out_dir = os.path.join(BASE, C.OUT_DIR)
    os.makedirs(out_dir, exist_ok=True)
    secciones, filas, rutas, todo_ok = [], [], [], True
    for op in G.OPCIONES:
        r = G.construir(op)
        m = metricas(r)
        val = validar(r)
        todo_ok &= all(ok for _, ok, _ in val)
        ruta = os.path.join(out_dir, f"{op['clave']}.dxf")
        escribir(r, m, ruta)
        rutas.append((op, ruta, m, val))
        secciones.append(tabla_md(r, m, val))
        pb = m["punto_bajo"]
        filas.append(f"| {op['clave'][-1]} · {op['corto']} | {m['n_lotes']} | {m['area_lotes']:,.2f} m² ({m['pct_lotes']:.2f} %) | {m['area_vial']:,.2f} m² ({m['pct_vial']:.2f} %) | {m['pct_donacion']:.3f} % | {m['area_remanente']:,.2f} m² | {m['long_vial']:,.2f} m | ({pb[0]:.2f}, {pb[1]:.2f}) |")

    readme = README_HEAD.format(W=C.ANCHO, L=C.LARGO, A=C.ANCHO * C.LARGO, FM=C.FONDO_MINIMO, Z=C.COTA_PUNTO_BAJO)
    readme += "\n".join(secciones) + README_TAIL.format(filas="\n".join(filas), Z=C.COTA_PUNTO_BAJO)
    with open(os.path.join(BASE, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    print("=" * 78)
    for op, ruta, m, val in rutas:
        doc = ezdxf.readfile(ruta)
        msp = doc.modelspace()
        n_ent = len(msp)
        capas = sorted({e.dxf.layer for e in msp})
        print(f"{op['titulo']}")
        print(f"  DXF: {os.path.abspath(ruta)}")
        print(f"  Lotes: {m['n_lotes']} | vendible {m['area_lotes']:,.2f} m2 ({m['pct_lotes']:.2f} %) | "
              f"donación {m['area_donacion']:,.2f} m2 ({m['pct_donacion']:.3f} %) | vialidad {m['area_vial']:,.2f} m2 ({m['pct_vial']:.2f} %)")
        print(f"  Longitud vial: {m['long_vial']:,.2f} m | punto bajo ({m['punto_bajo'][0]:.2f}, {m['punto_bajo'][1]:.2f}) "
              f"cota {m['cota_min']:.2f} m | punto alto {m['cota_max']:.2f} m")
        print(f"  ezdxf.readfile OK: {n_ent} entidades, $INSUNITS={doc.header['$INSUNITS']}, capas: {', '.join(capas)}")
        for p, ok, d in val:
            print(f"    [{'OK' if ok else 'FALLA'}] {p}: {d}")
        print("-" * 78)
    faltan = [r for _, r, _, _ in rutas if not os.path.isfile(r)]
    print("Los 3 DXF existen y se abren con ezdxf.readfile." if not faltan else f"Faltan: {faltan}")
    print("Todas las validaciones OK." if todo_ok else "ATENCIÓN: hay validaciones con falla (ver arriba).")
    return 0 if (todo_ok and not faltan) else 1


if __name__ == "__main__":
    sys.exit(main())
