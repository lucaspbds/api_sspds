from .crawler import crawler
from .downloader import download_xlsx
from .validator import validate_xlsx_file
from .classifier import classificar_arquivo
from .normalizer import normalizer
from .cleanup import limpar_pasta_temporaria
from .insert import (inserir_historico_ingestoes, atualizar_historico_ingestoes, 
                     inserir_informacoes_arquivo, atualizar_informacoes_arquivo, 
                     inserir_ocorrencias_crimes)
from logging_system.logging_config import configure_logging 

from datetime import datetime, timezone
import pandas as pd
import logging
import traceback
configure_logging()
logger = logging.getLogger("Pipeline")

def pipeline() -> None:
    """
    Função responsável por executar as etapas principais do processo
    de ingestão dos dados da SSPDS.

    Args:
        Não possui argumentos.

    Return:
        None

    Exception:
        Caso ocorra algum erro durante a execução das etapas do pipeline,
        o erro será retornado pela função responsável pela etapa em que
        o problema ocorrer.
    """
    
    logger.info("Crawler iniciado")
    # O crawler identifica os arquivos disponibilizados pela SSPDS
    # e retorna uma lista contendo os endereços desses arquivos e os tipos de crimes.
    lista_url = crawler()
    id_ingestao = inserir_historico_ingestoes(dados={
        "status": "EM_ANDAMENTO",
        "qtd_arquivos_encontrados": len(lista_url)
    })

    logger.info("Processamento dos dados iniciado")
    arquivos_processados = 0
    arquivos_falhas = 0
    for i in range(len(lista_url)):
        try:    
            filePath_relative = download_xlsx(lista_url[i])
            data_coleta = datetime.now(timezone.utc).isoformat()
            file_validated = validate_xlsx_file(filePath_relative)
            if file_validated["is_new"]:
                file_classified = classificar_arquivo(file_validated)
                if file_validated["name_exists"]:
                    atualizado_em = datetime.now(timezone.utc).isoformat()
                    arquivo_id = atualizar_informacoes_arquivo(id=file_classified["id_registro"], dados={
                        "url_download": lista_url[i],
                        "hash_sha256": file_classified["sha256"],
                        "periodo_dados": None,
                        "tamanho_bytes": file_classified["size_bytes"],
                        "data_coleta": data_coleta,
                        "atualizado_em": atualizado_em,
                        "ingestao_id": id_ingestao
                    })

                else:
                    arquivo_id = inserir_informacoes_arquivo(dados={
                        "nome_arquivo": file_classified["name"],
                        "url_download": lista_url[i],
                        "hash_sha256": file_classified["sha256"],
                        "tipo_crime": file_classified["tipo_ocorrencia"],
                        "periodo_dados": None,
                        "tamanho_bytes": file_classified["size_bytes"],
                        "data_coleta": data_coleta,
                        "ingestao_id": id_ingestao
                    })
                
                df = pd.read_excel(file_classified["path"])
                dados_normalizados = normalizer(df=df, arquivo_id=arquivo_id, 
                            tipo_ocorrencia=file_classified["tipo_ocorrencia"])
                
                inserir_ocorrencias_crimes(dados_normalizados)
                anos = list(map(lambda dado: datetime.fromisoformat(dado["data_fato"]).year, dados_normalizados))
                ano_min = min(anos)
                ano_max = max(anos)
                if ano_min == ano_max:
                    periodo = str(ano_min)
                else:
                    periodo = f"{ano_min} - {ano_max}"
                atualizar_informacoes_arquivo(id=arquivo_id, dados=
                                                {"periodo_dados": periodo})
            arquivos_processados += 1
        except Exception:
            arquivos_falhas += 1
            msg_erro = traceback.format_exc()
            logger.exception(msg_erro)

    logger.info("Processamento dos dados finalizado")
    data_fim = datetime.now(timezone.utc).isoformat()
    atualizar_historico_ingestoes(id=id_ingestao, dados={
        "data_fim": data_fim,
        "status": "SUCESSO",   
        "qtd_arquivos_processados": arquivos_processados,
        "qtd_arquivos_falhas": arquivos_falhas
    })
    limpar_pasta_temporaria()


if __name__ == "__main__":
    pipeline()