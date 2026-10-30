"""3 propuestas de 6 lotes con la vialidad de proyecto de Drawing1.dxf."""

from __future__ import annotations

import math
import sys

import ezdxf
from ezdxf.addons import Importer

import config_carretera as cfg
import lotificacion_6 as L

L.usar_config(cfg)


def importar_contexto(doc, msp, dx: float) -> None:
    """Copia el plano de referencia (cuadrícula, norte, rótulos, anillo vial...)."""
    src = ezdxf.readfile(cfg.REFERENCIA_DXF)
    ents = [e for e in src.modelspace() if e.dxf.layer not in cfg.CONTEXTO_EXCLUIR_CAPAS]
    antes = {e.dxf.handle for e in msp}
    imp = Importer(src, doc)
    imp.import_entities(ents, msp)
    imp.finalize()
    if dx:
        for e in msp:
            if e.dxf.handle not in antes:
                try:
                    e.translate(dx, 0, 0)
                except Exception:  # entidades sin transformación soportada
                    msp.delete_entity(e)


def readme(props, rutas, checks):
    M = list(cfg.MACROLOTES)
    L_ = [
        "# Lotificación en 6 lotes con la vialidad de proyecto (Drawing1.dxf)",
        "",
        "Base: `referencia/Drawing1.dxf`, que traza la **vialidad de proyecto diagonal** dentro "
        "de los dos macrolotes y marca las superficies afectadas. `extraer_drawing1.py` "
        "toma de ese plano, sin moverlos, los paramentos de la vialidad (capa `ASFALTO`), "
        "el predio del Macrolote 2 (capa `Polígono`) y los linderos poniente y sur del Macrolote 1, y "
        "escribe `traza_carretera.py`. El plano de referencia (cuadrícula UTM, norte, "
        "rótulos catastrales, parcelas vecinas 60 y 49, anillo vial y leyendas de superficie "
        "afectada) se importa "
        "tal cual como contexto, en sus mismas coordenadas.",
        "",
        "En cada macrolote **neto** (predio menos vialidad) se deja una **donación del 10 %** "
        "y el resto se divide en **3 lotes de igual área**, todos con frente a la vialidad "
        "de proyecto. En total son 6 lotes.",
        "",
        "```bash",
        "pip install -r requirements.txt && python main_carretera.py",
        "```",
        "",
        "## Áreas de partida",
        "",
        "| Concepto | Macrolote 1 | Macrolote 2 | Total |",
        "|---|---:|---:|---:|",
    ]
    ms = props[1]
    def fila(t, f):
        L_.append(f"| {t} | {f(ms[0])} | {f(ms[1])} | {f(None) if True else ''} |")
    tot = lambda g: f"{sum(g(m) for m in ms):,.2f}"  # noqa: E731
    for t, g in [("Área bruta del predio (m2)", lambda m: m.area_bruta),
                 ("Vialidad de proyecto dentro del predio (m2)", lambda m: m.vialidad.area),
                 ("Superficie afectada, leyenda del plano (m2)", lambda m: m.afectada_plano),
                 ("Área neta del macrolote (m2)", lambda m: m.area_total),
                 ("Donación 10 % del área neta (m2)", lambda m: m.area_donacion),
                 ("Área vendible (m2)", lambda m: m.area_vendible)]:
        L_.append(f"| {t} | {g(ms[0]):,.2f} | {g(ms[1]):,.2f} | {tot(g)} |")
    L_ += ["",
           "La sección real de la vialidad se acota en el plano en dos puntos por macrolote. "
           "En el Macrolote 2 mide 1.50 + 8.98 + 1.50 = 12.0 m. En el Macrolote 1 el arroyo "
           "se abre hacia el anillo vial, tal como está dibujado.",
           "", "## Archivos", ""]
    for k, r in rutas.items():
        L_.append(f"- `out/carretera/{r.name}`: {k}")
    L_ += ["", "## Comparativo de propuestas", "",
           "| Concepto | Propuesta 1 | Propuesta 2 | Propuesta 3 |", "|---|---:|---:|---:|"]
    for i, nombre in enumerate(M):
        L_.append(f"| {nombre}: área de cada lote (m2) | " +
                  " | ".join(f"{props[n][i].lotes[0].area:,.2f}" for n in (1, 2, 3)) + " |")
        L_.append(f"| {nombre}: frentes a la vialidad (m) | " +
                  " | ".join(" / ".join(f"{l.frente:.2f}" for l in props[n][i].lotes)
                             for n in (1, 2, 3)) + " |")
    L_.append("")
    for n, ms_ in props.items():
        p = cfg.PROPUESTAS[n]
        L_ += [f"## {p['nombre']}", "", p["descripcion"], "",
               "| Lote | Macrolote | Área (m2) | % del área neta | Frente a vialidad (m) |",
               "|---:|---|---:|---:|---:|"]
        for m in ms_:
            for l in m.lotes:
                L_.append(f"| {l.numero} | {m.nombre} | {l.area:,.2f} | "
                          f"{100 * l.area / m.area_total:.2f} % | {l.frente:,.2f} |")
        L_.append("")
    x, y = cfg.PUNTO_DRENAJE
    L_ += ["## Drenaje", "",
           f"Punto más bajo / salida: X = {x:,.2f}, Y = {y:,.2f} (vértice suroeste del "
           f"Macrolote 1). Pendiente asumida {cfg.PENDIENTE_DRENAJE * 100:.1f} %, cota mínima "
           f"{cfg.COTA_MINIMA:.2f} m (banco de nivel local supuesto).", ""]
    for m in ms:
        d = max(math.dist(cfg.PUNTO_DRENAJE, c) for c in m.poligono.exterior.coords)
        L_.append(f"- {m.nombre}: punto más lejano a {d:,.2f} m, cota de inicio "
                  f"{cfg.COTA_MINIMA + cfg.PENDIENTE_DRENAJE * d:.2f} m.")
    L_ += ["", "## Supuestos a confirmar", "",
           "- **Lindero del Macrolote 1:** es la línea de `ASFALTO` que arranca sobre el "
           "lindero sur. La línea paralela que corre 1.50 m hacia dentro del predio se "
           "dibuja como referencia de guarnición y no se descuenta. Si es banqueta dentro "
           "del predio, el área neta baja unos 530 m2.",
           "- **Base de la donación:** el 10 % se calcula sobre el área neta (predio menos "
           "vialidad de proyecto).",
           "- **Superficie afectada:** la cifra de la leyenda del plano se reporta tal cual. "
           "La vialidad medida dentro de cada predio aparece en su propio renglón.",
           "", "## Validación", "", "| Verificación | Resultado | Detalle |", "|---|:---:|---|"]
    for n, chks in checks.items():
        for t, ok, det in chks:
            L_.append(f"| P{n} - {t} | {'OK' if ok else 'REVISAR'} | {det} |")
    L_.append("")
    cfg.README_PATH.write_text("\n".join(L_), encoding="utf-8")


def main() -> int:
    props = {n: L.construir_propuesta(n) for n in (1, 2, 3)}
    rutas, checks = {}, {}
    for n, ms in props.items():
        r = L.escribir(cfg.OUT_DIR / f"propuesta_{n}_carretera.dxf", [(n, ms, 0.0)],
                       importar_contexto)
        rutas[cfg.PROPUESTAS[n]["nombre"]] = r
        checks[n] = L.validar(ms) + L.verificar_dxf(r)
    comp = L.escribir(cfg.OUT_DIR / "comparativo_3_propuestas_carretera.dxf",
                      [(n, ms, 650.0 * (n - 1)) for n, ms in props.items()], importar_contexto)
    rutas["Las 3 propuestas lado a lado (desplazadas 650 m en X)"] = comp
    readme(props, rutas, checks)
    print("=" * 78)
    for r in rutas.values():
        ezdxf.readfile(r)
        print(f"{r.resolve()}  (readfile OK)")
    print(cfg.README_PATH.resolve())
    for n, ms in props.items():
        print(cfg.PROPUESTAS[n]["nombre"])
        for m in ms:
            print(f"  {m.nombre}: bruta {m.area_bruta:,.2f} | vialidad "
                  f"{m.vialidad.area:,.2f} | neta {m.area_total:,.2f} | donación "
                  f"{m.area_donacion:,.2f} ({100 * m.area_donacion / m.area_total:.2f} %) | "
                  + " | ".join(f"L{l.numero} {l.area:,.2f} fte {l.frente:.2f}" for l in m.lotes))
    fallas = [(n, c) for n, cs in checks.items() for c in cs if not c[1]]
    print("VALIDACIÓN:", "TODO OK" if not fallas else fallas)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
