"""Genera el plano DXF del parque industrial, lo valida y escribe la memoria."""

from __future__ import annotations

import sys

import ezdxf

import config
from dxf_writer import escribir_dxf
from geometry import construir_proyecto
from validacion import drenaje, escribir_readme, validar, verificar_dxf


def main() -> int:
    modo = config.MODO_LOTIFICACION
    otro = "FRENTE_25" if modo == "TRAZA" else "TRAZA"
    rutas = {"principal": config.DXF_PATH, "alterno": config.DXF_PATH_FRENTE_25}
    if modo == "FRENTE_25":
        rutas = {"principal": config.DXF_PATH_FRENTE_25, "alterno": config.DXF_PATH}

    macros = construir_proyecto(modo)
    alterno = construir_proyecto(otro)
    dren = drenaje(macros)

    escribir_dxf(macros, rutas["principal"], config.COTA_MINIMA,
                 "PARQUE INDUSTRIAL - LOTIFICACIÓN (TRAZA DE REFERENCIA)"
                 if modo == "TRAZA" else "PARQUE INDUSTRIAL - LOTIFICACIÓN FRENTE 25 m")
    escribir_dxf(alterno, rutas["alterno"], config.COTA_MINIMA,
                 "PARQUE INDUSTRIAL - VARIANTE LOTES FRENTE 25 m"
                 if otro == "FRENTE_25" else "PARQUE INDUSTRIAL - TRAZA DE REFERENCIA")

    checks = validar(macros) + verificar_dxf(rutas["principal"])
    readme = escribir_readme(macros, alterno, dren, checks, rutas)

    print("=" * 78)
    print("ARCHIVOS GENERADOS")
    for k, r in rutas.items():
        doc = ezdxf.readfile(r)  # confirma que el DXF abre correctamente
        print(f"  DXF {k:<10}: {r.resolve()}  "
              f"(ezdxf.readfile OK, {len(doc.modelspace())} entidades)")
    print(f"  Memoria       : {readme.resolve()}")
    print("=" * 78)
    print(f"MÉTRICAS ({modo})")
    fmt = "  {:<38}{:>16}{:>16}{:>16}"
    print(fmt.format("", *(m.nombre for m in macros), "TOTAL"))
    filas = [
        ("Área total (m2)", "area_total"),
        ("Área de donación (m2)", "area_donacion"),
        ("Área de vialidad (m2)", "area_vialidad"),
        ("Área vendible (m2)", "area_vendible"),
        ("Longitud de vialidad (ml)", "longitud_vialidad"),
    ]
    for t, k in filas:
        v = [getattr(m, k) for m in macros]
        print(fmt.format(t, *(f"{x:,.2f}" for x in v), f"{sum(v):,.2f}"))
    pct = [100 * m.area_donacion / m.area_total for m in macros]
    tot_pct = 100 * sum(m.area_donacion for m in macros) / sum(m.area_total for m in macros)
    print(fmt.format("Donación (%)", *(f"{p:.2f} %" for p in pct), f"{tot_pct:.2f} %"))
    n = [len(m.lotes) for m in macros]
    print(fmt.format("Número de lotes", *map(str, n), str(sum(n))))
    print(fmt.format("Cota de inicio (m)",
                     *(f"{dren[m.nombre]['cota_inicio']:.2f}" for m in macros), ""))
    x, y = config.PUNTO_DRENAJE
    print(f"  Punto más bajo / salida de drenaje: X={x:,.2f}  Y={y:,.2f}  "
          f"cota mínima {config.COTA_MINIMA:.2f} m, pendiente "
          f"{config.PENDIENTE_DRENAJE * 100:.1f} %")
    print("=" * 78)
    print("VALIDACIÓN")
    for c in checks:
        print(f"  [{'OK' if c.ok else '!!'}] {c.nombre}: {c.detalle}")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
