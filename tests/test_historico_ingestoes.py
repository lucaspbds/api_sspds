import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
# Importamos o serviço para mockar a dependência do banco de dados
from app.services.historico_ingestoes_service import HistoricoIngestoesService

client = TestClient(app)


def test_listar_historico_sem_filtros():
    response = client.get("/historico-ingestoes/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_listar_historico_com_status_valido():
    response = client.get("/historico-ingestoes/?status=SUCESSO")

    if response.status_code == 200:
        for item in response.json():
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

def test_listar_historico_sem_banco_retorna_404(monkeypatch):
    """Testa retorno 404 quando o serviço não encontra registros (banco vazio)."""
    # Mocka a função do repository para retornar lista vazia
    monkeypatch.setattr(
        "app.services.historico_ingestoes_service.consultar_registros",
        lambda **kwargs: []
    )

    response = client.get("/historico-ingestoes/")
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos."
    )


def test_listar_historico_mockado_valida_schema(monkeypatch):
    """Testa a serialização do schema HistoricoIngestaoResponse e repasse de filtros."""
    capturado = {}

    def fake_consultar_registros(**kwargs):
        # Captura os argumentos repassados pelo serviço para o repository
        capturado.update(kwargs)
        
        # Retorna um registro fictício simulando a resposta do banco
        return [
            {
                "id": 1,
                "data_inicio": datetime.now(timezone.utc).isoformat(),
                "data_fim": None,
                "status": "SUCESSO",
                "qtd_arquivos_encontrados": 10,
                "qtd_arquivos_processados": 10,
                "qtd_arquivos_falhas": 0,
                "mensagem_erro": None,
                "criado_em": datetime.now(timezone.utc).isoformat(),
            }
        ]

    # Mocka a função com a nossa versão falsa
    monkeypatch.setattr(
        "app.services.historico_ingestoes_service.consultar_registros",
        fake_consultar_registros
    )

    # Faz a requisição enviando filtros
    response = client.get("/historico-ingestoes/?status=SUCESSO&limit=5")

    assert response.status_code == 200
    
    # 1. Valida se o schema serializou os dados corretamente
    dados = response.json()
    assert len(dados) == 1
    assert dados[0]["id"] == 1
    assert dados[0]["status"] == "SUCESSO"
    assert dados[0]["qtd_arquivos_processados"] == 10

    # 2. Valida se o serviço repassou os filtros corretamente para o repository
    assert capturado["tabela"] == "historico_ingestoes"
    assert capturado["limite"] == 5
    assert capturado["filtros"] == {"status": "SUCESSO"}