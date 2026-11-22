import pytest
from fastapi.testclient import TestClient

from app.main import app

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