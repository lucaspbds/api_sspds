import hashlib
import logging
import uuid
from unittest.mock import MagicMock
import pytest

from database.config import get_variavel_ambiente
from database.exceptions import (
    ErroOperacaoBanco,
    VariavelAmbienteNaoEncontrada,
)
from database.repository import (
    LIMITE_MAXIMO_PAGINACAO,
    LIMITE_PADRAO_PAGINACAO,
    atualizar_registro,
    consultar_registros,
    consultar_registros_paginados,
    contar_ocorrencias_por_arquivo,
    excluir_arquivo,
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


@pytest.fixture
def ocorrencia_agosto_2026(banco_local):
    """Cria arquivo e ocorrência temporários em 2026-08-12 e remove via CASCADE ao final."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    arquivo = inserir_registros(
        tabela="informacoes_arquivo",
        dados={
            "nome_arquivo": "teste_intervalo_datas_2026.xlsx",
            "url_download": "https://exemplo.sspds.ce.gov.br/teste_datas.xlsx",
            "hash_sha256": hash_unico,
            "tipo_crime": "cvli",
        },
        cliente=banco_local,
    )
    id_arquivo = arquivo[0]["id"]

    ocorrencia = inserir_registros(
        tabela="ocorrencias_crimes",
        dados={
            "arquivo_id": id_arquivo,
            "tipo_crime": "cvli",
            "municipio": "Fortaleza",
            "data_fato": "2026-08-12",
        },
        cliente=banco_local,
    )

    yield ocorrencia[0]

    # Teardown garantido: remove o arquivo e, por ON DELETE CASCADE, a ocorrência criada
    excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)


@pytest.mark.database
def test_deve_consultar_ocorrencias_com_filtro_de_intervalo_de_datas(
    banco_local, ocorrencia_agosto_2026
):
    """Valida a leitura com filtro por intervalo de datas (coluna_data, data_inicio, data_fim)."""
    registros = consultar_registros(
        tabela="ocorrencias_crimes",
        coluna_data="data_fato",
        data_inicio="2026-08-01",
        data_fim="2026-08-15",
        cliente=banco_local,
    )
    assert isinstance(registros, list)
    assert len(registros) > 0
    # Garante que todos os registros retornados estão dentro do intervalo especificado
    assert all("2026-08-01" <= r["data_fato"] <= "2026-08-15" for r in registros)


@pytest.mark.database
def test_deve_consultar_ocorrencias_combinando_filtros_de_igualdade_e_data(
    banco_local, ocorrencia_agosto_2026
):
    """Valida a combinação de filtro de igualdade com intervalo de data e limite."""
    registros = consultar_registros(
        tabela="ocorrencias_crimes",
        filtros={"municipio": "Fortaleza"},
        coluna_data="data_fato",
        data_inicio="2026-08-10",
        data_fim="2026-08-20",
        limite=1,
        cliente=banco_local,
    )
    assert isinstance(registros, list)
    assert len(registros) == 1
    assert registros[0]["municipio"] == "Fortaleza"

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
# 5. TESTE DE EXCLUSÃO
# ============================================================================
@pytest.mark.database
def test_deve_excluir_arquivo_e_ocorrencias_em_cascata(banco_local):
    """Valida a exclusão em informacoes_arquivo e o ON DELETE CASCADE em ocorrencias_crimes."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    arquivo_inserido = inserir_registros(
        tabela="informacoes_arquivo",
        dados={
            "nome_arquivo": "teste_exclusao_cvli.xlsx",
            "url_download": "https://exemplo.sspds.ce.gov.br/teste_exclusao.xlsx",
            "hash_sha256": hash_unico,
            "tipo_crime": "cvli",
        },
        cliente=banco_local,
    )
    id_arquivo = arquivo_inserido[0]["id"]
    
    # Insere uma ocorrência filha vinculada ao arquivo para provar o ON DELETE CASCADE
    inserir_registros(
        tabela="ocorrencias_crimes",
        dados={
            "arquivo_id": id_arquivo,
            "tipo_crime": "cvli",
            "municipio": "Fortaleza",
            "data_fato": "2026-01-10",
        },
        cliente=banco_local,
    )
    removidos = excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)
    assert len(removidos) == 1
    assert removidos[0]["id"] == id_arquivo
    
    # Confirma no banco que o arquivo e a ocorrência vinculada não existem mais
    assert consultar_registros("informacoes_arquivo", filtros={"id": id_arquivo}, cliente=banco_local) == []
    assert consultar_registros("ocorrencias_crimes", filtros={"arquivo_id": id_arquivo}, cliente=banco_local) == []


@pytest.mark.database
def test_deve_retornar_lista_vazia_quando_arquivo_nao_existir(banco_local, caplog):
    """Valida a idempotência da exclusão e o log WARNING quando o ID não existe no banco."""
    with caplog.at_level(logging.WARNING):
        removidos = excluir_arquivo(id_arquivo=999999999, cliente=banco_local)
    assert removidos == []
    assert any(record.levelname == "WARNING" for record in caplog.records)


@pytest.mark.parametrize("id_invalido", [0, -1, -50, "10", None, True, False, 1.5])
def test_deve_lancar_value_error_quando_id_arquivo_for_invalido(id_invalido):
    """Valida que IDs inválidos são rejeitados antes mesmo de tentar conectar ao banco."""
    with pytest.raises(ValueError):
        excluir_arquivo(id_arquivo=id_invalido)


def test_deve_lancar_erro_operacao_banco_quando_exclusao_falhar(caplog):
    """Valida o tratamento de erro e o log ERROR quando o Supabase falha durante a exclusão."""
    cliente_falso = MagicMock()
    cliente_falso.table.side_effect = RuntimeError("Falha simulada de conexão")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            excluir_arquivo(id_arquivo=1, cliente=cliente_falso)
    assert contexto.value.operacao == "exclusao"
    assert contexto.value.tabela == "informacoes_arquivo"
    assert any(record.levelname == "ERROR" for record in caplog.records)
# ============================================================================
# 6. TESTES DE TRATAMENTO DE ERRO
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
# 7. TESTE DE LOGS DO SISTEMA
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


@pytest.mark.parametrize(
    "operacao_esperada,chamada",
    [
        (
            "consulta",
            lambda cli: consultar_registros(tabela="ocorrencias_crimes", cliente=cli),
        ),
        (
            "inserção",
            lambda cli: inserir_registros(
                tabela="historico_ingestoes", dados={"status": "SUCESSO"}, cliente=cli
            ),
        ),
        (
            "atualização",
            lambda cli: atualizar_registro(
                tabela="historico_ingestoes",
                id_registro=1,
                novos_dados={"status": "SUCESSO"},
                cliente=cli,
            ),
        ),
    ],
)
def test_deve_incluir_operacao_e_mensagem_da_excecao_no_log_de_erro(
    caplog, operacao_esperada, chamada
):
    """Valida que falhas de consulta, inserção e atualização logam a operação e o detalhe da Exception."""
    mensagem_erro = "violates check constraint simulada"
    cliente_falso = MagicMock()
    cliente_falso.table.side_effect = RuntimeError(mensagem_erro)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            chamada(cliente_falso)

    assert mensagem_erro in str(contexto.value)
    

    mensagens_log = [record.getMessage() for record in caplog.records if record.levelname == "ERROR"]
    assert any(
        operacao_esperada in msg and mensagem_erro in msg
        for msg in mensagens_log
    )


# ============================================================================
# 8. TESTES DE VERSIONAMENTO DE SÉRIES (serie e ultimo_mes)
# ============================================================================
@pytest.mark.database
def test_deve_inserir_arquivo_com_serie_e_ultimo_mes_validos(banco_local):
    """Valida inserção em informacoes_arquivo com serie='historica' e ultimo_mes='10'."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_criado = None
    try:
        inseridos = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_serie_historica.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/historica.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
                "serie": "historica",
                "ultimo_mes": 10,
            },
            cliente=banco_local,
        )
        assert len(inseridos) == 1
        id_criado = inseridos[0]["id"]
        assert inseridos[0]["serie"] == "historica"
        assert inseridos[0]["ultimo_mes"] == 10
    finally:
        if id_criado is not None:
            banco_local.table("informacoes_arquivo").delete().eq("id", id_criado).execute()


@pytest.mark.database
def test_deve_usar_serie_corrente_como_padrao_quando_omitida(banco_local):
    """Valida que serie assume 'corrente' e ultimo_mes aceita NULL quando omitidos."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_criado = None
    try:
        inseridos = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_serie_default.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/corrente.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
            },
            cliente=banco_local,
        )
        assert len(inseridos) == 1
        id_criado = inseridos[0]["id"]
        assert inseridos[0]["serie"] == "corrente"
        assert inseridos[0]["ultimo_mes"] is None
    finally:
        if id_criado is not None:
            banco_local.table("informacoes_arquivo").delete().eq("id", id_criado).execute()


@pytest.mark.database
@pytest.mark.parametrize("serie_invalida", ["mensal", "histórica", "CORRENTE", ""])
def test_deve_rejeitar_serie_invalida_em_informacoes_arquivo(banco_local, serie_invalida):
    """Valida se o CHECK do banco bloqueia valores fora de ('corrente', 'historica')."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    with pytest.raises(ErroOperacaoBanco):
        inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_serie_invalida.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/invalida.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
                "serie": serie_invalida,
            },
            cliente=banco_local,
        )


@pytest.mark.database
@pytest.mark.parametrize("mes_invalido", [0, -1, 13, 99, "AB"])
def test_deve_rejeitar_ultimo_mes_invalido_em_informacoes_arquivo(banco_local, mes_invalido):
    """Valida se o CHECK e o tipo INTEGER bloqueiam meses fora do intervalo 1..12."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    with pytest.raises(ErroOperacaoBanco):
        inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_mes_invalido.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/mes_invalido.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
                "ultimo_mes": mes_invalido,
            },
            cliente=banco_local,
        )


@pytest.mark.database
def test_deve_aceitar_status_parcial_em_historico_ingestoes(banco_local):
    """Valida que o status 'PARCIAL' é aceito pela constraint CHECK de historico_ingestoes."""
    id_criado = None
    try:
        inseridos = inserir_registros(
            tabela="historico_ingestoes",
            dados={"status": "PARCIAL", "qtd_arquivos_processados": 1, "qtd_arquivos_falhas": 1},
            cliente=banco_local,
        )
        assert len(inseridos) == 1
        id_criado = inseridos[0]["id"]
        assert inseridos[0]["status"] == "PARCIAL"
    finally:
        if id_criado is not None:
            banco_local.table("historico_ingestoes").delete().eq("id", id_criado).execute()


@pytest.mark.database
@pytest.mark.parametrize("status_invalido", ["ERRO", "CONCLUIDO", "sucesso", ""])
def test_deve_rejeitar_status_invalido_em_historico_ingestoes(banco_local, status_invalido):
    """Valida se a constraint CHECK bloqueia valores fora dos 4 status permitidos."""
    with pytest.raises(ErroOperacaoBanco):
        inserir_registros(
            tabela="historico_ingestoes",
            dados={"status": status_invalido},
            cliente=banco_local,
        )
# ============================================================================
# 9. TESTES DE CONTAGEM (COUNT)
# ============================================================================
@pytest.mark.database
def test_deve_contar_ocorrencias_vinculadas_a_um_arquivo(banco_local):
    """Valida a contagem exata de ocorrências associadas a um arquivo_id."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_arquivo = None
    try:
        arquivo = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_contagem_cvli.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/teste_contagem.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
            },
            cliente=banco_local,
        )
        id_arquivo = arquivo[0]["id"]

        inserir_registros(
            tabela="ocorrencias_crimes",
            dados=[
                {
                    "arquivo_id": id_arquivo,
                    "tipo_crime": "cvli",
                    "municipio": "Fortaleza",
                    "data_fato": "2026-03-10",
                },
                {
                    "arquivo_id": id_arquivo,
                    "tipo_crime": "cvli",
                    "municipio": "Sobral",
                    "data_fato": "2026-03-11",
                },
            ],
            cliente=banco_local,
        )

        total = contar_ocorrencias_por_arquivo(arquivo_id=id_arquivo, cliente=banco_local)
        assert isinstance(total, int)
        assert total == 2
    finally:
        if id_arquivo is not None:
            excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)


@pytest.mark.database
def test_deve_retornar_zero_quando_arquivo_nao_possuir_ocorrencias(banco_local):
    """Valida que um arquivo_id sem registros retorna 0 (e não erro de None)."""
    total = contar_ocorrencias_por_arquivo(arquivo_id=999999999, cliente=banco_local)
    assert total == 0


@pytest.mark.parametrize("arquivo_id_invalido", [0, -1, -50, "10", None, True, False, 1.5])
def test_deve_lancar_value_error_quando_arquivo_id_para_contagem_for_invalido(
    arquivo_id_invalido,
):
    """Valida que arquivo_id inválido é rejeitado antes de conectar ao banco."""
    with pytest.raises(ValueError):
        contar_ocorrencias_por_arquivo(arquivo_id=arquivo_id_invalido)


def test_deve_lancar_erro_operacao_banco_quando_contagem_falhar(caplog):
    """Valida tratamento de erro e log ERROR quando a consulta de contagem falha."""
    cliente_falso = MagicMock()
    cliente_falso.table.side_effect = RuntimeError("Falha simulada de conexão")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            contar_ocorrencias_por_arquivo(arquivo_id=1, cliente=cliente_falso)

    assert contexto.value.operacao == "contagem"
    assert contexto.value.tabela == "ocorrencias_crimes"
    assert any(record.levelname == "ERROR" for record in caplog.records)


def test_deve_lancar_erro_operacao_banco_quando_count_retornar_none(caplog):
    """Valida que resposta.count == None gera ErroOperacaoBanco em vez de mascarar como 0."""
    resposta_falsa = MagicMock()
    resposta_falsa.count = None

    cliente_falso = MagicMock()
    (
        cliente_falso.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value
    ) = resposta_falsa

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            contar_ocorrencias_por_arquivo(arquivo_id=1, cliente=cliente_falso)

    assert contexto.value.operacao == "contagem"
    assert contexto.value.tabela == "ocorrencias_crimes"
    assert "não retornou a contagem" in str(contexto.value)
    assert any(record.levelname == "ERROR" for record in caplog.records)


# ============================================================================
# 10. TESTES DA VIEW (vw_ocorrencias_publicadas)
# ============================================================================
@pytest.mark.database
def test_view_deve_retornar_ocorrencias_com_periodo_dados_preenchido(banco_local):
    """Valida que a view exibe ocorrências de arquivos publicados e apenas colunas de ocorrencias_crimes."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_arquivo = None
    try:
        arquivo = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_view_publicado.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/view_publicado.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
                "periodo_dados": "2026-01 a 2026-10",
            },
            cliente=banco_local,
        )
        id_arquivo = arquivo[0]["id"]

        inserir_registros(
            tabela="ocorrencias_crimes",
            dados={
                "arquivo_id": id_arquivo,
                "tipo_crime": "cvli",
                "municipio": "Fortaleza",
                "data_fato": "2026-04-15",
            },
            cliente=banco_local,
        )

        registros = consultar_registros(
            tabela="vw_ocorrencias_publicadas",
            filtros={"arquivo_id": id_arquivo},
            cliente=banco_local,
        )

        assert len(registros) == 1
        assert registros[0]["municipio"] == "Fortaleza"
        assert "hash_sha256" not in registros[0]
        assert "periodo_dados" not in registros[0]
    finally:
        if id_arquivo is not None:
            excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)


@pytest.mark.database
@pytest.mark.parametrize("periodo_nao_preenchido", [None, "", "   "])
def test_view_deve_ocultar_ocorrencias_sem_periodo_e_exibir_apos_publicacao(
    banco_local, periodo_nao_preenchido
):
    """Valida o ciclo completo: oculta quando periodo_dados é NULL/vazio e exibe após UPDATE."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_arquivo = None
    try:
        arquivo = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_view_em_carga.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/view_em_carga.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
                "periodo_dados": periodo_nao_preenchido,
            },
            cliente=banco_local,
        )
        id_arquivo = arquivo[0]["id"]

        inserir_registros(
            tabela="ocorrencias_crimes",
            dados={
                "arquivo_id": id_arquivo,
                "tipo_crime": "cvli",
                "municipio": "Caucaia",
                "data_fato": "2026-04-20",
            },
            cliente=banco_local,
        )

        # 1. Existe na tabela bruta, mas NÃO aparece na view enquanto periodo_dados não for preenchido
        assert len(consultar_registros("ocorrencias_crimes", filtros={"arquivo_id": id_arquivo}, cliente=banco_local)) == 1
        assert consultar_registros("vw_ocorrencias_publicadas", filtros={"arquivo_id": id_arquivo}, cliente=banco_local) == []

        # 2. Simula o passo final do pipeline: preenche periodo_dados -> passa a aparecer na view!
        atualizar_registro(
            tabela="informacoes_arquivo",
            id_registro=id_arquivo,
            novos_dados={"periodo_dados": "2026"},
            cliente=banco_local,
        )
        publicados = consultar_registros(
            tabela="vw_ocorrencias_publicadas",
            filtros={"arquivo_id": id_arquivo},
            cliente=banco_local,
        )
        assert len(publicados) == 1
        assert publicados[0]["municipio"] == "Caucaia"
    finally:
        if id_arquivo is not None:
            excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)


# ============================================================================
# 11. TESTES DE CONSULTA PAGINADA (KEYSET / CURSOR PAGINATION)
# ============================================================================
def _criar_cliente_paginado_fake(dados_retorno):
    """Cria um mock fluente do query builder do Supabase registrando todas as chamadas."""
    chamadas = []

    class QueryBuilderFake:
        def select(self, colunas):
            chamadas.append(("select", colunas))
            return self

        def eq(self, coluna, valor):
            chamadas.append(("eq", coluna, valor))
            return self

        def in_(self, coluna, valores):
            chamadas.append(("in_", coluna, list(valores)))
            return self

        def gte(self, coluna, valor):
            chamadas.append(("gte", coluna, valor))
            return self

        def lte(self, coluna, valor):
            chamadas.append(("lte", coluna, valor))
            return self

        def lt(self, coluna, valor):
            chamadas.append(("lt", coluna, valor))
            return self

        def order(self, coluna, desc=False):
            chamadas.append(("order", coluna, desc))
            return self

        def limit(self, tamanho):
            chamadas.append(("limit", tamanho))
            return self

        def execute(self):
            chamadas.append(("execute",))
            resposta = MagicMock()
            resposta.data = dados_retorno
            return resposta

    cliente = MagicMock()
    cliente.table.side_effect = lambda nome: chamadas.append(("table", nome)) or QueryBuilderFake()
    return cliente, chamadas


def test_deve_paginar_primeira_pagina_desc_e_retornar_next_cursor():
    """Sem cursor e com limite+1 registros retornados, devolve has_next=True e next_cursor do último item."""
    dados_banco = [{"id": 103}, {"id": 102}, {"id": 101}]
    cliente, chamadas = _criar_cliente_paginado_fake(dados_banco)

    resultado = consultar_registros_paginados(
        tabela="ocorrencias_crimes",
        limite=2,
        cliente=cliente,
    )

    assert resultado == {
        "items": [{"id": 103}, {"id": 102}],
        "pagination": {
            "limit": 2,
            "next_cursor": 102,
            "has_next": True,
        },
    }
    assert ("table", "ocorrencias_crimes") in chamadas
    assert ("order", "id", True) in chamadas
    assert ("limit", 3) in chamadas
    assert not any(c[0] == "lt" for c in chamadas)


def test_deve_paginar_com_cursor_e_encerrar_quando_nao_houver_proxima_pagina():
    """Com cursor, aplica lt(coluna_cursor, cursor) e devolve has_next=False quando retorna < limite+1."""
    dados_banco = [{"id": 101}]
    cliente, chamadas = _criar_cliente_paginado_fake(dados_banco)

    resultado = consultar_registros_paginados(
        tabela="ocorrencias_crimes",
        limite=2,
        cursor=102,
        cliente=cliente,
    )

    assert resultado == {
        "items": [{"id": 101}],
        "pagination": {
            "limit": 2,
            "next_cursor": None,
            "has_next": False,
        },
    }
    assert ("lt", "id", 102) in chamadas
    assert ("order", "id", True) in chamadas
    assert ("limit", 3) in chamadas


def test_deve_retornar_has_next_false_quando_quantidade_for_exatamente_igual_ao_limite():
    """Fronteira exata (len(dados) == limite): não há próxima página."""
    dados_banco = [{"id": 20}, {"id": 19}]
    cliente, _ = _criar_cliente_paginado_fake(dados_banco)

    resultado = consultar_registros_paginados(
        tabela="ocorrencias_crimes",
        limite=2,
        cliente=cliente,
    )

    assert resultado["items"] == dados_banco
    assert resultado["pagination"] == {
        "limit": 2,
        "next_cursor": None,
        "has_next": False,
    }


def test_deve_retornar_lista_vazia_e_paginacao_encerrada_quando_nao_houver_registros():
    """Quando o banco retorna [], items fica vazio e pagination indica fim."""
    cliente, _ = _criar_cliente_paginado_fake([])

    resultado = consultar_registros_paginados(
        tabela="ocorrencias_crimes",
        limite=10,
        cliente=cliente,
    )

    assert resultado == {
        "items": [],
        "pagination": {
            "limit": 10,
            "next_cursor": None,
            "has_next": False,
        },
    }


def test_deve_usar_limite_padrao_quando_limite_for_omitido():
    """Sem informar limite, usa LIMITE_PADRAO_PAGINACAO (100) e solicita 101 linhas."""
    cliente, chamadas = _criar_cliente_paginado_fake([])

    resultado = consultar_registros_paginados(
        tabela="ocorrencias_crimes",
        cliente=cliente,
    )

    assert resultado["pagination"]["limit"] == LIMITE_PADRAO_PAGINACAO
    assert ("limit", LIMITE_PADRAO_PAGINACAO + 1) in chamadas


def test_deve_aplicar_filtros_combinados_in_datas_colunas_e_coluna_cursor_customizada():
    """Valida eq, in_, gte/lte, lt, colunas específicas e coluna_cursor customizada."""
    dados_banco = [
        {"codigo": 50, "municipio": "Fortaleza"},
        {"codigo": 40, "municipio": "Sobral"},
        {"codigo": 30, "municipio": "Caucaia"},
    ]
    cliente, chamadas = _criar_cliente_paginado_fake(dados_banco)

    resultado = consultar_registros_paginados(
        tabela="vw_ocorrencias_publicadas",
        filtros={"municipio": "Fortaleza"},
        filtros_in={"tipo_crime": ("FURTO", "CVP")},
        limite=2,
        cursor=60,
        coluna_cursor="codigo",
        coluna_data="data_fato",
        data_inicio="2026-01-01",
        data_fim="2026-12-31",
        colunas="codigo, municipio",
        cliente=cliente,
    )

    assert resultado["items"] == dados_banco[:2]
    assert resultado["pagination"] == {
        "limit": 2,
        "next_cursor": 40,
        "has_next": True,
    }
    assert ("select", "codigo, municipio") in chamadas
    assert ("eq", "municipio", "Fortaleza") in chamadas
    assert ("in_", "tipo_crime", ["FURTO", "CVP"]) in chamadas
    assert ("gte", "data_fato", "2026-01-01") in chamadas
    assert ("lte", "data_fato", "2026-12-31") in chamadas
    assert ("lt", "codigo", 60) in chamadas
    assert ("order", "codigo", True) in chamadas
    assert ("limit", 3) in chamadas


@pytest.mark.parametrize("tabela_invalida", ["", "   ", None])
def test_deve_rejeitar_tabela_invalida_na_paginacao(tabela_invalida):
    with pytest.raises(ValueError):
        consultar_registros_paginados(tabela=tabela_invalida)


@pytest.mark.parametrize("coluna_cursor_invalida", ["", "   ", None])
def test_deve_rejeitar_coluna_cursor_invalida_na_paginacao(coluna_cursor_invalida):
    with pytest.raises(ValueError):
        consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            coluna_cursor=coluna_cursor_invalida,
        )


@pytest.mark.parametrize(
    "limite_invalido",
    [0, -1, LIMITE_MAXIMO_PAGINACAO + 1, True, False, 1.5, "10", None],
)
def test_deve_rejeitar_limite_invalido_na_paginacao(limite_invalido):
    with pytest.raises(ValueError):
        consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            limite=limite_invalido,
        )


@pytest.mark.parametrize("cursor_invalido", [0, -1, True, False, 1.5, "10"])
def test_deve_rejeitar_cursor_invalido_na_paginacao(cursor_invalido):
    with pytest.raises(ValueError):
        consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            cursor=cursor_invalido,
        )


@pytest.mark.parametrize(
    "filtros_in_invalido",
    [
        {"tipo_crime": []},
        {"tipo_crime": ()},
        {"tipo_crime": "FURTO"},
        {"tipo_crime": None},
        {"tipo_crime": 123},
    ],
)
def test_deve_rejeitar_filtros_in_invalido_na_paginacao(filtros_in_invalido):
    with pytest.raises(ValueError):
        consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            filtros_in=filtros_in_invalido,
        )


@pytest.mark.parametrize("colunas_invalida", ["", "   ", "municipio,data_fato"])
def test_deve_rejeitar_colunas_invalidas_ou_sem_cursor_na_paginacao(colunas_invalida):
    with pytest.raises(ValueError):
        consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            colunas=colunas_invalida,
        )


def test_deve_lancar_erro_operacao_banco_quando_consulta_paginada_falhar(caplog):
    """Valida exceção e log ERROR quando a execução no Supabase falha."""
    cliente_falso = MagicMock()
    cliente_falso.table.side_effect = RuntimeError("timeout na consulta")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            consultar_registros_paginados(
                tabela="ocorrencias_crimes",
                cliente=cliente_falso,
            )

    assert contexto.value.operacao == "consulta_paginada"
    assert contexto.value.tabela == "ocorrencias_crimes"
    assert "timeout na consulta" in str(contexto.value)
    assert any(record.levelname == "ERROR" for record in caplog.records)


def test_deve_lancar_erro_operacao_banco_quando_cursor_nao_vier_no_retorno(caplog):
    """Se has_next=True mas o último item não contém a coluna_cursor, lança ErroOperacaoBanco."""
    dados_sem_id = [{"municipio": "Fortaleza"}, {"municipio": "Sobral"}, {"municipio": "Caucaia"}]
    cliente, _ = _criar_cliente_paginado_fake(dados_sem_id)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(ErroOperacaoBanco) as contexto:
            consultar_registros_paginados(
                tabela="ocorrencias_crimes",
                limite=2,
                cliente=cliente,
            )

    assert contexto.value.operacao == "consulta_paginada"
    assert contexto.value.tabela == "ocorrencias_crimes"
    assert "coluna de cursor" in str(contexto.value)
    assert any(record.levelname == "ERROR" for record in caplog.records)


@pytest.mark.database
def test_deve_percorrer_todas_as_paginas_em_ordem_desc_sem_duplicatas(banco_local):
    """Integração: insere 5 ocorrências e percorre todas as páginas com limite=2 em ordem DESC."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_arquivo = None
    try:
        arquivo = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_paginacao_desc.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/teste_paginacao.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "cvli",
            },
            cliente=banco_local,
        )
        id_arquivo = arquivo[0]["id"]

        inseridos = inserir_registros(
            tabela="ocorrencias_crimes",
            dados=[
                {
                    "arquivo_id": id_arquivo,
                    "tipo_crime": "cvli",
                    "municipio": f"Municipio {i}",
                    "data_fato": f"2026-05-0{i}",
                }
                for i in range(1, 6)
            ],
            cliente=banco_local,
        )
        ids_esperados = sorted((r["id"] for r in inseridos), reverse=True)

        p1 = consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            filtros={"arquivo_id": id_arquivo},
            limite=2,
            cliente=banco_local,
        )
        assert len(p1["items"]) == 2
        assert p1["pagination"]["limit"] == 2
        assert p1["pagination"]["has_next"] is True
        assert p1["pagination"]["next_cursor"] == p1["items"][-1]["id"]

        p2 = consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            filtros={"arquivo_id": id_arquivo},
            limite=2,
            cursor=p1["pagination"]["next_cursor"],
            cliente=banco_local,
        )
        assert len(p2["items"]) == 2
        assert p2["pagination"]["has_next"] is True
        assert p2["pagination"]["next_cursor"] == p2["items"][-1]["id"]

        p3 = consultar_registros_paginados(
            tabela="ocorrencias_crimes",
            filtros={"arquivo_id": id_arquivo},
            limite=2,
            cursor=p2["pagination"]["next_cursor"],
            cliente=banco_local,
        )
        assert len(p3["items"]) == 1
        assert p3["pagination"]["has_next"] is False
        assert p3["pagination"]["next_cursor"] is None

        ids_recebidos = [item["id"] for pagina in (p1, p2, p3) for item in pagina["items"]]
        assert ids_recebidos == ids_esperados
    finally:
        if id_arquivo is not None:
            excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)


@pytest.mark.database
def test_deve_paginar_view_publicada_com_filtros_in(banco_local):
    """Integração: pagina vw_ocorrencias_publicadas combinando filtros de igualdade e filtros_in."""
    hash_unico = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
    id_arquivo = None
    try:
        arquivo = inserir_registros(
            tabela="informacoes_arquivo",
            dados={
                "nome_arquivo": "teste_paginacao_view_in.xlsx",
                "url_download": "https://exemplo.sspds.ce.gov.br/teste_paginacao_view.xlsx",
                "hash_sha256": hash_unico,
                "tipo_crime": "FURTO",
                "periodo_dados": "2026",
            },
            cliente=banco_local,
        )
        id_arquivo = arquivo[0]["id"]

        inserir_registros(
            tabela="ocorrencias_crimes",
            dados=[
                {"arquivo_id": id_arquivo, "tipo_crime": "FURTO", "municipio": "Fortaleza", "data_fato": "2026-06-01"},
                {"arquivo_id": id_arquivo, "tipo_crime": "CVP", "municipio": "Caucaia", "data_fato": "2026-06-02"},
                {"arquivo_id": id_arquivo, "tipo_crime": "INCENDIO", "municipio": "Sobral", "data_fato": "2026-06-03"},
            ],
            cliente=banco_local,
        )

        pagina = consultar_registros_paginados(
            tabela="vw_ocorrencias_publicadas",
            filtros={"arquivo_id": id_arquivo},
            filtros_in={"tipo_crime": ["FURTO", "CVP"]},
            limite=10,
            cliente=banco_local,
        )

        assert pagina["pagination"] == {
            "limit": 10,
            "next_cursor": None,
            "has_next": False,
        }
        assert len(pagina["items"]) == 2
        assert pagina["items"][0]["id"] > pagina["items"][1]["id"]
        assert {item["tipo_crime"] for item in pagina["items"]} == {"FURTO", "CVP"}
    finally:
        if id_arquivo is not None:
            excluir_arquivo(id_arquivo=id_arquivo, cliente=banco_local)
