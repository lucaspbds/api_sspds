from dotenv import load_dotenv 
from app.exception import VariavelAmbienteNaoEncontrada
import os

load_dotenv()

def get_variavel_ambiente(nome_variavel: str) -> str:
    """
    Recupera o valor de uma variável de ambiente obrigatória (arquivo `.env` ou ambiente).

    A API tem a sua própria leitura de configuração, independente do pacote `database/`.

    Args:
        nome_variavel (str): Nome da variável de ambiente a ser buscada.

    Returns:
        str: Valor da variável, sem espaços extras nas extremidades.

    Raises:
        VariavelAmbienteNaoEncontrada: Se a variável não existir ou estiver vazia.
    """
    valor = os.getenv(nome_variavel)
    if not valor or not valor.strip():
        raise VariavelAmbienteNaoEncontrada(nome_variavel)
    return valor.strip()