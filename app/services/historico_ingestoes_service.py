from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional, Union

from database.repository import consultar_registros

TABELA_HISTORICO_INGESTOES = "historico_ingestoes"
COLUNA_DATA_CRIADO_EM = "criado_em"
STATUS_VALIDOS = {"EM_ANDAMENTO", "SUCESSO", "PARCIAL", "FALHA"}


def _parse_data_br_ou_iso(valor: Optional[str]) -> Optional[date]:
    """
    Converte uma string de data no formato brasileiro (DD/MM/AAAA) ou ISO (AAAA-MM-DD)
    para `datetime.date`. Lança `ValueError` se o formato for inválido.
    """
    if not valor:
        return None

    texto = valor.strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue

    raise ValueError(
        f"Data inválida '{valor}'. Utilize o formato DD/MM/AAAA (ex.: 21/11/2026)."
    )


class HistoricoIngestoesService:
    @staticmethod
    def listar_historico(
        status: Optional[str] = None,
        data: Optional[Union[date, str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        filtros: Dict[str, Any] = {}

        # ---- validação de status ----
        if status:
            status_normalizado = " ".join(status.split()).upper()
            if status_normalizado not in STATUS_VALIDOS:
                raise ValueError(
                    f"Status inválido '{status}'. "
                    f"Valores permitidos: {', '.join(sorted(STATUS_VALIDOS))}."
                )
            filtros["status"] = status_normalizado

        # ---- validação de limit ----
        if limit is not None and limit <= 0:
            raise ValueError("O parâmetro 'limit' deve ser um inteiro positivo.")

        # ---- normalização da data (aceita date ou string BR/ISO) ----
        data_normalizada: Optional[date]
        if isinstance(data, str):
            data_normalizada = _parse_data_br_ou_iso(data)
        else:
            data_normalizada = data

        data_inicio: Optional[str] = None
        data_fim: Optional[str] = None
        if data_normalizada is not None:
            data_inicio = datetime.combine(
                data_normalizada, time.min, tzinfo=timezone.utc
            ).isoformat()
            data_fim = datetime.combine(
                data_normalizada, time.max, tzinfo=timezone.utc
            ).isoformat()

        return consultar_registros(
            tabela=TABELA_HISTORICO_INGESTOES,
            filtros=filtros or None,
            limite=limit,
            coluna_data=COLUNA_DATA_CRIADO_EM if data_normalizada is not None else None,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )