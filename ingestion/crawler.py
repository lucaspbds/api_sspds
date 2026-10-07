import os
from config import get_variavel_ambiente
from exception import VariavelAmbienteNaoEncontrada
import requests as r
from bs4 import BeautifulSoup


def extrair_links(conteudo_html):
    """
    Função responsável por extrair todas as tags <a> de um conteúdo HTML.

    Args:
        conteudo_html: conteúdo HTML processado pelo BeautifulSoup.

    Return:
        links: lista contendo todas as tags <a> encontradas no conteúdo HTML.
    """
    return conteudo_html.find_all('a')


def crawler() -> list:
    """
    Função responsável por acessar a página da SSPDS e capturar os
    links dos arquivos disponibilizados na seção de indicadores detalhados, além dos
    tipos de ocorrências criminais.

    Args:
        Não possui argumentos.

    Return:
        list [links_arquivos, tipos_ocorrencias]: lista contendo os endereços (href) dos arquivos
        encontrados na seção de indicadores detalhados da página da SSPDS e uma lista dos tipos 
        de ocorrências.

    Exception:
        Caso a variável de ambiente necessária para acessar a página
        da SSPDS não exista, será retornado um erro indicando que a
        variável de ambiente não foi encontrada.
    """
    try:
        # A URL da SSPDS é obtida através da variável de ambiente
        # para evitar deixar a URL diretamente escrita no código.
        url_sspds = get_variavel_ambiente('url_sspds')

        timeout_crawler = int(os.getenv("CRAWLER_TIMEOUT", 10))
        resposta = r.get(url_sspds, timeout=timeout_crawler)
        resposta.raise_for_status()
        html = resposta.text
        soup = BeautifulSoup(html, 'html.parser')

        # Seleciona o elemento da página onde estão localizados
        # os indicadores detalhados disponibilizados pela SSPDS.
        container_indicadores_detalhados = soup.select(
            "#conteudo > div > div > div > section > section > "
            "div > div:nth-child(20)"
        )

        # Extrai as tags <a> presentes no elemento selecionado.
        links = list(map(extrair_links, container_indicadores_detalhados))[0]

        print(f"Qtd de links encontrados: {len(links)}")
        tipos_ocorrencias = list(map(lambda link: link.text, links))
        # Extrai somente o endereço dos arquivos (atributo href)
        # de cada link encontrado.
        links_arquivos = list(map(lambda link: link['href'], links))

        return [links_arquivos, tipos_ocorrencias]

    except VariavelAmbienteNaoEncontrada as VANE:
        VANE.print_mensagem_erro()