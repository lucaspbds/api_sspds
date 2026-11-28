import logging
from unittest.mock import Mock, patch
import pytest
import requests
from datetime import date, time
import pandas as pd
from pathlib import Path

import ingestion.config as modulo_config
import ingestion.pipeline as modulo_pipeline
import ingestion.validator as modulo_validator
from ingestion.pipeline import ResumoIngestao
import ingestion.crawler as modulo_crawler
from ingestion.crawler import (
    crawler,
    extrair_links,
    normalizar_links,
    extrair_links_atuais,
    extrair_links_historicos,
)
from ingestion.exception import (DownloadHTTPError, EstruturaCSSDoSiteAlterado, VariavelAmbienteNaoEncontrada, 
                                 ValorInteiroInvalido, ColunasAusentesNaPlanilha, DatabaseLookupError, 
                                 FileValidationError, tipoOcorrenciaNaoEncontrado,CaminhoTemporarioInseguro, 
                                 ValorInteiroInvalido)
from ingestion.helpers import recebeInteiro
from ingestion.helpers import avaliar_expressao_inteira
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

import ingestion.cleanup as modulo_cleanup
from ingestion.cleanup import (
    limpar_pasta_temporaria,
    remover_arquivo_temporario,
    validar_pasta_temporaria,
)
import ingestion.normalizer as modulo_normalizer
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


def test_normalizar_links_converte_urls_e_remove_duplicatas():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        """
        <div>
            <a href="/arquivo.xlsx">Arquivo</a>
            <a href="https://dados.test/outro.xlsx">Outro</a>
            <a href="/arquivo.xlsx">Duplicado</a>
            <a href="   ">Sem URL</a>
        </div>
        """,
        "html.parser",
    )

    resultado = normalizar_links(soup.find_all("a"), "https://dados.test/sspds/")

    assert resultado == [
        "https://dados.test/arquivo.xlsx",
        "https://dados.test/outro.xlsx",
    ]


def test_extrair_links_atuais_retorna_urls_absolutas(html_sspds_atual):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sspds_atual, "html.parser")

    assert extrair_links_atuais(soup, "https://dados.test/atual/") == [
        "https://dados.test/arquivo1.xlsx",
        "https://dados.test/arquivo2.xlsx",
    ]


def test_extrair_links_historicos_retorna_apenas_botoes_da_secao(
    html_sspds_historico,
):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_sspds_historico, "html.parser")

    resultado = extrair_links_historicos(
        soup, "https://dados.test/historico/"
    )

    assert resultado == [
        "https://dados.test/historico1.xlsx",
        "https://dados.test/historico2.xlsx",
        "https://dados.test/arquivo1.xlsx",
    ]


def test_crawler_retorna_links_atuais_e_historicos_sem_duplicatas(
    caplog, configurar_resposta_http
):
    resultado = crawler()

    assert resultado == [
        "https://dados.test/arquivo1.xlsx",
        "https://dados.test/arquivo2.xlsx",
        "https://dados.test/historico1.xlsx",
        "https://dados.test/historico2.xlsx",
    ]
    assert "2 links atuais, 3 históricos e 4 únicos no total" in caplog.text
    assert modulo_crawler.obter_serie_origem("https://dados.test/arquivo1.xlsx") == "corrente"
    assert modulo_crawler.obter_serie_origem("https://dados.test/historico1.xlsx") == "historica"

#HELPERS
@pytest.mark.parametrize("valor", [1])
def test_funcao_recebeInteiro_devolve_um_numero_inteiro(valor):
    numero_inteiro = recebeInteiro(valor)
    assert type(numero_inteiro) == int

@pytest.mark.parametrize(
    ("expressao", "esperado"),
    [
        ("300", 300),
        ("1024 * 64", 65536),
        (" 1024*1024 ", 1048576),
        ("2 + 3 * 4", 14),
        ("(1 + 2) * 3", 9),
        ("10 // 3", 3),
        ("-5", -5),
    ],
)
def test_avaliar_expressao_inteira_aceita_aritmetica_simples(expressao, esperado):
    assert avaliar_expressao_inteira(expressao) == esperado


@pytest.mark.parametrize(
    "expressao",
    [
        "__import__('os').system('echo pwn')",
        "open('/etc/passwd')",
        "2 ** 10",
        "1 / 2",
        "1.5",
        "True",
        "abc",
        "(1 +",
        "10 // 0",
        "99999999999999",
        "1000000 * 1000000 * 1000000",
        "",
        "   ",
        None,
        123,
    ],
)
def test_avaliar_expressao_inteira_rejeita_o_que_nao_e_aritmetica_simples(expressao):
    with pytest.raises(ValorInteiroInvalido):
        avaliar_expressao_inteira(expressao)

#NORMALIZER
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

@pytest.mark.parametrize(
    ("registros", "esperado"),
    [
        ([], False),                                          # hash desconhecido
        ([{"id": 1, "periodo_dados": "2024"}], True),         # carga completa
        ([{"id": 1, "periodo_dados": "2019 - 2024"}], True),
        ([{"id": 1, "periodo_dados": None}], False),          # carga interrompida
        ([{"id": 1, "periodo_dados": ""}], False),
        ([{"id": 1}], False),                                 # sem o campo: não confia
    ],
)
def test_hash_so_conta_como_ingerido_com_periodo_preenchido(monkeypatch, registros, esperado):
    consulta = Mock(return_value=registros)
    monkeypatch.setattr(modulo_validator, "consultar_registros", consulta)
    monkeypatch.setattr(modulo_validator, "deletar_informacoes_arquivo", Mock(return_value=False)
)
    assert modulo_validator.check_hash_in_database("h") is esperado
    consulta.assert_called_once_with(
        tabela="informacoes_arquivo", filtros={"hash_sha256": "h"}
    )

def test_calculate_sha256_calcula_hash_do_arquivo(tmp_path, monkeypatch):
    arquivo = tmp_path / "dados.xlsx"
    conteudo = b"conteudo de teste para hash"
    arquivo.write_bytes(conteudo)
    monkeypatch.setattr(modulo_validator, "HASH_CHUNK_SIZE", 4)

    import hashlib
    esperado = hashlib.sha256(conteudo).hexdigest()

    assert modulo_validator.calculate_sha256(arquivo) == esperado

def test_check_hash_in_database_retorna_true_quando_encontra_registro(monkeypatch):
    consulta = Mock(return_value=[{"id": 1, "periodo_dados": "2024"}])
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

#CLEANUP
def test_limpar_remove_subpasta_do_diretorio_de_trabalho(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pasta = tmp_path / "temp"
    pasta.mkdir()
    (pasta / "a.xlsx").write_bytes(b"x")

    limpar_pasta_temporaria("temp")

    assert not pasta.exists()

def test_validar_aceita_subpasta_valida(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert validar_pasta_temporaria("ingestion/tempfiles") == (tmp_path / "ingestion" / "tempfiles").resolve()

def test_remover_arquivo_temporario_apaga_o_arquivo(tmp_path):
    arquivo = tmp_path / "a.xlsx"
    arquivo.write_bytes(b"x")
    remover_arquivo_temporario(arquivo)
    assert not arquivo.exists()

#PIPELINE
def test_recorte_temporal_sem_limite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo_pipeline,"get_intervalo_maximo_anos", lambda: None)

    df = pd.DataFrame(
        {
            "Data": ["2020-01-10", "2023-05-20", "2026-11-01"],
            "Valor": [1, 2, 3]
        }
    )

    resultado = modulo_pipeline.recorte_temporal(df)

    assert len(resultado) == 3
    assert resultado["Valor"].tolist() == [1, 2, 3]


def test_recorte_temporal_aplica_janela_de_anos(monkeypatch: pytest.MonkeyPatch) -> None:
    # Com intervalo = 3 e ano_max = 2026 -> ano_minimo = 2026 - (3 - 1) = 2024
    monkeypatch.setattr(modulo_pipeline, "get_intervalo_maximo_anos", lambda: 3)

    df = pd.DataFrame(
        {
            "Data": ["2022-03-15", "2024-01-01", "2025-07-10", "2026-12-31"],
            "Id": [10, 20, 30, 40],
        }
    )

    resultado = modulo_pipeline.recorte_temporal(df)

    assert resultado["Id"].tolist() == [20, 30, 40]
    assert resultado["Data"].dt.year.min() == 2024
    assert resultado["Data"].dt.year.max() == 2026

def test_arquivo_novo_e_carregado_e_concluido(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    STATUS_INGESTAO_SUCESSO = "SUCESSO"

    ambiente.urls = [URL_CVLI]

    resumo = modulo_pipeline.pipeline()

    inserido = ambiente.dados("arquivo_inserido")[0]
    assert "status" not in inserido  # nenhuma coluna nova é necessária
    assert inserido["tipo_crime"] == "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI"
    assert inserido["hash_sha256"] == "hash-CVLI_2024.xlsx"
    assert inserido["periodo_dados"] is None
    assert ambiente.dados("ocorrencias_inseridas") == [{"qtd": 2}]

    # periodo_dados é o marcador de "carga completa": só no passo final.
    concluido = ambiente.dados("arquivo_atualizado")[-1]
    assert concluido["id"] == inserido["id"]
    assert concluido["periodo_dados"] == "2024"
    assert ambiente.posicao("ocorrencias_inseridas") < ambiente.posicao("arquivo_atualizado")

    assert ambiente.dados("arquivo_deletado") == []
    assert (resumo.carregados, resumo.ignorados, resumo.falhas) == (1, 0, 0)
    assert resumo.status == STATUS_INGESTAO_SUCESSO

def test_periodo_cobre_varios_anos(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2019-a-2024.xlsx"
    ambiente.urls = [URL_CVLI]
    ambiente.registros = [{"data_fato": "2019-12-31"}, {"data_fato": "2024-01-01"}]
    ambiente.df_data = pd.DataFrame({"Data": ["2019-12-31", "2024-01-01"]})
    modulo_pipeline.pipeline()

    assert ambiente.dados("arquivo_atualizado")[-1]["periodo_dados"] == "2019-2024"

def test_arquivo_temporario_e_pasta_sao_removidos(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    ambiente.urls = [URL_CVLI]

    modulo_pipeline.pipeline()

    assert ambiente.dados("arquivo_removido") == [str(Path("tmp") / "CVLI_2024.xlsx")]
    assert ambiente.dados("limpeza") == [None]

def test_historico_e_aberto_antes_do_crawler_e_fechado_com_contadores(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    URL_FURTO = "https://dados.test/furtos.xlsx"
    STATUS_INGESTAO_EM_ANDAMENTO = "EM_ANDAMENTO"
    STATUS_INGESTAO_SUCESSO = "SUCESSO"
    ambiente.urls = [URL_CVLI, URL_FURTO]
    ambiente.validacoes["furtos.xlsx"] = {"is_new": False}

    modulo_pipeline.pipeline()

    assert ambiente.dados("historico_inserido") == [{"status": STATUS_INGESTAO_EM_ANDAMENTO}]
    assert ambiente.posicao("historico_inserido") < ambiente.posicao("crawler")
    final = ambiente.dados("historico_atualizado")[-1]
    assert final["id"] == 99
    assert final["status"] == STATUS_INGESTAO_SUCESSO
    assert final["qtd_arquivos_encontrados"] == 2
    assert final["qtd_arquivos_processados"] == 1  # o ignorado não conta como processado
    assert final["qtd_arquivos_falhas"] == 0
    assert final["mensagem_erro"] is None

def test_resumo_sem_erros_nao_gera_mensagem():
    assert ResumoIngestao().montar_mensagem_erro() is None


def test_resumo_limita_a_quantidade_de_erros_na_mensagem():
    resumo = ResumoIngestao(falhas=30, erros=[f"url{i}: Erro" for i in range(30)])

    mensagem = resumo.montar_mensagem_erro()

    assert "30 arquivo(s) com falha" in mensagem
    assert "url19" in mensagem and "url20" not in mensagem
    assert "mais 10 falha(s)" in mensagem

# ---------------------------------------------------------
# 2. SAD PATH
# ---------------------------------------------------------

#PIPELINE
def test_recorte_temporal_ignora_datas_invalidas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo_pipeline, "get_intervalo_maximo_anos", lambda: 2)

    df = pd.DataFrame(
        {
            "Data": ["data-invalida", "2025-02-01", "2026-06-01"],
            "Id": [1, 2, 3],
        }
    )

    with pytest.warns(UserWarning, match="Could not infer format"):
        resultado = modulo_pipeline.recorte_temporal(df)
        assert resultado["Id"].tolist() == [2, 3]

def test_arquivo_ja_ingerido_e_ignorado_sem_tocar_no_banco(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    STATUS_INGESTAO_SUCESSO = "SUCESSO"
    ambiente.urls = [URL_CVLI]
    ambiente.validacoes["CVLI_2024.xlsx"] = {"is_new": False, "name_exists": True, "id_registro": 5}

    resumo = modulo_pipeline.pipeline()

    assert ambiente.dados("arquivo_inserido") == []
    assert ambiente.dados("arquivo_deletado") == []
    assert ambiente.dados("normalizado") == []
    assert (resumo.carregados, resumo.ignorados, resumo.falhas) == (0, 1, 0)
    assert resumo.status == STATUS_INGESTAO_SUCESSO
    assert len(ambiente.dados("arquivo_removido")) == 1


def test_republicacao_publica_nova_versao_antes_de_excluir_anterior(
    ambiente, monkeypatch
):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"

    ambiente.urls = [URL_CVLI]

    # Simula a versão anterior já publicada no banco.
    estado_anterior = [{
        "id": 7,
        "nome_arquivo": "CVLI_2024.xlsx",
        "tipo_crime": "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
        "serie": "corrente",
        "periodo_dados": "2024",
        "ultimo_mes": 5,
        "hash_sha256": "hash-antigo",
    }]

    # O pipeline precisa encontrar o registro antigo na fotografia do banco.
    monkeypatch.setattr(
        modulo_pipeline,
        "listar_informacoes_arquivo",
        lambda cliente=None: estado_anterior,
    )

    resumo = modulo_pipeline.pipeline()

    # A nova versão deve ser inserida.
    inserido = ambiente.dados("arquivo_inserido")[0]

    assert inserido["id"] != 7
    assert inserido["periodo_dados"] is None

    # A nova versão deve ser publicada.
    atualizado = ambiente.dados("arquivo_atualizado")[-1]

    assert atualizado["periodo_dados"] == "2024"

    # A versão antiga só pode ser excluída depois da publicação.
    assert ambiente.dados("arquivos_excluidos") == [[7]]

    assert (
        ambiente.posicao("arquivo_inserido")
        < ambiente.posicao("arquivo_atualizado")
        < ambiente.posicao("arquivos_excluidos")
    )

    assert resumo.carregados == 1


def test_planilha_vazia_desfaz_a_carga_sem_queimar_o_hash(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    STATUS_INGESTAO_FALHA = "FALHA"
    ambiente.urls = [URL_CVLI]
    ambiente.registros = []

    resumo = modulo_pipeline.pipeline()

    assert ambiente.dados("ocorrencias_inseridas") == []
    assert ambiente.dados("arquivo_atualizado") == []  # periodo_dados nunca foi gravado
    assert ambiente.dados("arquivo_deletado") == [{"id": 100}]  # registro desfeito
    assert resumo.falhas == 1
    assert "PlanilhaSemRegistros" in resumo.erros[0]
    assert resumo.status == STATUS_INGESTAO_FALHA


def test_falha_no_meio_da_carga_desfaz_e_segue_para_o_proximo(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    URL_FURTO = "https://dados.test/furtos.xlsx"
    STATUS_INGESTAO_PARCIAL = "PARCIAL"
    ambiente.urls = [URL_CVLI, URL_FURTO]
    ambiente.ocorrencias_que_falham = 1  # só o primeiro arquivo falha

    resumo = modulo_pipeline.pipeline()

    # 1º arquivo (id 100): registro excluído (CASCADE limpa o que foi inserido).
    assert ambiente.dados("arquivo_deletado") == [{"id": 100}]
    # 2º arquivo (id 101): carga completa, periodo_dados gravado.
    atualizacoes = ambiente.dados("arquivo_atualizado")
    assert [(a["id"], a["periodo_dados"]) for a in atualizacoes] == [(101, "2024")]
    assert (resumo.carregados, resumo.falhas) == (1, 1)
    assert resumo.status == STATUS_INGESTAO_PARCIAL
    historico = ambiente.dados("historico_atualizado")[-1]
    assert historico["status"] == STATUS_INGESTAO_PARCIAL
    assert URL_CVLI in historico["mensagem_erro"]
    assert "RuntimeError" in historico["mensagem_erro"]


def test_falha_de_download_nao_impede_os_demais(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    URL_FURTO = "https://dados.test/furtos.xlsx"
    STATUS_INGESTAO_PARCIAL = "PARCIAL"
    ambiente.urls = [URL_CVLI, URL_FURTO]
    ambiente.erros_download["CVLI_2024.xlsx"] = DownloadHTTPError("Falha HTTP 503")

    resumo = modulo_pipeline.pipeline()

    assert ambiente.dados("arquivo_inserido")[0]["nome_arquivo"] == "furtos.xlsx"
    assert (resumo.carregados, resumo.falhas) == (1, 1)
    assert "DownloadHTTPError" in resumo.erros[0]
    assert resumo.status == STATUS_INGESTAO_PARCIAL


def test_falha_ao_desfazer_nao_mascara_o_erro_original(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    STATUS_INGESTAO_FALHA = "FALHA"
    ambiente.urls = [URL_CVLI]
    ambiente.registros = []
    ambiente.falha_ao_desfazer = True

    resumo = modulo_pipeline.pipeline()

    assert resumo.falhas == 1
    assert "PlanilhaSemRegistros" in resumo.erros[0]
    assert "banco fora do ar" not in resumo.erros[0]
    # Sem a exclusão, o registro fica com periodo_dados nulo (carga incompleta).
    assert ambiente.dados("arquivo_atualizado") == []
    assert ambiente.dados("historico_atualizado")[-1]["status"] == STATUS_INGESTAO_FALHA

def test_erro_do_crawler_fecha_historico_limpa_e_propaga(ambiente):
    STATUS_INGESTAO_FALHA = "FALHA"
    ambiente.erro_crawler = ConnectionError("sem rede")

    with pytest.raises(ConnectionError):
        modulo_pipeline.pipeline()

    final = ambiente.dados("historico_atualizado")[-1]
    assert final["status"] == STATUS_INGESTAO_FALHA
    assert "ConnectionError" in final["mensagem_erro"]
    assert "sem rede" in final["mensagem_erro"]
    assert ambiente.dados("limpeza") == [None]


def test_pasta_temporaria_insegura_aborta_antes_de_criar_historico(ambiente):
    ambiente.erro_validar_pasta = CaminhoTemporarioInseguro("TEMP_PATH=/")

    with pytest.raises(CaminhoTemporarioInseguro):
        modulo_pipeline.pipeline()

    assert ambiente.dados("historico_inserido") == []
    assert ambiente.dados("crawler") == []

def test_main_retorna_zero_sem_falhas(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    ambiente.urls = [URL_CVLI]
    assert modulo_pipeline.main() == 0


def test_main_retorna_um_quando_algum_arquivo_falha(ambiente):
    URL_CVLI = "https://dados.test/CVLI_2024.xlsx"
    ambiente.urls = [URL_CVLI]
    ambiente.registros = []
    assert modulo_pipeline.main() == 1


def test_main_retorna_um_em_erro_fatal(ambiente):
    ambiente.erro_crawler = ConnectionError("sem rede")
    assert modulo_pipeline.main() == 1

#HELPERS
@pytest.mark.parametrize("valor", ["", "abc", None])
def test_funcao_recebeInteiro_retorna_o_erro_ValorInteiroInvalido(valor):
    with pytest.raises(ValorInteiroInvalido):
        recebeInteiro(valor)
    

#CRAWLER
@pytest.mark.parametrize("conteudo", [None, "", False])
def test_extrair_links_retorna_lista_vazia_sem_conteudo(conteudo):
    assert extrair_links(conteudo) == []


def test_crawler_registra_e_propaga_variavel_atual_ausente(caplog):
    def obter_variavel(nome):
        if nome == "url_sspds":
            raise VariavelAmbienteNaoEncontrada(nome)
        return {
            "url_sspds_historico": "https://dados.test/historico/",
            "CRAWLER_TIMEOUT": "10",
        }[nome]

    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=obter_variavel):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(VariavelAmbienteNaoEncontrada):
                crawler()

    assert "Falha crítica de inicialização" in caplog.text


def test_crawler_registra_e_propaga_url_historica_ausente(caplog):
    def obter_variavel(nome):
        if nome == "url_sspds_historico":
            raise VariavelAmbienteNaoEncontrada(nome)
        return {
            "url_sspds": "https://dados.test/atual/",
            "CRAWLER_TIMEOUT": "10",
        }[nome]

    with patch.object(modulo_crawler, "get_variavel_ambiente", side_effect=obter_variavel):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(VariavelAmbienteNaoEncontrada):
                crawler()

    assert "Falha crítica de inicialização" in caplog.text


@pytest.mark.parametrize(
    ("erro", "mensagem"),
    [
        (requests.exceptions.Timeout("tempo excedido"), "Tempo limite excedido"),
        (requests.exceptions.ConnectionError("sem conexão"), "Erro de conexão"),
        (requests.exceptions.RequestException("erro inesperado"), "Erro inesperado na requisição"),
    ],
)
def test_obter_conteudo_html_registra_e_propaga_erros_de_requisicao(
    erro, mensagem, caplog
):
    with patch.object(modulo_crawler.r, "get", side_effect=erro):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(type(erro)):
                modulo_crawler.obter_conteudo_html(
                    "https://dados.test/atual/", timeout=10
                )

    assert mensagem in caplog.text


def test_obter_conteudo_html_registra_e_propaga_erro_http(caplog):
    resposta = Mock()
    resposta.status_code = 503
    erro_http = requests.exceptions.HTTPError(
        "Service Unavailable", response=resposta
    )
    resposta.raise_for_status.side_effect = erro_http

    with patch.object(modulo_crawler.r, "get", return_value=resposta):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(requests.exceptions.HTTPError):
                modulo_crawler.obter_conteudo_html(
                    "https://dados.test/atual/", timeout=10
                )

    assert "Status 503" in caplog.text


@pytest.mark.parametrize(
    ("funcao", "html", "url_base", "mensagem"),
    [
        (
            extrair_links_atuais,
            "<html><body><p>Estrutura atual alterada</p></body></html>",
            "https://dados.test/atual/",
            "seção de indicadores detalhados atuais",
        ),
        (
            extrair_links_historicos,
            "<html><body><p>Estrutura histórica alterada</p></body></html>",
            "https://dados.test/historico/",
            "seção de indicadores históricos",
        ),
    ],
)
def test_extratores_rejeitam_estrutura_html_ausente(
    funcao, html, url_base, mensagem
):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    with pytest.raises(EstruturaCSSDoSiteAlterado, match=mensagem):
        funcao(soup, url_base)


@pytest.mark.parametrize(
    ("funcao", "html", "url_base", "mensagem"),
    [
        (
            extrair_links_atuais,
            """<div id="conteudo"><div><div><div><section><section>
                <div>{}</div>
            </section></section></div></div></div></div>""".format(
                "".join("<div></div>" for _ in range(19)) + "<div>Sem links</div>"
            ),
            "https://dados.test/atual/",
            "não contém links",
        ),
        (
            extrair_links_historicos,
            """
            <div class="wp-block-columns" style="text-transform:uppercase">
                <a href="/sem-classe.xlsx">Link sem classe esperada</a>
            </div>
            """,
            "https://dados.test/historico/",
            "não contém links de download",
        ),
    ],
)
def test_extratores_rejeitam_secoes_sem_links_de_download(
    funcao, html, url_base, mensagem
):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    with pytest.raises(EstruturaCSSDoSiteAlterado, match=mensagem):
        funcao(soup, url_base)


@pytest.mark.parametrize("timeout_invalido", ["abc", "", None])
def test_crawler_usa_timeout_padrao_quando_configuracao_invalida(
    caplog, timeout_invalido, configurar_resposta_http
):
    def obter_variavel(nome):
        if nome == "url_sspds":
            return "https://dados.test/atual/"
        if nome == "url_sspds_historico":
            return "https://dados.test/historico/"
        if nome == "CRAWLER_TIMEOUT":
            if timeout_invalido is None:
                raise VariavelAmbienteNaoEncontrada(nome)
            return timeout_invalido
        raise VariavelAmbienteNaoEncontrada(nome)

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
        with pytest.raises(tipoOcorrenciaNaoEncontrado):
            resultado = normalizer(pd.DataFrame(), 1, "TIPO DESCONHECIDO")
            assert resultado is None
        assert "Falha na normalização: Tipo de ocorrência não encontrado!" in caplog.text


def test_normalizer_registra_erro_de_colunas_ausentes_e_retorna_none(
    caplog, monkeypatch
):
    monkeypatch.setattr(modulo_normalizer, "configure_logging", lambda: None)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ColunasAusentesNaPlanilha):
            resultado = normalizer(
                pd.DataFrame(),
                1,
                "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI",
            )

            assert resultado is None
    assert "Falha na normalização: Colunas ausentes na planilha:" in caplog.text

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

    with pytest.raises(DatabaseLookupError, match="Falha ao verificar o hash"):
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

#CLEANUP
def test_limpar_pasta_inexistente_nao_gera_erro(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    limpar_pasta_temporaria("nao_existe")


def test_limpar_caminho_que_e_arquivo_levanta_not_a_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "arquivo.txt").write_text("x")
    with pytest.raises(NotADirectoryError):
        limpar_pasta_temporaria("arquivo.txt")


@pytest.mark.parametrize("caminho", [".", "..", "/", "subpasta/.."])
def test_validar_rejeita_cwd_ancestrais_e_raiz(tmp_path, monkeypatch, caminho):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "subpasta").mkdir()
    with pytest.raises(CaminhoTemporarioInseguro):
        validar_pasta_temporaria(caminho)


def test_validar_rejeita_pasta_fora_do_diretorio_de_trabalho(tmp_path, monkeypatch):
    trabalho = tmp_path / "trabalho"
    fora = tmp_path / "fora"
    trabalho.mkdir()
    fora.mkdir()
    monkeypatch.chdir(trabalho)
    with pytest.raises(CaminhoTemporarioInseguro):
        validar_pasta_temporaria(str(fora))


def test_limpar_rejeita_e_nao_apaga_a_pasta_do_codigo(monkeypatch):
    pacote = Path(modulo_cleanup.__file__).resolve().parent
    monkeypatch.chdir(pacote.parent)

    with pytest.raises(CaminhoTemporarioInseguro):
        limpar_pasta_temporaria(str(pacote))

    assert (pacote / "cleanup.py").exists()

def test_remover_arquivo_temporario_ignora_arquivo_inexistente(tmp_path):
    remover_arquivo_temporario(tmp_path / "nao_existe.xlsx")


def test_remover_arquivo_temporario_nao_propaga_erro_do_sistema(tmp_path):
    # Um diretório não pode ser removido com unlink: deve virar apenas aviso.
    remover_arquivo_temporario(tmp_path)
    assert tmp_path.exists()

def test_check_hash_remove_orfao_da_fotografia_em_memoria(monkeypatch):
    registros = [
        {"id": 10, "hash_sha256": "hash-orfa", "periodo_dados": None},
        {"id": 11, "hash_sha256": "outro-hash", "periodo_dados": "2026"},
    ]
    removidos = []
    monkeypatch.setattr(
        modulo_validator,
        "deletar_informacoes_arquivo",
        lambda id, cliente=None: removidos.append(id),
    )

    assert modulo_validator.check_hash_in_database("hash-orfa", registros=registros) is False
    assert removidos == [10]
    assert [r["id"] for r in registros] == [11]


def test_check_hash_completo_nao_remove_registro(monkeypatch):
    registros = [{"id": 10, "hash_sha256": "hash-ok", "periodo_dados": "2026"}]
    remover = Mock()
    monkeypatch.setattr(modulo_validator, "deletar_informacoes_arquivo", remover)

    assert modulo_validator.check_hash_in_database("hash-ok", registros=registros) is True
    remover.assert_not_called()

def test_carregar_arquivo_bloqueia_contagem_persistida_incompleta(monkeypatch):
    inserir_arquivo = Mock(return_value=50)
    remover_arquivo = Mock()
    monkeypatch.setattr(modulo_pipeline, "inserir_informacoes_arquivo", inserir_arquivo)
    monkeypatch.setattr(modulo_pipeline, "normalizer", Mock(return_value=[{}, {}]))
    monkeypatch.setattr(modulo_pipeline, "inserir_ocorrencias_crimes", Mock())
    monkeypatch.setattr(modulo_pipeline, "contar_ocorrencias_por_arquivo", Mock(return_value=1))
    monkeypatch.setattr(modulo_pipeline, "deletar_informacoes_arquivo", remover_arquivo)

    classificado = {
        "name": "CVLI_Outubro.xlsx",
        "sha256": "hash-novo",
        "tipo_ocorrencia": "CVLI",
        "serie": "corrente",
        "ultimo_mes": 10,
        "periodo_dados": "2026",
        "size_bytes": 100,
        "path": "tmp/CVLI_Outubro.xlsx",
        "_dataframe": pd.DataFrame(),
    }

    with pytest.raises(RuntimeError, match="Inserção incompleta"):
        modulo_pipeline.carregar_arquivo(
            "https://dados.test/CVLI_Outubro.xlsx",
            classificado,
            "2026-11-19T00:00:00+00:00",
            99,
            "cliente-fake",
        )

    remover_arquivo.assert_called_once_with(id=50, cliente="cliente-fake")


def test_carregar_arquivo_nao_publica_reducao_de_ocorrencias(monkeypatch):
    monkeypatch.setattr(modulo_pipeline, "inserir_informacoes_arquivo", Mock(return_value=50))
    monkeypatch.setattr(modulo_pipeline, "normalizer", Mock(return_value=[{}, {}]))
    monkeypatch.setattr(modulo_pipeline, "inserir_ocorrencias_crimes", Mock())
    monkeypatch.setattr(
        modulo_pipeline, "contar_ocorrencias_por_arquivo", Mock(side_effect=[2, 3])
    )
    remover_arquivo = Mock()
    atualizar_arquivo = Mock()
    excluir_antigo = Mock()
    monkeypatch.setattr(modulo_pipeline, "deletar_informacoes_arquivo", remover_arquivo)
    monkeypatch.setattr(modulo_pipeline, "atualizar_informacoes_arquivo", atualizar_arquivo)
    monkeypatch.setattr(modulo_pipeline, "excluir_arquivos_por_ids", excluir_antigo)

    classificado = {
        "name": "CVLI_Outubro.xlsx",
        "sha256": "hash-novo",
        "tipo_ocorrencia": "CVLI",
        "serie": "corrente",
        "ultimo_mes": 10,
        "periodo_dados": "2026",
        "size_bytes": 100,
        "path": "tmp/CVLI_Outubro.xlsx",
        "ids_substituir": [1],
        "_estado_arquivos": [{"id": 1}],
        "_dataframe": pd.DataFrame(),
    }

    with pytest.raises(modulo_pipeline.IntegridadeVersaoError, match="menos ocorrências"):
        modulo_pipeline.carregar_arquivo(
            "https://dados.test/CVLI_Outubro.xlsx",
            classificado,
            "2026-11-19T00:00:00+00:00",
            99,
            "cliente-fake",
        )

    remover_arquivo.assert_called_once_with(id=50, cliente="cliente-fake")
    atualizar_arquivo.assert_not_called()
    excluir_antigo.assert_not_called()
