"""Genera las 3 propuestas de lotificación de 6 lotes (3 por macrolote)."""

from __future__ import annotations

import math
import sys

import ezdxf
from shapely.geometry import Point

import config_6lotes as cfg
from lotificacion_6 import construir_propuesta, escribir, validar, verificar_dxf


def drenaje(macros):
    salida = Point(cfg.PUNTO_DRENAJE)
    out = {}
    for m in macros:
        lejano = max(math.dist(cfg.PUNTO_DRENAJE, c) for c in m.poligono.exterior.coords)
        out[m.nombre] = (lejano, cfg.COTA_MINIMA + cfg.PENDIENTE_DRENAJE * lejano)
    return out


def readme(props, rutas, checks):
    L = [
        "# Lotificación en 6 lotes - 3 propuestas",
        "",
        "Base: `lotificaciones.dwfx`. Los polígonos de los dos macrolotes y la avenida "
        "lateral diagonal se tomaron en coordenadas UTM (m), sin modificar. Cada "
        "macrolote se divide en **3 lotes de igual área** con frente a la avenida lateral "
        "diagonal y deja **10.00 % de donación al fondo**. En total son **6 lotes**.",
        "",
        "```bash",
        "pip install -r requirements.txt && python main_6lotes.py",
        "```",
        "",
        "## Archivos",
        "",
    ]
    for k, r in rutas.items():
        L.append(f"- `out/6_lotes/{r.name}`: {k}")
    L += ["", "## Comparativo de propuestas", "",
          "| Concepto | Propuesta 1 | Propuesta 2 | Propuesta 3 |", "|---|---:|---:|---:|"]

    def fila(t, f):
        L.append(f"| {t} | " + " | ".join(f(props[n]) for n in (1, 2, 3)) + " |")

    fila("Donación", lambda ms: {"fondo": "Franja al fondo (lindero poniente)",
                                 "extremo": "Extremo norte"}[
        cfg.PROPUESTAS[[k for k, v in props.items() if v is ms][0]]["donacion"]])
    fila("Cortes", lambda ms: {"cabecera": "Paralelos a cabeceras",
                               "avenida": "Perpendiculares a la avenida"}[
        cfg.PROPUESTAS[[k for k, v in props.items() if v is ms][0]]["cortes"]])
    for i, nombre in enumerate(cfg.MACROLOTES):
        fila(f"{nombre}: área total (m2)", lambda ms: f"{ms[i].area_total:,.2f}")
        fila(f"{nombre}: donación (m2)", lambda ms: f"{ms[i].area_donacion:,.2f} "
             f"({100 * ms[i].area_donacion / ms[i].area_total:.2f} %)")
        fila(f"{nombre}: área de cada lote (m2)", lambda ms: f"{ms[i].lotes[0].area:,.2f}")
        fila(f"{nombre}: frentes a avenida (m)",
             lambda ms: " / ".join(f"{l.frente:.2f}" for l in ms[i].lotes))
    fila("Total vendible (m2)", lambda ms: f"{sum(m.area_vendible for m in ms):,.2f}")
    fila("Total donación (m2)", lambda ms: f"{sum(m.area_donacion for m in ms):,.2f}")
    fila("Total de lotes", lambda ms: str(sum(len(m.lotes) for m in ms)))
    L.append("")
    for n, ms in props.items():
        p = cfg.PROPUESTAS[n]
        L += [f"## {p['nombre']}", "", p["descripcion"], "",
              "| Lote | Macrolote | Área (m2) | % del macrolote | Frente a avenida (m) |",
              "|---:|---|---:|---:|---:|"]
        for m in ms:
            for l in m.lotes:
                L.append(f"| {l.numero} | {m.nombre} | {l.area:,.2f} | "
                         f"{100 * l.area / m.area_total:.2f} % | {l.frente:,.2f} |")
        L.append("")
    d = drenaje(props[1])
    x, y = cfg.PUNTO_DRENAJE
    L += ["## Drenaje", "",
          f"Punto más bajo / salida: X = {x:,.2f}, Y = {y:,.2f}, en el vértice suroeste del "
          f"Macrolote 1. Se asume una pendiente de {cfg.PENDIENTE_DRENAJE * 100:.1f} % y una cota "
          f"mínima de {cfg.COTA_MINIMA:.2f} m (banco de nivel local supuesto).", ""]
    for k, (dist, cota) in d.items():
        L.append(f"- {k}: punto más lejano a {dist:,.2f} m, cota de inicio {cota:.2f} m.")
    L += ["", "## Validación", "", "| Verificación | Resultado | Detalle |", "|---|:---:|---|"]
    for n, chks in checks.items():
        for t, ok, det in chks:
            L.append(f"| P{n} - {t} | {'OK' if ok else 'REVISAR'} | {det} |")
    L.append("")
    cfg.README_PATH.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    props = {n: construir_propuesta(n) for n in (1, 2, 3)}
    rutas = {}
    checks = {}
    for n, ms in props.items():
        r = escribir(cfg.OUT_DIR / f"propuesta_{n}_6_lotes.dxf", [(n, ms, 0.0)])
        rutas[cfg.PROPUESTAS[n]["nombre"]] = r
        checks[n] = validar(ms) + verificar_dxf(r)
    comp = escribir(cfg.OUT_DIR / "comparativo_3_propuestas.dxf",
                    [(n, ms, 450.0 * (n - 1)) for n, ms in props.items()])
    rutas["Las 3 propuestas lado a lado (desplazadas 450 m en X)"] = comp
    readme(props, rutas, checks)

    print("=" * 78)
    for k, r in rutas.items():
        ezdxf.readfile(r)
        print(f"{r.resolve()}  (readfile OK)")
    print(f"{cfg.README_PATH.resolve()}")
    print("=" * 78)
    for n, ms in props.items():
        print(cfg.PROPUESTAS[n]["nombre"])
        for m in ms:
            print(f"  {m.nombre}: total {m.area_total:,.2f} m2 | donación "
                  f"{m.area_donacion:,.2f} m2 ({100 * m.area_donacion / m.area_total:.2f} %) | "
                  + " | ".join(f"L{l.numero} {l.area:,.2f} m2 fte {l.frente:.2f} m"
                               for l in m.lotes))
    fallas = [(n, c) for n, cs in checks.items() for c in cs if not c[1]]
    print("=" * 78)
    print("VALIDACIÓN:", "TODO OK" if not fallas else fallas)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
