import json
M=json.load(open('metrics.json'))
def f(x,d=0): return f"{x:,.{d}f}"
rows=[]
for k,m in M.items():
    t=m['tot']
    rows.append((k,m,t))
# hybrid: A from t1, B from t2
hy={kk:M['t1']['per']['A'][kk]+M['t2']['per']['B'][kk] for kk in M['t1']['per']['A']}
def tr(name,t,cls=''):
    return f"""<tr class="{cls}"><th scope="row">{name}</th><td>{t['n']:.0f}</td><td>{t['near']:.0f} <small>({100*t['near']/t['n']:.0f}%)</small></td><td>{t['std']:.0f}</td><td>{f(t['lot'])}</td><td>{100*t['lot']/t['gross']:.1f}%</td><td>{f(t['road'])} <small>({100*t['road']/t['gross']:.1f}%)</small></td><td>{f(t['rl'])}</td><td>{t['rl']/t['n']:.1f}</td><td>{f(t['green'])} <small>({100*t['green']/t['gross']:.1f}%)</small></td><td>{t['ret']:.0f}</td></tr>"""
table=''.join(tr(m['title'].split('·')[0].strip()+f" <small>{m['mod']}</small>",t) for k,m,t in rows)+tr('Híbrido recomendado <small>A: Tipo 1 · B: Tipo 2</small>',hy,'rec')
desc={
't1':("Una calle principal paralela a la colindancia poniente, a 35.5 m del lindero (30 m de lote + 5.5 m de media sección). De ella salen calles transversales cerradas con retorno hacia el bulevar: una en el polígono A y dos en el B.",
      "Es el que más lotes da y llena casi toda la zona ancha del norte. A cambio tiene tres retornos y la mayor superficie de vialidad por lote."),
't2':("La misma espina se recorre a 45.5 m del lindero para alojar lotes de 15 × 40 m, con una sola transversal con retorno al norte de cada polígono.",
      "Es la vialidad más corta (384 m) y la que tiene más lotes exactos de 600 m² en B. En A pierde lotes porque la punta sur es angosta para fondos de 40 m."),
't3':("La espina sube por el poniente, cruza al norte y regresa en paralelo al bulevar hasta reconectar con la propia espina. No hay retornos y la circulación es continua.",
      "Es el más cómodo para recolección de basura y emergencias, pero ninguno de los dos polígonos es lo bastante ancho para dos filas de lotes espalda con espalda dentro del anillo. El centro queda como remanente verde y es el que menos rinde."),
}
cards=''
for k,m,t in rows:
    svg=open(f'out_{k}.svg').read()
    a,b=m['per']['A'],m['per']['B']
    cards+=f"""<section class="alt" id="{k}">
<header><p class="eyebrow">{m['mod']}</p><h2>{m['title']}</h2></header>
<div class="alt-grid"><figure class="plan">{svg}<figcaption>Polígono A: {a['n']:.0f} lotes · Polígono B: {b['n']:.0f} lotes. Pasa el cursor sobre un lote para ver su clave y superficie.</figcaption></figure>
<div class="alt-text"><p>{desc[k][0]}</p><p>{desc[k][1]}</p>
<dl class="kv"><div><dt>Lotes</dt><dd>{t['n']:.0f}</dd></div><div><dt>Lotes de 600 ± 5%</dt><dd>{t['near']:.0f}</dd></div><div><dt>Vendible</dt><dd>{100*t['lot']/t['gross']:.1f}%</dd></div><div><dt>Vialidad</dt><dd>{100*t['road']/t['gross']:.1f}%</dd></div><div><dt>m de calle por lote</dt><dd>{t['rl']/t['n']:.1f}</dd></div><div><dt>Retornos</dt><dd>{t['ret']:.0f}</dd></div></dl>
<p class="files">Archivos: <code>lotificacion_{k}.dxf</code> · <code>tabla_lotes_{k}.csv</code></p></div></div></section>"""
html=f"""<title>Lotificación Polígonos A y B</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: hoja de proyecto — encabezado de plano, tabla comparativa, tres láminas, dictamen */
:root{{--bg:#f6f7f4;--panel:#ffffff;--fg:#1d2420;--muted:#5b655f;--line:#cfd6d0;--accent:#2f6b4f;
--lot:#f3dc9b;--lot-irr:#bcd6ea;--green:#9fcf9a;--pav:#6f7672;--walk:#c8ccc8;--parcel:#eef0ea;--ctx:#9aa39e;--acc:#c0392b;--rec:#e3efe7;
--display:"Archivo Narrow","Arial Narrow",sans-serif;--body:"Source Serif 4",Georgia,serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#151a17;--panel:#1d2420;--fg:#e6ebe7;--muted:#a3ada7;--line:#36403a;--accent:#7cc39d;
--lot:#8a7638;--lot-irr:#3e5f78;--green:#3f6e3c;--pav:#4c524f;--walk:#7e8580;--parcel:#232b26;--ctx:#5f6a64;--acc:#ff7a6b;--rec:#20382b;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#151a17;--panel:#1d2420;--fg:#e6ebe7;--muted:#a3ada7;--line:#36403a;--accent:#7cc39d;
--lot:#8a7638;--lot-irr:#3e5f78;--green:#3f6e3c;--pav:#4c524f;--walk:#7e8580;--parcel:#232b26;--ctx:#5f6a64;--acc:#ff7a6b;--rec:#20382b;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font:16px/1.6 var(--body)}}
.wrap{{max-width:1180px;margin:0 auto;padding-block:32px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:40px}}
h1,h2,h3{{font-family:var(--display);text-wrap:balance;line-height:1.15;margin:0}}
h1{{font-size:clamp(28px,4vw,40px)}} h2{{font-size:26px}} h3{{font-size:19px}}
p{{margin:0;max-width:68ch}} .eyebrow{{font:500 12px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}}
.stack{{display:grid;gap:14px}}
.sheet{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border:1px solid var(--line);background:var(--panel)}}
.sheet div{{padding:10px 14px;border-right:1px solid var(--line)}} .sheet div:last-child{{border-right:0}}
.sheet dt,.kv dt{{font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.sheet dd,.kv dd{{margin:0;font:600 20px var(--display);font-variant-numeric:tabular-nums}}
.tbl{{overflow-x:auto;border:1px solid var(--line);background:var(--panel)}}
table{{border-collapse:collapse;width:100%;min-width:860px;font:14px var(--mono);font-variant-numeric:tabular-nums}}
th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}}
thead th{{font-weight:500;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);text-align:right}}
tbody th{{text-align:left;font:600 15px var(--display)}} th small,td small{{color:var(--muted);font-weight:400;display:block}}
tr.rec{{background:var(--rec)}}
.alt{{display:grid;gap:16px;border-top:2px solid var(--fg);padding-top:16px}}
.alt-grid{{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:28px;align-items:start}}
@media (max-width:820px){{.alt-grid{{grid-template-columns:1fr}}}}
.alt-text{{display:grid;gap:14px;min-width:0}}
.plan{{margin:0;background:var(--panel);border:1px solid var(--line);padding:8px}} .plan svg{{width:100%;height:auto;display:block}}
figcaption{{font:12px var(--mono);color:var(--muted);padding:6px 4px 2px}}
.parcel{{fill:var(--parcel);stroke:var(--fg);stroke-width:.5}} .green{{fill:var(--green);stroke:none}}
.walk{{fill:var(--walk)}} .pav{{fill:var(--pav)}} .cl{{fill:none;stroke:var(--bg);stroke-width:.3;stroke-dasharray:3 2}}
.lot{{stroke:var(--fg);stroke-width:.25}} .lot.std{{fill:var(--lot)}} .lot.irr{{fill:var(--lot-irr)}} .lot:hover{{stroke-width:.8}}
.lt{{font:600 3px var(--mono);fill:var(--fg);text-anchor:middle;pointer-events:none}} .la{{font:2.4px var(--mono);fill:var(--fg);text-anchor:middle;opacity:.75;pointer-events:none}}
.pl{{font:700 6px var(--display);fill:var(--muted);letter-spacing:.1em}}
.acc{{fill:none;stroke:var(--acc);stroke-width:.9}}
.kv{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:0}}
.kv div{{background:var(--panel);padding:8px 12px}}
.files{{font:13px var(--mono);color:var(--muted)}} code{{font-family:var(--mono)}}
.legend{{display:flex;flex-wrap:wrap;gap:8px 20px;font:13px var(--mono);color:var(--muted)}}
.legend span{{display:inline-flex;align-items:center;gap:8px}} .sw{{width:18px;height:12px;border:1px solid var(--fg)}}
.verdict{{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);padding:20px 22px;display:grid;gap:12px}}
ol,ul{{margin:0;padding-left:1.3em;display:grid;gap:8px;max-width:72ch}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:28px}}
</style>
<div class="wrap">
<header class="stack">
<p class="eyebrow">lotificaciones.dwg · Model · coordenadas UTM</p>
<h1>Lotificación de los polígonos A y B</h1>
<p>Tres esquemas de lotificación con lote objetivo de 600 m² y vialidad interna de 11 m (1.5 m de banqueta, 8.0 m de arroyo de doble sentido y 1.5 m de banqueta). La entrada a cada polígono es el círculo que marcaste en el plano.</p>
<dl class="sheet"><div><dt>Polígono A</dt><dd>14,131 m²</dd></div><div><dt>Polígono B</dt><dd>17,965 m²</dd></div><div><dt>Total bruto</dt><dd>32,097 m²</dd></div><div><dt>Sección vial</dt><dd>1.5 + 8 + 1.5 m</dd></div><div><dt>Lote tipo</dt><dd>600 m²</dd></div></dl>
<div class="legend"><span><i class="sw" style="background:var(--lot)"></i>Lote estándar rectangular de 600 m²</span><span><i class="sw" style="background:var(--lot-irr)"></i>Lote irregular o ajustado</span><span><i class="sw" style="background:var(--green)"></i>Área verde / donación</span><span><i class="sw" style="background:var(--pav)"></i>Arroyo 8 m</span><span><i class="sw" style="background:var(--walk)"></i>Banqueta 1.5 m</span><span><i class="sw" style="border-color:var(--acc);border-radius:50%"></i>Acceso</span></div>
</header>

<section class="stack"><h2>Comparativo</h2>
<div class="tbl"><table><thead><tr><th style="text-align:left">Esquema</th><th>Lotes</th><th>600 m² ±5%</th><th>Rectángulo exacto</th><th>Vendible m²</th><th>Aprovechamiento</th><th>Vialidad m²</th><th>Calle (m)</th><th>m calle / lote</th><th>Área verde m²</th><th>Retornos</th></tr></thead><tbody>{table}</tbody></table></div>
<p style="font-size:14px;color:var(--muted)">Superficies calculadas sobre la geometría exacta de los polígonos del DWFX. Un «rectángulo exacto» es un lote de 600 m² ±2% sin cortes por lindero. Un lote ajustado conserva el área de 600 m² (o un poco más) pero tiene un lado inclinado porque toca el bulevar o la colindancia.</p>
</section>

{cards}

<section class="stack"><h2>Análisis de acceso y distribución</h2>
<div class="cols">
<div class="stack"><h3>Lo que dicta la geometría</h3>
<ul><li>Los dos polígonos tienen una colindancia poniente recta y <strong>con el mismo rumbo</strong> (176 m en A y 200 m en B). Es el único lado largo y recto, así que la retícula se alinea con él. Así toda la fila poniente sale en lotes rectangulares idénticos y el mismo módulo sirve para ambos polígonos.</li>
<li>Los dos se ensanchan hacia el norte: A pasa de unos 26 m en la punta sur a unos 120 m, y B de unos 40 m a unos 117 m. El lado oriente es el bulevar, en diagonal, y ahí siempre resultan lotes ajustados o remanentes.</li>
<li>Los accesos están en la esquina sur-oriente, en el punto más angosto de cada polígono. Por eso la vialidad interna nace como una sola calle y se ramifica donde ya hay ancho.</li></ul></div>
<div class="stack"><h3>Mejor forma de acceso</h3>
<ol><li>Entrar por el círculo con un tramo de transición corto (unos 25 m en A y 12 m en B) que se alinea con la espina sin salir del polígono. Ese tramo no lleva lotes de frente. Es el lugar natural para la caseta, la pluma y el área verde de acceso.</li>
<li>Correr la espina paralela a la colindancia poniente, a 35.5 m del lindero con lote de 20 × 30, o a 45.5 m con lote de 15 × 40. En A coincide casi con el acceso y en B queda a menos de 3 m del círculo, así que la transición es mínima.</li>
<li>Cerrar al norte con una calle transversal paralela al lindero norte, a la misma distancia, para que la fila norte también salga estandarizada.</li>
<li>Agregar transversales intermedias solo donde el fondo entre la espina y el bulevar pase de unos 45 m. En B eso ocurre a partir de u ≈ 95 m.</li></ol></div>
</div>
<div class="verdict"><p class="eyebrow">Recomendación</p>
<h3>Híbrido: Tipo 1 en el polígono A y Tipo 2 en el polígono B</h3>
<p>Este híbrido da <strong>{hy['n']:.0f} lotes</strong>, igual que el máximo de los tres esquemas puros. Requiere {f(hy['road'])} m² de vialidad (16% menos que el Tipo 1) y solo dos retornos. Además tiene {hy['near']:.0f} lotes de 600 m² ±5%, la misma cifra que el Tipo 2, pero con un lote más. En A el lote 20 × 30 se adapta mejor a la punta angosta. En B el lote 15 × 40 aprovecha el ancho de 90 a 117 m con una sola calle.</p>
<p>El circuito (Tipo 3) solo convendría si el municipio prohíbe calles cerradas o exige circulación continua para el camión de basura. Para que el anillo tenga lotes por los dos lados se necesitan unos 142 m de ancho, y estos polígonos no los tienen.</p></div>
<div class="stack"><h3>Supuestos que conviene validar</h3>
<ul><li>Retorno circular con derecho de vía de 24 m de diámetro y arroyo de 21 m. Confírmalo con el reglamento de construcción y fraccionamientos de tu municipio.</li>
<li>Las áreas verdes que aparecen son remanentes sin frente útil. Antes de cerrar, compara su suma con el porcentaje de donación que exija la ley estatal; suele estar entre 10 y 15%.</li>
<li>Los lotes de la punta sur de A y del extremo de cada retorno tienen frentes irregulares. Se pueden fusionar o reasignar a amenidades sin cambiar el esquema.</li>
<li>Los DXF están en las mismas coordenadas que el dibujo original, así que se pueden insertar en 0,0,0 sobre <code>lotificaciones.dwg</code>. Las capas son LOT-LOTES, LOT-LOTES-IRREG, VIAL-ARROYO, VIAL-BANQUETA, VIAL-EJE, AREA-VERDE, LOT-TEXTO y POLIGONO.</li></ul></div>
</section>
</div>"""
open('lotificacion.html','w').write(html)
print(len(html), hy)
