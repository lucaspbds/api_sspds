import pytest
import ingestion.crawler as modulo_crawler
from unittest.mock import Mock, patch
import pandas as pd

@pytest.fixture
def html_sspds():
    """
    Monta um HTML de teste compatível com o seletor CSS utilizado
    pelo crawler, sem depender do site real da SSPDS.
    """
    divs = "".join(
        f"<div>{conteudo}</div>"
        for conteudo in (
            [""] * 19 +
            ["<a href='/arquivo1.xlsx'>CVLI</a>"
             "<a href='/arquivo2.xlsx'>Furto</a>"] 
        )
    )

    return f"""
        <html>
            <body>
                <div id="conteudo">
                    <div>
                        <div>
                            <div>
                                <section>
                                    <section>
                                        <div>{divs}</div>
                                    </section>
                                </section>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    """

@pytest.fixture
def configurar_resposta_http(html_sspds):
    """
    Fixture que já faz o patch do requests.get e configura a resposta
    automaticamente usando o html_sspds.
    """
    with patch.object(modulo_crawler.r, "get") as mock_get:
        resposta = Mock()
        resposta.text = html_sspds
        resposta.raise_for_status.return_value = None
        mock_get.return_value = resposta
        yield resposta  # Retorna a resposta configurada para o teste, se ele precisar

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
