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
  --plane:#fbfbfc; --surface-1:#ffffff;
  --text-primary:#171c2e; --text-secondary:#5a6072; --muted:#9298a8;
  --grid:#eceef2; --border:#e4e6ec; --series-1:#4f46e5;
  --radius:12px; --shadow:none;
}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
  color-scheme:dark;
  --plane:#0e1015; --surface-1:#15181f;
  --text-primary:#e8eaf2; --text-secondary:#9aa0b2; --muted:#6b7284;
  --grid:#232733; --border:#262b38; --series-1:#8b93ff;
}}
:root[data-theme=dark]{
  color-scheme:dark;
  --plane:#0e1015; --surface-1:#15181f;
  --text-primary:#e8eaf2; --text-secondary:#9aa0b2; --muted:#6b7284;
  --grid:#232733; --border:#262b38; --series-1:#8b93ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--plane);color:var(--text-primary);
font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.5;
-webkit-font-smoothing:antialiased}
/* ---- shell minimalista: topbar + conteúdo ---- */
.topbar{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--plane) 82%,transparent);
backdrop-filter:blur(10px);border-bottom:1px solid var(--border)}
.topbar-in{max-width:1080px;margin:0 auto;padding:0 24px;height:58px;
display:flex;align-items:center;gap:28px}
.brand{font-weight:700;font-size:.95rem;letter-spacing:-.01em;color:var(--text-primary);
text-decoration:none;white-space:nowrap}
.brand small{color:var(--muted);font-weight:500;margin-left:8px;font-size:.78rem}
.snav{display:flex;gap:4px;overflow-x:auto;flex:1}
.snav a{display:flex;align-items:center;gap:7px;padding:7px 12px;border-radius:8px;
text-decoration:none;color:var(--text-secondary);font-weight:500;font-size:.85rem;white-space:nowrap}
.snav a svg{width:15px;height:15px;flex:none;stroke:currentColor;fill:none;stroke-width:2;
stroke-linecap:round;stroke-linejoin:round}
.snav a:hover{color:var(--text-primary);background:var(--grid)}
.snav a.on{color:var(--series-1);background:color-mix(in srgb,var(--series-1) 9%,transparent)}
.main{min-width:0}
.wrap{max-width:1080px;margin:0 auto;padding:36px 24px 72px}
.crumb{color:var(--muted);font-size:.78rem;margin:0 0 4px;letter-spacing:.02em}
.crumb b{color:var(--text-secondary);font-weight:600}
header h1{margin:0 0 6px;font-size:1.75rem;letter-spacing:-.03em;line-height:1.15;text-wrap:balance}
header .sub{color:var(--text-secondary);margin:0 0 8px;font-size:.95rem;max-width:70ch}
@media (max-width:720px){.topbar-in{padding:0 14px;gap:14px}.brand small{display:none}}
/* hero (home de busca) */
.wrap-hero{padding-top:9vh;text-align:center}
.hero h1{font-size:2.3rem;letter-spacing:-.035em;margin:0 0 8px}
.hero .sub{margin:0 auto 8px;max-width:60ch}
.wrap-hero .busca{max-width:640px;margin:22px auto 0;display:block;font-size:1.05rem;
padding:16px 20px;text-align:left}
.wrap-hero #res{text-align:left;max-width:860px;margin:0 auto}
.wrap-hero #res .vazio{text-align:center;margin-top:10px}
.chips{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:14px}
.chips button{border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary);
border-radius:20px;padding:6px 14px;font-size:.82rem;cursor:pointer;font-family:inherit}
.chips button:hover{color:var(--series-1);border-color:var(--series-1)}
/* stat-row minimalista: números grandes separados por hairlines */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0;margin:24px 0 8px;
border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;background:var(--surface-1)}
.tile{padding:18px 20px;border-right:1px solid var(--grid)}
.tile:last-child{border-right:0}
.tile-val{font-size:1.85rem;font-weight:650;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.tile-lbl{color:var(--text-secondary);font-size:.78rem;margin-top:2px;font-weight:500;
text-transform:uppercase;letter-spacing:.05em}
.tile-sub{color:var(--muted);font-size:.75rem;margin-top:4px}
section{margin-top:34px}h2{font-size:1.05rem;margin:0 0 2px;letter-spacing:-.015em;font-weight:650}
.sec-desc{color:var(--text-secondary);font-size:.85rem;margin:0 0 12px}
.card{background:var(--surface-1);border:1px solid var(--border);border-radius:var(--radius);
padding:20px;overflow-x:auto}
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
.explica{margin-top:12px;border-top:1px solid var(--grid);padding-top:8px}
.explica summary{cursor:pointer;color:var(--series-1);font-size:.82rem;font-weight:600}
.explica p{color:var(--text-secondary);font-size:.84rem;margin:8px 0 0;max-width:70ch}
.nota{background:color-mix(in srgb,#eda100 10%,var(--surface-1));color:var(--text-primary);
border:1px solid color-mix(in srgb,#eda100 35%,var(--border));border-radius:10px;
padding:10px 14px;font-size:.85rem;font-weight:500;margin:14px 0}
/* abas: segmented control minimalista (CSS puro) */
.tabs>input{position:absolute;opacity:0;pointer-events:none}
.tabbar{display:inline-flex;gap:2px;margin:24px 0 4px;flex-wrap:wrap;background:var(--grid);
border-radius:10px;padding:3px}
.tabbar label{padding:8px 16px;border-radius:8px;cursor:pointer;font-weight:550;font-size:.85rem;
color:var(--text-secondary);transition:all .12s}
.tabbar label:hover{color:var(--text-primary)}
#tab1:checked~.tabbar label[for=tab1],
#tab2:checked~.tabbar label[for=tab2],
#tab3:checked~.tabbar label[for=tab3],
#tab4:checked~.tabbar label[for=tab4]{background:var(--surface-1);color:var(--text-primary);
box-shadow:0 1px 3px rgba(0,0,0,.08)}
.panel{display:none}
#tab1:checked~.p1{display:block}
#tab2:checked~.p2{display:block}
#tab3:checked~.p3{display:block}
#tab4:checked~.p4{display:block}
"""


_ICONES = {
    "painel": '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    "acoes": '<svg viewBox="0 0 24 24"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
    "busca": '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
    "sem": '<svg viewBox="0 0 24 24"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    "pend": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15h6"/><path d="M9 11h3"/></svg>',
    "pessoas": '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
}

_NAV_ITENS = [("index.html", "Buscar", "busca"), ("painel.html", "Painel", "painel"),
              ("acoes/index.html", "Ações", "acoes"),
              ("extensionistas/index.html", "Extensionistas", "pessoas"),
              ("sem-participacao.html", "Sem participações", "sem"),
              ("pendencias-relatorio.html", "Pendências", "pend")]


def montar_shell(base: str, ativo: str, crumb: str, titulo: str, sub: str, corpo: str,
                 hero: bool = False) -> str:
    """Layout minimalista: topbar (brand + menu) + conteúdo.

    hero=True centraliza o cabeçalho (usado na home de busca)."""
    links = "".join(
        f'<a href="{base}{href}" class="{"on" if href == ativo else ""}">'
        f'{_ICONES[ic]}<span>{escape(rotulo)}</span></a>'
        for href, rotulo, ic in _NAV_ITENS)
    cab = (f'<header class="hero"><h1>{escape(titulo)}</h1><p class="sub">{escape(sub)}</p></header>'
           if hero else
           f'<p class="crumb">Páginas / <b>{escape(crumb)}</b></p>'
           f'<header><h1>{escape(titulo)}</h1><p class="sub">{escape(sub)}</p></header>')
    return f"""<div class="topbar"><div class="topbar-in">
  <a class="brand" href="{base}index.html">SRC · Campus Serra<small>Extensão &amp; Ensino</small></a>
  <nav class="snav">{links}</nav>
</div></div>
<div class="main"><div class="wrap{' wrap-hero' if hero else ''}">
{cab}
{corpo}
</div></div>"""


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
    conteudo = f"""{banner}
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
<footer>Gerado por src-etl · {a_rel['n_acoes']} ações · {a_ind['alunos_unicos']} alunos únicos · {a_net['n_programas']} programas.</footer>"""
    corpo = montar_shell(
        "", "painel.html", "Painel", titulo,
        "Painel analítico — visão geral, indicadores e rede de colaboração", conteudo)

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
