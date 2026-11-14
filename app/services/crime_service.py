import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from database.exceptions import ErroOperacaoBanco
from database.repository import criar_cliente_supabase, consultar_registro

logger = logging.getLogger("app.services.crime_service")

TABELA_OCORRENCIAS = "ocorrencias_crimes"

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
    filtros: Optional[Dict[str, Any]] = None,
    tipos: Optional[Sequence[str]] = None,
    municipio: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limite: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Executa a consulta em `ocorrencias_crimes` utilizando o repositório centralizado.

    Args:
        tipos: Um ou mais valores exatos de `tipo_crime` (filtro de igualdade ou lista).
        municipio: Município (igualdade exata, já normalizado).
        data_inicio: Limite inferior (inclusive) de `data_fato`.
        data_fim: Limite superior (inclusive) de `data_fato`.
        limite: Número máximo de registros (deve ser maior que zero).

    Returns:
        Lista de registros encontrados.

    Raises:
        ValueError: Se `limite` for <= 0 ou `data_inicio` for posterior a `data_fim`.
        VariavelAmbienteNaoEncontrada / ErroConexaoBanco: Falha ao conectar.
        ErroOperacaoBanco: Falha ao executar a consulta no Supabase.
    """
    if limite is not None and limite <= 0:
        raise ValueError("O limite da consulta deve ser maior que zero.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")

    # Montamos o dicionário de filtros dinâmicos de igualdade
    filtros = dict(filtros or {})
    if municipio:
        filtros["municipio"] = municipio
    if tipos:
        # Se houver apenas um tipo, podemos usar direto no filtro; 
        # se forem vários, o repositório padrão por igualdade simples lida com .eq. 
        # Caso queira suporte a IN, podemos tratar, mas mantendo a compatibilidade atual:
        if len(tipos) == 1:
            filtros["tipo_crime"] = tipos[0]

    try:
        # Se houver múltiplos tipos (filtro IN), tratamos a query ou passamos ao repositório.
        # Como a função consultar_registros padrão lida com .eq(), se tivermos múltiplos tipos,
        # podemos chamar diretamente passando os parâmetros atualizados do repositório:
        if tipos and len(tipos) > 1:
            # Caso especial para múltiplos tipos usando o cliente diretamente ou expandindo o repo se necessário,
            # mas mantendo a chamada limpa via consultar_registros se aplicável:
            cliente = criar_cliente_supabase()
            query = cliente.table(TABELA_OCORRENCIAS).select("*")
            if municipio:
                query = query.eq("municipio", municipio)
            query = query.in_("tipo_crime", list(tipos))
            if data_inicio:
                query = query.gte("data_fato", data_inicio.isoformat())
            if data_fim:
                query = query.lte("data_fato", data_fim.isoformat())
            query = query.order("id")
            if limite is not None:
                query = query.limit(limite)
            resposta = query.execute()
            dados = resposta.data or []
        else:
            # Consulta padrão com suporte a datas
            dados = consultar_registros(
                tabela=TABELA_OCORRENCIAS,
                filtros=filtros if filtros else None,
                limite=limite,
                coluna_data="data_fato" if (data_inicio or data_fim) else None,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )

        logger.info(
            "Consulta concluída tabela=%s registros_retornados=%s",
            TABELA_OCORRENCIAS,
            len(dados),
        )
        return dados

    except Exception as e:
        logger.error("Erro ao consultar %s: %s", TABELA_OCORRENCIAS, type(e).__name__)
        if not isinstance(e, ErroOperacaoBanco):
            raise ErroOperacaoBanco("consulta", TABELA_OCORRENCIAS) from e
        raise


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
        Consulta geral com filtros dinâmicos cobrindo as principais colunas do CrimeGeralResponse.
        """
        # 1. Normalizações necessárias
        tipo_normalizado = _normalizar_tipo(tipo_crime)
        mun_normalizado = _normalizar_municipio(municipio)

        # 2. Monta o dicionário dinâmico com todos os filtros de igualdade (.eq)
        filtros_extras: Dict[str, Any] = {}
        
        if mun_normalizado:
            filtros_extras["municipio"] = mun_normalizado
        if tipo_normalizado:
            filtros_extras["tipo_crime"] = tipo_normalizado
        if ais:
            filtros_extras["ais"] = ais
        if natureza:
            filtros_extras["natureza"] = natureza
        if meio_empregado:
            filtros_extras["meio_empregado"] = meio_empregado
        if vitima_genero:
            filtros_extras["vitima_genero"] = vitima_genero
        if vitima_raca:
            filtros_extras["vitima_raca"] = vitima_raca
        if dia_semana:
            filtros_extras["dia_semana"] = dia_semana
        if tipo_entorpecente:
            filtros_extras["tipo_entorpecente"] = tipo_entorpecente

        # 3. Chama o _consultar passando o dicionário completo de filtros
        return _consultar(
            filtros=filtros_extras,
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