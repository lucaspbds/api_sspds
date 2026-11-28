#Responsável por capturar as configurações necessárias para o serviço de ingestão
# no arquivo .env 
from dotenv import load_dotenv 
from .exception import VariavelAmbienteNaoEncontrada
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

def get_intervalo_maximo_anos() -> int:
    """
    Função responsável por capturar a variável de ambiente INTERVALO_MAXIMO_ANOS do arquivo .env.
    Return:
        int : valor da variável de ambiente contida na .env.
    """
    intervalo_maximo_anos = get_variavel_ambiente("INTERVALO_MAXIMO_ANOS").strip().title()
    if intervalo_maximo_anos is None or intervalo_maximo_anos == "None" or intervalo_maximo_anos == "0":
        return None
    return int(intervalo_maximo_anos)
    