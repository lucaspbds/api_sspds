import pytest
import ingestion.crawler as modulo_crawler
from unittest.mock import Mock, patch
import pandas as pd
from database.repository import criar_cliente_supabase
from pathlib import Path
import ingestion.pipeline as modulo_pipeline

REGISTROS_2024 = [{"data_fato": "2024-03-10"}, {"data_fato": "2024-05-01"}]




class AmbienteFake:
    """Estado e registro de eventos compartilhados pelos fakes."""

    def __init__(self):
        self.eventos = []
        self.urls = []
        self.validacoes = {}              # nome do arquivo -> campos a sobrescrever
        self.registros = REGISTROS_2024   # retorno do normalizer
        self.erro_crawler = None
        self.erros_download = {}          # nome do arquivo -> exceção
        self.ocorrencias_que_falham = 0   # as N primeiras inserções de ocorrências falham
        self.falha_ao_desfazer = False
        self.erro_validar_pasta = None
        self._chamadas_ocorrencias = 0
        self._proximo_id = 100

    def dados(self, nome):
        return [d for n, d in self.eventos if n == nome]

    def posicao(self, nome):
        return [n for n, _ in self.eventos].index(nome)


@pytest.fixture
def html_sspds_atual():
    """HTML sintético compatível com o seletor da seção de dados atuais."""
    divs = "".join(
        f"<div>{conteudo}</div>"
        for conteudo in (
            [""] * 19
            + [
                "<a href='/arquivo1.xlsx'>CVLI</a>"
                "<a href='/arquivo2.xlsx'>Furto</a>"
            ]
        )
    )

    return f"""
        <html>
            <body>
                <div id="conteudo">
                    <div><div><div>
                        <section><section>
                            <div>{divs}</div>
                        </section></section>
                    </div></div></div>
                </div>
            </body>
        </html>
    """


@pytest.fixture
def html_sspds_historico():
    """HTML sintético compatível com a seção Gutenberg de dados históricos."""
    return """
        <html>
            <body>
                <div class="wp-block-columns" style="text-transform:uppercase">
                    <a class="wp-block-button__link" href="/historico1.xlsx">CVLI</a>
                    <a class="wp-block-button__link" href="/historico2.xlsx">Furto</a>
                    <a class="wp-block-button__link" href="/arquivo1.xlsx">Duplicado</a>
                </div>
                <div>
                    <a class="wp-block-button__link" href="/fora-da-secao.xlsx">Menu</a>
                </div>
            </body>
        </html>
    """


@pytest.fixture
def configurar_resposta_http(html_sspds_atual, html_sspds_historico):
    """Simula as duas respostas HTTP: página atual e página histórica."""
    urls = {
        "url_sspds": "https://dados.test/atual/",
        "url_sspds_historico": "https://dados.test/historico/",
        "CRAWLER_TIMEOUT": "10",
    }

    with patch.object(
        modulo_crawler,
        "get_variavel_ambiente",
        side_effect=lambda nome: urls[nome],
    ):
        with patch.object(modulo_crawler.r, "get") as mock_get:
            respostas = []
            for html in (html_sspds_atual, html_sspds_historico):
                resposta = Mock()
                resposta.text = html
                resposta.raise_for_status.return_value = None
                respostas.append(resposta)

            mock_get.side_effect = respostas
            yield mock_get


@pytest.fixture
def df_cvli():
    return pd.DataFrame([{
        "Município": "  FORTALEZA ",
        "AIS": "AIS 1",
        "Natureza": "HOMICÍDIO",
        "Data": "2024-01-01",  # segunda-feira
        "Hora": "08:30",
        "Dia da Semana": "segunda-feira",
        "Meio Empregado": "ARMA DE FOGO",
        "Gênero": "masculino",
        "Idade da Vítima": "25",
        "Escolaridade da Vítima": "ensino médio",
        "Raça da Vítima": "parda",
    }])


@pytest.fixture
def df_animais():
    return pd.DataFrame([{
        "Município": "FORTALEZA",
        "AIS": "AIS 1",
        "Data": "2024-01-01",
        "Hora": "09:15",
        "Dia da Semana": "segunda-feira",
    }])


@pytest.fixture
def df_armas(df_animais):
    df = df_animais.copy()
    df["Quantidade"] = "2"
    return df


@pytest.fixture
def df_entorpecentes(df_animais):
    df = df_animais.copy()
    df["Quantidade (Kg)"] = "1,25"
    df["Tipo de Entorpecente"] = "maconha"
    return df


@pytest.fixture
def df_preconceito(df_animais):
    df = df_animais.copy()
    df["Gênero"] = "feminino"
    df["Idade da Vítima"] = "30"
    df["Escolaridade da Vítima"] = "ensino superior"
    df["Raça da Vítima"] = "parda"
    return df


@pytest.fixture
def df_homofobia(df_animais):
    df = df_animais.copy()
    df["Idade da Vítima"] = "22"
    df["Escolaridade da Vítima"] = "ensino médio"
    df["Raça da Vítima"] = "branca"
    df["Natureza"] = "ameaça"
    df["Identidade de Gênero"] = "mulher trans"
    df["Orientação Sexual"] = "heterossexual"
    df["Local"] = "via pública"
    return df

@pytest.fixture(scope="function")
def banco_local():
    """
    Fixture que fornece uma instância do cliente Supabase conectada ao banco local.
    """
    cliente = criar_cliente_supabase()
    yield cliente
    cliente = None

@pytest.fixture
def ambiente(monkeypatch):
    amb = AmbienteFake()
    registrar = lambda nome, dados=None: amb.eventos.append((nome, dados))  # noqa: E731

    def validar_pasta_temporaria(*args, **kwargs):
        if amb.erro_validar_pasta:
            raise amb.erro_validar_pasta
        registrar("pasta_validada")

    def crawler():
        registrar("crawler")
        if amb.erro_crawler:
            raise amb.erro_crawler
        return list(amb.urls)

    def download_xlsx(url):
        nome = url.rsplit("/", 1)[-1]
        if nome in amb.erros_download:
            raise amb.erros_download[nome]
        return Path("tmp") / nome

    def validate_xlsx_file(caminho, registros=None):
        nome = Path(caminho).name
        base = {
            "path": f"tmp/{nome}", "name": nome, "sha256": f"hash-{nome}",
            "is_new": True, "size_bytes": 123, "name_exists": False, "id_registro": None,
        }
        base.update(amb.validacoes.get(nome, {}))
        return base

    def normalizer(df, arquivo_id, tipo_ocorrencia):
        registrar("normalizado", {"arquivo_id": arquivo_id, "tipo": tipo_ocorrencia})
        return list(amb.registros)

    def inserir_historico_ingestoes(dados, cliente=None):
        registrar("historico_inserido", dict(dados))
        return 99

    def atualizar_historico_ingestoes(id, dados, cliente=None):
        registrar("historico_atualizado", {"id": id, **dados})
        return []

    def inserir_informacoes_arquivo(dados, cliente=None):
        novo_id = amb._proximo_id
        amb._proximo_id += 1
        registrar("arquivo_inserido", {"id": novo_id, **dados})
        return novo_id

    def atualizar_informacoes_arquivo(id, dados, cliente=None):
        registrar("arquivo_atualizado", {"id": id, **dados})
        return id

    def deletar_informacoes_arquivo(id, cliente=None):
        if amb.falha_ao_desfazer and id >= 100:  # só a compensação (ids novos)
            raise RuntimeError("banco fora do ar")
        registrar("arquivo_deletado", {"id": id})

    def inserir_ocorrencias_crimes(dados, tamanho_lote=None, cliente=None):
        amb._chamadas_ocorrencias += 1
        if amb._chamadas_ocorrencias <= amb.ocorrencias_que_falham:
            raise RuntimeError("falha na inserção em lote")
        registrar("ocorrencias_inseridas", {"qtd": len(dados)})

    fakes = {
        "validar_pasta_temporaria": validar_pasta_temporaria,
        "limpar_pasta_temporaria": lambda *a, **k: registrar("limpeza"),
        "remover_arquivo_temporario": lambda caminho: registrar("arquivo_removido", str(caminho)),
        "criar_cliente_supabase": lambda: "cliente-fake",
        "crawler": crawler,
        "download_xlsx": download_xlsx,
        "validate_xlsx_file": validate_xlsx_file,
         "ler_planilha": lambda caminho: pd.DataFrame({"Data": ["2024-01-01", "2024-05-01"]}),
        "normalizer": normalizer,
        "inserir_historico_ingestoes": inserir_historico_ingestoes,
        "atualizar_historico_ingestoes": atualizar_historico_ingestoes,
        "inserir_informacoes_arquivo": inserir_informacoes_arquivo,
        "atualizar_informacoes_arquivo": atualizar_informacoes_arquivo,
        "deletar_informacoes_arquivo": deletar_informacoes_arquivo,
        "inserir_ocorrencias_crimes": inserir_ocorrencias_crimes,
        "listar_informacoes_arquivo": lambda cliente=None: [],
        "excluir_arquivos_por_ids": lambda ids, cliente=None: registrar("arquivos_excluidos", list(ids)),
        "contar_ocorrencias_por_arquivo": lambda arquivo_id, cliente=None: len(amb.registros),
    }
    for nome, funcao in fakes.items():
        monkeypatch.setattr(modulo_pipeline, nome, funcao)
    return amb
