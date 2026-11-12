import logging
from typing import List, Dict, Optional, Any
from database.repository import consultar_registros
from database.exceptions import ErroConexaoBanco, ErroOperacaoBanco

logger = logging.getLogger("app.services.crime_service")

class CrimeService:
    @staticmethod
    def listar_ocorrencias(limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Serviço responsável por buscar ocorrências criminais diretamente 
        da tabela 'ocorrencias_crimes' no banco de dados Supabase/PostgreSQL,
        com tratamento defensivo de erros.
        """
        try:
            ocorrencias = consultar_registros(
                tabela="ocorrencias_crimes", 
                limite=limit
            )
            return ocorrencias
            
        except (ErroConexaoBanco, ErroOperacaoBanco) as e:
            logger.error("Erro de infraestrutura ao buscar ocorrências no banco: %s", e)
            raise
        except Exception as e:
            logger.error("Erro inesperado no serviço de crimes: %s", type(e).__name__)
            raise RuntimeError("Não foi possível processar a listagem de ocorrências.") from e