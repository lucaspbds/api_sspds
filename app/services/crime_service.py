import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from database.exceptions import ErroOperacaoBanco
from database.repository import criar_cliente_supabase

logger = logging.getLogger("app.services.crime_service")

TABELA_OCORRENCIAS = "ocorrencias_crimes"

# Valores **exatos** da coluna `tipo_crime` (os mesmos gerados por
# `ingestion/classifier.py`). Para listar os valores atuais no banco:
#     SELECT DISTINCT tipo_crime FROM ocorrencias_crimes ORDER BY tipo_crime;
TIPO_CVLI = "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
TIPO_PRECONCEITO = "HOMOFOBIA E TRANSFOBIA"
TIPO_FURTO = "FURTO"
TIPO_CVP = "CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP"
TIPO_MARIA_DA_PENHA = "LEI 11.340/06 (LEI MARIA DA PENHA)"
TIPO_CRIMES_SEXUAIS = "CRIMES SEXUAIS"
TIPO_INDIGENAS = "INDÍGENAS VÍTIMAS DE CRIMES"

# Agrupamentos usados pelas rotas específicas.
TIPOS_OPERACIONAIS = (TIPO_FURTO, TIPO_CVP)
TIPOS_COM_VITIMA = (TIPO_MARIA_DA_PENHA, TIPO_CRIMES_SEXUAIS, TIPO_INDIGENAS)

def _normalizar_municipio(valor: Optional[str]) -> Optional[str]:
    """Aplica o mesmo padrão da ingestão (espaços colapsados + Title Case)."""
    if not valor:
        return None
    texto = " ".join(valor.split()).title()
    return texto or None


def _normalizar_tipo(valor: Optional[str]) -> Optional[str]:
    """Os tipos de crime são gravados em caixa alta; espaços extras são removidos."""
    if not valor:
        return None
    texto = " ".join(valor.split()).upper()
    return texto or None


def _consultar(
    *,
    tipos: Optional[Sequence[str]] = None,
    municipio: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Executa a consulta em `ocorrencias_crimes` com filtros opcionais.

    Args:
        tipos: Um ou mais valores exatos de `tipo_crime` (filtro `IN`).
        municipio: Município (igualdade exata, já normalizado).
        data_inicio: Limite inferior (inclusive) de `data_fato`.
        data_fim: Limite superior (inclusive) de `data_fato`.
        limite: Número máximo de registros (deve ser maior que zero).

    Returns:
        Lista de registros, ordenada por `id` para que `limit` seja determinístico.

    Raises:
        ValueError: Se `limite` for <= 0 ou `data_inicio` for posterior a `data_fim`.
        VariavelAmbienteNaoEncontrada / ErroConexaoBanco: Falha ao criar o cliente.
        ErroOperacaoBanco: Falha ao executar a consulta no Supabase.
    """
    if limite is not None and limite <= 0:
        raise ValueError("O limite da consulta deve ser maior que zero.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")

    # Falha na criação (variável ausente/conexão) propaga como exceção tratada em app.exception.
    cliente = criar_cliente_supabase()

    try:
        query = cliente.table(TABELA_OCORRENCIAS).select("*")

        if municipio:
            query = query.eq("municipio", municipio)
        if tipos:
            if len(tipos) == 1:
                query = query.eq("tipo_crime", tipos[0])
            else:
                query = query.in_("tipo_crime", list(tipos))
        if data_inicio:
            query = query.gte("data_fato", data_inicio.isoformat())
        if data_fim:
            query = query.lte("data_fato", data_fim.isoformat())

        query = query.order("id")
        if limite is not None:
            query = query.limit(limite)

        resposta = query.execute()
    except Exception as e:
        logger.error("Erro ao consultar %s: %s", TABELA_OCORRENCIAS, type(e).__name__)
        raise ErroOperacaoBanco("consulta", TABELA_OCORRENCIAS) from e

    dados = resposta.data or []
    logger.info(
        "Consulta concluída tabela=%s registros_retornados=%s",
        TABELA_OCORRENCIAS,
        len(dados),
    )
    return dados


class CrimeService:

    @staticmethod
    def listar_com_filtros(
        municipio: Optional[str] = None,
        tipo_crime: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Consulta geral com filtros dinâmicos (todos opcionais e combináveis).

        - `municipio`: igualdade exata, sem diferenciar maiúsculas/minúsculas
          (a entrada é normalizada para o padrão gravado pela ingestão).
        - `tipo_crime`: valor exato da coluna `tipo_crime` (maiúsculas e espaços
          extras são normalizados).
        - `data_inicio` / `data_fim`: período inclusivo sobre `data_fato`.
        """
        tipo_normalizado = _normalizar_tipo(tipo_crime)
        return _consultar(
            tipos=[tipo_normalizado] if tipo_normalizado else None,
            municipio=_normalizar_municipio(municipio),
            data_inicio=data_inicio,
            data_fim=data_fim,
            limite=limit,
        )

    @staticmethod
    def listar_por_tipo(tipo: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Consulta específica por **um** tipo de crime.

        O valor de `tipo` deve ser exatamente uma das strings presentes na coluna
        `tipo_crime` (veja as constantes `TIPO_*` deste módulo).
        """
        return _consultar(tipos=[tipo], limite=limit)

    @staticmethod
    def listar_por_tipos(
        tipos: Sequence[str], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Consulta específica por **vários** tipos de crime (filtro `IN`), como
        `TIPOS_OPERACIONAIS` e `TIPOS_COM_VITIMA`.
        """
        return _consultar(tipos=tipos, limite=limit)

    @staticmethod
    def listar_ocorrencias(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Consulta simples de ocorrências, sem filtros (mantida para compatibilidade).
        """
        return _consultar(limite=limit)