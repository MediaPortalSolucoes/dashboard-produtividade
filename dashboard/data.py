import streamlit as st
import pandas as pd
import numpy as np
import gspread
import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from utils import converter_data_robusta, tornar_colunas_unicas

load_dotenv()

ABA_DADOS = "Total BaseCamp para Notas"
ABA_EQUIPES = "Equipes"
ABA_PONTUACAO = "Notas"
ABA_LIDERANCA = "Liderança"
ABA_BACKLOG = "Backlog"
ABA_SOURCE = "Total BaseCamp"

COLS_NUMERICAS = ['Pablo', 'Leonardo', 'Itiel', 'Ítalo']

def autenticar_planilha():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"]
    try:
        creds_json = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    except FileNotFoundError:
        try:
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=scopes)
        except Exception:
            return None
    except KeyError:
        try:
            creds = Credentials.from_service_account_file("google_credentials.json", scopes=scopes)
        except Exception:
            return None
    
    client = gspread.authorize(creds)

    return client.open_by_url(f"https://docs.google.com/spreadsheets/d/{os.getenv('SPREADSHEET_ID')}")

def extrair_notas(spreadsheet):
    df_tabela1 = pd.DataFrame()
    df_tabela2 = pd.DataFrame()
    try:
        all_values = spreadsheet.worksheet(ABA_PONTUACAO).get_all_values()
        linha_branca = next((i for i, r in enumerate(all_values) if not r or all(c == '' for c in r)), -1)
        
        if linha_branca == -1:
            sup = all_values
            inf = [] 
        else:
            sup = all_values[:linha_branca]
            inf_inicio = next((i for i, r in enumerate(all_values[linha_branca + 1:], start=linha_branca + 1) if r and any(c != '' for c in r)), -1)
            inf = all_values[inf_inicio:] if inf_inicio != -1 else []
            
        if len(sup) > 1:
            df_tabela1 = pd.DataFrame(sup[1:], columns=tornar_colunas_unicas(sup[0]))
        if len(inf) > 1:
            df_tabela2 = pd.DataFrame(inf[1:], columns=tornar_colunas_unicas(inf[0]))
    except Exception:
        pass
    return df_tabela1, df_tabela2

def processar_equipes(df):
    if df.empty:
        return df
    df.columns = df.columns.astype(str).str.strip()
    if 'Status' in df.columns:
        df = df.rename(columns={'Status': 'Status_Funcionario'})
    if 'Nome' in df.columns:
        df = df.drop_duplicates(subset=['Nome'])
    if 'Data de Saída' in df.columns:
        df['Data de Saída'] = converter_data_robusta(df['Data de Saída'])
    if 'Data de Entrada' in df.columns:
        df['Data de Entrada'] = converter_data_robusta(df['Data de Entrada'])
    return df

def processar_dados_principais(df):
    if df.empty:
        return df
    df.columns = df.columns.astype(str).str.strip()
    df_grafico = df.copy()
    
    if 'ID' in df_grafico.columns:
        df_grafico['ID'] = df_grafico['ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_grafico = df_grafico.drop_duplicates(subset=['ID'], keep='last')

    if 'Sub-Lista / Grupo' in df_grafico.columns:
        df_grafico = df_grafico[df_grafico['Sub-Lista / Grupo'].astype(str).str.upper().str.contains('ATIVIDADES')].copy()

    for col in COLS_NUMERICAS:
        if col not in df_grafico.columns:
            df_grafico[col] = 0
        else:
            df_grafico[col] = pd.to_numeric(df_grafico[col], errors='coerce').fillna(0)

    if 'Data Inicial' in df_grafico.columns:
        df_grafico['Data Inicial'] = converter_data_robusta(df_grafico['Data Inicial'])
        
    if 'Data Final' in df_grafico.columns:
        df_grafico['Data Final'] = converter_data_robusta(df_grafico['Data Final'])
        df_grafico['Status_Tarefa'] = np.where(df_grafico['Data Final'].isnull(), 'Aberto', 'Executado')
        df_grafico['Data Final (aberta)'] = df_grafico['Data Final'].fillna(pd.Timestamp.now().normalize())
    else:
        df_grafico['Status_Tarefa'] = 'Desconhecido'
        df_grafico['Data Final (aberta)'] = pd.Timestamp.now().normalize()
    
    if 'Encarregado' in df_grafico.columns:
        df_grafico['Encarregado'] = df_grafico['Encarregado'].astype(str).str.strip().replace('', 'Em Branco')
    else:
        df_grafico['Encarregado'] = 'Em Branco'
        
    if 'Nome Task' in df_grafico.columns:
        df_grafico['Nome Task'] = df_grafico['Nome Task'].astype(str).str.strip().replace('', 'Vazio')
    else:
        df_grafico['Nome Task'] = 'Sem Nome'
        
    return df_grafico

def gerar_calendario(df_grafico, df_source):
    data_inicio_analise = pd.Timestamp.now().normalize()
    if not df_grafico.empty and 'Data Inicial' in df_grafico.columns and pd.notna(df_grafico['Data Inicial'].min()):
        data_inicio_analise = df_grafico['Data Inicial'].min()
        
    data_fim_analise = pd.Timestamp.now().normalize() + pd.Timedelta(days=365)
    
    data_inicio_calendario = data_inicio_analise
    if not df_source.empty and 'Data Inicial' in df_source.columns and pd.notna(df_source['Data Inicial'].min()):
        if df_source['Data Inicial'].min() < data_inicio_analise:
            data_inicio_calendario = df_source['Data Inicial'].min()

    tabela_calendario = pd.DataFrame({"Date": pd.date_range(start=data_inicio_calendario, end=data_fim_analise, freq='D')})
    tabela_calendario['Ano'] = tabela_calendario['Date'].dt.year
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    tabela_calendario['Nome Mês'] = tabela_calendario['Date'].dt.month.map(meses_pt)
    tabela_calendario['Mes_Ano_Abrev'] = tabela_calendario['Nome Mês'] + '/' + tabela_calendario['Date'].dt.strftime('%y')
    tabela_calendario['Ano-Mês'] = tabela_calendario['Date'].dt.strftime('%Y-%m')
    tabela_calendario['Dia'] = tabela_calendario['Date'].dt.day
    tabela_calendario['Dia da Semana_ISO'] = tabela_calendario['Date'].dt.dayofweek
    tabela_calendario['Nome Dia Semana'] = tabela_calendario['Dia da Semana_ISO'].map({0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'})
    tabela_calendario['Data_Inicio_Semana'] = tabela_calendario['Date'] - pd.to_timedelta(tabela_calendario['Dia da Semana_ISO'], unit='d')
    tabela_calendario['Data_Sexta_Feira'] = tabela_calendario['Data_Inicio_Semana'] + pd.to_timedelta(4, unit='d')
    tabela_calendario['Nome_da_Semana'] = tabela_calendario['Data_Sexta_Feira'].dt.strftime('%d/%m/%Y')
    tabela_calendario['Semana_Ano'] = tabela_calendario['Data_Sexta_Feira'].dt.strftime('%Y-%U') 
    tabela_calendario['Semana do Mês'] = (tabela_calendario['Date'].dt.dayofweek + (tabela_calendario['Date'].dt.day - 1)).floordiv(7) + 1
    tabela_calendario['Dia da Semana'] = tabela_calendario['Dia da Semana_ISO'] + 1
    return tabela_calendario

def processar_base_secundaria(df, df_equipe, tabela_calendario=None):
    if df.empty:
        return df
        
    df_proc = df.copy()
    df_proc.columns = df_proc.columns.astype(str).str.strip()
    
    if 'Data Inicial' in df_proc.columns:
        df_proc['Data Inicial'] = converter_data_robusta(df_proc.get('Data Inicial', pd.Series()))
    if 'Data Final' in df_proc.columns:
        df_proc['Data Final'] = converter_data_robusta(df_proc.get('Data Final', pd.Series()))
        df_proc['Status_Tarefa'] = np.where(df_proc['Data Final'].isnull(), 'Aberto', 'Executado')
        df_proc['Status_Backlog'] = np.where(df_proc['Data Final'].isnull(), 'Aberto', 'Fechado')
        df_proc['Data Final (aberta)'] = df_proc['Data Final'].fillna(pd.Timestamp.now().normalize())
        
    if 'Encarregado' in df_proc.columns:
        df_proc['Encarregado'] = df_proc['Encarregado'].astype(str).str.strip().replace('', 'Em Branco')
    if 'Nome Task' in df_proc.columns:
        df_proc['Nome Task'] = df_proc['Nome Task'].astype(str).str.strip().replace('', 'Vazio')
        
    if tabela_calendario is not None and 'Data Final (aberta)' in df_proc.columns:
        df_proc = pd.merge(df_proc, tabela_calendario, how='left', left_on='Data Final (aberta)', right_on='Date').drop(columns=['Date'], errors='ignore')
        
    if not df_equipe.empty and 'Encarregado' in df_proc.columns:
        df_proc = pd.merge(df_proc, df_equipe, how='left', left_on='Encarregado', right_on='Nome')
        if 'Status_Funcionario' in df_proc.columns:
            df_proc['Status_Funcionario'] = df_proc['Status_Funcionario'].fillna('Outros')
    else:
        df_proc['Status_Funcionario'] = 'Outros'
        
    return df_proc

def finalizar_datas(df):
    if not df.empty:
        if 'Data Inicial' in df.columns:
            df['Data Inicial'] = df['Data Inicial'].dt.date
        if 'Data Final' in df.columns:
            df['Data Final'] = df['Data Final'].dt.date
    return df

@st.cache_data(ttl=600)
def carregar_dados_completos():
    spreadsheet = autenticar_planilha()
    if not spreadsheet:
        return [pd.DataFrame() for _ in range(7)]
        
    try: df_dados = pd.DataFrame(spreadsheet.worksheet(ABA_DADOS).get_all_records())
    except Exception: df_dados = pd.DataFrame()
    
    try: df_equipe_bruta = pd.DataFrame(spreadsheet.worksheet(ABA_EQUIPES).get_all_records())
    except Exception: df_equipe_bruta = pd.DataFrame()
    
    try: df_lideranca = pd.DataFrame(spreadsheet.worksheet(ABA_LIDERANCA).get_all_records())
    except Exception: df_lideranca = pd.DataFrame()
    
    try: df_backlog_bruto = pd.DataFrame(spreadsheet.worksheet(ABA_BACKLOG).get_all_records())
    except Exception: df_backlog_bruto = pd.DataFrame()
    
    try: df_source_bruto = pd.DataFrame(spreadsheet.worksheet(ABA_SOURCE).get_all_records())
    except Exception: df_source_bruto = pd.DataFrame()

    df_notas_tabela1, df_notas_tabela2 = extrair_notas(spreadsheet)
    
    if not df_lideranca.empty:
        df_lideranca.columns = df_lideranca.columns.astype(str).str.strip()

    df_equipe = processar_equipes(df_equipe_bruta)
    df_grafico = processar_dados_principais(df_dados)
    
    df_source_datas = df_source_bruto.copy()
    if not df_source_datas.empty:
        df_source_datas.columns = df_source_datas.columns.astype(str).str.strip()
        if 'Data Inicial' in df_source_datas.columns:
            df_source_datas['Data Inicial'] = converter_data_robusta(df_source_datas['Data Inicial'])

    tabela_calendario = gerar_calendario(df_grafico, df_source_datas)
    
    df_analise_temp = pd.merge(df_grafico, tabela_calendario, how='left', left_on='Data Final (aberta)', right_on='Date').drop(columns=['Date'], errors='ignore')
    
    if not df_equipe.empty:
        df_analise = pd.merge(df_analise_temp, df_equipe, how='left', left_on='Encarregado', right_on='Nome')
        if 'Status_Funcionario' in df_analise.columns:
            df_analise['Status_Funcionario'] = df_analise['Status_Funcionario'].fillna('Outros')
    else:
        df_analise = df_analise_temp
        df_analise['Status_Funcionario'] = 'Outros'

    df_source_analise = processar_base_secundaria(df_source_bruto, df_equipe, tabela_calendario)
    df_backlog = processar_base_secundaria(df_backlog_bruto, df_equipe, None)

    df_analise = finalizar_datas(df_analise)
    df_backlog = finalizar_datas(df_backlog)

    return df_analise, df_notas_tabela1, df_notas_tabela2, df_lideranca, df_equipe, df_backlog, df_source_analise