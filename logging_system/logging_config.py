import logging
from .config import get_variavel_ambiente


def configure_logging() -> None:
    """Configura a saída dos logs para o processo atual."""
    level_name = get_variavel_ambiente("LOG_LEVEL").upper()
    level = getattr(logging, level_name, logging.INFO)

    #Estrutura padrão
    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )