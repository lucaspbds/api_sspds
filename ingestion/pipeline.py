from crawler import crawler
from processor import processor
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

    # O crawler identifica os arquivos disponibilizados pela SSPDS
    # e retorna uma lista contendo os endereços desses arquivos.
    lista_url = crawler()

    print(lista_url[0])

    # O primeiro arquivo encontrado é enviado para o processador,
    # que realiza a leitura da planilha e sua conversão para JSON.
    processor(lista_url[0])


if __name__ == "__main__":
    pipeline()