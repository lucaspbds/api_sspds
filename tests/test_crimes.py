import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _pagina_mock(items, limit=100, next_cursor=None, has_next=False):
    return {
        "items": items,
        "pagination": {
            "limit": limit,
            "next_cursor": next_cursor,
            "has_next": has_next,
        },
    }


def _item_cvli_mock(**overrides):
    base = {
        "id": 1,
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
    base.update(overrides)
    return base


def _item_preconceito_mock(**overrides):
    base = {
        "id": 2,
        "tipo_crime": "HOMOFOBIA E TRANSFOBIA",
        "ais": "AIS 01",
        "municipio": "Fortaleza",
        "local_fato": "Via Pública",
        "vitima_orientacao_sexual": "Homossexual",
        "vitima_idade": 30,
        "data_fato": "2024-05-10",
    }
    base.update(overrides)
    return base


def _item_operacional_mock(**overrides):
    base = {
        "id": 3,
        "tipo_crime": "FURTO",
        "ais": "AIS 02",
        "municipio": "Fortaleza",
        "dia_semana": "Sexta-feira",
        "data_fato": "2024-05-10",
    }
    base.update(overrides)
    return base


def _item_vitima_mock(**overrides):
    base = {
        "id": 4,
        "tipo_crime": "CRIMES SEXUAIS",
        "ais": "AIS 01",
        "municipio": "Fortaleza",
        "vitima_genero": "Feminino",
        "vitima_raca": "Parda",
        "vitima_idade": 28,
        "vitima_escolaridade": "Superior",
        "data_fato": "2024-05-10",
    }
    base.update(overrides)
    return base


def test_listar_cvli_sem_limite(monkeypatch):
    """Testa se a listagem sem o parâmetro limit retorna 200 e uma resposta paginada."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_cvli_mock()], limit=100),
    )

    response = client.get("/crimes/cvli")
    assert response.status_code == 200
    dados = response.json()
    assert isinstance(dados, dict)
    assert "items" in dados
    assert "pagination" in dados
    assert isinstance(dados["items"], list)


def test_listar_cvli_com_limite_valido(monkeypatch):
    """Testa se a listagem com limit positivo respeita o tamanho máximo."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_cvli_mock()], limit=5),
    )

    response = client.get("/crimes/cvli?limit=5")
    assert response.status_code == 200
    dados = response.json()
    assert isinstance(dados, dict)
    assert len(dados["items"]) <= 5


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


def test_rotas_especificas_respondem(monkeypatch):
    """Verifica se as demais rotas específicas respondem sem erro interno (500)."""
    def fake_repo(**kwargs):
        filtros = kwargs.get("filtros") or {}
        filtros_in = kwargs.get("filtros_in") or {}
        tipo_unico = filtros.get("tipo_crime")
        tipos_lista = filtros_in.get("tipo_crime") or []

        if tipo_unico == "HOMOFOBIA E TRANSFOBIA":
            return _pagina_mock([_item_preconceito_mock()])
        if "FURTO" in tipos_lista:
            return _pagina_mock([_item_operacional_mock()])
        if "CRIMES SEXUAIS" in tipos_lista:
            return _pagina_mock([_item_vitima_mock()])
        return _pagina_mock([])

    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        fake_repo,
    )

    for rota in ("/crimes/preconceito", "/crimes/operacionais", "/crimes/vitimas"):
        response = client.get(rota)
        assert response.status_code in (200, 404)


def test_listar_cvli_com_filtros_especificos(monkeypatch):
    """Testa filtros específicos do schema de CVLI (município, AIS, natureza, meio e vítima)."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_cvli_mock()], limit=5),
    )

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
        assert isinstance(response.json(), dict)
        assert isinstance(response.json()["items"], list)


def test_listar_preconceito_com_filtros_especificos(monkeypatch):
    """Testa filtros específicos do schema de preconceito."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_preconceito_mock()]),
    )

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
        assert isinstance(response.json(), dict)
        assert isinstance(response.json()["items"], list)


def test_listar_operacionais_com_filtros_especificos(monkeypatch):
    """Testa filtros específicos do schema de crimes operacionais."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_operacional_mock()], limit=5),
    )

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
        assert isinstance(response.json(), dict)
        assert isinstance(response.json()["items"], list)


def test_listar_vitimas_com_filtros_especificos(monkeypatch):
    """Testa filtros específicos do schema de crimes com perfil de vítima."""
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([_item_vitima_mock()], limit=5),
    )

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
        assert isinstance(response.json(), dict)
        assert isinstance(response.json()["items"], list)


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
    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        lambda **kwargs: _pagina_mock([]),
    )

    for rota in ("/crimes/cvli", "/crimes/preconceito", "/crimes/operacionais", "/crimes/vitimas"):
        response = client.get(rota)
        assert response.status_code == 404


def test_listar_cvli_mockado_valida_filtros_e_schema(monkeypatch):
    """Testa repasse de filtros em /crimes/cvli e serialização do schema CvliPaginadoResponse."""
    capturado = {}

    def fake_consultar_registros_paginados(**kwargs):
        capturado.update(kwargs)
        return _pagina_mock([_item_cvli_mock(vitima_idade="Não Informada")], limit=1)

    monkeypatch.setattr(
        "app.services.crime_service.consultar_registros_paginados",
        fake_consultar_registros_paginados,
    )

    response = client.get(
        "/crimes/cvli",
        params={"municipio": "Fortaleza", "vitima_idade": 0, "limit": 1},
    )

    assert response.status_code == 200
    assert capturado["filtros"]["municipio"] == "Fortaleza"
    assert capturado["filtros"]["vitima_idade"] == 0
    assert capturado["limite"] == 1
    dados = response.json()
    assert "items" in dados
    assert "pagination" in dados
    assert len(dados["items"]) == 1
    # Valida que "Não Informada" em vitima_idade vira null no schema de CVLI
    assert dados["items"][0]["vitima_idade"] is None