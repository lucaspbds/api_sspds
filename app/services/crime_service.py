import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from database.exceptions import (
    ErroConexaoBanco,
    ErroOperacaoBanco,
)
from database.exceptions import (
    VariavelAmbienteNaoEncontrada as VariavelAmbienteNaoEncontradaBanco,
)
from database.repository import consultar_registros, criar_cliente_supabase

logger = logging.getLogger("app.services.crime_service")

TABELA_OCORRENCIAS = "ocorrencias_crimes"
COLUNA_DATA = "data_fato"

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


def _normalizar_texto(valor: Optional[str]) -> Optional[str]:
    """
    Aplica o mesmo padrão da ingestão (`normalizar_texto`): espaços colapsados + Title Case.
    Usado nos filtros de texto livre (município, AIS, natureza, gênero etc.), que são
    gravados nesse formato. Retorna `None` para valores vazios.
    """
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


def _consultar_varios_tipos(
    filtros: Dict[str, Any],
    tipos: Sequence[str],
    data_inicio: Optional[date],
    data_fim: Optional[date],
    limite: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Consulta com filtro `IN` em `tipo_crime`. O `consultar_registros` do repository só
    aceita igualdade, então a query é montada diretamente com o cliente Supabase.
    """
    cliente = criar_cliente_supabase()
    query = cliente.table(TABELA_OCORRENCIAS).select("*")

    for coluna, valor in filtros.items():
        query = query.eq(coluna, valor)
    query = query.in_("tipo_crime", list(tipos))
    if data_inicio:
        query = query.gte(COLUNA_DATA, data_inicio.isoformat())
    if data_fim:
        query = query.lte(COLUNA_DATA, data_fim.isoformat())
    if limite is not None:
        query = query.limit(limite)

    return query.execute().data or []


def _consultar(
    *,
    filtros: Optional[Dict[str, Any]] = None,
    tipos: Optional[Sequence[str]] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Executa a consulta em `ocorrencias_crimes`.

    Com zero ou um tipo, usa `database.repository.consultar_registros` (igualdade +
    período + limite). Com vários tipos, usa um filtro `IN` (`_consultar_varios_tipos`).

    Args:
        filtros: Pares {coluna: valor} comparados por igualdade (já normalizados).
        tipos: Um ou mais valores exatos de `tipo_crime`.
        data_inicio: Limite inferior (inclusive) de `data_fato`.
        data_fim: Limite superior (inclusive) de `data_fato`.
        limite: Número máximo de registros (deve ser maior que zero).

    Returns:
        Lista de registros encontrados.

    Raises:
        ValueError: Se `limite` for <= 0 ou `data_inicio` for posterior a `data_fim`.
        VariavelAmbienteNaoEncontrada / ErroConexaoBanco: Falha ao conectar ao banco.
        ErroOperacaoBanco: Falha ao executar a consulta no Supabase.
    """
    if limite is not None and limite <= 0:
        raise ValueError("O limite da consulta deve ser maior que zero.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")

    filtros = dict(filtros or {})
    tipos = list(tipos or [])
    if len(tipos) == 1:
        filtros["tipo_crime"] = tipos[0]

    try:
        if len(tipos) > 1:
            dados = _consultar_varios_tipos(filtros, tipos, data_inicio, data_fim, limite)
        else:
            dados = consultar_registros(
                tabela=TABELA_OCORRENCIAS,
                filtros=filtros or None,
                limite=limite,
                coluna_data=COLUNA_DATA if (data_inicio or data_fim) else None,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
    except (ErroOperacaoBanco, ErroConexaoBanco, VariavelAmbienteNaoEncontradaBanco):
        # Já são exceções de domínio com handler próprio (500/503); não reembrulhar.
        raise
    except Exception as e:
        logger.error("Erro ao consultar %s: %s", TABELA_OCORRENCIAS, type(e).__name__)
        raise ErroOperacaoBanco("consulta", TABELA_OCORRENCIAS) from e

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
        ais: Optional[str] = None,
        natureza: Optional[str] = None,
        meio_empregado: Optional[str] = None,
        vitima_genero: Optional[str] = None,
        vitima_raca: Optional[str] = None,
        dia_semana: Optional[str] = None,
        tipo_entorpecente: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Consulta geral com filtros dinâmicos (todos opcionais e combináveis).

        - `tipo_crime`: valor exato da coluna (maiúsculas e espaços extras normalizados).
        - Demais filtros de texto: igualdade exata, sem diferenciar maiúsculas/minúsculas
          (a entrada é normalizada para o padrão gravado pela ingestão).
        - `data_inicio` / `data_fim`: período inclusivo sobre `data_fato`.
        """
        candidatos: Dict[str, Optional[str]] = {
            "municipio": _normalizar_texto(municipio),
            "tipo_crime": _normalizar_tipo(tipo_crime),
            "ais": _normalizar_texto(ais),
            "natureza": _normalizar_texto(natureza),
            "meio_empregado": _normalizar_texto(meio_empregado),
            "vitima_genero": _normalizar_texto(vitima_genero),
            "vitima_raca": _normalizar_texto(vitima_raca),
            "dia_semana": _normalizar_texto(dia_semana),
            "tipo_entorpecente": _normalizar_texto(tipo_entorpecente),
        }
        filtros = {coluna: valor for coluna, valor in candidatos.items() if valor}

        return _consultar(
            filtros=filtros,
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
