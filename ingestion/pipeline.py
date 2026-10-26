from .crawler import crawler
from .processor import processor
from logging_system.logging_config import configure_logging 
import logging
configure_logging()

def pipeline() -> None:
    """
    Função responsável por executar as etapas principais do processo
    de ingestão dos dados da SSPDS.

    Args:
        Não possui argumentos.

    Return:
        None

    Exception:
        Caso ocorra algum erro durante a execução das etapas do pipeline,
        o erro será retornado pela função responsável pela etapa em que
        o problema ocorrer.
    """
    logger = logging.getLogger("Pipeline")
    logger.info("Crawler iniciado")
    # O crawler identifica os arquivos disponibilizados pela SSPDS
    # e retorna uma lista contendo os endereços desses arquivos e os tipos de crimes.
    lista_url, tipos_ocorrencias = crawler()
    if len(lista_url) > 0 and len(tipos_ocorrencias) > 0:
        logger.info("Crawler concluído com sucesso")

    logger.info("Processamento dos dados iniciado")

    
    # O primeiro arquivo encontrado é enviado para o processador,
    # que realiza a leitura da planilha e sua conversão para JSON.
    
    # processor(lista_url[0], tipos_ocorrencias)
    logger.info("Processamento dos dados finalizado")


if __name__ == "__main__":
    pipeline()