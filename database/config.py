import os
from dotenv import load_dotenv
from database.exceptions import VariavelAmbienteNaoEncontrada

load_dotenv()

    
def get_variavel_ambiente(nome_variavel: str) -> str:
    """
    Recupera o valor de uma variável de ambiente obrigatória.
    Lança VariavelAmbienteNaoEncontrada se estiver ausente ou vazia.
    """
    valor = os.getenv(nome_variavel)
    if not valor or not valor.strip():
        raise VariavelAmbienteNaoEncontrada(nome_variavel)
    return valor.strip()