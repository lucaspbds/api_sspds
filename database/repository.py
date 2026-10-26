import logging
from typing import Any, Dict, List, Optional, Union
import httpx
from supabase import Client, ClientOptions, create_client

from logging_system.logging_config import configure_logging
from database.config import get_variavel_ambiente
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
    configurando o cliente HTTP (httpx) com timeout explícito de 10 segundos.

    Args:
        Nenhum.

    Returns:
        Client: Instância autenticada do cliente Supabase.

    Raises:
        VariavelAmbienteNaoEncontrada: Se as variáveis obrigatórias 'SUPABASE_URL'
            ou 'SUPABASE_KEY' não estiverem definidas no ambiente.
        ErroConexaoBanco: Se ocorrer falha ao inicializar o cliente do Supabase.
    """
    try:
        url = get_variavel_ambiente("SUPABASE_URL")
        key = get_variavel_ambiente("SUPABASE_KEY")
        opcoes = ClientOptions(httpx_client=httpx.Client(timeout=10.0))
        cliente = create_client(url, key, options=opcoes)
        logger.info("Cliente Supabase inicializado com sucesso")
        return cliente
    except VariavelAmbienteNaoEncontrada as e:
        logger.error("Configuração ausente ao conectar ao banco: %s", e)
        raise
    except Exception as e:
        logger.error("Erro ao inicializar cliente Supabase: %s", type(e).__name__)
        raise ErroConexaoBanco("Não foi possível inicializar o cliente do Supabase.") from e


def validar_conexao(cliente: Optional[Client] = None) -> bool:
    """
    Valida se a conexão com o banco de dados está ativa realizando uma leitura leve.

    Args:
        cliente (Optional[Client]): Instância opcional do cliente Supabase já criada.
            Caso omitido, um novo cliente será instanciado automaticamente.

    Returns:
        bool: True se a comunicação com o banco ocorrer com sucesso.

    Raises:
        VariavelAmbienteNaoEncontrada: Se 'cliente' não for informado e faltar
            variável de ambiente ao criar a conexão.
        ErroConexaoBanco: Se houver falha na comunicação ou autenticação com o banco.
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

    Args:
        tabela (str): Nome da tabela a ser consultada no banco de dados.
        filtros (Optional[Dict[str, Any]]): Dicionário de pares {coluna: valor}
            para filtrar os registros por igualdade.
        limite (Optional[int]): Quantidade máxima de registros a serem retornados
            (deve ser maior que zero).
        colunas (str): Colunas a serem selecionadas separadas por vírgula (padrão '*').
        cliente (Optional[Client]): Instância opcional do cliente Supabase.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários representando os registros encontrados.

    Raises:
        ValueError: Se o nome da tabela for vazio ou se o limite for menor ou igual a zero.
        ErroOperacaoBanco: Se ocorrer falha na execução da consulta junto ao Supabase.
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

    Args:
        tabela (str): Nome da tabela onde os dados serão inseridos.
        dados (Union[Dict[str, Any], List[Dict[str, Any]]]): Dicionário (para um
            único registro) ou lista de dicionários (para inserção em lote).
        cliente (Optional[Client]): Instância opcional do cliente Supabase.

    Returns:
        List[Dict[str, Any]]: Lista contendo os registros recém-inseridos no banco.

    Raises:
        ValueError: Se o nome da tabela for vazio ou se 'dados' estiver vazio.
        ErroOperacaoBanco: Se ocorrer falha de integridade, constraint ou comunicação
            ao inserir os registros no Supabase.
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

    Args:
        tabela (str): Nome da tabela onde o registro será atualizado.
        id_registro (int): Identificador único (ID) do registro a ser modificado.
        novos_dados (Dict[str, Any]): Dicionário contendo as colunas e os novos
            valores a serem atualizados.
        coluna_id (str): Nome da coluna chave primária usada no filtro (padrão 'id').
        cliente (Optional[Client]): Instância opcional do cliente Supabase.

    Returns:
        List[Dict[str, Any]]: Lista contendo o registro atualizado retornado pelo banco.

    Raises:
        ValueError: Se o nome da tabela for vazio ou se 'novos_dados' estiver vazio.
        ErroOperacaoBanco: Se ocorrer falha durante a atualização no Supabase.
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