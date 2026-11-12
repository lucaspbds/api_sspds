from urllib.parse import urljoin

import logging
import requests as r
from bs4 import BeautifulSoup

from .config import get_variavel_ambiente
from .exception import VariavelAmbienteNaoEncontrada
from .exception import EstruturaCSSDoSiteAlterado
from .exception import ValorInteiroInvalido
from .helpers import recebeInteiro
from logging_system.logging_config import configure_logging


configure_logging()



def extrair_links(conteudo_html):
    """Retorna todas as tags <a> encontradas no conteúdo informado."""
    if not conteudo_html:
        return []
    return conteudo_html.find_all("a", href=True)


def obter_conteudo_html(url: str, timeout: int) -> BeautifulSoup:
    """Faz a requisição HTTP e retorna o HTML convertido em BeautifulSoup."""
    logger = logging.getLogger(__name__)
    try:
        resposta = r.get(url, timeout=timeout)
        resposta.raise_for_status()
    except r.exceptions.Timeout:
        logger.error("Tempo limite excedido ao tentar acessar a URL: %s", url)
        raise
    except r.exceptions.ConnectionError:
        logger.error("Erro de conexão ao tentar acessar a URL: %s", url)
        raise
    except r.exceptions.HTTPError as erro:
        status = erro.response.status_code if erro.response is not None else "desconhecido"
        logger.error("Erro HTTP (Status %s) ao acessar %s: %s", status, url, erro)
        raise
    except r.exceptions.RequestException as erro:
        logger.error("Erro inesperado na requisição para %s: %s", url, erro)
        raise

    return BeautifulSoup(resposta.text, "html.parser")


def normalizar_links(tags, url_base: str) -> list[str]:
    """Converte hrefs em URLs absolutas e remove duplicatas preservando a ordem."""
    links = []
    vistos = set()

    for tag in tags:
        href = tag.get("href", "").strip()
        if not href:
            continue

        url = urljoin(url_base, href)
        if url not in vistos:
            vistos.add(url)
            links.append(url)

    return links


def extrair_links_atuais(soup: BeautifulSoup, url_base: str) -> list[str]:
    """Extrai os arquivos publicados na seção de indicadores detalhados atuais."""
    logger = logging.getLogger(__name__)
    containers = soup.select(
        "#conteudo > div > div > div > section > section > "
        "div > div:nth-child(20)"
    )

    if not containers:
        raise EstruturaCSSDoSiteAlterado(
            "Não foi possível localizar a seção de indicadores detalhados atuais."
        )

    tags = []
    for container in containers:
        tags.extend(extrair_links(container))

    links = normalizar_links(tags, url_base)
    if not links:
        raise EstruturaCSSDoSiteAlterado(
            "A seção de indicadores atuais foi encontrada, mas não contém links."
        )

    logger.info("Links encontrados na página atual: %s", len(links))
    return links


def extrair_links_historicos(soup: BeautifulSoup, url_base: str) -> list[str]:
    """Extrai os arquivos históricos da seção de indicadores detalhados.

    Na página histórica, os downloads ficam em uma coluna Gutenberg
    ``div.wp-block-columns`` marcada com ``text-transform:uppercase``.
    Cada arquivo é um link ``a.wp-block-button__link``.
    """
    logger = logging.getLogger(__name__)

    # Seleciona a seção específica informada no HTML da página histórica,
    # evitando capturar botões de navegação, cabeçalho ou rodapé.
    containers = soup.select(
        'div.wp-block-columns[style*="text-transform:uppercase"]'
    )
    if not containers:
        raise EstruturaCSSDoSiteAlterado(
            "Não foi possível localizar a seção de indicadores históricos."
        )

    tags = []
    for container in containers:
        tags.extend(container.select("a.wp-block-button__link[href]"))

    links = normalizar_links(tags, url_base)
    if not links:
        raise EstruturaCSSDoSiteAlterado(
            "A seção de indicadores históricos foi encontrada, mas não contém links de download."
        )

    logger.info("Links encontrados na página histórica: %s", len(links))
    return links


def crawler() -> list[str]:
    """Coleta os links dos arquivos atuais e de toda a série histórica da SSPDS.

    A URL atual é obtida pela variável de ambiente `url_sspds`. A página
    histórica é consultada diretamente. O retorno continua sendo uma lista
    única de URLs absolutas, compatível com o fluxo de ingestão existente.

    Raises:
        VariavelAmbienteNaoEncontrada: variável obrigatória não encontrada.
        EstruturaCSSDoSiteAlterado: estrutura esperada não encontrada ou sem links.
        requests.exceptions.RequestException: falhas de rede ou HTTP.
    """
    logger = logging.getLogger(__name__)
    logger.info("Crawler iniciado: coleta atual e histórica")

    try:
        url_sspds = get_variavel_ambiente("url_sspds")
        URL_DADOS_HISTORICOS = get_variavel_ambiente("url_sspds_historico")
        try:
            timeout_crawler = recebeInteiro(
                get_variavel_ambiente("CRAWLER_TIMEOUT")
            )
        except (ValorInteiroInvalido, VariavelAmbienteNaoEncontrada):
            logger.warning(
                "CRAWLER_TIMEOUT inválido ou não definido. Utilizando padrão de 10 segundos."
            )
            timeout_crawler = 10

        # Coleta dos indicadores atuais (ex.: dados mensais de 2026).
        soup_atual = obter_conteudo_html(url_sspds, timeout_crawler)
        links_atuais = extrair_links_atuais(soup_atual, url_sspds)

        # Coleta da série histórica publicada separadamente pela SSPDS.
        soup_historico = obter_conteudo_html(
            URL_DADOS_HISTORICOS, timeout_crawler
        )
        links_historicos = extrair_links_historicos(
            soup_historico, URL_DADOS_HISTORICOS
        )

        # Mantém a ordem: primeiro os dados atuais, depois o histórico.
        links_arquivos = list(dict.fromkeys(links_atuais + links_historicos))
        logger.info(
            "Crawler concluído: %s links atuais, %s históricos e %s únicos no total.",
            len(links_atuais),
            len(links_historicos),
            len(links_arquivos),
        )
        return links_arquivos

    except VariavelAmbienteNaoEncontrada as erro:
        logger.exception("Falha crítica de inicialização: %s", erro)
        raise
    except EstruturaCSSDoSiteAlterado as erro:
        logger.exception("Erro de parsing/estrutura de dados no HTML: %s", erro)
        raise
    except Exception as erro:
        logger.exception("Erro crítico e não mapeado no crawler: %s", erro)
        raise