from datetime import datetime, timezone

import pytest

from ingestion.versionamento import (
    classificar_versao,
    extrair_ultimo_mes,
    identificar_serie,
    ids_orfaos_antigos,
    ids_reconciliacao,
    ids_transicao_anual,
    periodo_historico,
    proximo_mes,
)


def registro(id, serie, periodo, mes=None, tipo="CVLI", data="2026-11-01T00:00:00+00:00"):
    return {
        "id": id, "tipo_crime": tipo, "serie": serie,
        "periodo_dados": periodo, "ultimo_mes": mes,
        "data_coleta": data, "atualizado_em": data,
    }


def test_identifica_serie_historica_e_periodo():
    nome = "CVLI_2009-a-2025.xlsx"
    assert identificar_serie(nome) == "historica"
    assert periodo_historico(nome) == "2009-2025"


def test_identifica_serie_corrente_e_ultimo_mes():
    assert identificar_serie("CVLI_Outubro.xlsx") == "corrente"
    assert extrair_ultimo_mes("CVLI_Outubro.xlsx") == 10


def test_proximo_mes_considera_virada_do_ano():
    assert proximo_mes(2026, 12) == (2027, 1)


def test_classifica_acrescimo_mensal():
    novo = {"tipo_crime": "CVLI", "serie": "corrente", "periodo_dados": "2026", "ultimo_mes": 10}
    anterior = registro(1, "corrente", "2026", 9)
    resultado = classificar_versao(novo, [anterior])
    assert resultado["tipo_atualizacao"] == "acrescimo"
    assert resultado["ids_substituir"] == [1]


def test_classifica_correcao_mensal():
    novo = {"tipo_crime": "CVLI", "serie": "corrente", "periodo_dados": "2026", "ultimo_mes": 9}
    anterior = registro(1, "corrente", "2026", 9)
    assert classificar_versao(novo, [anterior])["tipo_atualizacao"] == "correcao"


def test_salva_versao_anterior_em_salto_mensal():
    novo = {"tipo_crime": "CVLI", "serie": "corrente", "periodo_dados": "2026", "ultimo_mes": 11}
    anterior = registro(1, "corrente", "2026", 9)
    resultado = classificar_versao(novo, [anterior])
    assert resultado["ids_substituir"] == []
    assert resultado["avisos"]


def test_historico_e_corrente_nao_sao_comparados():
    novo = {"tipo_crime": "CVLI", "serie": "corrente", "periodo_dados": "2026", "ultimo_mes": 1}
    historico = registro(1, "historica", "2009-2025")
    assert classificar_versao(novo, [historico])["ids_substituir"] == []


def test_classifica_acrescimo_historico():
    novo = {"tipo_crime": "CVLI", "serie": "historica", "periodo_dados": "2009-2026"}
    anterior = registro(1, "historica", "2009-2025")
    resultado = classificar_versao(novo, [anterior])
    assert resultado["tipo_atualizacao"] == "acrescimo"
    assert resultado["ids_substituir"] == [1]


def test_transicao_anual_so_remove_corrente_coberta():
    registros = [
        registro(1, "corrente", "2026", 12),
        registro(2, "corrente", "2027", 1),
        registro(3, "historica", "2009-2026"),
    ]
    assert ids_transicao_anual(registros) == [1]


def test_purga_seleciona_somente_orfaos_antigos():
    agora = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    registros = [
        registro(1, "corrente", None, data="2026-11-18T01:00:00+00:00"),
        registro(2, "corrente", None, data="2026-11-18T11:00:00+00:00"),
        registro(3, "corrente", "2026", 10, data="2026-11-17T00:00:00+00:00"),
    ]
    assert ids_orfaos_antigos(registros, agora=agora) == [1]


def test_reconciliacao_remove_versao_anterior_da_mesma_serie():
    registros = [
        registro(1, "corrente", "2026", 9),
        registro(2, "corrente", "2026", 10, data="2026-11-18T10:00:00+00:00"),
    ]
    assert ids_reconciliacao(registros) == [1]


def test_reconciliacao_preserva_salto_mensal():
    registros = [
        registro(1, "corrente", "2026", 8),
        registro(2, "corrente", "2026", 10, data="2026-11-18T10:00:00+00:00"),
    ]
    assert ids_reconciliacao(registros) == []


def test_reconciliacao_historica_remove_versao_anterior_em_sequencia():
    registros = [
        registro(1, "historica", "2009-2024"),
        registro(2, "historica", "2009-2025", data="2026-11-18T10:00:00+00:00"),
    ]
    assert ids_reconciliacao(registros) == [1]


def test_reconciliacao_preserva_intervalo_historico_inesperado():
    registros = [
        registro(1, "historica", "2009-2024"),
        registro(2, "historica", "2010-2025", data="2026-11-18T10:00:00+00:00"),
    ]
    assert ids_reconciliacao(registros) == []
