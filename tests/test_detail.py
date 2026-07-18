"""Testa o parser de detalhe contra HTML fixo (sem rede)."""

from src_etl.etl.detail import parse_detalhe
from src_etl.etl.models import Acao

HTML = """
<table><tbody>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Processo nº</label></td>
  <td class="ui-panelgrid-cell">23158.001712/2025-14</td>
</tr>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Natureza</label></td>
  <td class="ui-panelgrid-cell">Extensão</td>
</tr>
<tr>
  <td class="ui-panelgrid-cell"><label class="ui-outputlabel">Título ação</label></td>
  <td class="ui-panelgrid-cell">Projeto X</td>
</tr>
</tbody></table>
"""


def test_parse_detalhe_pares():
    dados = parse_detalhe(HTML)
    assert dados["Processo nº"] == "23158.001712/2025-14"
    assert dados["Natureza"] == "Extensão"
    assert dados["Título ação"] == "Projeto X"


def test_acao_from_labels_aliases():
    dados = parse_detalhe(HTML)
    acao = Acao.from_labels("5646", dados, campus="Serra")
    assert acao.acao_id == "5646"
    assert acao.campus == "Serra"
    assert acao.processo == "23158.001712/2025-14"
    assert acao.natureza == "Extensão"
    assert acao.titulo == "Projeto X"
