from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_listar_historico_sem_filtros():
    # Dependendo do mock ou do banco real que você usa
    response = client.get("/historico-ingestoes/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_listar_historico_com_status_valido():
    response = client.get("/historico-ingestoes/?status=SUCESSO")
    
    if response.status_code == 200:
        # Se retornou 200, o banco tem dados. Vamos validar o conteúdo.
        for item in response.json():
            assert item["status"] == "SUCESSO"
            
    elif response.status_code == 404:
        # Se retornou 404, garantimos que é a nossa mensagem customizada de "lista vazia"
        # e não um erro genérico do FastAPI (ex: rota não encontrada)
        assert response.json()["detail"] == "Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos."
        
    else:
        # Se cair aqui, é um erro inesperado (ex: 500 Internal Server Error)
        pytest.fail(f"Status inesperado retornado pela API: {response.status_code}")

def test_listar_historico_com_status_invalido():
    response = client.get("/historico-ingestoes/?status=INVALIDO")
    assert response.status_code == 422
    assert "Status inválido" in response.json()["detail"]

def test_listar_historico_com_limite_invalido():
    response = client.get("/historico-ingestoes/?limit=0")
    assert response.status_code == 422

def test_listar_historico_com_data_invalida():
    response = client.get("/historico-ingestoes/?data=21/11/2026") # Formato BR não é aceito pelo FastAPI diretamente na query
    assert response.status_code == 422
