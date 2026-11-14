from logging_system.logging_config import configure_logging
from .config import get_variavel_ambiente
from .exception import CaminhoTemporarioInseguro

import logging
import shutil
from pathlib import Path

configure_logging()
logger = logging.getLogger(__name__)
TEMP_PATH = get_variavel_ambiente("TEMP_PATH")

PASTA_DO_PACOTE = Path(__file__).resolve().parent


def validar_pasta_temporaria(caminho: str | Path = TEMP_PATH) -> Path:
    """Garante que a pasta temporária pode ser apagada sem risco.

    Regras: o caminho precisa ficar **dentro** do diretório de trabalho (nunca
    ser o próprio diretório, um ancestral dele ou algo fora dele) e não pode ser
    a pasta do pacote ``ingestion`` nem um ancestral dela. Isso evita que uma
    configuração como ``TEMP_PATH=.`` ou ``TEMP_PATH=/`` apague código ou dados.

    Returns:
        O caminho absoluto e resolvido, pronto para uso.

    Raises:
        CaminhoTemporarioInseguro: se alguma regra for violada.
    """
    resolvido = Path(caminho).resolve()
    base = Path.cwd().resolve()

    if resolvido == base or base not in resolvido.parents:
        raise CaminhoTemporarioInseguro(
            f"TEMP_PATH deve apontar para uma subpasta do diretório de trabalho "
            f"({base}); recebido: {caminho!s}"
        )
    if resolvido == PASTA_DO_PACOTE or resolvido in PASTA_DO_PACOTE.parents:
        raise CaminhoTemporarioInseguro(
            f"TEMP_PATH não pode ser a pasta do código-fonte nem um ancestral dela: {caminho!s}"
        )
    return resolvido


def limpar_pasta_temporaria(caminho: str | Path = TEMP_PATH) -> None:
    """Remove a pasta temporária e todo o seu conteúdo.

    Raises:
        CaminhoTemporarioInseguro: se o caminho não passar em
            ``validar_pasta_temporaria`` (nada é apagado).
        NotADirectoryError: se o caminho existir, mas não for uma pasta.
        OSError: se a remoção falhar.
    """
    pasta = validar_pasta_temporaria(caminho)
    logger.info("Apagando a pasta %s", caminho)

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


def remover_arquivo_temporario(caminho: str | Path) -> None:
    """Remove um arquivo baixado assim que ele deixa de ser necessário.

    Não lança exceção: falhas de remoção são apenas registradas, pois a pasta
    temporária inteira ainda é apagada ao final da execução.
    """
    try:
        Path(caminho).unlink(missing_ok=True)
    except OSError:
        logger.warning("Não foi possível remover o arquivo temporário: %s", caminho)
