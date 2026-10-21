from .config import get_variavel_ambiente
from .exception import VariavelAmbienteNaoEncontrada
from .exception import EstruturaCSSDoSiteAlterado
from .exception import ValorInteiroInvalido
from .helpers import recebeInteiro
import requests as r
from bs4 import BeautifulSoup
from logging_system.logging_config import configure_logging
import logging

configure_logging()

def extrair_links(conteudo_html):
    """
    Função responsável por extrair todas as tags <a> de um conteúdo HTML.

    Args:
        conteudo_html: conteúdo HTML processado pelo BeautifulSoup.

    Return:
        links: lista contendo todas as tags <a> encontradas no conteúdo HTML.
    """
    if not conteudo_html:
        return []
    return conteudo_html.find_all('a')


def crawler() -> list:
    """
    Acessa a página da SSPDS e captura os links dos arquivos disponibilizados 
    na seção de indicadores detalhados, além dos tipos de ocorrências criminais.

    Returns:
        list: Uma lista contendo dois elementos:
            - links_arquivos (list[str]): Endereços (href) dos arquivos encontrados.
            - tipos_ocorrencias (list[str]): Textos descritivos correspondentes a cada ocorrência.

    Raises:
        VariavelAmbienteNaoEncontrada: Se a variável de ambiente obrigatória `url_sspds` não for encontrada.
        EstruturaCSSDoSiteAlterado: Se o container CSS esperado não for encontrado no HTML da página.
        requests.exceptions.Timeout: Se o tempo limite da requisição (timeout) for excedido.
        requests.exceptions.ConnectionError: Se houver falha de conexão com o servidor da SSPDS.
        requests.exceptions.HTTPError: Se o servidor retornar um código de status HTTP de erro.
        requests.exceptions.RequestException: Para outros erros genéricos na requisição HTTP.
    """

    logger = logging.getLogger(__name__)
    try:
        # A URL da SSPDS é obtida através da variável de ambiente
        # para evitar deixar a URL diretamente escrita no código.
        url_sspds = get_variavel_ambiente('url_sspds')
        try:
            timeout_crawler = recebeInteiro(get_variavel_ambiente("CRAWLER_TIMEOUT"))
        except (ValorInteiroInvalido, VariavelAmbienteNaoEncontrada):
            logger.warning("CRAWLER_TIMEOUT inválido ou não definido. Utilizando padrão de 10 segundos.")
            timeout_crawler = 10

        try:
            resposta = r.get(url_sspds, timeout=timeout_crawler)
            resposta.raise_for_status()
        except r.exceptions.Timeout:
            logger.error("Tempo limite excedido (timeout) ao tentar acessar a URL da SSPDS: %s", url_sspds)
            raise
        except r.exceptions.ConnectionError:
            logger.error("Erro de conexão ao tentar acessar a URL da SSPDS: %s", url_sspds)
            raise
        except r.exceptions.HTTPError as e:
            logger.error("Erro HTTP retornado pelo servidor da SSPDS (Status %s): %s", e.response.status_code, e)
            raise
        except r.exceptions.RequestException as e:
            logger.error("Erro inesperado na requisição HTTP: %s", e)
            raise

        html = resposta.text
        soup = BeautifulSoup(html, 'html.parser')

        # Seleciona o elemento da página onde estão localizados
        # os indicadores detalhados disponibilizados pela SSPDS.
        container_indicadores_detalhados = soup.select(
            "#conteudo > div > div > div > section > section > "
            "div > div:nth-child(20)"
        )
        if not container_indicadores_detalhados:
            raise EstruturaCSSDoSiteAlterado()
        
        # Extrai as tags <a> presentes no elemento selecionado.
        links = list(map(extrair_links, container_indicadores_detalhados))[0]
        logger.info("Qtd de links encontrados: %s", len(links))

        #Extrai os tipos de ocorrências que existem
        tipos_ocorrencias = [link.text.strip() for link in links if link.text]
        # Extrai somente o endereço dos arquivos (atributo href)
        # de cada link encontrado.
        links_arquivos = [link.get('href') for link in links if link.get('href')]

        return [links_arquivos, tipos_ocorrencias]

    except VariavelAmbienteNaoEncontrada as VANE:
        logger.exception("Falha crítica de inicialização: %s", VANE)
        raise
    except (EstruturaCSSDoSiteAlterado) as ECDSA:
        logger.exception("Erro de parsing/estrutura de dados no HTML: %s", ECDSA)
        raise
    except Exception as e:
        logger.exception("Erro crítico e não mapeado no crawler: %s", e)
        raise
