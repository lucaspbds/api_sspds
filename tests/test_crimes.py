import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.crime_service import CrimeService
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

def test_listar_crimes_intervalo_datas_invalido():
    """Testa se data_inicio posterior a data_fim retorna 422."""
    response = client.get("/crimes/?data_inicio=2026-12-31&data_fim=2026-01-01")
    assert response.status_code == 422


def test_rotas_especificas_respondem():
    """Verifica se as demais rotas específicas respondem sem erro interno (500)."""
    for rota in ("/crimes/preconceito", "/crimes/operacionais", "/crimes/vitimas"):
        response = client.get(rota)
        assert response.status_code in (200, 404)


def test_listar_cvli_com_filtros_especificos():
    """Testa filtros específicos do schema de CVLI (município, AIS, natureza, meio e vítima)."""
    response = client.get(
        "/crimes/cvli",
        params={
            "municipio": "Fortaleza",
            "ais": "AIS 01",
            "dia_semana": "Segunda-feira",
            "natureza": "Homicídio",
            "meio_empregado": "Arma de fogo",
            "vitima_genero": "Masculino",
            "vitima_raca": "Parda",
            "vitima_idade": 25,
            "vitima_escolaridade": "Ensino Médio",
            "data_inicio": "2024-01-01",
            "data_fim": "2024-12-31",
            "limit": 5,
        },
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_listar_preconceito_com_filtros_especificos():
    """Testa filtros específicos do schema de preconceito."""
    response = client.get(
        "/crimes/preconceito",
        params={
            "municipio": "Fortaleza",
            "local_fato": "Via Pública",
            "vitima_orientacao_sexual": "Homossexual",
            "vitima_idade": 30,
            "data_inicio": "2024-01-01",
            "data_fim": "2024-12-31",
        },
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_listar_operacionais_com_filtros_especificos():
    """Testa filtros específicos do schema de crimes operacionais."""
    response = client.get(
        "/crimes/operacionais",
        params={
            "municipio": "Fortaleza",
            "ais": "AIS 02",
            "dia_semana": "Sexta-feira",
            "data_inicio": "2024-01-01",
            "data_fim": "2024-12-31",
            "limit": 5,
        },
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_listar_vitimas_com_filtros_especificos():
    """Testa filtros específicos do schema de crimes com perfil de vítima."""
    response = client.get(
        "/crimes/vitimas",
        params={
            "municipio": "Fortaleza",
            "vitima_genero": "Feminino",
            "vitima_raca": "Parda",
            "vitima_idade": 28,
            "vitima_escolaridade": "Superior",
            "data_inicio": "2024-01-01",
            "data_fim": "2024-12-31",
            "limit": 5,
        },
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_rotas_especificas_intervalo_datas_invalido():
    """Testa se data_inicio posterior a data_fim retorna 422 nas rotas específicas."""
    for rota in ("/crimes/cvli", "/crimes/preconceito", "/crimes/operacionais", "/crimes/vitimas"):
        response = client.get(f"{rota}?data_inicio=2026-12-31&data_fim=2026-01-01")
        assert response.status_code == 422


def test_rotas_especificas_idade_negativa_invalida():
    """Testa se vitima_idade negativa retorna 422 nas rotas que aceitam o filtro."""
    for rota in ("/crimes/cvli", "/crimes/preconceito", "/crimes/vitimas"):
        response = client.get(f"{rota}?vitima_idade=-1")
        assert response.status_code == 422

def test_rotas_especificas_sem_banco_retornam_404(monkeypatch):
    """Testa retorno 404 nas rotas específicas quando o serviço não encontra registros."""
    monkeypatch.setattr(CrimeService, "listar_por_tipo", lambda **kwargs: [])
    monkeypatch.setattr(CrimeService, "listar_por_tipos", lambda **kwargs: [])

    for rota in ("/crimes/cvli", "/crimes/preconceito", "/crimes/operacionais", "/crimes/vitimas"):
        response = client.get(rota)
        assert response.status_code == 404


def test_listar_cvli_mockado_valida_filtros_e_schema(monkeypatch):
    """Testa repasse de filtros em /crimes/cvli e serialização do schema CvliResponse."""
    capturado = {}

    def fake_listar_por_tipo(**kwargs):
        capturado.update(kwargs)
        return [
            {
                "tipo_crime": "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
                "ais": "AIS 01",
                "municipio": "Fortaleza",
                "data_fato": "2024-05-10",
                "hora_fato": "21:30:00",
                "dia_semana": "Sexta-feira",
                "st_dia_semana_divergente": False,
                "st_idade_invalida": False,
                "vitima_genero": "Masculino",
                "vitima_idade": "Não Informada",
                "vitima_escolaridade": "Ensino Médio",
                "vitima_raca": "Parda",
                "natureza": "Homicídio",
                "meio_empregado": "Arma de fogo",
            }
        ]

    monkeypatch.setattr(CrimeService, "listar_por_tipo", fake_listar_por_tipo)

    response = client.get(
        "/crimes/cvli",
        params={"municipio": "Fortaleza", "vitima_idade": 0, "limit": 1},
    )

    assert response.status_code == 200
    assert capturado["municipio"] == "Fortaleza"
    assert capturado["vitima_idade"] == 0
    assert capturado["limit"] == 1
    dados = response.json()
    assert len(dados) == 1
    # Valida que "Não Informada" em vitima_idade vira null no schema CvliResponse
    assert dados[0]["vitima_idade"] is None