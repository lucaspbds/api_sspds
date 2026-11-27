import logging
from datetime import date
from typing import Any, Dict, Optional, Sequence

from database.exceptions import (
    ErroConexaoBanco,
    ErroOperacaoBanco,
)
from database.exceptions import (
    VariavelAmbienteNaoEncontrada as VariavelAmbienteNaoEncontradaBanco,
)
from database.repository import LIMITE_PADRAO_PAGINACAO, consultar_registros_paginados

logger = logging.getLogger("app.services.crime_service")

VIEW_OCORRENCIAS_PUBLICADAS = "vw_ocorrencias_publicadas"
TABELA_OCORRENCIAS = VIEW_OCORRENCIAS_PUBLICADAS
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


def _consultar(
    *,
    filtros: Optional[Dict[str, Any]] = None,
    tipos: Optional[Sequence[str]] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    cursor: Optional[int] = None,
    limite: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Executa a consulta paginada por cursor em `vw_ocorrencias_publicadas`
    via `database.repository.consultar_registros_paginados`.
    """
    limite_efetivo = LIMITE_PADRAO_PAGINACAO if limite is None else limite
    if limite_efetivo <= 0:
        raise ValueError("O limite da consulta deve ser maior que zero.")
    if cursor is not None and cursor <= 0:
        raise ValueError("O parâmetro 'cursor' deve ser um inteiro positivo.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")

    filtros_limpos = dict(filtros or {})
    tipos_lista = list(tipos or [])
    filtros_in: Optional[Dict[str, Sequence[Any]]] = None

    if len(tipos_lista) == 1:
        filtros_limpos["tipo_crime"] = tipos_lista[0]
    elif len(tipos_lista) > 1:
        filtros_in = {"tipo_crime": tipos_lista}

    try:
        resultado = consultar_registros_paginados(
            tabela=TABELA_OCORRENCIAS,
            filtros=filtros_limpos or None,
            filtros_in=filtros_in,
            limite=limite_efetivo,
            cursor=cursor,
            coluna_cursor="id",
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
        "Consulta concluída tabela=%s registros_retornados=%s has_next=%s next_cursor=%s",
        TABELA_OCORRENCIAS,
        len(resultado["items"]),
        resultado["pagination"]["has_next"],
        resultado["pagination"]["next_cursor"],
    )
    return resultado


def _montar_filtros_especificos(
    *,
    municipio: Optional[str] = None,
    ais: Optional[str] = None,
    dia_semana: Optional[str] = None,
    natureza: Optional[str] = None,
    local_fato: Optional[str] = None,
    meio_empregado: Optional[str] = None,
    vitima_genero: Optional[str] = None,
    vitima_orientacao_sexual: Optional[str] = None,
    vitima_raca: Optional[str] = None,
    vitima_idade: Optional[int] = None,
    vitima_escolaridade: Optional[str] = None,
) -> Dict[str, Any]:
    """Monta o dicionário de filtros normalizados para rotas específicas."""
    candidatos_texto: Dict[str, Optional[str]] = {
        "municipio": _normalizar_texto(municipio),
        "ais": _normalizar_texto(ais),
        "dia_semana": _normalizar_texto(dia_semana),
        "natureza": _normalizar_texto(natureza),
        "local_fato": _normalizar_texto(local_fato),
        "meio_empregado": _normalizar_texto(meio_empregado),
        "vitima_genero": _normalizar_texto(vitima_genero),
        "vitima_orientacao_sexual": _normalizar_texto(vitima_orientacao_sexual),
        "vitima_raca": _normalizar_texto(vitima_raca),
        "vitima_escolaridade": _normalizar_texto(vitima_escolaridade),
    }
    filtros: Dict[str, Any] = {
        coluna: valor for coluna, valor in candidatos_texto.items() if valor
    }
    if vitima_idade is not None:
        filtros["vitima_idade"] = vitima_idade
    return filtros


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
        cursor: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Consulta geral com filtros dinâmicos (todos opcionais e combináveis) e paginação por cursor.

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
            cursor=cursor,
            limite=limit,
        )

    @staticmethod
    def listar_por_tipo(
        tipo: str,
        limit: Optional[int] = None,
        cursor: Optional[int] = None,
        municipio: Optional[str] = None,
        ais: Optional[str] = None,
        dia_semana: Optional[str] = None,
        natureza: Optional[str] = None,
        local_fato: Optional[str] = None,
        meio_empregado: Optional[str] = None,
        vitima_genero: Optional[str] = None,
        vitima_orientacao_sexual: Optional[str] = None,
        vitima_raca: Optional[str] = None,
        vitima_idade: Optional[int] = None,
        vitima_escolaridade: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Consulta específica por **um** tipo de crime com paginação por cursor.

        O valor de `tipo` deve ser exatamente uma das strings presentes na coluna
        `tipo_crime` (veja as constantes `TIPO_*` deste módulo).
        """
        filtros = _montar_filtros_especificos(
            municipio=municipio,
            ais=ais,
            dia_semana=dia_semana,
            natureza=natureza,
            local_fato=local_fato,
            meio_empregado=meio_empregado,
            vitima_genero=vitima_genero,
            vitima_orientacao_sexual=vitima_orientacao_sexual,
            vitima_raca=vitima_raca,
            vitima_idade=vitima_idade,
            vitima_escolaridade=vitima_escolaridade,
        )
        return _consultar(
            filtros=filtros,
            tipos=[tipo],
            data_inicio=data_inicio,
            data_fim=data_fim,
            cursor=cursor,
            limite=limit,
        )

    @staticmethod
    def listar_por_tipos(
        tipos: Sequence[str],
        limit: Optional[int] = None,
        cursor: Optional[int] = None,
        municipio: Optional[str] = None,
        ais: Optional[str] = None,
        dia_semana: Optional[str] = None,
        natureza: Optional[str] = None,
        local_fato: Optional[str] = None,
        meio_empregado: Optional[str] = None,
        vitima_genero: Optional[str] = None,
        vitima_orientacao_sexual: Optional[str] = None,
        vitima_raca: Optional[str] = None,
        vitima_idade: Optional[int] = None,
        vitima_escolaridade: Optional[str] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Consulta específica por **vários** tipos de crime (filtro `IN`), como
        `TIPOS_OPERACIONAIS` e `TIPOS_COM_VITIMA`, com paginação por cursor.
        """
        filtros = _montar_filtros_especificos(
            municipio=municipio,
            ais=ais,
            dia_semana=dia_semana,
            natureza=natureza,
            local_fato=local_fato,
            meio_empregado=meio_empregado,
            vitima_genero=vitima_genero,
            vitima_orientacao_sexual=vitima_orientacao_sexual,
            vitima_raca=vitima_raca,
            vitima_idade=vitima_idade,
            vitima_escolaridade=vitima_escolaridade,
        )
        return _consultar(
            filtros=filtros,
            tipos=tipos,
            data_inicio=data_inicio,
            data_fim=data_fim,
            cursor=cursor,
            limite=limit,
        )

    @staticmethod
    def listar_ocorrencias(
        limit: Optional[int] = None,
        cursor: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Consulta simples de ocorrências, sem filtros (mantida para compatibilidade).
        """
        return _consultar(limite=limit, cursor=cursor)