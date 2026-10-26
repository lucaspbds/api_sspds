import os
from dotenv import load_dotenv
from database.exceptions import VariavelAmbienteNaoEncontrada

load_dotenv()

def get_variavel_ambiente(nome_variavel: str) -> str:
    """
    Recupera o valor de uma variável de ambiente obrigatória do arquivo .env.

    Args:
        nome_variavel (str): Nome da variável de ambiente a ser buscada.

    Returns:
        str: Valor da variável de ambiente sem espaços extras nas extremidades.

    Raises:
        VariavelAmbienteNaoEncontrada: Se a variável de ambiente não existir
            ou estiver vazia.
    """
    valor = os.getenv(nome_variavel)
    if not valor or not valor.strip():
        raise VariavelAmbienteNaoEncontrada(nome_variavel)
    return valor.strip()