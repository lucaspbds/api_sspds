from datetime import date, time
import pandas as pd
from logging_system.logging_config import configure_logging
import logging
from .exception import ColunasAusentesNaPlanilha, DiaInformadoDivergeDoDiaDaSemana, tipoOcorrenciaNaoEncontrado

DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


def normalizar_texto(valor):
    """Remove espaços excedentes sem alterar o conteúdo original."""
    if pd.isna(valor):
        return None

    texto = str(valor).strip().title()
    return texto or None

def normalizar_data(valor) -> date:
    """Converte a data da planilha para datetime.date."""
    return pd.to_datetime(valor, errors="raise").date()

def normalizar_hora(valor) -> time | None:
    """Converte a hora para datetime.time."""
    if pd.isna(valor):
        return None

    if isinstance(valor, str) and valor.lower() == "não informada":
            return None
    
    if isinstance(valor, time):
        return valor

    return pd.to_datetime(
        str(valor), errors="raise"
    ).time()

def normalizar_idade(valor) -> int | None:
    """Converte idade para inteiro, rejeitando valores inválidos."""

    if pd.isna(valor):
        return None

    if isinstance(valor, str) and valor.lower() in ("não informada", "não informado"):
        return None
    
    idade = float(valor)

    if not idade.is_integer() or not 0 <= idade <= 130:
        # raise ValueError(f"Idade inválida: {valor}")
        logging.warning("Idade inválida: %s", valor)

    return int(idade)

def normalizar_quantidadeArmas(valor) -> int | None:
    """Converte quantidade de armas para inteiro, rejeitando valores inválidos"""
    if pd.isna(valor):
            return None
    
    if isinstance(valor, str) and valor.lower() == "não informada":
        return None
        
    qtd_armas = float(valor)
    
    if not qtd_armas.is_integer():
        raise ValueError(f"Quantidade de armas inválido: {valor}")
    
    return int(qtd_armas)

def normalizar_quantidadeEntorpecente(valor) -> int | None:
    """Converte quantidade de entorpecente para float, rejeitando valores inválidos"""
    if pd.isna(valor):
            return None
    
    if isinstance(valor, str):
        if valor.lower() == "não informada":
            return None
        else:
            raise ValueError(f"Quantidade de entorpecente inválido: {valor}")
        
    return float(valor)

#NORMALIZADORES PARA CADA TIPO DE OCORRÊNCIA
def normalizar_cvli(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas da aba CVLI para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")

    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Natureza",
        "Data",
        "Hora",
        "Dia da Semana",
        "Meio Empregado",
        "Gênero",
        "Idade da Vítima",
        "Escolaridade da Vítima",
        "Raça da Vítima",
    }

    faltantes = colunas_obrigatorias - set(df.columns)

    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))

    registros = []

    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]

            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)

            municipio = normalizar_texto(linha["Município"])

            if municipio is None:
                raise ValueError("Município ausente")

            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "dia_semana": dia_semana,
                "natureza": normalizar_texto(linha["Natureza"]),
                "meio_empregado": normalizar_texto(linha["Meio Empregado"]),
                "vitima_genero": normalizar_texto(linha["Gênero"]),
                "vitima_idade": normalizar_idade(linha["Idade da Vítima"]),
                "vitima_escolaridade": normalizar_texto(linha["Escolaridade da Vítima"]),
                "vitima_raca": normalizar_texto(linha["Raça da Vítima"]),
                "vitima_orientacao_sexual": None,
                "quantidade_armas": None,
                "tipo_entorpecente": None,
                "peso_entorpecente_kg": None,
            }

            registros.append(registro)

        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 

    return registros

def normalizar_animais_CVP_Furto_Incendio_Salvamento(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas das abas animais, CVP, Furto, Incendio e Salvamento para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")
    
    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Data",
        "Hora",
        "Dia da Semana"
        }
    
    faltantes = colunas_obrigatorias - set(df.columns)
    
    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))
    
    registros = []
    
    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]
    
            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)
    
            municipio = normalizar_texto(linha["Município"])
    
            if municipio is None:
                raise ValueError("Município ausente")
    
            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "dia_semana": dia_semana,
                "natureza": None,
                "meio_empregado": None,
                "vitima_genero": None,
                "vitima_idade": None,
                "vitima_escolaridade": None,
                "vitima_raca": None,
                "vitima_orientacao_sexual": None,
                "quantidade_armas": None,
                "tipo_entorpecente": None,
                "peso_entorpecente_kg": None,
            }

            registros.append(registro)
        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 
        
    return registros

def normalizar_armaDeFogo(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas da aba armaDeFogo para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")
    
    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Data",
        "Hora",
        "Dia da Semana",
        "Quantidade"
    }
    
    faltantes = colunas_obrigatorias - set(df.columns)
    
    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))
    
    registros = []
    
    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]
    
            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)
    
            municipio = normalizar_texto(linha["Município"])
    
            if municipio is None:
                raise ValueError("Município ausente")
    
            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "dia_semana": dia_semana,
                "natureza": None,
                "meio_empregado": None,
                "vitima_genero": None,
                "vitima_idade": None,
                "vitima_escolaridade": None,
                "vitima_raca": None,
                "vitima_orientacao_sexual": None,
                "quantidade_armas": normalizar_quantidadeArmas(linha["Quantidade"]),
                "tipo_entorpecente": None,
                "peso_entorpecente_kg": None,
            }

            registros.append(registro)
        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 
        
    return registros    

def normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas da aba Crime ou Preconceito de Raça Ou Cor, Crimes Sexuais, Indígenas
    e Lei Maria Da Penha para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")

    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Data",
        "Hora",
        "Dia da Semana",
        "Gênero",
        "Idade da Vítima",
        "Escolaridade da Vítima",
        "Raça da Vítima",
    }

    faltantes = colunas_obrigatorias - set(df.columns)

    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))

    registros = []

    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]

            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)

            municipio = normalizar_texto(linha["Município"])

            if municipio is None:
                raise ValueError("Município ausente")

            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "dia_semana": dia_semana,
                "natureza": None,
                "meio_empregado": None,
                "vitima_genero": normalizar_texto(linha["Gênero"]),
                "vitima_idade": normalizar_idade(linha["Idade da Vítima"]),
                "vitima_escolaridade": normalizar_texto(linha["Escolaridade da Vítima"]),
                "vitima_raca": normalizar_texto(linha["Raça da Vítima"]),
                "vitima_orientacao_sexual": None,
                "quantidade_armas": None,
                "tipo_entorpecente": None,
                "peso_entorpecente_kg": None,
            }

            registros.append(registro)

        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 

    return registros

def normalizar_entorpecentes(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas da aba entorpecentes para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")
    
    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Data",
        "Hora",
        "Dia da Semana",
        "Quantidade (Kg)",
        "Tipo de Entorpecente"
    }
    
    faltantes = colunas_obrigatorias - set(df.columns)
    
    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))
    
    registros = []
    
    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]
    
            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)

            municipio = normalizar_texto(linha["Município"])
    
            if municipio is None:
                raise ValueError("Município ausente")
    
            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "dia_semana": dia_semana,
                "natureza": None,
                "meio_empregado": None,
                "vitima_genero": None,
                "vitima_idade": None,
                "vitima_escolaridade": None,
                "vitima_raca": None,
                "vitima_orientacao_sexual": None,
                "quantidade_armas": None,
                "tipo_entorpecente": normalizar_texto(linha["Tipo de Entorpecente"]),
                "peso_entorpecente_kg": normalizar_quantidadeEntorpecente(linha["Quantidade (Kg)"]),
            }

            registros.append(registro)
        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha, DiaInformadoDivergeDoDiaDaSemana) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 
        
    return registros    

def normalizar_homofobiaETransfobia(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    """Converte as linhas da aba Homofobia e Transfobia para o schema do banco."""
    if arquivo_id <= 0:
        raise ValueError("arquivo_id deve ser positivo")

    colunas_obrigatorias = {
        "Município",
        "AIS",
        "Data",
        "Hora",
        "Dia da Semana",
        "Idade da Vítima",
        "Escolaridade da Vítima",
        "Raça da Vítima",
        "Natureza",
        "Identidade de Gênero",
        "Orientação Sexual",
        "Local"
    }

    faltantes = colunas_obrigatorias - set(df.columns)

    if faltantes:
        raise ColunasAusentesNaPlanilha(sorted(faltantes))

    registros = []

    for numero_linha, linha in enumerate(df.to_dict(orient="records")):
        try:
            data_fato = normalizar_data(linha["Data"])
            dia_informado = normalizar_texto(linha["Dia da Semana"])
            dia_semana = DIAS_SEMANA[data_fato.weekday()]

            # Não corrigimos silenciosamente divergências na fonte.
            if (dia_informado is not None and dia_informado.lower().replace("-feira", "") != dia_semana.lower().replace("-feira", "")):
                # raise DiaInformadoDivergeDoDiaDaSemana(dia_informado, dia_semana)
                logging.warning("Dia informado '%s' diverge da data (%s)", dia_informado, dia_semana)

            municipio = normalizar_texto(linha["Município"])

            if municipio is None:
                raise ValueError("Município ausente")

            registro = {
                "arquivo_id": arquivo_id,
                "tipo_crime": tipo_ocorrencia,
                "municipio": municipio,
                "ais": normalizar_texto(linha["AIS"]),
                "data_fato": data_fato,
                "hora_fato": normalizar_hora(linha["Hora"]),
                "local_fato": normalizar_texto(linha["Local"]),
                "dia_semana": dia_semana,
                "natureza": normalizar_texto(linha["Natureza"]),
                "meio_empregado": None,
                "vitima_genero": normalizar_texto(linha["Identidade de Gênero"]),
                "vitima_idade": normalizar_idade(linha["Idade da Vítima"]),
                "vitima_escolaridade": normalizar_texto(linha["Escolaridade da Vítima"]),
                "vitima_raca": normalizar_texto(linha["Raça da Vítima"]),
                "vitima_orientacao_sexual": normalizar_texto(linha["Orientação Sexual"]),
                "quantidade_armas": None,
                "tipo_entorpecente": None,
                "peso_entorpecente_kg": None,
            }

            registros.append(registro)

        except (ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha, DiaInformadoDivergeDoDiaDaSemana) as erro:
            logging.exception("Erro ao normalizar a linha %s: %s", numero_linha, erro)
            raise 

    return registros

def normalizer(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia:str) -> list[dict]:
    configure_logging()
    logging.getLogger(__name__)

    logging.info("Iniciando a normalização dos dados: %s", tipo_ocorrencia)

    #Lista dos tipos de ocorrências que utilizam o mesmo processo de normalização
    list_animais_CVP_Furto_Incendio_Salvamento = [
        "CRIME DE MAUS-TRATOS A ANIMAIS",
        "CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP",
        "FURTO",
        "INCÊNDIO",
        "BUSCA E SALVAMENTO"
    ]

    list_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha = [
        "CRIME OU PRECONCEITO DE RAÇA OU DE COR",
        "CRIMES SEXUAIS",
        "INDÍGENAS VÍTIMAS DE CRIMES",
        "LEI 11.340/06 (LEI MARIA DA PENHA)"
    ]
    try:
        if tipo_ocorrencia == "CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI":
            return normalizar_cvli(df, arquivo_id, tipo_ocorrencia)
        
        elif tipo_ocorrencia == "APREENSÃO DE ARMAS DE FOGO":
            return normalizar_armaDeFogo(df, arquivo_id, tipo_ocorrencia)

        elif tipo_ocorrencia == "APREENSÃO DE ENTORPECENTES":
            return normalizar_entorpecentes(df, arquivo_id, tipo_ocorrencia)

        elif tipo_ocorrencia == "HOMOFOBIA E TRANSFOBIA":
            return normalizar_homofobiaETransfobia(df, arquivo_id, tipo_ocorrencia)

        elif tipo_ocorrencia in list_animais_CVP_Furto_Incendio_Salvamento:
            return normalizar_animais_CVP_Furto_Incendio_Salvamento(df, arquivo_id, tipo_ocorrencia)
        
        elif tipo_ocorrencia in list_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha:
            return normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha(df, arquivo_id, tipo_ocorrencia)
        
        else:
            raise tipoOcorrenciaNaoEncontrado(tipo_ocorrencia)
    except(ValueError, TypeError, OverflowError, ColunasAusentesNaPlanilha, DiaInformadoDivergeDoDiaDaSemana, tipoOcorrenciaNaoEncontrado) as erro:
        logging.exception("Falha na normalização: %s", erro)
