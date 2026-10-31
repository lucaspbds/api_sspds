import hashlib
import logging
from pathlib import Path
from typing import TypedDict

from .exception import DatabaseLookupError, FileValidationError
from .config import get_variavel_ambiente
from .helpers import recebeInteiro
from database.repository import consultar_registros
from logging_system.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)
HASH_CHUNK_SIZE = recebeInteiro(eval(get_variavel_ambiente("HASH_CHUNK_SIZE")))
TEMP_PATH = get_variavel_ambiente("TEMP_PATH")


class ValidatedFile(TypedDict):
    """Metadados de um único arquivo validado."""

    path: str
    name: str
    sha256: str
    is_new: bool
    size_bytes: int
    name_exists: bool
    id_registro: int


def calculate_sha256(file_path: str | Path) -> str:
    """Calcula o SHA-256 do arquivo sem carregá-lo todo na memória.

    Raises:
        FileValidationError: se o arquivo não puder ser lido ou o tamanho do
            bloco de leitura for inválido.
    """
    path = Path(file_path)
    if HASH_CHUNK_SIZE <= 0:
        raise FileValidationError("HASH_CHUNK_SIZE deve ser um inteiro positivo.")

    digest = hashlib.sha256()
    try:
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(HASH_CHUNK_SIZE), b""):
                digest.update(chunk)
    except OSError as exc:
        logger.exception("Não foi possível calcular o hash de %s", path)
        raise FileValidationError(
            f"Não foi possível ler o arquivo para calcular seu SHA-256: {path}"
        ) from exc

    return digest.hexdigest()


def check_hash_in_database(file_hash: str) -> bool:
    """Retorna True se o hash já estiver cadastrado no banco.

    Raises:
        DatabaseLookupError: se o hash for vazio ou a consulta falhar.
    """
    if not file_hash:
        raise DatabaseLookupError("O hash consultado não pode ser vazio.")

    try:
        registros = consultar_registros(
            tabela="informacoes_arquivo",
            filtros={"hash_sha256": file_hash},
        )
    except DatabaseLookupError:
        raise
    except Exception as exc:
        logger.exception("Falha ao consultar o hash no banco de dados")
        raise DatabaseLookupError("Falha ao consultar o hash no banco de dados.") from exc

    return bool(registros)


def check_filename_in_database(file_name: str) -> list:
    """Retorna True se já existir um registro com esse nome de arquivo e o id do registro.

    A comparação é feita pelo campo ``nome_arquivo`` da tabela
    ``informacoes_arquivo``. Se a consulta falhar, propaga DatabaseLookupError.
    """
    if not isinstance(file_name, str) or not file_name.strip():
        raise DatabaseLookupError("O nome do arquivo consultado não pode ser vazio.")

    try:
        registros = consultar_registros(
            tabela="informacoes_arquivo",
            filtros={"nome_arquivo": file_name},
        )

        if registros:
            return [registros[0]['id'], bool(registros)]
        return [None, bool(registros)]
    except DatabaseLookupError:
        raise
    except Exception as exc:
        logger.exception("Falha ao consultar o nome do arquivo no banco de dados")
        raise DatabaseLookupError(
            f"Falha ao consultar o nome do arquivo {file_name!r} no banco de dados."
        ) from exc

    


def validate_xlsx_file(file_path: str | Path) -> ValidatedFile:
    """Valida um único arquivo XLSX e retorna seus metadados.

    O arquivo é verificado, seu SHA-256 é calculado e o banco é consultado
    para determinar se o conteúdo já foi cadastrado e se seu nome já existe.

    Args:
        file_path: caminho para um único arquivo XLSX.

    Returns:
        Dicionário com ``path``, ``name``, ``sha256``, ``is_new``, ``size_bytes``, ``name_exists``
        e ``id_registro``.

    Raises:
        FileValidationError: caminho inexistente, não regular, extensão
            diferente de XLSX ou arquivo ilegível.
        DatabaseLookupError: falha na consulta ao banco de dados.
    """
    path = Path(file_path)
    logger.info("Iniciando validação do arquivo %s", path)

    if not path.exists():
        raise FileValidationError(f"Arquivo não encontrado: {path}")
    if not path.is_file():
        raise FileValidationError(f"O caminho não é um arquivo: {path}")
    if path.suffix.lower() != ".xlsx":
        raise FileValidationError(f"O arquivo não possui extensão XLSX: {path}")

    file_hash = calculate_sha256(path)
    already_exists = check_hash_in_database(file_hash)
    id_registro, name_exists = check_filename_in_database(path.name)

    try:
        relative_path = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        # Mantém um caminho relativo quando o arquivo está fora do diretório
        # de trabalho, evitando expor ou depender de um caminho absoluto.
        relative_path = Path(path.parent.name) / path.name

    file_size = path.stat().st_size
    result: ValidatedFile = {
        "path": relative_path.as_posix(),
        "name": path.name,
        "sha256": file_hash,
        "is_new": not already_exists,
        "size_bytes": file_size,
        "name_exists": name_exists,
        "id_registro": id_registro
    }
    logger.info(
        "Validação concluída para %s (novo=%s, nome_existente=%s)",
        result["name"],
        result["is_new"],
        result["name_exists"],
    )
    return result
