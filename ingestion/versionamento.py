"""Regras de identidade, classificação e reconciliação das versões SSPDS.

Este módulo pertence exclusivamente ao serviço de ingestão. Não altera o
schema do banco: utiliza serie e ultimo_mes já existentes em
informacoes_arquivo.
"""
from __future__ import annotations

import logging
import re
from calendar import month_name
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
}
PADRAO_HISTORICO = re.compile(r"(?P<inicio>20\d{2})-a-(?P<fim>20\d{2})", re.I)
PADRAO_MES = re.compile(
    r"(?P<mes>janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|"
    r"agosto|setembro|outubro|novembro|dezembro)", re.I
)


def proximo_mes(ano: int, mes: int) -> tuple[int, int]:
    """Avança um mês respeitando a virada do ano."""
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def periodo_historico(nome: str) -> str | None:
    """Extrai o intervalo histórico explícito do nome do arquivo."""
    match = PADRAO_HISTORICO.search(nome)
    if not match:
        return None
    inicio, fim = int(match.group("inicio")), int(match.group("fim"))
    if inicio > fim:
        raise ValueError(f"Intervalo histórico inválido no arquivo {nome!r}.")
    return f"{inicio}-{fim}"


def identificar_serie(nome: str) -> str:
    """Classifica a série pelo padrão de publicação da SSPDS.

    Arquivos históricos possuem intervalo explícito AAAA-a-BBBB; os arquivos
    mensais da seção corrente não possuem esse intervalo.
    """
    return "historica" if periodo_historico(nome) else "corrente"


def extrair_ultimo_mes(nome: str) -> int | None:
    match = PADRAO_MES.search(nome)
    if not match:
        return None
    return MESES[match.group("mes").casefold()]


def normalizar_periodo(periodo: str | None) -> str | None:
    if not periodo:
        return None
    return re.sub(r"\s+", "", str(periodo)).replace("–", "-").replace("—", "-")


def classificar_versao(
    novo: dict[str, Any], existentes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Classifica uma nova versão contra registros completos da mesma série.

    Mudanças inesperadas nunca autorizam exclusão automática.
    """
    tipo = novo["tipo_crime"]
    serie = novo["serie"]
    candidatos = [
        r for r in existentes
        if r.get("periodo_dados") is not None
        and r.get("tipo_crime") == tipo
        and r.get("serie") == serie
    ]
    resultado = {
        **novo, "is_new": True, "is_update": False,
        "tipo_atualizacao": None, "ids_substituir": [], "avisos": [],
    }
    if len(candidatos) > 1:
        resultado["avisos"].append(
            f"Mais de uma versão completa para ({tipo}, {serie}); preservadas."
        )
        return resultado
    if not candidatos:
        return resultado

    anterior = candidatos[0]
    periodo_novo = normalizar_periodo(novo.get("periodo_dados"))
    periodo_antigo = normalizar_periodo(anterior.get("periodo_dados"))
    resultado["is_update"] = True

    if serie == "corrente":
        try:
            ano_novo = int(periodo_novo)
            ano_antigo = int(periodo_antigo)
            mes_novo = int(novo["ultimo_mes"])
            mes_antigo = int(anterior["ultimo_mes"])
        except (TypeError, ValueError, KeyError):
            resultado["avisos"].append("Metadados da série corrente insuficientes.")
            return resultado
        if (ano_novo, mes_novo) == (ano_antigo, mes_antigo):
            resultado["tipo_atualizacao"] = "correcao"
        elif proximo_mes(ano_antigo, mes_antigo) == (ano_novo, mes_novo):
            resultado["tipo_atualizacao"] = "acrescimo"
        else:
            resultado["avisos"].append(
                f"Salto inesperado da série corrente: {ano_antigo}/{mes_antigo} "
                f"para {ano_novo}/{mes_novo}."
            )
            return resultado
    else:
        try:
            inicio_novo, fim_novo = map(int, periodo_novo.split("-"))
            inicio_antigo, fim_antigo = map(int, periodo_antigo.split("-"))
        except (AttributeError, TypeError, ValueError):
            resultado["avisos"].append("Intervalo histórico inválido.")
            return resultado
        if (inicio_novo, fim_novo) == (inicio_antigo, fim_antigo):
            resultado["tipo_atualizacao"] = "correcao"
        elif inicio_novo == inicio_antigo and fim_novo == fim_antigo + 1:
            resultado["tipo_atualizacao"] = "acrescimo"
        else:
            resultado["avisos"].append(
                f"Intervalo histórico inesperado: {periodo_antigo} para {periodo_novo}."
            )
            return resultado

    resultado["ids_substituir"] = [anterior["id"]]
    return resultado


def selecionar_registro_hash(registros: list[dict[str, Any]], file_hash: str):
    """Retorna o registro do hash e se ele já foi publicado."""
    for registro in registros:
        if registro.get("hash_sha256") == file_hash:
            return registro, registro.get("periodo_dados") is not None
    return None, False


def ids_orfaos_antigos(
    registros: list[dict[str, Any]], horas: int = 6, agora: datetime | None = None
) -> list[int]:
    """Seleciona somente tentativas incompletas antigas (periodo_dados NULL)."""
    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(hours=horas)
    ids = []
    for registro in registros:
        if registro.get("periodo_dados") is not None:
            continue
        coletado = registro.get("data_coleta")
        if not coletado:
            continue
        try:
            data = datetime.fromisoformat(str(coletado).replace("Z", "+00:00"))
            if data.tzinfo is None:
                data = data.replace(tzinfo=timezone.utc)
            if data < limite:
                ids.append(registro["id"])
        except (TypeError, ValueError):
            logger.warning("data_coleta inválida no registro incompleto id=%s", registro.get("id"))
    return ids


def ids_transicao_anual(registros: list[dict[str, Any]]) -> list[int]:
    """Remove corrente encerrada somente quando o histórico correspondente está publicado."""
    completos = [r for r in registros if r.get("periodo_dados") is not None]
    remover = []
    for corrente in completos:
        if corrente.get("serie") != "corrente":
            continue
        try:
            ano = int(normalizar_periodo(corrente.get("periodo_dados")))
        except (TypeError, ValueError):
            continue
        historicos = [
            h for h in completos
            if h.get("serie") == "historica"
            and h.get("tipo_crime") == corrente.get("tipo_crime")
        ]
        for historico in historicos:
            intervalo = normalizar_periodo(historico.get("periodo_dados"))
            try:
                _, fim = map(int, intervalo.split("-"))
            except (AttributeError, ValueError):
                continue
            # A série corrente só pode ser descartada depois de cobrir o ano
            # inteiro. O mês 12 é a evidência persistida de que a versão corrente
            # chegou ao encerramento; um histórico publicado até esse ano, sozinho,
            # não prova que uma corrente interrompida em outubro/novembro foi coberta.
            if fim == ano and int(corrente.get("ultimo_mes") or 0) == 12:
                remover.append(corrente["id"])
                break
    return sorted(set(remover))


def ids_reconciliacao(registros: list[dict[str, Any]]) -> list[int]:
    """Seleciona versões completas superadas somente em sequências reconhecidas."""
    completos = [r for r in registros if r.get("periodo_dados") is not None]
    remover: set[int] = set()
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for registro in completos:
        chave = (registro.get("tipo_crime"), registro.get("serie"))
        grupos.setdefault(chave, []).append(registro)

    for (_, serie), grupo in grupos.items():
        if len(grupo) <= 1:
            continue
        if serie == "corrente":
            try:
                ordenados = sorted(
                    grupo,
                    key=lambda r: (
                        int(normalizar_periodo(r.get("periodo_dados"))),
                        int(r.get("ultimo_mes") or 0),
                    ),
                    reverse=True,
                )
                pares = [
                    (int(normalizar_periodo(r.get("periodo_dados"))), int(r.get("ultimo_mes") or 0))
                    for r in ordenados
                ]
            except (TypeError, ValueError):
                continue
            if len(set(pares)) == 1:
                por_publicacao = sorted(
                    grupo,
                    key=lambda r: (r.get("atualizado_em") or r.get("data_coleta") or "", r["id"]),
                    reverse=True,
                )
                remover.update(r["id"] for r in por_publicacao[1:])
                continue
            # Só elimina se cada versão anterior for exatamente o mês anterior.
            sequencia_valida = all(
                proximo_mes(*pares[i + 1]) == pares[i]
                for i in range(len(pares) - 1)
            )
            if sequencia_valida:
                remover.update(r["id"] for r in ordenados[1:])
        else:
            # Históricos só são concorrentes quando têm o mesmo ano inicial
            # e avançam em sequência anual; intervalos inesperados são preservados.
            try:
                ordenados = sorted(
                    grupo,
                    key=lambda r: tuple(
                        map(int, normalizar_periodo(r.get("periodo_dados")).split("-"))
                    ),
                    reverse=True,
                )
                intervalos = [
                    tuple(map(int, normalizar_periodo(r.get("periodo_dados")).split("-")))
                    for r in ordenados
                ]
            except (AttributeError, TypeError, ValueError):
                continue
            if len(set(intervalos)) == 1:
                por_publicacao = sorted(
                    grupo,
                    key=lambda r: (r.get("atualizado_em") or r.get("data_coleta") or "", r["id"]),
                    reverse=True,
                )
                remover.update(r["id"] for r in por_publicacao[1:])
            elif all(
                atual[0] == anterior[0] and atual[1] == anterior[1] + 1
                for atual, anterior in zip(intervalos, intervalos[1:])
            ):
                remover.update(r["id"] for r in ordenados[1:])

    remover.update(ids_transicao_anual(completos))
    return sorted(remover)
