"""Validación geométrica, verificación del DXF y memoria (README.md)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import ezdxf
from shapely.geometry import LineString, Point

import config
from dxf_writer import CAPAS
from geometry import Macrolote, lines, seccion_en


@dataclass
class Check:
    nombre: str
    ok: bool
    detalle: str


# ---------------------------------------------------------------------------
# Drenaje
# ---------------------------------------------------------------------------
def drenaje(macros: list[Macrolote]) -> dict:
    """Recorrido del escurrimiento: del retorno en T al acceso y a la salida."""
    salida = Point(config.PUNTO_DRENAJE)
    res = {}
    for m in macros:
        recorrido = m.eje.length + m.acceso.distance(salida)
        res[m.nombre] = {
            "recorrido": recorrido,
            "cota_inicio": config.COTA_MINIMA + config.PENDIENTE_DRENAJE * recorrido,
        }
    return res


# ---------------------------------------------------------------------------
# Validación geométrica
# ---------------------------------------------------------------------------
def _ancho(geom, m: Macrolote, f: float) -> float:
    (x, y), _, (nx, ny) = seccion_en(m, f)
    corte = LineString([(x - nx * 20, y - ny * 20), (x + nx * 20, y + ny * 20)])
    tramo = [ln for ln in lines(corte.intersection(geom)) if ln.distance(Point(x, y)) < 1e-6]
    return tramo[0].length if tramo else 0.0


def validar(macros: list[Macrolote]) -> list[Check]:
    checks: list[Check] = []
    for m in macros:
        resid = m.area_total - m.area_donacion - m.area_vialidad - m.area_vendible
        checks.append(Check(f"{m.nombre}: cierre de áreas", abs(resid) < 0.5,
                            f"total - (donación + vialidad + vendible) = {resid:+.3f} m2"))
        traslape = sum(a.poligono.intersection(b.poligono).area
                       for i, a in enumerate(m.lotes) for b in m.lotes[i + 1:])
        checks.append(Check(f"{m.nombre}: lotes sin traslape", traslape < 0.01,
                            f"traslape acumulado = {traslape:.4f} m2"))
        inv = sum(l.poligono.intersection(m.derecho_via).area +
                  l.poligono.intersection(m.donacion).area for l in m.lotes)
        checks.append(Check(f"{m.nombre}: lotes no invaden vialidad ni donación",
                            inv < 0.01, f"invasión = {inv:.4f} m2"))
        inv_d = m.donacion.intersection(m.derecho_via).area
        checks.append(Check(f"{m.nombre}: vialidad y retorno T no invaden donación",
                            inv_d < 0.01, f"invasión = {inv_d:.4f} m2"))
        anchos = [(_ancho(m.arroyo, m, f), _ancho(m.derecho_via, m, f)) for f in (0.25, 0.55)]
        ok = all(abs(a - config.ARROYO) < 0.02 and abs(r - config.SECCION_TOTAL) < 0.02
                 for a, r in anchos)
        checks.append(Check(f"{m.nombre}: sección vial 1.50 | 9.00 | 1.50", ok,
                            "; ".join(f"arroyo {a:.2f} m / derecho de vía {r:.2f} m"
                                      for a, r in anchos)))
        sin_frente = [l.numero for l in m.lotes if l.frente < 1.0]
        checks.append(Check(f"{m.nombre}: todos los lotes con frente a vialidad",
                            not sin_frente, f"sin frente: {sin_frente or 'ninguno'}"))
    tot = sum(m.area_total for m in macros)
    don = sum(m.area_donacion for m in macros)
    pct = 100 * don / tot
    checks.append(Check("Proyecto: donación ~10 %", 9.0 <= pct <= 11.0, f"{pct:.2f} %"))
    return checks


def verificar_dxf(ruta: Path) -> list[Check]:
    doc = ezdxf.readfile(ruta)
    auditor = doc.audit()
    msp = doc.modelspace()
    checks = [
        Check("DXF: ezdxf.readfile", True, str(ruta)),
        Check("DXF: auditoría sin errores", not auditor.has_errors,
              f"{len(auditor.errors)} errores, {len(auditor.fixes)} correcciones"),
        Check("DXF: $INSUNITS = 6 (metros)", doc.header.get("$INSUNITS") == 6,
              f"$INSUNITS = {doc.header.get('$INSUNITS')}"),
    ]
    for capa, color in CAPAS.items():
        ok = capa in doc.layers and doc.layers.get(capa).color == color
        n = len(msp.query(f'*[layer=="{capa}"]'))
        checks.append(Check(f"DXF: capa {capa} (color {color})", ok and n > 0,
                            f"{n} entidades"))
    return checks


# ---------------------------------------------------------------------------
# Memoria
# ---------------------------------------------------------------------------
def _fmt(v: float) -> str:
    return f"{v:,.2f}"


JUSTIFICACION = {
    "A": (
        "Acceso único por el lindero sur, sobre la vialidad central que separa ambos "
        "macrolotes. El eje sube con una curva en S hacia el norte-noreste (tramo recto "
        "de ~68 m) y gira al oriente hasta rematar en el retorno en T. El cabezal de la T "
        "(20.0 x 29.8 m a límite de banqueta) permite la vuelta en U de vehículos de carga y remata a 13.7 m de la donación, "
        "sin requerir una glorieta; el arroyo no se acerca al lindero sureste: "
        "la franja de donación perimetral y la cuña verde del vértice oriente quedan "
        "íntegras. Los lotes 1-7 dan frente al lado poniente/norte de la vialidad y los "
        "lotes 8-12 al lado oriente; los lotes 6-9 también dan frente al propio cabezal "
        "de la T; ninguno depende de la donación para su acceso."
    ),
    "B": (
        "Acceso único por el lindero sur con radios de giro de 15.0 m (poniente) y 13.5 m "
        "(oriente) sobre la vialidad central. El eje corre recto ~155 m hacia el "
        "norte-noreste, paralelo al lindero poniente, y gira al oriente hasta el retorno en "
        "T (20.0 x 29.8 m). La T remata a 12.4 m de la franja de donación, de modo que el "
        "retorno resuelve la vuelta en U del extremo cerrado sin invadir la donación "
        "perimetral sureste y además genera frente para los lotes 20, 21 y 22, que rodean "
        "el cabezal. Los lotes 13-19 quedan al poniente/norte y los lotes 20-26 al oriente, "
        "entre la vialidad y la franja verde."
    ),
}


def escribir_readme(macros: list[Macrolote], alterno: list[Macrolote], dren: dict,
                    checks: list[Check], rutas: dict[str, Path]) -> Path:
    tot = {k: sum(getattr(m, k) for m in macros)
           for k in ("area_total", "area_donacion", "area_vialidad", "area_vendible",
                     "longitud_vialidad")}
    n_tot = sum(len(m.lotes) for m in macros)
    x, y = config.PUNTO_DRENAJE
    M1, M2 = macros

    def fila(nombre, f, total=""):
        return f"| {nombre} | {f(M1)} | {f(M2)} | {total} |"

    L = []
    L += [
        "# Parque industrial - Lotificación DXF",
        "",
        "Proyecto en Python (`ezdxf` + `shapely`) que reproduce la traza del plano de "
        "referencia `PROPUESTA_1.dwfx`: polígono irregular en \"boomerang/V\" dividido en dos "
        "macrolotes por la vialidad central, cada uno con una vialidad interna que remata en un "
        "retorno en \"T\" y lotes perpendiculares a la vialidad. Todas las coordenadas "
        "están en UTM, en metros, y se extrajeron directamente de las capas del DWFX "
        "(`POLIGONO`, `LOTES`, `VIAL-EJE`, `VIAL-DERECHO-VIA`, `DONACION-AREA-VERDE`). "
        "Ningún vértice, ángulo ni divisoria se desplazó.",
        "",
        "## Ejecución",
        "",
        "```bash",
        "pip install -r requirements.txt && python main.py",
        "```",
        "",
        "Salidas:",
        "",
        f"- `out/{rutas['principal'].name}`: plano principal, con la traza exacta de la referencia.",
        f"- `out/{rutas['alterno'].name}`: variante opcional con los lotes regenerados a "
        "frente fijo de 25.00 m (ver la nota de diseño).",
        "",
        "## Tabla de metrados por macrolote",
        "",
        "| Concepto | Macrolote 1 | Macrolote 2 | Total proyecto |",
        "|---|---:|---:|---:|",
        fila("Área total del polígono (m2)", lambda m: _fmt(m.area_total), _fmt(tot["area_total"])),
        fila("Área de donación verde (m2)", lambda m: _fmt(m.area_donacion),
             _fmt(tot["area_donacion"])),
        fila("Donación respecto al macrolote (%)",
             lambda m: f"{100 * m.area_donacion / m.area_total:.2f} %",
             f"{100 * tot['area_donacion'] / tot['area_total']:.2f} %"),
        fila("Área de vialidad y banquetas (m2)", lambda m: _fmt(m.area_vialidad),
             _fmt(tot["area_vialidad"])),
        fila("  - arroyo asfáltico (m2)", lambda m: _fmt(m.arroyo.area),
             _fmt(sum(m.arroyo.area for m in macros))),
        fila("  - banquetas (m2)", lambda m: _fmt(m.banqueta.area),
             _fmt(sum(m.banqueta.area for m in macros))),
        fila("Área vendible / lotes (m2)", lambda m: _fmt(m.area_vendible),
             _fmt(tot["area_vendible"])),
        fila("Número total de lotes", lambda m: str(len(m.lotes)), str(n_tot)),
        fila("Longitud total de vialidad, eje dentro del predio (ml)",
             lambda m: _fmt(m.longitud_vialidad), _fmt(tot["longitud_vialidad"])),
        fila("Punto más bajo de drenaje (X, Y)", lambda m: f"{x:,.2f}, {y:,.2f}",
             "común a ambos"),
        fila("Pendiente asumida", lambda m: f"{config.PENDIENTE_DRENAJE * 100:.1f} %", ""),
        fila("Recorrido hidráulico a la salida (m)",
             lambda m: _fmt(dren[m.nombre]["recorrido"]), ""),
        fila("Cota de inicio (retorno en T) (m)",
             lambda m: f"{dren[m.nombre]['cota_inicio']:.2f}", ""),
        fila("Cota mínima (salida de drenaje) (m)", lambda m: f"{config.COTA_MINIMA:.2f}", ""),
        "",
        "La cota mínima de 100.00 m es un banco de nivel local supuesto; la cota de inicio es "
        "`cota mínima + 0.5 % × recorrido`. El recorrido va del retorno en T al acceso por el "
        "eje y, desde el acceso, por la vialidad central hasta la salida en la esquina "
        "inferior izquierda (vértice suroeste del Macrolote 1).",
        "",
        "## Justificación de accesos y retornos en \"T\"",
        "",
    ]
    for m in macros:
        L += [f"**{m.nombre}.** {JUSTIFICACION[m.clave]}", ""]
    L += [
        "En ambos casos el retorno en T se resolvió con la sección completa: el arroyo de "
        "9.00 m entra al cabezal y la banqueta de 1.50 m lo rodea. La validación comprueba "
        "que la intersección entre la vialidad y la donación es de 0.00 m2.",
        "",
        "## Cuadro de lotes (plano principal)",
        "",
        "| Lote | Macrolote | Lado | Área (m2) | Frente (m) | Ancho x fondo (m) |",
        "|---:|---|---|---:|---:|---|",
    ]
    for m in macros:
        for l in m.lotes:
            a, f = l.ancho_fondo()
            L.append(f"| {l.numero} | {m.nombre} | {l.lado} | {_fmt(l.area)} | "
                     f"{_fmt(l.frente)} | {a:.2f} x {f:.2f} |")
    L += [
        "",
        "## Notas de diseño (regla de oro vs. parámetros)",
        "",
        "- **Sección vial.** En la referencia el derecho de vía mide 11.0 m (arroyo de 8.0 m). "
        "El plano aplica la sección pedida de **12.00 m = 1.50 + 9.00 + 1.50** sobre el "
        "*mismo eje* del DWFX, sin moverlo. Así, el frente de los lotes recorre 0.50 m y "
        "las divisorias conservan su posición y su ángulo. El cabezal de la T se toma tal "
        "cual de la capa `VIAL-DERECHO-VIA` y su arroyo resulta de restar la banqueta de 1.50 m.",
        "- **Frente de lote.** En la traza de referencia los frentes típicos miden **30 m**, "
        "no 25 m. Por la regla de oro, el plano principal respeta las divisorias originales "
        f"({n_tot} lotes). Para cumplir el parámetro de 25.00 m sin tocar polígono, eje, "
        "retornos ni donación se genera además "
        f"`out/{rutas['alterno'].name}`, con lotes perpendiculares a la banqueta cada 25.00 m "
        f"({sum(len(m.lotes) for m in alterno)} lotes; vendible "
        f"{_fmt(sum(m.area_vendible for m in alterno))} m2). El modo se elige con "
        "`MODO_LOTIFICACION` en `config.py`.",
        "- **Donación.** Es la franja perimetral sureste más los remates verdes del dibujo, "
        "menos lo que ocupa la sección de 12 m.",
        "",
        "## Validación",
        "",
        "| Verificación | Resultado | Detalle |",
        "|---|:---:|---|",
    ]
    for c in checks:
        L.append(f"| {c.nombre} | {'OK' if c.ok else 'REVISAR'} | {c.detalle} |")
    L += [
        "",
        "## Capas del DXF",
        "",
        "| Capa | Color | Contenido |",
        "|---|---:|---|",
        "| `LOTES` | 2 | Polilíneas cerradas y relleno amarillo de cada lote |",
        "| `DONACION` | 3 | Franja perimetral de donación (verde) |",
        "| `VIAL_ASFALTO` | 8 | Arroyo de 9.00 m, retornos en T y eje (CENTER) |",
        "| `VIAL_BANQUETA` | 9 | Límite de derecho de vía y banquetas de 1.50 m |",
        "| `DRENAJE` | 1 | Símbolo y texto del punto más bajo / salida de drenaje |",
        "| `COTAS` | 6 | Cotas alineadas de lados y frentes de cada predio y de la sección vial |",
        "| `TEXTOS` | 7 | Número, área, frente y medidas de cada lote; rótulos de la sección |",
        "| `TABLA_CONTENIDOS` | 7 | Bloques `TABLA_CONTENIDOS` (metrados) y `TABLA_CONTENIDOS_LOTES` |",
        "",
        "## Estructura",
        "",
        "```",
        "parque_industrial_dxf/",
        "  README.md          memoria y validación (generado por main.py)",
        "  requirements.txt",
        "  main.py            orquestación",
        "  config.py          coordenadas de la traza y parámetros",
        "  geometry.py        vialidad, donación y lotificación (shapely)",
        "  dxf_writer.py      capas, rellenos, cotas, textos y tabla (ezdxf)",
        "  validacion.py      verificaciones, drenaje y esta memoria",
        "  out/plano_parque_industrial.dxf",
        "```",
        "",
    ]
    config.README_PATH.write_text("\n".join(L), encoding="utf-8")
    return config.README_PATH
