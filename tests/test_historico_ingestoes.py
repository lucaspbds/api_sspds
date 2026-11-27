import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app

client = TestClient(app)

# TESTES DE INTEGRAÇÃO (Dependem do banco de dados real / Supabase)


def test_listar_historico_sem_filtros():
    response = client.get("/historico-ingestoes/")
    assert response.status_code == 200
    
    dados = response.json()
    # A resposta agora é um objeto paginado, não uma lista solta
    assert isinstance(dados, dict)
    assert "items" in dados
    assert "pagination" in dados
    assert isinstance(dados["items"], list)


def test_listar_historico_com_status_valido():
    response = client.get("/historico-ingestoes/?status=SUCESSO")

    if response.status_code == 200:
        dados = response.json()
        for item in dados["items"]:
            assert item["status"] == "SUCESSO"
    elif response.status_code == 404:
        assert (
            response.json()["detail"]
            == "Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos."
        )
    else:
        pytest.fail(f"Status inesperado retornado pela API: {response.status_code}")


def test_listar_historico_com_status_invalido():
    response = client.get("/historico-ingestoes/?status=INVALIDO")
    assert response.status_code == 422
    assert "Status inválido" in response.json()["detail"]


def test_listar_historico_com_limite_invalido():
    response = client.get("/historico-ingestoes/?limit=0")
    assert response.status_code == 422


def test_listar_historico_com_data_invalida():
    response = client.get("/historico-ingestoes/?data=data-invalida")
    assert response.status_code == 422

# TESTES UNITÁRIOS COM MONKEYPATCH (Não dependem do banco de dados)

def test_listar_historico_sem_banco_retorna_404(monkeypatch):
    """Testa retorno 404 quando o serviço não encontra registros (banco vazio)."""
    # CORREÇÃO: O mock deve ser na função correta que o service chama
    monkeypatch.setattr(
        "app.services.historico_ingestoes_service.consultar_registros_paginados",
        lambda **kwargs: {"items": [], "pagination": {"limit": 10, "next_cursor": None, "has_next": False}}
    )

    response = client.get("/historico-ingestoes/")
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos."
    )


def test_listar_historico_mockado_valida_schema(monkeypatch):
    """Testa a serialização do schema Paginado e repasse de filtros."""
    capturado = {}

    def fake_consultar_registros_paginados(**kwargs):
        capturado.update(kwargs)
        return {
            "items": [
                {
                    "id": 1,
                    "data_inicio": "2026-11-21T10:00:00Z",
                    "data_fim": None,
                    "status": "SUCESSO",
                    "qtd_arquivos_encontrados": 10,
                    "qtd_arquivos_processados": 10,
                    "qtd_arquivos_falhas": 0,
                    "mensagem_erro": None,
                    "criado_em": "2026-11-21T10:00:00Z",
                }
            ],
            "pagination": {"limit": 5, "next_cursor": 1, "has_next": False},
        }

    monkeypatch.setattr(
        "app.services.historico_ingestoes_service.consultar_registros_paginados",
        fake_consultar_registros_paginados
    )

    response = client.get("/historico-ingestoes/?status=SUCESSO&limit=5")

    assert response.status_code == 200
    
    dados = response.json()
    # 1. Valida a estrutura de paginação e serialização
    assert "items" in dados
    assert "pagination" in dados
    assert len(dados["items"]) == 1
    assert dados["items"][0]["id"] == 1
    assert dados["items"][0]["status"] == "SUCESSO"
    assert dados["pagination"]["limit"] == 5

    # 2. Valida se o serviço repassou os filtros corretamente para o repository
    assert capturado["tabela"] == "historico_ingestoes"
    assert capturado["limite"] == 5
    assert capturado["filtros"] == {"status": "SUCESSO"}