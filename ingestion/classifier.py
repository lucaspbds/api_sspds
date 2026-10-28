import re
import unicodedata
from pathlib import Path
from typing import TypedDict


class MetadadoArquivo(TypedDict, total=False):
    path: str
    sha256: str
    is_new: bool
    tipo_ocorrencia: str


class TipoOcorrenciaNaoIdentificado(ValueError):
    """O nome do arquivo não corresponde a uma categoria conhecida."""


def normalizar_nome(texto: str) -> str:
    """Padroniza o texto para comparação sem diferenciar caixa ou acentos."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = texto.casefold()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# A ordem importa: regras mais específicas devem vir antes das mais genéricas.
# O valor de cada regra deve corresponder exatamente ao nome esperado por normalizer.py.
REGRAS_TIPO_OCORRENCIA: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
        ("cvli", "crimes violentos letais e intencionais"),
    ),
    (
        "APREENSÃO DE ARMAS DE FOGO",
        ("apreensao de armas de fogo", "armas de fogo", "arma de fogo"),
    ),
    (
        "APREENSÃO DE ENTORPECENTES",
        ("apreensao de entorpecentes", "entorpecentes", "apreensao de drogas"),
    ),
    (
        "HOMOFOBIA E TRANSFOBIA",
        ("homofobia e transfobia", "homofobia", "transfobia"),
    ),
    (
        "CRIME OU PRECONCEITO DE RAÇA OU DE COR",
        ("crime ou preconceito de raca ou de cor", "preconceito de raca", "preconceito de cor"),
    ),
    (
        "CRIMES SEXUAIS",
        ("crimes sexuais", "crime sexual"),
    ),
    (
        "INDÍGENAS VÍTIMAS DE CRIMES",
        ("indigenas vitimas de crimes", "indigenas"),
    ),
    (
        "LEI 11.340/06 (LEI MARIA DA PENHA)",
        ("lei maria da penha", "lei 11 340 06", "maria da penha"),
    ),
    (
        "CRIME DE MAUS-TRATOS A ANIMAIS",
        ("maus tratos a animais", "maus tratos animais", "animais"),
    ),
    (
        "CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP",
        ("crimes violentos contra o patrimonio", "cvp"),
    ),
    (
        "FURTO",
        ("furto", "furtos"),
    ),
    (
        "INCÊNDIO",
        ("incendio", "incendios"),
    ),
    (
        "BUSCA E SALVAMENTO",
        ("busca e salvamento", "salvamento"),
    ),
)


def classificar_tipo_ocorrencia(nome_arquivo: str | Path) -> str:
    """
    Retorna a categoria canônica correspondente ao nome do arquivo.

    Raises:
        TipoOcorrenciaNaoIdentificado: se nenhuma regra corresponder ao nome.
        ValueError: se o nome fornecido estiver vazio.
    """
    nome = Path(nome_arquivo).name
    if not nome.strip():
        raise ValueError("O nome do arquivo não pode ser vazio.")

    nome_normalizado = normalizar_nome(nome)

    correspondencias = []
    for categoria, palavras_chave in REGRAS_TIPO_OCORRENCIA:
        if any(normalizar_nome(chave) in nome_normalizado for chave in palavras_chave):
            correspondencias.append(categoria)

    # Deduplica preservando a ordem.
    correspondencias = list(dict.fromkeys(correspondencias))

    if not correspondencias:
        raise TipoOcorrenciaNaoIdentificado(
            f"Não foi possível identificar o tipo de ocorrência pelo nome: {nome!r}. "
            "Adicione uma palavra-chave correspondente em REGRAS_TIPO_OCORRENCIA."
        )

    if len(correspondencias) > 1:
        raise TipoOcorrenciaNaoIdentificado(
            f"O nome do arquivo {nome!r} corresponde a mais de uma categoria: "
            f"{correspondencias}. Torne as palavras-chave mais específicas."
        )

    return correspondencias[0]


def classificar_arquivos(
    lista_metadados: list[MetadadoArquivo],
) -> list[MetadadoArquivo]:
    """
    Enriquece os metadados retornados por validate_xlsx_files() com
    `tipo_ocorrencia`, preservando path, sha256 e is_new.

    Retorna uma nova lista e não altera os dicionários recebidos.
    Interrompe com erro explícito se algum arquivo não puder ser classificado.
    """
    arquivos_classificados: list[MetadadoArquivo] = []

    for metadado in lista_metadados:
        caminho = metadado.get("path")
        if not caminho:
            raise ValueError(
                "Metadado de arquivo sem a chave 'path'; não é possível classificá-lo."
            )

        tipo = classificar_tipo_ocorrencia(caminho)
        arquivos_classificados.append({**metadado, "tipo_ocorrencia": tipo})

    return arquivos_classificados
