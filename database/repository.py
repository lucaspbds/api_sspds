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
        logger.error("Falha ao validar conexão com o banco de dados erro=%s", e)
        raise ErroConexaoBanco("Falha na comunicação com o banco de dados.") from e


def consultar_registros(
    tabela: str,
    filtros: Optional[Dict[str, Any]] = None,
    limite: Optional[int] = None,
    coluna_data: Optional[str] = None,      # Ex: "data_fato"
    data_inicio: Optional[Any] = None,      # Ex: "2026-01-01"
    data_fim: Optional[Any] = None,
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
        coluna_data (Optional[str]): Nome da coluna temporal a ser utilizada no
            filtro por intervalo (ex: 'data_fato', 'data_coleta').
        data_inicio (Optional[Any]): Data ou carimbo temporal inicial do intervalo
            inclusivo (WHERE coluna >= data_inicio).
        data_fim (Optional[Any]): Data ou carimbo temporal final do intervalo
            inclusivo (WHERE coluna <= data_fim).
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
        if coluna_data:
            if data_inicio is not None:
                query = query.gte(coluna_data, str(data_inicio))
            if data_fim is not None:
                query = query.lte(coluna_data, str(data_fim))

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
        logger.error(
            "Erro na operação de consulta tabela=%s erro=%s",
            tabela,
            e,
        )
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
        logger.error(
            "Erro na operação de inserção tabela=%s erro=%s",
            tabela,
            e,
        )
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
            "Erro na operação de atualização tabela=%s id=%s erro=%s",
            tabela,
            id_registro,
            e,
        )
        raise ErroOperacaoBanco("atualizacao", tabela) from e


def excluir_arquivo(id_arquivo:int, cliente: Optional[Client] = None) -> list[Dict[str,Any]]:
    """
    Exclui um registro da tabela 'informacoes_arquivo' a partir do seu ID.

    A exclusão é idempotente: caso nenhum registro seja encontrado para o ID
    informado, retorna uma lista vazia sem lançar exceção. Quando o registro
    existe, todas as ocorrências vinculadas em 'ocorrencias_crimes' também são
    removidas automaticamente pelo banco (ON DELETE CASCADE).

    Args:
        id_arquivo (int): Identificador único do arquivo a ser excluído
            (deve ser um número inteiro maior que zero).
        cliente (Optional[Client]): Instância opcional do cliente Supabase.
            Caso omitido, um novo cliente será instanciado automaticamente.

    Returns:
        List[Dict[str, Any]]: Lista contendo o registro excluído ou lista
            vazia caso o ID não exista na tabela.

    Raises:
        ValueError: Se 'id_arquivo' não for um inteiro válido ou for menor
            ou igual a zero.
        ErroOperacaoBanco: Se ocorrer falha de integridade, permissão ou
            comunicação ao excluir o registro no Supabase.
    """
    if isinstance(id_arquivo, bool) or not isinstance(id_arquivo, int) or id_arquivo <= 0:
        logger.error("id_arquivo inválido")
        raise ValueError("O id_arquivo deve ser um inteiro maior que 0")
    db = cliente or criar_cliente_supabase()
    try:
        resposta = db.table("informacoes_arquivo").delete().eq("id", id_arquivo).execute()
        removidos = resposta.data or []
        if not removidos:
            logger.warning("Nenhum registro encontrado para o id=%s",id_arquivo)
        else:
            logger.info("O registro de id=%s foi removido CASCADE removeu ocorrências associadas", id_arquivo)
        return removidos
    except Exception as e:
        logger.error(
            "Erro na operação de exclusão tabela=informacoes_arquivo id=%s erro=%s",
            id_arquivo,
            e,
        )
        raise ErroOperacaoBanco("exclusao", "informacoes_arquivo") from e


def contar_ocorrencias_por_arquivo(arquivo_id:int, cliente: Optional[Client] = None) -> int:
    """
    Conta o número de ocorrências vinculadas a um arquivo específico na tabela 'ocorrencias_crimes'.

    Args:
        arquivo_id (int): Identificador único do arquivo para o qual as ocorrências serão contadas.
        cliente (Optional[Client]): Instância opcional do cliente Supabase.
            Caso omitido, um novo cliente será instanciado automaticamente.

    Returns:
        int: Número de ocorrências associadas ao arquivo especificado.

    Raises:
        ValueError: Se 'arquivo_id' não for um inteiro válido ou for menor
            ou igual a zero.
        ErroOperacaoBanco: Se ocorrer falha de comunicação ou consulta ao Supabase.
    """
    if isinstance(arquivo_id, bool) or not isinstance(arquivo_id, int) or arquivo_id <= 0:
        logger.error("arquivo_id inválido para contagem")
        raise ValueError("O arquivo_id deve ser um inteiro maior que 0")
    
    db = cliente or criar_cliente_supabase()
    try:
        resposta = (
            db.table("ocorrencias_crimes")
            .select("id", count="exact", head=True)
            .eq("arquivo_id", arquivo_id)
            .execute()
        )
    except Exception as e:
        logger.error(
            "Erro na operação de contagem tabela=ocorrencias_crimes arquivo_id=%s erro=%s",
            arquivo_id,
            e,
        )
        raise ErroOperacaoBanco("contagem", "ocorrencias_crimes") from e

    if resposta.count is None:
        logger.error("Contagem retornou None para arquivo_id=%s", arquivo_id)
        raise ErroOperacaoBanco(
            "contagem",
            "ocorrencias_crimes",
            "O banco não retornou a contagem de registros.",
        )

    total = int(resposta.count)
    logger.info("Contagem de ocorrências para arquivo_id=%s: %s", arquivo_id, total)
    return total