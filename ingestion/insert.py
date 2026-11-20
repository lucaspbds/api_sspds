import logging
from typing import Any

from database.exceptions import ErroOperacaoBanco
from database.repository import inserir_registros
from database.repository import atualizar_registro
from database.repository import criar_cliente_supabase
from database.repository import excluir_arquivo
from database.repository import consultar_registros
from .config import get_variavel_ambiente
from .helpers import recebeInteiro

logger = logging.getLogger(__name__)

tamanho_lote = recebeInteiro(get_variavel_ambiente("INSERT_CHUNK_SIZE"))
def inserir_historico_ingestoes(dados: dict[str, Any], cliente=None) -> int:
    if cliente is None: 
        cliente = criar_cliente_supabase()
    resposta = inserir_registros(tabela="historico_ingestoes", dados=dados, cliente=cliente)
    return resposta[0]['id']

def atualizar_historico_ingestoes(id:int, dados: dict[str, Any], cliente=None) -> list[dict[str, Any]]:
    if cliente is None:
        cliente = criar_cliente_supabase()
    resposta = atualizar_registro(tabela="historico_ingestoes", id_registro=id, coluna_id="id", novos_dados=dados, cliente=cliente)
    return resposta

def inserir_informacoes_arquivo(dados: dict[str, Any], cliente=None) -> int:
    if cliente is None:
        cliente = criar_cliente_supabase()
    resposta = inserir_registros(tabela="informacoes_arquivo", dados=dados, cliente=cliente)
    return resposta[0]['id']

def atualizar_informacoes_arquivo(id:int, dados: dict[str, Any], cliente=None) -> int:
    if cliente is None:
        cliente = criar_cliente_supabase()
    resposta = atualizar_registro(tabela="informacoes_arquivo", id_registro=id, coluna_id="id", novos_dados=dados, cliente=cliente)
    return resposta[0]['id']

def deletar_informacoes_arquivo(id: int, cliente=None) -> None:
    """Remove o registro do arquivo.

    ``ocorrencias_crimes.arquivo_id`` tem ``ON DELETE CASCADE``: todas as
    ocorrências do arquivo são apagadas pelo próprio banco.

    Raises:
        ErroOperacaoBanco: se a exclusão falhar.
    """
    if cliente is None:
        cliente = criar_cliente_supabase()
    try:
        excluir_arquivo(id=id, cliente=cliente)
        logger.info("Registro de arquivo removido (CASCADE nas ocorrências) id=%s", id)
    except Exception as erro:
        logger.error("Erro ao remover registro de arquivo id=%s", id)
        raise ErroOperacaoBanco("exclusao", "informacoes_arquivo") from erro

def inserir_ocorrencias_crimes(dados: list[dict[str, Any]], tamanho_lote=tamanho_lote, cliente=None):
    if cliente is None:
        cliente = criar_cliente_supabase()
    for i in range(0, len(dados), tamanho_lote):
        lote = dados[i:i + tamanho_lote]
        inserir_registros(tabela="ocorrencias_crimes", dados=lote, cliente=cliente)


def listar_informacoes_arquivo(cliente=None) -> list[dict[str, Any]]:
    """Obtém a fotografia dos metadados para uma execução de ingestão."""
    if cliente is None:
        cliente = criar_cliente_supabase()
    return consultar_registros(
        tabela="informacoes_arquivo",
        colunas="id,nome_arquivo,hash_sha256,tipo_crime,serie,periodo_dados,ultimo_mes,data_coleta,atualizado_em,ingestao_id",
        cliente=cliente,
    )


def excluir_arquivos_por_ids(ids: list[int], cliente=None) -> None:
    """Exclui metadados por ID; o CASCADE remove as ocorrências vinculadas."""
    if not ids:
        return
    for arquivo_id in sorted(set(ids)):
        deletar_informacoes_arquivo(id=arquivo_id, cliente=cliente)


def contar_ocorrencias_por_arquivo(arquivo_id: int, cliente=None) -> int:
    """Conta as ocorrências vinculadas a um arquivo para validar a carga."""
    if cliente is None:
        cliente = criar_cliente_supabase()
    resposta = cliente.table("ocorrencias_crimes").select("id", count="exact").eq(
        "arquivo_id", arquivo_id
    ).limit(1).execute()
    return int(getattr(resposta, "count", 0) or 0)
