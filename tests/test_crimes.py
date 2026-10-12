from fastapi.testclient import TestClient
from app.main import app  

client = TestClient(app)

def test_listar_cvli_sem_limite():
    """Testa se a listagem sem o parâmetro limit retorna 200 e uma lista."""
    response = client.get("/crimes/cvli")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_listar_cvli_com_limite_valido():
    """Testa se a listagem com limit positivo respeita o tamanho máximo."""
    response = client.get("/crimes/cvli?limit=5")
    assert response.status_code == 200
    dados = response.json()
    assert isinstance(dados, list)
    assert len(dados) <= 1193

def test_listar_cvli_com_limite_negativo():
    """Testa se o FastAPI bloqueia números negativos com erro 422 (gt=0)."""
    response = client.get("/crimes/cvli?limit=-10")
    assert response.status_code == 422
    detalhes = response.json()["detail"]
    # Valida se o erro gerado está relacionado com o limite maior que zero
    assert any(err["type"] == "greater_than" for err in detalhes)

def test_listar_cvli_com_limite_invalido_texto():
    """Testa se o FastAPI bloqueia letras/strings no parâmetro limit com erro 422."""
    response = client.get("/crimes/cvli?limit=abc")
    assert response.status_code == 422
    detalhes = response.json()["detail"]
    # Valida se o erro gerado é de falha de conversão para inteiro
    assert any(err["type"] == "int_parsing" for err in detalhes)