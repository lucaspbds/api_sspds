import pytest
import ingestion.crawler as modulo_crawler
from ingestion.crawler import crawler, extrair_links
from ingestion.exception import VariavelAmbienteNaoEncontrada
from unittest.mock import Mock, patch
from database.repository import criar_cliente_supabase

@pytest.fixture
def html_sspds():
    """
    Monta um HTML de teste compatível com o seletor CSS utilizado
    pelo crawler, sem depender do site real da SSPDS.
    """
    divs = "".join(
        f"<div>{conteudo}</div>"
        for conteudo in (
            [""] * 19 +
            ["<a href='/arquivo1.xlsx'>CVLI</a>"
             "<a href='/arquivo2.xlsx'>Furto</a>"] 
        )
    )

    return f"""
        <html>
            <body>
                <div id="conteudo">
                    <div>
                        <div>
                            <div>
                                <section>
                                    <section>
                                        <div>{divs}</div>
                                    </section>
                                </section>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    """

@pytest.fixture
def configurar_resposta_http(html_sspds):
    """
    Fixture que já faz o patch do requests.get e configura a resposta
    automaticamente usando o html_sspds.
    """
    with patch.object(modulo_crawler.r, "get") as mock_get:
        resposta = Mock()
        resposta.text = html_sspds
        resposta.raise_for_status.return_value = None
        mock_get.return_value = resposta
        yield resposta  # Retorna a resposta configurada para o teste, se ele precisar


@pytest.fixture(scope="function")
def banco_local():
    """
    Fixture que fornece uma instância do cliente Supabase conectada ao banco local.
    """
    cliente = criar_cliente_supabase()
    yield cliente
    cliente = None