from logging_system.logging_config import configure_logging
from .config import get_variavel_ambiente

import logging
import shutil
from pathlib import Path

configure_logging()
logger = logging.getLogger(__name__)
TEMP_PATH = get_variavel_ambiente("TEMP_PATH")

def limpar_pasta_temporaria(caminho: str | Path = TEMP_PATH) -> None:
    """Remove a pasta temporária e todo o seu conteúdo."""
    logger.info("Apagando a pasta %s", caminho)
    pasta = Path(caminho)

    if not pasta.exists():
        logger.info("Pasta temporária não encontrada: %s", pasta)
        return

    if not pasta.is_dir():
        raise NotADirectoryError(
            f"O caminho não é uma pasta: {pasta}"
        )

    try:
        shutil.rmtree(pasta)
        logger.info("Pasta temporária removida: %s", pasta)
    except OSError:
        logger.exception(
            "Erro ao remover a pasta temporária: %s", pasta
        )
        raise
