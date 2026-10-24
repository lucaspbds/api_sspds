import logging
from typing import Any, Dict, List, Optional, Union
import httpx
from supabase import Client, ClientOptions, create_client

from database.config import configure_logging, get_variavel_ambiente
from database.exceptions import (
    ErroConexaoBanco,
    ErroOperacaoBanco,
    VariavelAmbienteNaoEncontrada,
)

configure_logging()
logger = logging.getLogger("database.repository")


def criar_cliente_supabase() -> Client:
    """
    Inicializa e retorna o cliente de conexão com o Supabase
    configurando o cliente HTTP (httpx) com timeout explícito.
    """
    try:
        url = get_variavel_ambiente("SUPABASE_URL")
        key = get_variavel_ambiente("SUPABASE_KEY")
        opcoes = ClientOptions(httpx_client=httpx.Client(timeout=10.0))
        cliente = create_client(url, key, options=opcoes)
        logger.info("Cliente Supabase inicializado com sucesso url=%s", url)
        return cliente
    except VariavelAmbienteNaoEncontrada as e:
        logger.error("Configuração ausente ao conectar ao banco: %s", e)
        raise
    except Exception as e:
        logger.error("Erro ao inicializar cliente Supabase: %s", type(e).__name__)
        raise ErroConexaoBanco("Não foi possível inicializar o cliente do Supabase.") from e


def validar_conexao(cliente: Optional[Client] = None) -> bool:
    """
    Valida se a conexão com o banco está ativa realizando uma leitura leve.
    """
    db = cliente or criar_cliente_supabase()
    try:
        db.table("historico_ingestoes").select("id").limit(1).execute()
        logger.info("Conexão com o banco de dados validada com sucesso")
        return True
    except Exception as e:
        logger.error("Falha ao validar conexão com o banco de dados")
        raise ErroConexaoBanco("Falha na comunicação com o banco de dados.") from e


def consultar_registros(
    tabela: str,
    filtros: Optional[Dict[str, Any]] = None,
    limite: Optional[int] = None,
    colunas: str = "*",
    cliente: Optional[Client] = None,
) -> List[Dict[str, Any]]:
    """
    Realiza leitura (SELECT) em uma tabela do banco com filtros e limite opcionais.
    """
    if not tabela or not tabela.strip():
        logger.error("Tentativa de consulta com nome de tabela vazio")
        raise ValueError("O nome da tabela não pode ser vazio.")

    if limite is not None and limite <= 0:
        logger.error("Tentativa de consulta com limite inválido limite=%s", limite)
        raise ValueError("O limite da consulta deve ser maior que zero.")

    db = cliente or criar_cliente_supabase()

    try:
        query = db.table(tabela).select(colunas)

        if filtros:
            for coluna, valor in filtros.items():
                query = query.eq(coluna, valor)

        if limite is not None:
            query = query.limit(limite)

        resposta = query.execute()
        dados = resposta.data or []
        logger.info(
            "Consulta concluída tabela=%s registros_retornados=%s",
            tabela,
            len(dados),
        )
        return dados
    except Exception as e:
        logger.error("Erro ao consultar registros tabela=%s", tabela)
        raise ErroOperacaoBanco("consulta", tabela) from e


def inserir_registros(
    tabela: str,
    dados: Union[Dict[str, Any], List[Dict[str, Any]]],
    cliente: Optional[Client] = None,
) -> List[Dict[str, Any]]:
    """
    Realiza inserção (INSERT) de um ou mais registros em uma tabela do banco.
    """
    if not tabela or not tabela.strip():
        logger.error("Tentativa de inserção com nome de tabela vazio")
        raise ValueError("O nome da tabela não pode ser vazio.")

    if not dados:
        logger.error("Tentativa de inserção com payload vazio tabela=%s", tabela)
        raise ValueError("Os dados para inserção não podem ser vazios.")

    db = cliente or criar_cliente_supabase()

    try:
        resposta = db.table(tabela).insert(dados).execute()
        inseridos = resposta.data or []
        logger.info(
            "Inserção concluída tabela=%s registros_inseridos=%s",
            tabela,
            len(inseridos),
        )
        return inseridos
    except Exception as e:
        logger.error("Erro ao inserir registros tabela=%s", tabela)
        raise ErroOperacaoBanco("insercao", tabela) from e


def atualizar_registro(
    tabela: str,
    id_registro: int,
    novos_dados: Dict[str, Any],
    coluna_id: str = "id",
    cliente: Optional[Client] = None,
) -> List[Dict[str, Any]]:
    """
    Realiza atualização (UPDATE) de um registro específico pelo seu identificador.
    """
    if not tabela or not tabela.strip():
        logger.error("Tentativa de atualização com nome de tabela vazio")
        raise ValueError("O nome da tabela não pode ser vazio.")

    if not novos_dados:
        logger.error("Tentativa de atualização sem novos dados tabela=%s", tabela)
        raise ValueError("Os dados para atualização não podem ser vazios.")

    db = cliente or criar_cliente_supabase()

    try:
        resposta = (
            db.table(tabela)
            .update(novos_dados)
            .eq(coluna_id, id_registro)
            .execute()
        )
        atualizados = resposta.data or []
        logger.info(
            "Atualização concluída tabela=%s id=%s registros_afetados=%s",
            tabela,
            id_registro,
            len(atualizados),
        )
        return atualizados
    except Exception as e:
        logger.error(
            "Erro ao atualizar registro tabela=%s id=%s",
            tabela,
            id_registro,
        )
        raise ErroOperacaoBanco("atualizacao", tabela) from e