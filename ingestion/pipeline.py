import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pandas as pd

from database.repository import criar_cliente_supabase
from logging_system.logging_config import configure_logging

from .classifier import classificar_arquivo
from .cleanup import (
    limpar_pasta_temporaria,
    remover_arquivo_temporario,
    validar_pasta_temporaria,
)

from .crawler import crawler, obter_serie_origem
from .downloader import download_xlsx
from .exception import PlanilhaSemRegistros
from .insert import (
    atualizar_historico_ingestoes,
    atualizar_informacoes_arquivo,
    deletar_informacoes_arquivo,
    inserir_historico_ingestoes,
    inserir_informacoes_arquivo,
    inserir_ocorrencias_crimes,
    listar_informacoes_arquivo,
    excluir_arquivos_por_ids,
    contar_ocorrencias_por_arquivo,
)
from .normalizer import normalizer
from .validator import validate_xlsx_file
from .versionamento import (
    identificar_serie, periodo_historico, extrair_ultimo_mes, classificar_versao,
    ids_orfaos_antigos, ids_reconciliacao,
)

configure_logging()
logger = logging.getLogger("ingestion.pipeline")

MAX_ERROS_NA_MENSAGEM = 20
MAX_CARACTERES_MENSAGEM = 8000

# Valores da coluna `historico_ingestoes.status`.
STATUS_INGESTAO_EM_ANDAMENTO = "EM_ANDAMENTO"
STATUS_INGESTAO_SUCESSO = "SUCESSO"
STATUS_INGESTAO_PARCIAL = "PARCIAL"
STATUS_INGESTAO_FALHA = "FALHA"

class IntegridadeVersaoError(ValueError):
    """Nova versão não atende aos critérios mínimos para substituir a anterior."""


class ResultadoArquivo(Enum):
    """Desfecho de um arquivo que não gerou exceção."""

    CARREGADO = "carregado"
    IGNORADO = "ignorado"
    AVISO = "aviso"


@dataclass
class ResumoIngestao:
    """Contadores e erros de uma execução do pipeline."""

    encontrados: int = 0
    carregados: int = 0
    ignorados: int = 0
    falhas: int = 0
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    erro_fatal: str | None = None

    @property
    def status(self) -> str:
        """Status gravado em ``historico_ingestoes``.

        SUCESSO: nenhuma falha. PARCIAL: houve falhas, mas ao menos um arquivo
        foi carregado ou reconhecido como já ingerido. FALHA: erro fatal
        (ex.: crawler) ou nenhum arquivo teve êxito.
        """
        if self.erro_fatal is None and self.falhas == 0:
            return STATUS_INGESTAO_SUCESSO
        if self.erro_fatal is None and (self.carregados + self.ignorados) > 0:
            return STATUS_INGESTAO_PARCIAL
        return STATUS_INGESTAO_FALHA

    def montar_mensagem_erro(self) -> str | None:
        """Texto para ``historico_ingestoes.mensagem_erro`` (None se não houve erro)."""
        partes: list[str] = []
        if self.erro_fatal:
            partes.append(f"Execução interrompida: {self.erro_fatal}")
        if self.avisos:
            partes.append(f"{len(self.avisos)} aviso(s):")
            partes.extend(self.avisos[:MAX_ERROS_NA_MENSAGEM])
        if self.erros:
            partes.append(f"{len(self.erros)} arquivo(s) com falha:")
            partes.extend(self.erros[:MAX_ERROS_NA_MENSAGEM])
            restantes = len(self.erros) - MAX_ERROS_NA_MENSAGEM
            if restantes > 0:
                partes.append(f"... e mais {restantes} falha(s); veja os logs.")
        if not partes:
            return None
        return "\n".join(partes)[:MAX_CARACTERES_MENSAGEM]


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def ler_planilha(caminho: str) -> pd.DataFrame:
    """Lê a planilha (primeira aba). Isolada para facilitar testes e evoluções."""
    return pd.read_excel(caminho)


def calcular_periodo(dados: list[dict[str, Any]]) -> str:
    """Retorna ``"2024"`` ou ``"2019 - 2024"`` a partir de ``data_fato``."""
    anos = [datetime.fromisoformat(dado["data_fato"]).year for dado in dados]
    ano_min, ano_max = min(anos), max(anos)
    return str(ano_min) if ano_min == ano_max else f"{ano_min} - {ano_max}"


def desfazer_carga(arquivo_id: int, cliente: Any) -> None:
    """Compensa uma carga que falhou, sem mascarar o erro original.

    Exclui o registro do arquivo; o ON DELETE CASCADE apaga as ocorrências já
    inseridas. Assim não sobram dados parciais na API nem hash "queimado".

    Se a exclusão também falhar, o registro fica com ``periodo_dados`` nulo, o
    que o validator interpreta como carga incompleta: o arquivo será
    reprocessado (e o registro antigo, removido) na próxima execução.
    """
    try:
        deletar_informacoes_arquivo(id=arquivo_id, cliente=cliente)
    except Exception:
        logger.exception(
            "Não foi possível desfazer a carga do arquivo id=%s; ele permanece "
            "incompleto (periodo_dados nulo) e será reprocessado.",
            arquivo_id,
        )


def carregar_arquivo(
    url: str, classificado: dict[str, Any], data_coleta: str, id_ingestao: int, cliente: Any
) -> None:
    """Registra o arquivo, normaliza e carrega suas ocorrências.

    ``periodo_dados`` é gravado como **último passo**: é ele que marca o
    arquivo como totalmente carregado. Qualquer falha antes disso desfaz a
    carga (``desfazer_carga``).
    """
    arquivo_id = inserir_informacoes_arquivo(
        dados={
            "nome_arquivo": classificado["name"],
            "url_download": url,
            "hash_sha256": classificado["sha256"],
            "tipo_crime": classificado["tipo_ocorrencia"],
            "serie": classificado["serie"],
            "ultimo_mes": classificado.get("ultimo_mes"),
            "periodo_dados": None,
            "tamanho_bytes": classificado["size_bytes"],
            "data_coleta": data_coleta,
            "ingestao_id": id_ingestao,
        },
        cliente=cliente,
    )

    publicado = False
    try:
        df = classificado.get("_dataframe")
        if df is None:
            df = ler_planilha(classificado["path"])
        dados_normalizados = normalizer(
            df=df, arquivo_id=arquivo_id, tipo_ocorrencia=classificado["tipo_ocorrencia"]
        )
        if not dados_normalizados:
            raise PlanilhaSemRegistros(classificado["name"])

        inserir_ocorrencias_crimes(dados_normalizados, cliente=cliente)
        total_novo = contar_ocorrencias_por_arquivo(arquivo_id, cliente=cliente)
        ids_antigos = classificado.get("ids_substituir", [])
        for antigo in classificado.get("_estado_arquivos", []):
            if antigo.get("id") in ids_antigos:
                total_antigo = contar_ocorrencias_por_arquivo(antigo["id"], cliente=cliente)
                if total_novo < total_antigo:
                    raise IntegridadeVersaoError(
                        f"Nova versão possui menos ocorrências ({total_novo}) que a anterior "
                        f"({total_antigo}); publicação bloqueada."
                    )
        atualizar_informacoes_arquivo(
            id=arquivo_id,
            dados={"periodo_dados": classificado["periodo_dados"], "atualizado_em": agora_utc()},
            cliente=cliente,
        )
        publicado = True
        try:
            excluir_arquivos_por_ids(ids_antigos, cliente=cliente)
        except Exception:
            # A versão nova já está publicada; preservar ambas para reconciliação.
            logger.exception("Falha ao excluir versões substituídas; reconciliação pendente.")
    except Exception:
        if not publicado:
            desfazer_carga(arquivo_id, cliente)
        else:
            logger.exception("Falha após publicação; mantendo a nova versão completa id=%s", arquivo_id)
        raise


def processar_arquivo(
    url: str, id_ingestao: int, cliente: Any,
    estado_arquivos: list[dict[str, Any]] | None = None,
    avisos_execucao: list[str] | None = None,
) -> ResultadoArquivo:
    """Baixa, valida e (se for inédito) carrega um arquivo.

    Raises:
        Exception: qualquer falha do arquivo; quem chama contabiliza e segue.
    """
    caminho = None
    try:
        caminho = download_xlsx(url)
        data_coleta = agora_utc()
        validado = validate_xlsx_file(caminho, registros=estado_arquivos, cliente=cliente)

        if not validado["is_new"]:
            logger.info("Conteúdo já ingerido, arquivo ignorado: %s", validado["name"])
            return ResultadoArquivo.IGNORADO

        classificado = classificar_arquivo(validado)
        df_inspecao = ler_planilha(classificado["path"])
        # A seção/URL é a fonte primária; o nome é fallback para execuções
        # isoladas e arquivos históricos com intervalo explícito.
        serie = obter_serie_origem(url) or identificar_serie(classificado["name"])
        if serie == "historica":
            periodo = periodo_historico(classificado["name"])
            datas_historicas = pd.to_datetime(df_inspecao.get("Data"), errors="coerce").dropna()
            if datas_historicas.empty:
                raise ValueError("Não foi possível validar o período do arquivo histórico.")
            inicio, fim = map(int, periodo.split("-"))
            if int(datas_historicas.dt.year.min()) != inicio or int(datas_historicas.dt.year.max()) != fim:
                raise ValueError(
                    f"Datas da planilha não correspondem ao intervalo histórico {periodo}."
                )
            ultimo_mes = None
        else:
            datas = pd.to_datetime(df_inspecao.get("Data"), errors="coerce").dropna()
            if datas.empty:
                raise ValueError("Não foi possível identificar o período da série corrente.")
            anos = sorted(set(int(ano) for ano in datas.dt.year))
            if len(anos) != 1:
                raise ValueError(f"Arquivo corrente contém mais de um ano: {anos}.")
            periodo = str(anos[0])
            ultimo_mes = int(datas.dt.month.max())
            mes_no_nome = extrair_ultimo_mes(classificado["name"])
            if mes_no_nome is not None and mes_no_nome != ultimo_mes:
                raise ValueError(
                    f"Mês do nome ({mes_no_nome}) diverge do último mês dos dados ({ultimo_mes})."
                )
        estado = estado_arquivos if estado_arquivos is not None else listar_informacoes_arquivo(cliente=cliente)
        classificado.update({
            "serie": serie, "periodo_dados": periodo, "ultimo_mes": ultimo_mes,
            "tipo_crime": classificado["tipo_ocorrencia"],
            "_dataframe": df_inspecao, "_estado_arquivos": estado,
        })
        classificado.update(classificar_versao(classificado, estado))
        if classificado.get("avisos"):
            mensagem = f"{classificado['name']}: {'; '.join(classificado['avisos'])}"
            logger.warning("Classificação ambígua; versão anterior preservada: %s", mensagem)
            if avisos_execucao is not None:
                avisos_execucao.append(mensagem)
            return ResultadoArquivo.AVISO
        try:
            carregar_arquivo(url, classificado, data_coleta, id_ingestao, cliente)
        except IntegridadeVersaoError as erro:
            mensagem = f"{classificado['name']}: {erro}"
            logger.warning("Publicação bloqueada por divergência de integridade: %s", mensagem)
            if avisos_execucao is not None:
                avisos_execucao.append(mensagem)
            return ResultadoArquivo.AVISO
        return ResultadoArquivo.CARREGADO
    finally:
        if caminho is not None:
            remover_arquivo_temporario(caminho)


def finalizar_historico(id_ingestao: int, resumo: ResumoIngestao, cliente: Any) -> None:
    try:
        atualizar_historico_ingestoes(
            id=id_ingestao,
            dados={
                "data_fim": agora_utc(),
                "status": resumo.status,
                "qtd_arquivos_encontrados": resumo.encontrados,
                "qtd_arquivos_processados": resumo.carregados,
                "qtd_arquivos_falhas": resumo.falhas,
                "mensagem_erro": resumo.montar_mensagem_erro(),
            },
            cliente=cliente,
        )
    except Exception:
        logger.exception("Não foi possível fechar o histórico de ingestão id=%s", id_ingestao)


def limpar_temporarios() -> None:
    try:
        limpar_pasta_temporaria()
    except Exception:
        logger.exception("Falha ao limpar a pasta temporária")


def pipeline() -> ResumoIngestao:
    """Executa a ingestão completa dos dados da SSPDS.

    O registro em ``historico_ingestoes`` é criado antes do crawler e sempre
    fechado ao final (``finally``), com status e ``mensagem_erro``. A pasta
    temporária também é sempre limpa. Falhas por arquivo não interrompem os
    demais; falhas fatais (ex.: crawler) são relançadas depois do fechamento.

    Returns:
        ResumoIngestao: contadores da execução.

    Raises:
        CaminhoTemporarioInseguro: TEMP_PATH inválido (antes de qualquer registro).
        Exception: erro fatal fora do laço por arquivo.
    """
    validar_pasta_temporaria()

    cliente = criar_cliente_supabase()
    id_ingestao = inserir_historico_ingestoes(
        dados={"status": STATUS_INGESTAO_EM_ANDAMENTO}, cliente=cliente
    )
    resumo = ResumoIngestao()

    try:
        logger.info("Crawler iniciado")
        estado_inicial = listar_informacoes_arquivo(cliente=cliente)
        ids_orfaos = ids_orfaos_antigos(estado_inicial)
        excluir_arquivos_por_ids(ids_orfaos, cliente=cliente)
        if ids_orfaos:
            removidos = set(ids_orfaos)
            estado_inicial = [r for r in estado_inicial if r.get("id") not in removidos]
        lista_url = crawler()
        resumo.encontrados = len(lista_url)

        logger.info("Processamento dos dados iniciado (%s arquivos)", resumo.encontrados)
        for indice, url in enumerate(lista_url, start=1):
            logger.info("Arquivo %s/%s: %s", indice, resumo.encontrados, url)
            try:
                resultado = processar_arquivo(
                    url, id_ingestao, cliente, estado_inicial, resumo.avisos
                )
            except Exception as erro:
                resumo.falhas += 1
                resumo.erros.append(f"{url}: {type(erro).__name__}: {erro}")
                logger.exception("Falha ao processar %s", url)
                continue

            if resultado is ResultadoArquivo.IGNORADO:
                resumo.ignorados += 1
            elif resultado is ResultadoArquivo.AVISO:
                continue
            else:
                resumo.carregados += 1
                # Atualiza a fotografia após a publicação/exclusão confirmada.
                estado_inicial[:] = listar_informacoes_arquivo(cliente=cliente)

        estado_final = listar_informacoes_arquivo(cliente=cliente)
        excluir_arquivos_por_ids(ids_reconciliacao(estado_final), cliente=cliente)
        logger.info(
            "Processamento finalizado: %s carregados, %s ignorados, %s falhas",
            resumo.carregados, resumo.ignorados, resumo.falhas,
        )
    except BaseException as erro:
        resumo.erro_fatal = f"{type(erro).__name__}: {erro}"
        logger.error("Ingestão interrompida por erro fatal", exc_info=True)
        raise
    finally:
        finalizar_historico(id_ingestao, resumo, cliente)
        limpar_temporarios()

    return resumo


def main() -> int:
    """Executa o pipeline e devolve o código de saída do processo.

    0 somente se não houve nenhuma falha; 1 se algum arquivo falhou ou se
    houve erro fatal.
    """
    try:
        resumo = pipeline()
    except Exception:
        return 1
    return 0 if resumo.falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
