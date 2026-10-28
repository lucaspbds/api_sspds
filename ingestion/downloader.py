import logging
import os
import tempfile as tempfile_module
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from .exception import (
    DownloadConnectionError,
    DownloadError,
    DownloadHTTPError,
    DownloadTimeoutError,
    FileWriteError,
)
from .config import get_variavel_ambiente
from .helpers import recebeInteiro
logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = recebeInteiro(get_variavel_ambiente("DOWNLOADER_TIMEOUT"))
CHUNK_SIZE = recebeInteiro(eval(get_variavel_ambiente("CHUNK_SIZE")))
DEFAULT_PATH = get_variavel_ambiente("TEMP_PATH")

def download_xlsx(url: str,
destination_dir: str | Path = DEFAULT_PATH,
filename: str | None = None,
timeout: int = TIMEOUT_SECONDS,
) -> Path:
    
    """Baixa um arquivo XLSX e retorna o caminho do arquivo salvo.

    O diretório de destino é criado automaticamente. O download é gravado
    primeiro em um arquivo temporário parcial e só recebe o nome final após
    a transferência terminar com sucesso, evitando deixar um XLSX incompleto
    com aparência de arquivo pronto.

    Args:
        url: URL HTTP(S) do arquivo XLSX.
        destination_dir: Diretório em que o arquivo será armazenado.
        filename: Nome opcional para o arquivo. Se omitido, usa o nome
            extraído da URL.
        timeout: Tempo limite, em segundos, para cada operação de leitura
            da requisição.

    Returns:
        Caminho relativo do arquivo XLSX concluído.

    Raises:
        DownloadError: URL inválida, nome inválido ou falha inesperada
            durante o download.
        DownloadHTTPError: resposta HTTP com status de erro.
        DownloadTimeoutError: tempo limite excedido.
        DownloadConnectionError: falha de conexão.
        FileWriteError: falha ao criar ou gravar o arquivo local.
    """
    logger.info("Download dos arquivos iniciado")
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise DownloadError("A URL deve ser HTTP(S) e conter um host válido.")

    resolved_filename = Path(unquote(parsed_url.path)).name or filename
    if not resolved_filename:
        raise DownloadError("Não foi possível determinar o nome do arquivo; informe nome do arquivo.")
    if Path(resolved_filename).name != resolved_filename:
        raise DownloadError("filename deve conter apenas o nome, sem diretórios.")
    if Path(resolved_filename).suffix.lower() != ".xlsx":
        raise DownloadError("O nome do arquivo de destino deve terminar em .xlsx.")
    if timeout <= 0:
        raise DownloadError("timeout deve ser maior que zero.")

    destination = Path(destination_dir)
    try:
        destination.mkdir(parents=True, exist_ok=True)
        #Diretório relativo
        destination = destination.resolve().relative_to(Path.cwd().resolve())
    except OSError as exc:
        logger.exception("Não foi possível criar o diretório %s", destination)
        raise FileWriteError(f"Não foi possível criar o diretório de destino: {destination}") from exc

    partial_path: Path | None = None
    final_path = destination / resolved_filename

    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()

            # O arquivo parcial fica no mesmo diretório para permitir uma
            # substituição atômica no mesmo sistema de arquivos.
            file_descriptor, partial_name = tempfile_module.mkstemp(
                prefix=f".{resolved_filename}.",
                suffix=".part",
                dir=destination,
            )
            partial_path = Path(partial_name)

            try:
                with os.fdopen(file_descriptor, "wb") as output:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            except OSError as exc:
                logger.exception("Falha ao gravar o download em %s", partial_path)
                raise FileWriteError(
                    f"Falha ao gravar o arquivo em disco: {final_path}"
                ) from exc

        partial_path.replace(final_path)
        logger.info("Arquivo XLSX baixado com sucesso: %s", final_path)
        return final_path

    except requests.exceptions.Timeout as exc:
        logger.warning("Timeout ao baixar %s", url)
        raise DownloadTimeoutError(
            f"O download excedeu o timeout de {timeout} segundos."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "desconhecido"
        logger.warning("Erro HTTP %s ao baixar %s", status, url)
        raise DownloadHTTPError(f"Falha HTTP {status} ao baixar o arquivo.") from exc
    except requests.exceptions.ConnectionError as exc:
        logger.warning("Erro de conexão ao baixar %s", url)
        raise DownloadConnectionError(
            f"Não foi possível conectar ao servidor para baixar: {url}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        logger.exception("Erro de requisição ao baixar %s", url)
        raise DownloadError(f"Falha na requisição HTTP: {exc}") from exc
    except OSError as exc:
        logger.exception("Falha de sistema de arquivos ao salvar %s", final_path)
        raise FileWriteError(f"Falha ao salvar o arquivo: {final_path}") from exc
    
    #Limpeza de arquivos falhos
    finally:
        if partial_path is not None and partial_path.exists():
            try:
                partial_path.unlink()
            except OSError:
                logger.warning("Não foi possível remover arquivo parcial: %s", partial_path)
