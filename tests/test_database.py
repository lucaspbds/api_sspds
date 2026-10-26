import logging
import uuid
import pytest

from database.config import get_variavel_ambiente
from database.exceptions import (
    ErroOperacaoBanco,
    VariavelAmbienteNaoEncontrada,
)
from database.repository import (
    atualizar_registro,
    consultar_registros,
    inserir_registros,
    validar_conexao,
)


# ============================================================================
# 1. TESTE DE CONEXÃO
# ============================================================================
@pytest.mark.database
def test_deve_validar_conexao_com_banco_local(banco_local):
    """Valida se a aplicação consegue se conectar ao Supabase local."""
    conectado = validar_conexao(cliente=banco_local)
    assert conectado is True


# ============================================================================
# 2. TESTES DE LEITURA (CONSULTA)
# ============================================================================
@pytest.mark.database
def test_deve_consultar_ocorrencias_com_filtro_e_limite(banco_local):
    """Valida a leitura na tabela ocorrencias_crimes com filtro por município e limite."""
    registros = consultar_registros(
        tabela="ocorrencias_crimes",
        filtros={"municipio": "Fortaleza"},
        limite=2,
        cliente=banco_local,
    )
    assert isinstance(registros, list)
    assert len(registros) > 0
    assert len(registros) <= 2
    assert registros[0]["municipio"] == "Fortaleza"


@pytest.mark.database
def test_deve_consultar_ocorrencia_com_idade_nao_informada(banco_local):
    """Valida a leitura do caso de borda em que vitima_idade é NULL (Não Informada)."""
    registros = consultar_registros(
        tabela="ocorrencias_crimes",
        filtros={"ais": "AIS 02", "municipio": "Fortaleza"},
        cliente=banco_local,
    )
    assert len(registros) >= 1
    assert any(r["vitima_idade"] is None for r in registros)


# ============================================================================
# 3. TESTES DE INSERÇÃO
# ============================================================================
@pytest.mark.database
def test_deve_inserir_registro_em_historico_ingestoes(banco_local):
    """Valida a inserção de um novo registro na tabela historico_ingestoes."""
    novo_historico = {
        "status": "EM_ANDAMENTO",
        "qtd_arquivos_encontrados": 3,
        "qtd_arquivos_processados": 0,
        "qtd_arquivos_falhas": 0,
    }

    inseridos = inserir_registros(
        tabela="historico_ingestoes",
        dados=novo_historico,
        cliente=banco_local,
    )

    assert len(inseridos) == 1
    id_criado = inseridos[0]["id"]
    assert inseridos[0]["status"] == "EM_ANDAMENTO"
    assert inseridos[0]["qtd_arquivos_encontrados"] == 3

    # Limpeza do registro de teste
    banco_local.table("historico_ingestoes").delete().eq("id", id_criado).execute()


@pytest.mark.database
def test_deve_inserir_log_na_tabela_api_request_logs(banco_local):
    """Valida a inserção de uma métrica de requisição na tabela api_request_logs."""
    req_id = str(uuid.uuid4())
    novo_log = {
        "request_id": req_id,
        "method": "GET",
        "endpoint": "/crimes/cvli",
        "status_code": 200,
        "duration_ms": 18,
        "client_type": "public",
    }

    inseridos = inserir_registros(
        tabela="api_request_logs",
        dados=novo_log,
        cliente=banco_local,
    )

    assert len(inseridos) == 1
    id_criado = inseridos[0]["id"]
    assert inseridos[0]["request_id"] == req_id
    assert inseridos[0]["client_type"] == "public"

    # Limpeza do registro de teste
    banco_local.table("api_request_logs").delete().eq("id", id_criado).execute()


# ============================================================================
# 4. TESTE DE ATUALIZAÇÃO
# ============================================================================
@pytest.mark.database
def test_deve_atualizar_status_de_ingestao(banco_local):
    """Valida a atualização (UPDATE) de um registro existente no banco."""
    inseridos = inserir_registros(
        tabela="historico_ingestoes",
        dados={"status": "EM_ANDAMENTO", "qtd_arquivos_encontrados": 1},
        cliente=banco_local,
    )
    id_criado = inseridos[0]["id"]

    atualizados = atualizar_registro(
        tabela="historico_ingestoes",
        id_registro=id_criado,
        novos_dados={"status": "SUCESSO", "qtd_arquivos_processados": 1},
        cliente=banco_local,
    )

    assert len(atualizados) == 1
    assert atualizados[0]["status"] == "SUCESSO"
    assert atualizados[0]["qtd_arquivos_processados"] == 1

    # Limpeza do registro de teste
    banco_local.table("historico_ingestoes").delete().eq("id", id_criado).execute()


# ============================================================================
# 5. TESTES DE TRATAMENTO DE ERRO
# ============================================================================
def test_deve_lancar_erro_quando_variavel_ambiente_nao_existir(monkeypatch):
    """Valida se VariavelAmbienteNaoEncontrada é lançada quando falta variável."""
    monkeypatch.delenv("VARIAVEL_INEXISTENTE_TESTE", raising=False)

    with pytest.raises(VariavelAmbienteNaoEncontrada) as contexto:
        get_variavel_ambiente("VARIAVEL_INEXISTENTE_TESTE")

    assert "VARIAVEL_INEXISTENTE_TESTE" in str(contexto.value)


def test_deve_lancar_erro_quando_parametros_forem_invalidos(banco_local):
    """Valida se o repositório rejeita tabela vazia, limite negativo ou payload vazio."""
    with pytest.raises(ValueError):
        consultar_registros(tabela="", cliente=banco_local)

    with pytest.raises(ValueError):
        consultar_registros(tabela="ocorrencias_crimes", limite=-5, cliente=banco_local)

    with pytest.raises(ValueError):
        inserir_registros(tabela="historico_ingestoes", dados={}, cliente=banco_local)

    with pytest.raises(ValueError):
        atualizar_registro(
            tabela="historico_ingestoes",
            id_registro=1,
            novos_dados={},
            cliente=banco_local,
        )


@pytest.mark.database
def test_deve_lancar_erro_operacao_banco_quando_tabela_nao_existir(banco_local):
    """Valida se consultar uma tabela inexistente lança ErroOperacaoBanco."""
    with pytest.raises(ErroOperacaoBanco) as contexto:
        consultar_registros(tabela="tabela_que_nao_existe_123", cliente=banco_local)

    assert contexto.value.operacao == "consulta"


@pytest.mark.database
def test_deve_rejeitar_client_type_invalido_em_api_request_logs(banco_local):
    """Valida se a constraint CHECK do banco bloqueia client_type inválido."""
    log_invalido = {
        "request_id": str(uuid.uuid4()),
        "method": "GET",
        "endpoint": "/crimes/cvli",
        "status_code": 200,
        "duration_ms": 10,
        "client_type": "tipo_invalido_fora_do_check",
    }

    with pytest.raises(ErroOperacaoBanco):
        inserir_registros(
            tabela="api_request_logs",
            dados=log_invalido,
            cliente=banco_local,
        )


# ============================================================================
# 6. TESTE DE LOGS DO SISTEMA
# ============================================================================
@pytest.mark.database
def test_deve_registrar_log_de_erro_quando_operacao_falhar(banco_local, caplog):
    """Valida com caplog se falhas de banco geram registro no nível ERROR."""
    with caplog.at_level(logging.ERROR):
        try:
            consultar_registros(tabela="tabela_inexistente_erro_log", cliente=banco_local)
        except ErroOperacaoBanco:
            pass

    assert any(record.levelname == "ERROR" for record in caplog.records)