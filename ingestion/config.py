from dotenv import load_dotenv 
from exception import VariavelAmbienteNaoEncontrada
import os

load_dotenv()

def get_variavel_ambiente(nome_variavel:str):
    """
    Função responsável por capturar a variável de ambiente do arquivo .env.
    Args:
        string nome_variavel: nome dado a variável de ambiente.
        
    Return:
        variavel_ambiente : valor da variável de ambiente contida na .env.

    Exception:
        Caso a variável não exista, vai retornar um erro indicando que não encontrou a variável de ambiente.
    """
    variavel_ambiente = os.getenv(nome_variavel)
    if not variavel_ambiente:
        raise VariavelAmbienteNaoEncontrada(nome_variavel)
    return variavel_ambiente 
    