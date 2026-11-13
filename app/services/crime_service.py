import logging
from typing import List, Dict, Optional, Any
from datetime import date
from database.repository import consultar_registros
from database.exceptions import ErroConexaoBanco, ErroOperacaoBanco

logger = logging.getLogger("app.services.crime_service")


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
        Consulta geral com filtros dinâmicos.

        ⚠️ Filtros de data (data_inicio/data_fim) ainda não são aplicados porque
        o `consultar_registros` do repository só suporta igualdade (.eq()).
        Para aplicar período sobre a coluna `data_fato`, é necessário expandir
        o repository com suporte a operadores .gte() / .lte().
        """
        filtros: Dict[str, Any] = {}
        if municipio:
            filtros["municipio"] = municipio
        if tipo_crime:
            filtros["tipo_crime"] = tipo_crime

        if data_inicio or data_fim:
            logger.warning(
                "Filtros de período ignorados: repository não suporta gte/lte ainda. "
                "data_inicio=%s data_fim=%s",
                data_inicio,
                data_fim,
            )

        try:
            return consultar_registros(
                tabela="ocorrencias_crimes",
                filtros=filtros if filtros else None,
                limite=limit,
            )
        except (ErroConexaoBanco, ErroOperacaoBanco):
            raise
        except Exception as e:
            logger.error("Erro ao listar com filtros: %s", type(e).__name__)
            raise RuntimeError("Falha ao processar a consulta com filtros.") from e

    @staticmethod
    def listar_por_tipo(tipo: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Consulta específica por tipo de crime.

        O valor de `tipo` deve ser **exatamente** uma das strings presentes na
        coluna `tipo_crime` da tabela `ocorrencias_crimes`. Exemplos reais:

        - "FURTO"
        - "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
        - "CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP"
        - "CRIMES SEXUAIS"
        - "LEI 11.340/06 (LEI MARIA DA PENHA)"
        - "HOMOFOBIA E TRANSFOBIA"
        - "APREENSÃO DE ENTORPECENTES"
        - "APREENSÃO DE ARMAS DE FOGO"
        - "BUSCA E SALVAMENTO"
        - "CRIME DE MAUS-TRATOS A ANIMAIS"
        - "CRIME OU PRECONCEITO DE RAÇA OU DE COR"
        - "INCÊNDIO"
        - "INDÍGENAS VÍTIMAS DE CRIMES"

        Para listar os valores atuais, consulte o banco:
            SELECT DISTINCT tipo_crime FROM ocorrencias_crimes ORDER BY tipo_crime;
        """
        try:
            return consultar_registros(
                tabela="ocorrencias_crimes",
                filtros={"tipo_crime": tipo},
                limite=limit,
            )
        except (ErroConexaoBanco, ErroOperacaoBanco):
            raise
        except Exception as e:
            logger.error("Erro ao listar por tipo: %s", type(e).__name__)
            raise RuntimeError(f"Falha ao processar a consulta do tipo {tipo}.") from e

    @staticmethod
    def listar_ocorrencias(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Consulta simples de ocorrências (mantida para compatibilidade).
        """
        try:
            return consultar_registros(
                tabela="ocorrencias_crimes",
                limite=limit,
            )
        except (ErroConexaoBanco, ErroOperacaoBanco):
            raise
        except Exception as e:
            logger.error("Erro ao listar ocorrências: %s", type(e).__name__)
            raise RuntimeError("Falha ao listar ocorrências.") from e