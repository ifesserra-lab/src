"""Indicadores de impacto (aba "Impacto" do painel).

Dez indicadores derivados do consolidado, todos agregados (sem PII):
  1. Horas-aluno (C.H × participações) — esforço formativo
  2. Funil público -> equipe — quem foi atendido e virou executor
  3. Gap de certificação — aprovados sem certificado (pendência acionável)
  4. Perfil etário do público — faixas (usa Nasc. só para faixa, nunca exibe data)
  5. Concentração de alcance — CR5 / CR10 / HHI
  6. Renovação da equipe — % de pessoas novas por ano
  7. Sazonalidade — atividades por mês de início
  8. Participação externa — % de convidados na equipe
  9. Duração das atividades — faixas (pontual / curta / longa)
 10. Ações multi-ano — atividades em ≥ 2 anos (continuidade)
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime

from .relatorio import _barras, _donut, _secao, _secao_par, _tile

_MESES = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
          "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _data(s) -> datetime | None:
    try:
        return datetime.strptime((s or "").strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return None


def _num(s) -> float:
    try:
        return float((s or "").replace(",", ".").strip())
    except (ValueError, AttributeError):
        return 0.0


def agregar_impacto(consolidado: dict) -> dict:
    acoes = consolidado.get("acoes", [])

    horas_aluno = 0.0
    ch_por_tipo: Counter = Counter()
    total_pub = 0
    prim_pub: dict[str, datetime] = {}
    prim_eq: dict[str, datetime] = {}
    faixas_idade: Counter = Counter()
    gap_cert = 0
    gap_coord: Counter = Counter()
    pub_por_acao: list[int] = []
    eq_por_ano: dict[int, set] = defaultdict(set)
    vinc: Counter = Counter()
    meses: Counter = Counter()
    duracoes: list[int] = []
    multi_ano = 0
    ativas = 0

    for a in acoes:
        tipo = a.get("Tipo ação") or "—"
        coord = (a.get("Coordenador(a)") or "—").strip() or "—"
        npub = 0
        anos_ativ: set[int] = set()
        dur_por_ativ: dict[str, int] = {}
        mes_por_ativ: dict[str, int] = {}
        for p in a.get("participacoes", []):
            ini = _data(p.get("Início"))
            aid = p.get("atividade_id")
            if aid and ini:
                anos_ativ.add(ini.year)
                mes_por_ativ.setdefault(aid, ini.month)
                fim = _data(p.get("Término"))
                if fim and aid not in dur_por_ativ:
                    dias = (fim - ini).days
                    if 0 <= dias < 3700:
                        dur_por_ativ[aid] = dias
            if p.get("tipo", "").startswith("Público"):
                npub += 1
                total_pub += 1
                horas_aluno += _num(p.get("C.H"))
                ch_por_tipo[tipo] += _num(p.get("C.H"))
                cpf = p.get("CPF")
                if cpf and ini and (cpf not in prim_pub or ini < prim_pub[cpf]):
                    prim_pub[cpf] = ini
                nasc = _data(p.get("Nasc."))
                if nasc and ini:
                    idade = (ini - nasc).days / 365.25
                    faixas_idade[
                        "menor de 15" if idade < 15 else "15–17" if idade < 18
                        else "18–24" if idade < 25 else "25–34" if idade < 35
                        else "35–59" if idade < 60 else "60+"] += 1
                if (p.get("Situação") or "").strip().upper() == "APROVADO":
                    c = (p.get("Certificado") or "").strip().lower()
                    if not c or c in ("não", "nao", "-"):
                        gap_cert += 1
                        gap_coord[coord] += 1
            else:
                cpf = p.get("CPF")
                if cpf and ini and (cpf not in prim_eq or ini < prim_eq[cpf]):
                    prim_eq[cpf] = ini
                vinc[(p.get("Vínculo") or "—").strip() or "—"] += 1
                if aid and ini:
                    eq_por_ano[ini.year].add(cpf)
        if npub:
            pub_por_acao.append(npub)
        for m in mes_por_ativ.values():
            meses[m] += 1
        duracoes.extend(dur_por_ativ.values())
        if a.get("participacoes"):
            ativas += 1
            if len({y for y in anos_ativ}) >= 2:
                multi_ano += 1

    # 2. funil
    conv = [c for c in prim_pub if c in prim_eq and prim_eq[c] > prim_pub[c]]
    tempos = [(prim_eq[c] - prim_pub[c]).days for c in conv]

    # 5. concentração
    pub_sorted = sorted(pub_por_acao, reverse=True)
    tot = sum(pub_sorted) or 1
    cr5 = sum(pub_sorted[:5]) / tot * 100
    cr10 = sum(pub_sorted[:10]) / tot * 100
    hhi = sum((x / tot) ** 2 for x in pub_sorted) * 10000

    # 6. renovação
    renov = []
    vistos: set = set()
    for y in sorted(eq_por_ano):
        if 2013 <= y <= 2026:
            novos = len(eq_por_ano[y] - vistos)
            renov.append((str(y), round(novos / len(eq_por_ano[y]) * 100)))
            vistos |= eq_por_ano[y]

    # 8. externos
    eq_total = sum(vinc.values()) or 1
    pct_ext = vinc.get("Convidado", 0) / eq_total * 100

    # 9. duração em faixas
    faixa_dur = Counter()
    for x in duracoes:
        faixa_dur["Pontual (≤1 dia)" if x <= 1 else "Curta (2–30d)" if x <= 30
                  else "Média (31–180d)" if x <= 180 else "Longa (>180d)"] += 1
    ordem_dur = ["Pontual (≤1 dia)", "Curta (2–30d)", "Média (31–180d)", "Longa (>180d)"]

    ordem_idade = ["menor de 15", "15–17", "18–24", "25–34", "35–59", "60+"]

    return {
        "horas_aluno": round(horas_aluno),
        "horas_por_part": (horas_aluno / total_pub) if total_pub else 0,
        "ch_por_tipo": [(t, round(h)) for t, h in ch_por_tipo.most_common()],
        "funil_conv": len(conv),
        "funil_pct": (len(conv) / len(prim_pub) * 100) if prim_pub else 0,
        "funil_dias": round(statistics.median(tempos)) if tempos else 0,
        "gap_cert": gap_cert,
        "gap_coord": gap_coord.most_common(8),
        "idade": [(k, faixas_idade[k]) for k in ordem_idade if faixas_idade[k]],
        "cr5": round(cr5), "cr10": round(cr10), "hhi": round(hhi),
        "renovacao": renov,
        "vinculo": vinc.most_common(),
        "pct_externo": pct_ext,
        "meses": [(_MESES[m], meses.get(m, 0)) for m in range(1, 13)],
        "duracao": [(k, faixa_dur[k]) for k in ordem_dur if faixa_dur[k]],
        "multi_ano": multi_ano, "ativas": ativas,
    }


def blocos_impacto(a: dict) -> tuple[str, str]:
    tiles = "".join([
        _tile(f'{a["horas_aluno"]:,}'.replace(",", "."), "Horas-aluno",
              f'{a["horas_por_part"]:.0f}h por participação'),
        _tile(a["funil_conv"], "Público → equipe", f'{a["funil_pct"]:.1f}% viraram executor'),
        _tile(a["gap_cert"], "Aprovados sem certificado", "pendência acionável"),
        _tile(f'{a["pct_externo"]:.0f}%', "Equipe externa", "convidados/parcerias"),
        _tile(f'{a["cr10"]}%', "Top-10 do alcance", f'HHI {a["hhi"]}'),
    ])
    secoes = [
        _secao("Horas-aluno por tipo de ação", _barras(a["ch_por_tipo"], unidade="h"),
               "Esforço formativo = carga horária × nº de participações de público.",
               explica="Soma, por tipo de ação, das horas de formação entregues: para cada "
               "participação de público conta a carga horária (C.H) da atividade. É a métrica "
               "de esforço/impacto usada em relatórios de extensão — mede volume de formação "
               "efetivamente ofertado, não apenas número de pessoas."),
        _secao("Perfil etário do público", _donut(a["idade"]),
               "Faixas etárias das participações de público-alvo.",
               explica="Distribui as participações por faixa de idade (calculada da data de "
               "nascimento na data de início da atividade; a data em si nunca é exibida). "
               "Mostra QUEM a extensão alcança — predominância de jovens (15–24) indica forte "
               "conexão com o público estudantil e pré-universitário."),
        _secao("Funil de engajamento (público → equipe)",
               _barras([("Público único", len(a.get("idade")) and 0 or 0)]) if False else
               _barras([("Viraram equipe", a["funil_conv"])], unidade=" pessoas"),
               f'{a["funil_conv"]} pessoas ({a["funil_pct"]:.1f}%) foram atendidas e depois '
               f'entraram numa equipe — mediana de {a["funil_dias"]} dias.',
               explica="Conta pessoas (por CPF, nunca exibido) cuja primeira participação foi "
               "como público-alvo e que MAIS TARDE apareceram na equipe de execução de alguma "
               "ação. É o 'ciclo virtuoso' da extensão: quem é atendido depois vira protagonista. "
               "O tempo mediano indica quanto leva essa transição."),
        _secao("Gap de certificação por coordenador(a)", _barras(a["gap_coord"]),
               f'{a["gap_cert"]} participações APROVADAS sem certificado emitido.',
               explica="Participantes com situação APROVADO mas sem certificado registrado no "
               "SRC — têm direito e não receberam. Agrupado por coordenador(a) responsável, é "
               "uma lista de pendência acionável: basta emitir. Difere da taxa geral de "
               "certificação por isolar só os casos que já deveriam estar certificados."),
        _secao("Renovação da equipe por ano (% de pessoas novas)",
               _barras(a["renovacao"], unidade="%"),
               "Fração de membros de equipe que são novos (nunca haviam atuado antes).",
               explica="A cada ano, quantos % das pessoas na equipe de execução nunca tinham "
               "participado antes. Alto = oxigenação/entrada de novos extensionistas; baixo = "
               "dependência de um núcleo veterano. Ajuda a avaliar sustentabilidade da força de "
               "trabalho da extensão ao longo do tempo."),
        _secao("Sazonalidade — atividades por mês de início", _barras(a["meses"]),
               "Quando as atividades começam ao longo do ano.",
               explica="Distribui as atividades pelo mês de início. Revela o ritmo do calendário "
               "de extensão — concentração no 2º semestre (agosto–outubro) indica alinhamento "
               "com o calendário letivo. Útil para planejar editais, bolsas e infraestrutura nos "
               "períodos de pico."),
        _secao_par(
            "Duração das atividades e vínculo da equipe",
            ("Duração das atividades", _donut(a["duracao"]),
             "Distribuição das atividades por tempo de execução.",
             "Classifica cada atividade pelo intervalo início→término: pontual (evento "
             "de 1 dia), curta (até 1 mês), média (1–6 meses) ou longa (>6 meses). Mostra o "
             "mix entre ações pontuais de grande alcance e trabalho contínuo de proximidade."),
            ("Vínculo da equipe executora", _donut(a["vinculo"]),
             "Origem institucional de quem executa (aluno, servidor, convidado externo).",
             "Perfil de vínculo dos membros de equipe: Aluno (discente), Servidor "
             "(docente/técnico do Ifes) e Convidado (externo — parceiros, sociedade, empresas). "
             "A fatia de convidados mede o grau de abertura da extensão a atores de fora da "
             "instituição.")),
    ]
    # nota de continuidade (multi-ano) + concentração
    secoes.append(_secao(
        "Continuidade e concentração",
        f'<p class="vazio" style="font-size:14px">'
        f'<b>{a["multi_ano"]}</b> de {a["ativas"]} ações ativas têm atividades em '
        f'<b>2 anos ou mais</b> (institucionalização). '
        f'As <b>5 maiores</b> ações concentram <b>{a["cr5"]}%</b> do público e as '
        f'<b>10 maiores</b>, <b>{a["cr10"]}%</b> (HHI {a["hhi"]} — '
        f'{"concentração alta" if a["hhi"]>2500 else "concentração moderada" if a["hhi"]>1500 else "alcance distribuído"}).</p>',
        explica="Continuidade: ações que rodam em vários anos tendem a estar institucionalizadas "
        "(programas, laboratórios). Concentração: CR5/CR10 = quanto do público está nas maiores "
        "ações; HHI (índice Herfindahl-Hirschman) resume a concentração — abaixo de 1500 o "
        "alcance é bem distribuído entre muitas ações."))
    return tiles, "".join(secoes)
