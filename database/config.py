import logging
import os
from dotenv import load_dotenv
from database.exceptions import VariavelAmbienteNaoEncontrada

load_dotenv()


def configure_logging() -> None:
    """Configura a saída de logs padrão para o módulo de banco de dados."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )


def get_variavel_ambiente(nome_variavel: str) -> str:
    """
    Recupera o valor de uma variável de ambiente obrigatória.
    Lança VariavelAmbienteNaoEncontrada se estiver ausente ou vazia.
    """
    valor = os.getenv(nome_variavel)
    if not valor or not valor.strip():
        raise VariavelAmbienteNaoEncontrada(nome_variavel)
    return valor.strip()