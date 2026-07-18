"""A trava de PII do export deve bloquear CPF, e-mail e chaves proibidas."""

import pytest

from src_etl.dashboard.export_json import auditar_pii


def test_texto_limpo_passa():
    auditar_pii('{"nome": "Fulano de Tal", "funcao": "BOLSISTA", "ano": "2024"}')


def test_bloqueia_cpf_formatado():
    with pytest.raises(RuntimeError, match="CPF"):
        auditar_pii('{"doc": "123.456.789-01"}')


def test_bloqueia_cpf_cru_11_digitos():
    with pytest.raises(RuntimeError, match="11 dígitos"):
        auditar_pii('{"doc": "12345678901"}')


def test_bloqueia_email():
    with pytest.raises(RuntimeError, match="e-mail"):
        auditar_pii('{"contato": "aluno@example.com"}')


def test_bloqueia_chave_proibida():
    with pytest.raises(RuntimeError, match="chave"):
        auditar_pii('{"CPF": "oculto"}')
