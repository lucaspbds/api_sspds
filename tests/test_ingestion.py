import logging
from unittest.mock import Mock, patch
import pytest
import requests
from datetime import date, time
import pandas as pd
from pathlib import Path

import ingestion.crawler as modulo_crawler
from ingestion.crawler import crawler, extrair_links
from ingestion.exception import (EstruturaCSSDoSiteAlterado, VariavelAmbienteNaoEncontrada, 
                                 ValorInteiroInvalido, ColunasAusentesNaPlanilha, DatabaseLookupError, 
                                 FileValidationError)
from ingestion.helpers import recebeInteiro
from ingestion.normalizer import (
    normalizar_texto,
    normalizar_data,
    normalizar_hora,
    normalizar_idade,
    normalizar_quantidadeArmas,
    normalizar_quantidadeEntorpecente,
    normalizar_ais,
    normalizar_cvli,
    normalizar_animais_CVP_Furto_Incendio_Salvamento,
    normalizar_armaDeFogo,
    normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha,
    normalizar_entorpecentes,
    normalizar_homofobiaETransfobia,
    normalizer
)
import ingestion.normalizer as modulo_normalizer
import ingestion.classifier as modulo_classifier
import ingestion.validator as modulo_validator
from ingestion.classifier import (
    TipoOcorrenciaNaoIdentificado,
    classificar_tipo_ocorrencia,
    classificar_arquivo,
)

# ---------------------------------------------------------
# 1. HAPPY PATH
# ---------------------------------------------------------

#CRAWLER
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

    assert resultado == ["/arquivo1.xlsx", "/arquivo2.xlsx"]
    
    assert "Qtd de links encontrados: 2" in caplog.text

#HELPERS
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

#NORMALIZER
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
        (25.0, 25),
        ("0", 0),
        ("130", 130),
        ("25.5", 25.5),
        ("-1", -1),
        (2030, 2030),
        (5.9, 5.9)
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


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("AIS Não Identificada (Fortaleza)", None),
        ("Ais 1","Ais 1"),
        (None, None)
    ],
)
def test_normalizar_ais(valor, esperado):
    assert normalizar_ais(valor) == esperado

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
    assert registro["data_fato"] == date(2024, 1, 1).isoformat()
    assert registro["hora_fato"] == time(8, 30).isoformat()
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

#CLASSIFIER
@pytest.mark.parametrize(
    ("nome_arquivo", "categoria"),
    [
        ("CVLI_2024.xlsx", "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"),
        ("crimes_violentos_letais_e_intencionais.xlsx",
         "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"),
        ("Apreensão de armas de fogo.xlsx", "APREENSÃO DE ARMAS DE FOGO"),
        ("armas_de_fogo.xlsx", "APREENSÃO DE ARMAS DE FOGO"),
        ("Apreensão de entorpecentes.xlsx", "APREENSÃO DE ENTORPECENTES"),
        ("homofobia_transfobia.xlsx", "HOMOFOBIA E TRANSFOBIA"),
        ("preconceito_de_raça_ou_cor.xlsx", "CRIME OU PRECONCEITO DE RAÇA OU DE COR"),
        ("crimes_sexuais.xlsx", "CRIMES SEXUAIS"),
        ("indígenas_vítimas_de_crimes.xlsx", "INDÍGENAS VÍTIMAS DE CRIMES"),
        ("Lei Maria da Penha.xlsx", "LEI 11.340/06 (LEI MARIA DA PENHA)"),
        ("maus-tratos a animais.xlsx", "CRIME DE MAUS-TRATOS A ANIMAIS"),
        ("crimes_violentos_contra_o_patrimonio.xlsx",
         "CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP"),
        ("furtos.xlsx", "FURTO"),
        ("incêndios.xlsx", "INCÊNDIO"),
        ("busca_e_salvamento.xlsx", "BUSCA E SALVAMENTO"),
    ],
)

def test_classificar_tipo_ocorrencia_identifica_categoria(nome_arquivo, categoria):
    assert classificar_tipo_ocorrencia(nome_arquivo) == categoria

def test_classificar_tipo_ocorrencia_aceita_caminho_e_usa_apenas_nome():
    caminho = Path("diretorio") / "CVLI_2024.xlsx"
    assert classificar_tipo_ocorrencia(caminho) == (
        "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
    )


def test_classificar_tipo_ocorrencia_ignora_caixa_acentos_e_separadores():
    assert classificar_tipo_ocorrencia("APREENSAO---DE---ARMAS.xlsx") == (
        "APREENSÃO DE ARMAS DE FOGO"
    )


def test_classificar_arquivo_enriquece_copia_sem_alterar_metadado_original():
    metadado = {
        "path": "dados/CVLI_2024.xlsx",
        "sha256": "abc123",
        "is_new": True,
    }

    resultado = classificar_arquivo(metadado)

    assert resultado == {
        **metadado,
        "tipo_ocorrencia": "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
    }
    assert resultado is not metadado
    assert "tipo_ocorrencia" not in metadado

#VALIDATOR

def test_calculate_sha256_calcula_hash_do_arquivo(tmp_path, monkeypatch):
    arquivo = tmp_path / "dados.xlsx"
    conteudo = b"conteudo de teste para hash"
    arquivo.write_bytes(conteudo)
    monkeypatch.setattr(modulo_validator, "HASH_CHUNK_SIZE", 4)

    import hashlib
    esperado = hashlib.sha256(conteudo).hexdigest()

    assert modulo_validator.calculate_sha256(arquivo) == esperado

def test_check_hash_in_database_retorna_true_quando_encontra_registro(monkeypatch):
    consulta = Mock(return_value=[{"id": 1}])
    monkeypatch.setattr(modulo_validator, "consultar_registros", consulta)

    assert modulo_validator.check_hash_in_database("hash-existente") is True
    consulta.assert_called_once_with(
        tabela="informacoes_arquivo",
        filtros={"hash_sha256": "hash-existente"},
    )


def test_check_hash_in_database_retorna_false_quando_nao_encontra_registro(monkeypatch):
    monkeypatch.setattr(modulo_validator, "consultar_registros", Mock(return_value=[]))

    assert modulo_validator.check_hash_in_database("hash-novo") is False


def test_check_filename_in_database_retorna_id_e_indicador(monkeypatch):
    consulta = Mock(return_value=[{"id": 42}])
    monkeypatch.setattr(modulo_validator, "consultar_registros", consulta)

    assert modulo_validator.check_filename_in_database("CVLI.xlsx") == [42, True]
    consulta.assert_called_once_with(
        tabela="informacoes_arquivo",
        filtros={"nome_arquivo": "CVLI.xlsx"},
    )


def test_check_filename_in_database_retorna_none_quando_nao_encontra(monkeypatch):
    monkeypatch.setattr(modulo_validator, "consultar_registros", Mock(return_value=[]))

    assert modulo_validator.check_filename_in_database("novo.xlsx") == [None, False]


def test_validate_xlsx_file_retorna_metadados_completos(tmp_path, monkeypatch):
    arquivo = tmp_path / "CVLI.xlsx"
    conteudo = b"planilha xlsx ficticia"
    arquivo.write_bytes(conteudo)
    hash_esperado = __import__("hashlib").sha256(conteudo).hexdigest()

    monkeypatch.setattr(modulo_validator, "check_hash_in_database", Mock(return_value=False))
    monkeypatch.setattr(
        modulo_validator, "check_filename_in_database", Mock(return_value=[None, False])
    )

    resultado = modulo_validator.validate_xlsx_file(arquivo)

    assert resultado["name"] == "CVLI.xlsx"
    assert resultado["sha256"] == hash_esperado
    assert resultado["is_new"] is True
    assert resultado["size_bytes"] == len(conteudo)
    assert resultado["name_exists"] is False
    assert resultado["id_registro"] is None
    assert resultado["path"].endswith("CVLI.xlsx")


def test_validate_xlsx_file_reconhece_hash_e_nome_existentes(tmp_path, monkeypatch):
    arquivo = tmp_path / "CVLI.xlsx"
    arquivo.write_bytes(b"conteudo")
    monkeypatch.setattr(modulo_validator, "check_hash_in_database", Mock(return_value=True))
    monkeypatch.setattr(
        modulo_validator, "check_filename_in_database", Mock(return_value=[17, True])
    )

    resultado = modulo_validator.validate_xlsx_file(arquivo)

    assert resultado["is_new"] is False
    assert resultado["name_exists"] is True
    assert resultado["id_registro"] == 17


# ---------------------------------------------------------
# 2. SAD PATH
# ---------------------------------------------------------

#HELPERS
@pytest.mark.parametrize("valor", ["", "abc", None])
def test_funcao_recebeInteiro_retorna_o_erro_ValorInteiroInvalido(valor):
    with pytest.raises(ValorInteiroInvalido):
        recebeInteiro(valor)
    

#CRAWLER
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

#NORMALIZER
def test_normalizar_quantidade_entorpecente_registra_aviso_para_quantidade_invalido(caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_quantidadeEntorpecente('abc') is None
    assert "Quantidade de entorpecentes inválidos" in caplog.text

def test_normalizar_quantidade_armas_registra_aviso_para_quantidade_fracionaria(caplog):
    with caplog.at_level(logging.WARNING):
        assert normalizar_quantidadeArmas(1.6) is None
    assert "Quantidade de armas inválidas" in caplog.text

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

#CLASSIFIER

@pytest.mark.parametrize("nome_arquivo", ["", "   "])
def test_classificar_tipo_ocorrencia_rejeita_nome_vazio(nome_arquivo):
    with pytest.raises(ValueError, match="nome do arquivo não pode ser vazio"):
        classificar_tipo_ocorrencia(nome_arquivo)


def test_classificar_tipo_ocorrencia_rejeita_categoria_desconhecida():
    with pytest.raises(TipoOcorrenciaNaoIdentificado, match="Não foi possível identificar"):
        classificar_tipo_ocorrencia("relatorio_sem_categoria.xlsx")


def test_classificar_tipo_ocorrencia_rejeita_mais_de_uma_categoria():
    with pytest.raises(TipoOcorrenciaNaoIdentificado, match="mais de uma categoria"):
        classificar_tipo_ocorrencia("CVLI e Furto.xlsx")


@pytest.mark.parametrize("metadado", [None, [], "texto", 10])
def test_classificar_arquivo_rejeita_metadado_que_nao_e_dicionario(metadado):
    with pytest.raises(ValueError, match="devem ser um dicionário"):
        classificar_arquivo(metadado)


@pytest.mark.parametrize(
    "metadado",
    [
        {},
        {"path": None},
        {"path": ""},
        {"path": "   "},
        {"path": 123},
    ],
)
def test_classificar_arquivo_rejeita_path_ausente_ou_invalido(metadado):
    with pytest.raises(ValueError, match="sem a chave 'path' válida"):
        classificar_arquivo(metadado)

#VALIDATOR
def test_calculate_sha256_retorna_file_validation_error_quando_arquivo_nao_pode_ser_lido(
    tmp_path, monkeypatch
):
    arquivo = tmp_path / "inexistente.xlsx"
    monkeypatch.setattr(modulo_validator, "HASH_CHUNK_SIZE", 8)

    with pytest.raises(FileValidationError, match="Não foi possível ler"):
        modulo_validator.calculate_sha256(arquivo)


def test_check_hash_in_database_rejeita_hash_vazio():
    with pytest.raises(DatabaseLookupError, match="hash consultado não pode ser vazio"):
        modulo_validator.check_hash_in_database("")


@pytest.mark.parametrize("nome", ["", "   ", None, 123])
def test_check_filename_in_database_rejeita_nome_vazio_ou_invalido(nome):
    with pytest.raises(DatabaseLookupError, match="nome do arquivo consultado não pode ser vazio"):
        modulo_validator.check_filename_in_database(nome)


def test_check_hash_in_database_encapsula_erro_inesperado_do_banco(monkeypatch):
    monkeypatch.setattr(
        modulo_validator, "consultar_registros", Mock(side_effect=RuntimeError("banco indisponível"))
    )

    with pytest.raises(DatabaseLookupError, match="Falha ao consultar o hash"):
        modulo_validator.check_hash_in_database("hash")


def test_check_filename_in_database_encapsula_erro_inesperado_do_banco(monkeypatch):
    monkeypatch.setattr(
        modulo_validator, "consultar_registros", Mock(side_effect=RuntimeError("banco indisponível"))
    )

    with pytest.raises(DatabaseLookupError, match="Falha ao consultar o nome"):
        modulo_validator.check_filename_in_database("arquivo.xlsx")


def test_check_hash_in_database_propaga_database_lookup_error(monkeypatch):
    erro = DatabaseLookupError("falha original")
    monkeypatch.setattr(
        modulo_validator, "consultar_registros", Mock(side_effect=erro)
    )

    with pytest.raises(DatabaseLookupError, match="falha original"):
        modulo_validator.check_hash_in_database("hash")


def test_check_filename_in_database_propaga_database_lookup_error(monkeypatch):
    erro = DatabaseLookupError("falha original")
    monkeypatch.setattr(
        modulo_validator, "consultar_registros", Mock(side_effect=erro)
    )

    with pytest.raises(DatabaseLookupError, match="falha original"):
        modulo_validator.check_filename_in_database("arquivo.xlsx")


def test_validate_xlsx_file_rejeita_arquivo_inexistente(tmp_path):
    with pytest.raises(FileValidationError, match="Arquivo não encontrado"):
        modulo_validator.validate_xlsx_file(tmp_path / "nao_existe.xlsx")


def test_validate_xlsx_file_rejeita_diretorio(tmp_path):
    with pytest.raises(FileValidationError, match="não é um arquivo"):
        modulo_validator.validate_xlsx_file(tmp_path)


@pytest.mark.parametrize("nome", ["arquivo.csv", "arquivo.xls", "arquivo.txt"])
def test_validate_xlsx_file_rejeita_extensao_diferente_de_xlsx(tmp_path, nome):
    arquivo = tmp_path / nome
    arquivo.write_bytes(b"conteudo")

    with pytest.raises(FileValidationError, match="não possui extensão XLSX"):
        modulo_validator.validate_xlsx_file(arquivo)


def test_validate_xlsx_file_propaga_erro_ao_consultar_hash(tmp_path, monkeypatch):
    arquivo = tmp_path / "arquivo.xlsx"
    arquivo.write_bytes(b"conteudo")
    monkeypatch.setattr(
        modulo_validator,
        "check_hash_in_database",
        Mock(side_effect=DatabaseLookupError("falha de consulta")),
    )

    with pytest.raises(DatabaseLookupError, match="falha de consulta"):
        modulo_validator.validate_xlsx_file(arquivo)


def test_validate_xlsx_file_propaga_erro_ao_consultar_nome(tmp_path, monkeypatch):
    arquivo = tmp_path / "arquivo.xlsx"
    arquivo.write_bytes(b"conteudo")
    monkeypatch.setattr(modulo_validator, "check_hash_in_database", Mock(return_value=False))
    monkeypatch.setattr(
        modulo_validator,
        "check_filename_in_database",
        Mock(side_effect=DatabaseLookupError("falha de consulta")),
    )

    with pytest.raises(DatabaseLookupError, match="falha de consulta"):
        modulo_validator.validate_xlsx_file(arquivo)