import pytest
import ingestion.crawler as modulo_crawler
from unittest.mock import Mock, patch
import pandas as pd
from database.repository import criar_cliente_supabase

@pytest.fixture
def html_sspds_atual():
    """HTML sintético compatível com o seletor da seção de dados atuais."""
    divs = "".join(
        f"<div>{conteudo}</div>"
        for conteudo in (
            [""] * 19
            + [
                "<a href='/arquivo1.xlsx'>CVLI</a>"
                "<a href='/arquivo2.xlsx'>Furto</a>"
            ]
        )
    )

    return f"""
        <html>
            <body>
                <div id="conteudo">
                    <div><div><div>
                        <section><section>
                            <div>{divs}</div>
                        </section></section>
                    </div></div></div>
                </div>
            </body>
        </html>
    """


@pytest.fixture
def html_sspds_historico():
    """HTML sintético compatível com a seção Gutenberg de dados históricos."""
    return """
        <html>
            <body>
                <div class="wp-block-columns" style="text-transform:uppercase">
                    <a class="wp-block-button__link" href="/historico1.xlsx">CVLI</a>
                    <a class="wp-block-button__link" href="/historico2.xlsx">Furto</a>
                    <a class="wp-block-button__link" href="/arquivo1.xlsx">Duplicado</a>
                </div>
                <div>
                    <a class="wp-block-button__link" href="/fora-da-secao.xlsx">Menu</a>
                </div>
            </body>
        </html>
    """


@pytest.fixture
def configurar_resposta_http(html_sspds_atual, html_sspds_historico):
    """Simula as duas respostas HTTP: página atual e página histórica."""
    urls = {
        "url_sspds": "https://dados.test/atual/",
        "url_sspds_historico": "https://dados.test/historico/",
        "CRAWLER_TIMEOUT": "10",
    }

    with patch.object(
        modulo_crawler,
        "get_variavel_ambiente",
        side_effect=lambda nome: urls[nome],
    ):
        with patch.object(modulo_crawler.r, "get") as mock_get:
            respostas = []
            for html in (html_sspds_atual, html_sspds_historico):
                resposta = Mock()
                resposta.text = html
                resposta.raise_for_status.return_value = None
                respostas.append(resposta)

            mock_get.side_effect = respostas
            yield mock_get


@pytest.fixture
def df_cvli():
    return pd.DataFrame([{
        "Município": "  FORTALEZA ",
        "AIS": "AIS 1",
        "Natureza": "HOMICÍDIO",
        "Data": "2024-01-01",  # segunda-feira
        "Hora": "08:30",
        "Dia da Semana": "segunda-feira",
        "Meio Empregado": "ARMA DE FOGO",
        "Gênero": "masculino",
        "Idade da Vítima": "25",
        "Escolaridade da Vítima": "ensino médio",
        "Raça da Vítima": "parda",
    }])


@pytest.fixture
def df_animais():
    return pd.DataFrame([{
        "Município": "FORTALEZA",
        "AIS": "AIS 1",
        "Data": "2024-01-01",
        "Hora": "09:15",
        "Dia da Semana": "segunda-feira",
    }])


@pytest.fixture
def df_armas(df_animais):
    df = df_animais.copy()
    df["Quantidade"] = "2"
    return df


@pytest.fixture
def df_entorpecentes(df_animais):
    df = df_animais.copy()
    df["Quantidade (Kg)"] = "1,25"
    df["Tipo de Entorpecente"] = "maconha"
    return df


@pytest.fixture
def df_preconceito(df_animais):
    df = df_animais.copy()
    df["Gênero"] = "feminino"
    df["Idade da Vítima"] = "30"
    df["Escolaridade da Vítima"] = "ensino superior"
    df["Raça da Vítima"] = "parda"
    return df


@pytest.fixture
def df_homofobia(df_animais):
    df = df_animais.copy()
    df["Idade da Vítima"] = "22"
    df["Escolaridade da Vítima"] = "ensino médio"
    df["Raça da Vítima"] = "branca"
    df["Natureza"] = "ameaça"
    df["Identidade de Gênero"] = "mulher trans"
    df["Orientação Sexual"] = "heterossexual"
    df["Local"] = "via pública"
    return df

@pytest.fixture(scope="function")
def banco_local():
    """
    Fixture que fornece uma instância do cliente Supabase conectada ao banco local.
    """
    cliente = criar_cliente_supabase()
    yield cliente
    cliente = None