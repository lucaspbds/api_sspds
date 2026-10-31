import logging
from unittest.mock import Mock, patch
import pytest
import requests
from datetime import date, time
import pandas as pd

import ingestion.crawler as modulo_crawler
from ingestion.crawler import crawler, extrair_links
from ingestion.exception import (EstruturaCSSDoSiteAlterado, VariavelAmbienteNaoEncontrada, 
                                 ValorInteiroInvalido, ColunasAusentesNaPlanilha)
from ingestion.helpers import recebeInteiro
from ingestion.normalizer import (
    normalizar_texto,
    normalizar_data,
    normalizar_hora,
    normalizar_idade,
    normalizar_quantidadeArmas,
    normalizar_quantidadeEntorpecente,
    normalizar_cvli,
    normalizar_animais_CVP_Furto_Incendio_Salvamento,
    normalizar_armaDeFogo,
    normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha,
    normalizar_entorpecentes,
    normalizar_homofobiaETransfobia,
    normalizer,
)
import ingestion.normalizer as modulo_normalizer

# ---------------------------------------------------------
# 1. HAPPY PATH
# ---------------------------------------------------------

def test_extrair_links_retorna_todas_as_tags_a():
    from bs4 import BeautifulSoup

    html = """
        <div>
            <a href="/cvli.xlsx">CVLI</a>
            <a href="/furtos.xlsx">Furtos</a>
            <span>Não é um link</span>
        </div>
    """
    soup = BeautifulSoup(html, "html.parser")

    resultado = extrair_links(soup.div)

    assert len(resultado) == 2
    assert [link.get("href") for link in resultado] == [
        "/cvli.xlsx",
        "/furtos.xlsx",
    ]

def test_crawler_retorna_links_e_tipos_corretamente(caplog, configurar_resposta_http):
    resultado = crawler()

    assert resultado == [
        ["/arquivo1.xlsx", "/arquivo2.xlsx"],
        ["CVLI", "Furto"],
    ]
    assert "Qtd de links encontrados: 2" in caplog.text

@pytest.mark.parametrize("valor", [1])
def test_funcao_recebeInteiro_devolve_um_numero_inteiro(valor):
    numero_inteiro = recebeInteiro(valor)
    assert type(numero_inteiro) == int

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("  FORTALEZA  ", "Fortaleza"),
        ("joÃO   silva", "João Silva"),
        ("", None),
        ("   ", None),
        (None, None),
        (float("nan"), None),
    ],
)
def test_normalizar_texto(valor, esperado):
    assert normalizar_texto(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("2024-01-31", date(2024, 1, 31)),
        (pd.Timestamp("2024-01-31"), date(2024, 1, 31)),
    ],
)
def test_normalizar_data_converte_para_date(valor, esperado):
    assert normalizar_data(valor) == esperado

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("não informada", None),
        (None, None),
        (float("nan"), None),
        (time(8, 30), time(8, 30)),
        ("2024-01-31 14:45:00", time(14, 45)),
        ("14:45", time(14, 45)),
    ],
)
def test_normalizar_hora(valor, esperado):
    assert normalizar_hora(valor) == esperado

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("não informada", None),
        ("não informado", None),
        (None, None),
        (float("nan"), None),
        ("25", 25),
        (25.0, 25),
        ("0", 0),
        ("130", 130),
        ("25.5", None),
        ("-1", None),
        ("131", None),
        (2030, None),
        (5.9, None)
    ],
)
def test_normalizar_idade(valor, esperado, caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_idade(valor) == esperado

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("não informada", None),
        (None, None),
        (float("nan"), None),
        ("3", 3),
        (3.0, 3),
        ("0", 0),
        (3.5, None)
    ],
)
def test_normalizar_quantidade_armas(valor, esperado):
    assert normalizar_quantidadeArmas(valor) == esperado

@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("não informada", None),
        (None, None),
        (float("nan"), None),
        ("1,25", 1.25),
        ("2.5", 2.5),
        ("0", 0.0),
        ('abc', None)
    ],
)
def test_normalizar_quantidade_entorpecente(valor, esperado):
    assert normalizar_quantidadeEntorpecente(valor) == esperado


def test_normalizar_cvli_monta_registro_normalizado(df_cvli):
    resultado = normalizar_cvli(
        df_cvli, 7, "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
    )
    registro = resultado[0]

    assert len(resultado) == 1
    assert registro["arquivo_id"] == 7
    assert registro["tipo_crime"] == "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
    assert registro["municipio"] == "Fortaleza"
    assert registro["ais"] == "Ais 1"
    assert registro["data_fato"] == date(2024, 1, 1)
    assert registro["hora_fato"] == time(8, 30)
    assert registro["natureza"] == "Homicídio"
    assert registro["meio_empregado"] == "Arma De Fogo"
    assert registro["vitima_genero"] == "Masculino"
    assert registro["vitima_idade"] == 25
    assert registro["st_dia_semana_divergente"] is False
    assert registro["quantidade_armas"] is None


def test_normalizar_animais_retorna_campos_nao_aplicaveis_com_none(df_animais):
    registro = normalizar_animais_CVP_Furto_Incendio_Salvamento(
        df_animais, 3, "FURTO"
    )[0]

    assert registro["municipio"] == "Fortaleza"
    assert registro["natureza"] is None
    assert registro["vitima_idade"] is None
    assert registro["peso_entorpecente_kg"] is None
    assert registro["st_dia_semana_divergente"] is False


def test_normalizar_armas_converte_quantidade(df_armas):
    registro = normalizar_armaDeFogo(df_armas, 4, "APREENSÃO DE ARMAS DE FOGO")[0]
    assert registro["quantidade_armas"] == 2
    assert registro["tipo_entorpecente"] is None


def test_normalizar_preconceito_converte_dados_da_vitima(df_preconceito):
    registro = normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha(
        df_preconceito, 5, "CRIMES SEXUAIS"
    )[0]

    assert registro["vitima_genero"] == "Feminino"
    assert registro["vitima_idade"] == 30
    assert registro["vitima_escolaridade"] == "Ensino Superior"
    assert registro["vitima_raca"] == "Parda"
    assert registro["quantidade_armas"] is None


def test_normalizar_entorpecentes_converte_virgula_decimal(df_entorpecentes):
    registro = normalizar_entorpecentes(
        df_entorpecentes, 6, "APREENSÃO DE ENTORPECENTES"
    )[0]

    assert registro["peso_entorpecente_kg"] == 1.25
    assert registro["tipo_entorpecente"] == "Maconha"


def test_normalizar_homofobia_transfobia_mapeia_campos(df_homofobia):
    registro = normalizar_homofobiaETransfobia(
        df_homofobia, 8, "HOMOFOBIA E TRANSFOBIA"
    )[0]

    assert registro["local_fato"] == "Via Pública"
    assert registro["natureza"] == "Ameaça"
    assert registro["vitima_genero"] == "Mulher Trans"
    assert registro["vitima_orientacao_sexual"] == "Heterossexual"
    assert registro["vitima_idade"] == 22

@pytest.mark.parametrize(
    ("tipo", "funcao"),
    [
        ("CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI", "normalizar_cvli"),
        ("APREENSÃO DE ARMAS DE FOGO", "normalizar_armaDeFogo"),
        ("APREENSÃO DE ENTORPECENTES", "normalizar_entorpecentes"),
        ("HOMOFOBIA E TRANSFOBIA", "normalizar_homofobiaETransfobia"),
        ("FURTO", "normalizar_animais_CVP_Furto_Incendio_Salvamento"),
        ("CRIMES SEXUAIS",
         "normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha"),
    ],
)
def test_normalizer_encaminha_para_funcao_correta(monkeypatch, tipo, funcao):
    esperado = [{"teste": True}]
    monkeypatch.setattr(modulo_normalizer, funcao, lambda *args: esperado)
    monkeypatch.setattr(modulo_normalizer, "configure_logging", lambda: None)

    resultado = normalizer(pd.DataFrame(), 1, tipo)

    assert resultado == esperado


# ---------------------------------------------------------
# 2. SAD PATH
# ---------------------------------------------------------

@pytest.mark.parametrize("valor", ["", "abc", None])
def test_funcao_recebeInteiro_retorna_o_erro_ValorInteiroInvalido(valor):
    with pytest.raises(ValorInteiroInvalido):
        recebeInteiro(valor)
    

@pytest.mark.parametrize("conteudo", [None, "", False])
def test_extrair_links_retorna_lista_vazia_sem_conteudo(conteudo):
    assert extrair_links(conteudo) == []


def test_crawler_registra_e_propaga_variavel_ausente(caplog):
    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=VariavelAmbienteNaoEncontrada("url_sspds")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(VariavelAmbienteNaoEncontrada):
                crawler()

    assert "Falha crítica de inicialização" in caplog.text

def test_crawler_registra_e_propaga_timeout(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.Timeout("tempo excedido")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.Timeout):
                crawler()

    assert "Tempo limite excedido" in caplog.text


def test_crawler_registra_e_propaga_erro_de_conexao(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.ConnectionError("sem conexão")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.ConnectionError):
                crawler()

    assert "Erro de conexão" in caplog.text


def test_crawler_registra_e_propaga_erro_http(caplog):
    resposta = Mock()
    resposta.status_code = 503

    erro_http = requests.exceptions.HTTPError(
        "Service Unavailable",
        response=resposta,
    )

    resposta.raise_for_status.side_effect = erro_http

    with patch.object(modulo_crawler.r, "get", return_value=resposta):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                crawler()

    assert "Status 503" in caplog.text


def test_crawler_registra_erro_inesperado_de_requisicao(caplog):
    with patch.object(modulo_crawler.r, "get", side_effect=requests.exceptions.RequestException("erro inesperado")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.RequestException):
                crawler()

    assert "Erro inesperado na requisição HTTP" in caplog.text


def test_crawler_registra_e_propaga_estrutura_alterada(caplog):
    html_sem_container = """
        <html>
            <body>
                <div id="conteudo">
                    <p>A estrutura da página mudou.</p>
                </div>
            </body>
        </html>
    """

    with patch.object(modulo_crawler.r, "get") as mock_get:
        resposta = Mock()
        resposta.text = html_sem_container
        resposta.raise_for_status.return_value = None
        mock_get.return_value = resposta

        with caplog.at_level(logging.ERROR):
            with pytest.raises(EstruturaCSSDoSiteAlterado):
                crawler()

    assert "Erro de parsing/estrutura de dados no HTML" in caplog.text


@pytest.mark.parametrize("timeout_invalido", ["abc", "", None])
def test_crawler_usa_timeout_padrao_quando_configuracao_invalida(
    caplog, timeout_invalido, configurar_resposta_http):
    def obter_variavel(nome):
        if nome == "url_sspds":
            return "https://exemplo.test/sspds"
        if nome == "CRAWLER_TIMEOUT":
            return timeout_invalido
        raise VariavelAmbienteNaoEncontrada()

    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=obter_variavel):
        with caplog.at_level(logging.WARNING):
            crawler()

    assert "CRAWLER_TIMEOUT inválido ou não definido" in caplog.text

def test_normalizar_quantidade_entorpecente_registra_aviso_para_quantidade_invalido(caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_quantidadeEntorpecente('abc') is None
    assert "Quantidade de entorpecentes inválidos" in caplog.text

def test_normalizar_quantidade_armas_registra_aviso_para_quantidade_fracionaria(caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_quantidadeArmas(1.6) is None
    assert "Quantidade de armas inválidas" in caplog.text


def test_normalizar_idade_registra_aviso_para_valor_fora_do_intervalo(caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_idade(150) is None
    assert "Idade inválida" in caplog.text

def test_normalizar_data_propaga_data_invalida():
    with pytest.raises((ValueError, TypeError)):
        normalizar_data("data inválida")

def test_normalizar_hora_propaga_hora_invalida():
    with pytest.raises((ValueError, TypeError)):
        normalizar_hora("horário inválido")

@pytest.mark.parametrize(
    "funcao",
    [
        normalizar_cvli,
        normalizar_animais_CVP_Furto_Incendio_Salvamento,
        normalizar_armaDeFogo,
        normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha,
        normalizar_entorpecentes,
        normalizar_homofobiaETransfobia,
    ],
)
def test_normalizadores_rejeitam_arquivo_id_nao_positivo(funcao, df_cvli):
    with pytest.raises(ValueError, match="arquivo_id deve ser positivo"):
        funcao(df_cvli, 0, "TIPO")


@pytest.mark.parametrize(
    ("funcao", "colunas"),
    [
        (normalizar_cvli, {"Município", "AIS", "Natureza", "Data", "Hora",
                           "Dia da Semana", "Meio Empregado", "Gênero",
                           "Idade da Vítima", "Escolaridade da Vítima", "Raça da Vítima"}),
        (normalizar_animais_CVP_Furto_Incendio_Salvamento,
         {"Município", "AIS", "Data", "Hora", "Dia da Semana"}),
        (normalizar_armaDeFogo,
         {"Município", "AIS", "Data", "Hora", "Dia da Semana", "Quantidade"}),
        (normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha,
         {"Município", "AIS", "Data", "Hora", "Dia da Semana", "Gênero",
          "Idade da Vítima", "Escolaridade da Vítima", "Raça da Vítima"}),
        (normalizar_entorpecentes,
         {"Município", "AIS", "Data", "Hora", "Dia da Semana",
          "Quantidade (Kg)", "Tipo de Entorpecente"}),
        (normalizar_homofobiaETransfobia,
         {"Município", "AIS", "Data", "Hora", "Dia da Semana",
          "Idade da Vítima", "Escolaridade da Vítima", "Raça da Vítima",
          "Natureza", "Identidade de Gênero", "Orientação Sexual", "Local"}),
    ],
)
def test_normalizadores_rejeitam_colunas_ausentes(funcao, colunas):
    df = pd.DataFrame(columns=sorted(colunas - {"Município"}))
    with pytest.raises(ColunasAusentesNaPlanilha):
        funcao(df, 1, "TIPO")


@pytest.mark.parametrize(
    "funcao",
    [
        normalizar_cvli,
        normalizar_animais_CVP_Furto_Incendio_Salvamento,
        normalizar_armaDeFogo,
        normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha,
        normalizar_entorpecentes,
        normalizar_homofobiaETransfobia,
    ],
)
def test_normalizadores_rejeitam_municipio_vazio(funcao, df_animais):
    # O DataFrame contém as colunas-base; as demais colunas são adicionadas
    # para satisfazer a validação de cada normalizador.
    df = df_animais.copy()
    df["Município"] = None
    for coluna in [
        "Natureza", "Meio Empregado", "Gênero", "Idade da Vítima",
        "Escolaridade da Vítima", "Raça da Vítima", "Quantidade",
        "Quantidade (Kg)", "Tipo de Entorpecente", "Identidade de Gênero",
        "Orientação Sexual", "Local",
    ]:
        if coluna not in df.columns:
            df[coluna] = None
    with pytest.raises(ValueError, match="Município ausente"):
        funcao(df, 1, "TIPO")


def test_normalizar_cvli_detecta_divergencia_no_dia_da_semana(df_cvli, caplog):
    df_cvli.loc[0, "Dia da Semana"] = "domingo"

    with caplog.at_level(logging.WARNING):
        registro = normalizar_cvli(df_cvli, 1, "CVLI")[0]

    assert registro["st_dia_semana_divergente"] is True
    assert "diverge da data" in caplog.text



def test_normalizer_tipo_desconhecido_registra_erro_e_retorna_none(caplog, monkeypatch):
    monkeypatch.setattr(modulo_normalizer, "configure_logging", lambda: None)

    with caplog.at_level(logging.ERROR):
        resultado = normalizer(pd.DataFrame(), 1, "TIPO DESCONHECIDO")

    assert resultado is None
    assert "Falha na normalização" in caplog.text


def test_normalizer_registra_erro_de_colunas_ausentes_e_retorna_none(
    caplog, monkeypatch
):
    monkeypatch.setattr(modulo_normalizer, "configure_logging", lambda: None)

    with caplog.at_level(logging.ERROR):
        resultado = normalizer(
            pd.DataFrame(),
            1,
            "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
        )

    # A função normalizer captura a exceção e não a relança.
    assert resultado is None
    assert "Falha na normalização" in caplog.text
