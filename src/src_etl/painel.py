"""Painel único: combina relatório-base + indicadores em um HTML com abas.

Tema no padrão de cores do **Horizon UI** (roxo/indigo, fundo navy-claro, cards
arredondados com sombra suave; dark mode navy). Abas em CSS puro (sem JS).

Reaproveita os blocos de `relatorio` e `indicadores`; sobrepõe a paleta
categórica pela do Horizon.

CLI:  src-etl-painel --acoes data/serra --part data/participacoes \
                     --consolidado data/serra_consolidado.json --out painel.html
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from . import relatorio
from .formados import agregar_formados, blocos_formados
from .indicadores import agregar_indicadores, blocos_indicadores
from .rede import agregar_rede, blocos_rede
from .relatorio import (
    _carregar_acoes,
    _carregar_participacoes,
    agregar,
    blocos_relatorio,
)

# paleta categórica no espírito do Horizon UI (roxo/indigo + apoio)
HORIZON_CAT = ["#4318FF", "#6AD2FF", "#01B574", "#FFB547", "#EE5D50",
               "#7551FF", "#39B8FF", "#FFCF5C"]

HORIZON_CSS = """
:root{
  color-scheme:light;
  --plane:#f4f7fe; --surface-1:#ffffff;
  --text-primary:#2b3674; --text-secondary:#707eae; --muted:#a3aed0;
  --grid:#e9edf7; --border:#e0e5f2; --series-1:#4318ff;
  --radius:20px; --shadow:0 18px 40px rgba(112,144,176,.12);
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
  color-scheme:dark;
  --plane:#0b1437; --surface-1:#111c44;
  --text-primary:#ffffff; --text-secondary:#a3aed0; --muted:#8f9bba;
  --grid:#ffffff14; --border:#ffffff1f; --series-1:#7551ff;
  --shadow:0 18px 40px rgba(0,0,0,.35);
}}
:root[data-theme=dark]{
  color-scheme:dark;
  --plane:#0b1437; --surface-1:#111c44;
  --text-primary:#ffffff; --text-secondary:#a3aed0; --muted:#8f9bba;
  --grid:#ffffff14; --border:#ffffff1f; --series-1:#7551ff;
  --shadow:0 18px 40px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--text-primary);
font-family:"DM Sans",system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.45}
.wrap{max-width:1040px;margin:0 auto;padding:32px 20px 64px}
header h1{margin:0 0 4px;font-size:1.7rem;letter-spacing:-.02em}
header .sub{color:var(--text-secondary);margin:0 0 8px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin:20px 0 8px}
.tile{background:var(--surface-1);border:1px solid var(--border);border-radius:var(--radius);
padding:18px 20px;box-shadow:var(--shadow)}
.tile-val{font-size:2rem;font-weight:700;letter-spacing:-.03em}
.tile-lbl{color:var(--text-secondary);font-size:.85rem;margin-top:2px;font-weight:600}
.tile-sub{color:var(--muted);font-size:.75rem;margin-top:4px}
section{margin-top:26px}h2{font-size:1.12rem;margin:0 0 2px;letter-spacing:-.01em}
.sec-desc{color:var(--text-secondary);font-size:.85rem;margin:0 0 10px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:var(--radius);
padding:20px;overflow-x:auto;box-shadow:var(--shadow)}
.lbl{fill:var(--text-secondary);font-size:12px}
.val{fill:var(--text-primary);font-size:12px;font-weight:700}
.vazio{color:var(--muted);margin:0;font-size:.9rem}
.donut-wrap{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.donut-num{fill:var(--text-primary);font-size:26px;font-weight:700}
.donut-cap{fill:var(--muted);font-size:11px}
.leg{display:flex;flex-direction:column;gap:6px;min-width:220px}
.leg-item{display:flex;align-items:center;gap:8px;font-size:.85rem}
.sw{width:12px;height:12px;border-radius:4px;flex:none}
.leg-nome{flex:1}.leg-val{color:var(--text-secondary);font-variant-numeric:tabular-nums}
footer{margin-top:36px;color:var(--muted);font-size:.78rem;border-top:1px solid var(--border);padding-top:12px}
.pii{background:color-mix(in srgb,var(--series-1) 8%,transparent);border:1px solid var(--border);
border-radius:14px;padding:10px 14px;font-size:.82rem;color:var(--text-secondary);margin-top:16px}
.lista{max-height:360px;overflow-y:auto;display:flex;flex-direction:column;gap:1px}
.li{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;
padding:8px 4px;border-bottom:1px solid var(--grid);font-size:.85rem}
.li4{grid-template-columns:1fr auto auto auto}
.li-coord{color:var(--text-secondary);font-size:.78rem;white-space:nowrap}
.li-tit{color:var(--text-primary)}
.li-tipo{color:var(--muted);font-size:.75rem;border:1px solid var(--border);border-radius:20px;padding:1px 8px}
.li-proc{color:var(--text-secondary);font-variant-numeric:tabular-nums;font-size:.8rem}
.net-lbl{fill:var(--text-secondary);font-size:11px;font-weight:600}
.topnav{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 2px}
.topnav a{padding:9px 16px;border-radius:14px;font-weight:700;font-size:.85rem;text-decoration:none;
color:var(--text-secondary);background:var(--surface-1);border:1px solid var(--border);box-shadow:var(--shadow)}
.topnav a:hover,.topnav a.on{background:var(--series-1);color:#fff;border-color:var(--series-1)}
.explica{margin-top:12px;border-top:1px dashed var(--grid);padding-top:8px}
.explica summary{cursor:pointer;color:var(--series-1);font-size:.82rem;font-weight:700}
.explica p{color:var(--text-secondary);font-size:.84rem;margin:8px 0 0;max-width:70ch}
.nota{background:#fff4e0;color:#8a5a00;border:1px solid #ffd98a;border-radius:12px;
padding:10px 14px;font-size:.85rem;font-weight:600;margin:14px 0}
:root[data-theme=dark] .nota,@media (prefers-color-scheme:dark){.nota{background:#3a2e10;color:#ffcf5c;border-color:#5c4a1a}}
/* abas (CSS puro) */
.tabs>input{position:absolute;opacity:0;pointer-events:none}
.tabbar{display:flex;gap:10px;margin:22px 0 4px;flex-wrap:wrap}
.tabbar label{padding:11px 20px;border-radius:16px;cursor:pointer;font-weight:700;font-size:.9rem;
color:var(--text-secondary);background:var(--surface-1);border:1px solid var(--border);
box-shadow:var(--shadow);transition:all .15s}
.tabbar label:hover{color:var(--text-primary)}
#tab1:checked~.tabbar label[for=tab1],
#tab2:checked~.tabbar label[for=tab2],
#tab3:checked~.tabbar label[for=tab3],
#tab4:checked~.tabbar label[for=tab4]{background:var(--series-1);color:#fff;border-color:var(--series-1)}
.panel{display:none}
#tab1:checked~.p1{display:block}
#tab2:checked~.p2{display:block}
#tab3:checked~.p3{display:block}
#tab4:checked~.p4{display:block}
"""


def gerar_painel(
    acoes_dir: str | Path = "data/serra",
    part_dir: str | Path = "data/participacoes",
    consolidado_json: str | Path = "data/serra_consolidado.json",
    out_html: str | Path = "painel.html",
    *,
    titulo: str = "SRC/Ifes — Campus Serra",
    nota: str = "",
    formandos_dir: str | Path = "data/formandos",
) -> Path:
    # aplica a paleta categórica do Horizon aos donuts (rebind do global usado por _donut)
    original = relatorio._CAT
    relatorio._CAT = HORIZON_CAT
    try:
        a_rel = agregar(_carregar_acoes(acoes_dir), _carregar_participacoes(part_dir))
        t1, s1 = blocos_relatorio(a_rel)
        consolidado = json.loads(Path(consolidado_json).read_text(encoding="utf-8"))
        a_ind = agregar_indicadores(consolidado)
        t2, s2 = blocos_indicadores(a_ind)
        a_net = agregar_rede(consolidado)
        t3, s3 = blocos_rede(a_net)
        try:  # aba Formados (opcional — depende das planilhas)
            a_form = agregar_formados(consolidado, formandos_dir)
            t4, s4 = blocos_formados(a_form)
        except Exception:
            a_form, t4, s4 = None, "", ""
    finally:
        relatorio._CAT = original

    banner = (f'<div class="nota">{escape(nota)}</div>' if nota else "")
    topnav = ('<div class="topnav">'
              '<a class="on" href="index.html">Painel</a>'
              '<a href="acoes/index.html">Ações</a>'
              '<a href="busca.html">Buscar coordenador</a>'
              '<a href="sem-participacao.html">Sem participações</a>'
              '<a href="pendencias-relatorio.html">Pendências de relatório</a></div>')
    corpo = f"""<div class="wrap">
<header><h1>{escape(titulo)}</h1>
<p class="sub">Painel analítico — visão geral, indicadores e rede de colaboração</p></header>
{topnav}
{banner}
<div class="tabs">
  <input type="radio" name="tab" id="tab1" checked>
  <input type="radio" name="tab" id="tab2">
  <input type="radio" name="tab" id="tab3">
  <input type="radio" name="tab" id="tab4">
  <div class="tabbar"><label for="tab1">Visão geral</label><label for="tab2">Indicadores</label><label for="tab3">Rede &amp; programas</label>{('<label for="tab4">Formados na Extensão</label>' if t4 else '')}</div>
  <div class="panel p1"><div class="tiles">{t1}</div>{s1}</div>
  <div class="panel p2"><div class="tiles">{t2}</div>{s2}</div>
  <div class="panel p3"><div class="tiles">{t3}</div>{s3}</div>
  {(f'<div class="panel p4"><div class="tiles">{t4}</div>{s4}<div class="pii">Cruzamento por nome (planilhas de formados não têm CPF): pode haver homônimos/variações. Só contagens agregadas — sem nomes.</div></div>' if t4 else '')}
</div>
<div class="pii">Painel <b>agregado</b>: sem nomes de alunos, CPF ou e-mail. Coordenadores(as)
são dado público do sistema; membros de equipe entram só como elo, nunca exibidos.</div>
<footer>Gerado por src-etl · {a_rel['n_acoes']} ações · {a_ind['alunos_unicos']} alunos únicos · {a_net['n_programas']} programas.</footer>
</div>"""

    doc = (f"<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{escape(titulo)} — Painel</title><style>{HORIZON_CSS}</style></head>"
           f"<body>{corpo}</body></html>")
    out = Path(out_html)
    out.write_text(doc, encoding="utf-8")
    return out


def _cli(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="src-etl-painel",
                                 description="Painel combinado (relatório + indicadores), tema Horizon.")
    ap.add_argument("--acoes", default="data/serra")
    ap.add_argument("--part", default="data/participacoes")
    ap.add_argument("--consolidado", default="data/serra_consolidado.json")
    ap.add_argument("--out", default="painel.html")
    ap.add_argument("--titulo", default="SRC/Ifes — Campus Serra")
    args = ap.parse_args(argv)
    p = gerar_painel(args.acoes, args.part, args.consolidado, args.out, titulo=args.titulo)
    print(f"Painel gerado: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
