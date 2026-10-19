import logging
from unittest.mock import Mock, patch
import pytest
import requests

import ingestion.crawler as modulo_crawler
from ingestion.crawler import crawler, extrair_links
from ingestion.exception import (EstruturaCSSDoSiteAlterado, VariavelAmbienteNaoEncontrada, ValorInteiroInvalido)
from ingestion.helpers import recebeInteiro

# ---------------------------------------------------------
# 1. HAPPY PATH
# ---------------------------------------------------------

def test_extrair_links_retorna_todas_as_tags_a():
    from bs4 import BeautifulSoup

    html = """
        <div>
            <a href="/cvli.xlsx">CVLI</a>
            <a href="/furtos.xlsx">Furtos</a>
            <span>Não é um link</span>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    resultado = extrair_links(soup.div)

    assert len(resultado) == 2
    assert [link.get("href") for link in resultado] == [
        "/cvli.xlsx",
        "/furtos.xlsx",
    ]

def test_crawler_retorna_links_e_tipos_corretamente(caplog, configurar_resposta_http):
    # O mock e a resposta já estão prontos e ativos aqui graças à fixture!
    resultado = crawler()

    assert resultado == [
        ["/arquivo1.xlsx", "/arquivo2.xlsx"],
        ["CVLI", "Furto"],
    ]
    assert "Qtd de links encontrados: 2" in caplog.text

@pytest.mark.parametrize("valor", [1])
def test_funcao_recebeInteiro_devolve_um_numero_inteiro(valor):
    numero_inteiro = recebeInteiro(valor)
    assert type(numero_inteiro) == int


# ---------------------------------------------------------
# 2. SAD PATH
# ---------------------------------------------------------

@pytest.mark.parametrize("valor", ["", "abc", None])
def test_funcao_recebeInteiro_retorna_o_erro_ValorInteiroInvalido(valor):
    with pytest.raises(ValorInteiroInvalido):
        recebeInteiro(valor)
    

@pytest.mark.parametrize("conteudo", [None, "", False])
def test_extrair_links_retorna_lista_vazia_sem_conteudo(conteudo):
    assert extrair_links(conteudo) == []


def test_crawler_registra_e_propaga_variavel_ausente(caplog):
    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=VariavelAmbienteNaoEncontrada("url_sspds")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(VariavelAmbienteNaoEncontrada):
                crawler()

    assert "Falha crítica de inicialização" in caplog.text

def test_crawler_registra_e_propaga_timeout(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.Timeout("tempo excedido")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.Timeout):
                crawler()

    assert "Tempo limite excedido" in caplog.text


def test_crawler_registra_e_propaga_erro_de_conexao(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.ConnectionError("sem conexão")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.ConnectionError):
                crawler()

    assert "Erro de conexão" in caplog.text


def test_crawler_registra_e_propaga_erro_http(caplog):
    resposta = Mock()
    resposta.status_code = 503

    erro_http = requests.exceptions.HTTPError(
        "Service Unavailable",
        response=resposta,
    )

    resposta.raise_for_status.side_effect = erro_http

    with patch.object(modulo_crawler.r, "get", return_value=resposta):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                crawler()

    assert "Status 503" in caplog.text


def test_crawler_registra_erro_inesperado_de_requisicao(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.RequestException("erro inesperado")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.RequestException):
                crawler()

    assert "Erro inesperado na requisição HTTP" in caplog.text


def test_crawler_registra_e_propaga_estrutura_alterada(caplog):
    html_sem_container = """
        <html>
            <body>
                <div id="conteudo">
                    <p>A estrutura da página mudou.</p>
                </div>
            </body>
        </html>
    """

    with patch.object(modulo_crawler.r, "get") as mock_get:
        resposta = Mock()
        resposta.text = html_sem_container
        resposta.raise_for_status.return_value = None
        mock_get.return_value = resposta

        with caplog.at_level(logging.ERROR):
            with pytest.raises(EstruturaCSSDoSiteAlterado):
                crawler()

    assert "Erro de parsing/estrutura de dados no HTML" in caplog.text


@pytest.mark.parametrize("timeout_invalido", ["abc", "", None])
def test_crawler_usa_timeout_padrao_quando_configuracao_invalida(
    caplog, timeout_invalido, configurar_resposta_http):
    def obter_variavel(nome):
        if nome == "url_sspds":
            return "https://exemplo.test/sspds"
        if nome == "CRAWLER_TIMEOUT":
            return timeout_invalido
        raise VariavelAmbienteNaoEncontrada()

    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=obter_variavel):
        with caplog.at_level(logging.WARNING):
            crawler()

    assert "CRAWLER_TIMEOUT inválido ou não definido" in caplog.text
