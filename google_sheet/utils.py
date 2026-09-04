import pandas as pd
import numpy as np
import re
import unicodedata
from config import *

def df_para_dados_planilha(df):
    df_clean = df.fillna("").astype(str).replace("nan", "").replace("NaT", "")
    return [df_clean.columns.values.tolist()] + df_clean.values.tolist()

def normalizar_texto(texto):
    if not isinstance(texto, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()

def converter_data_segura(series):
    series = series.astype(str).str.strip().replace(['nan', 'None', '', 'NaT', '0', '#N/A'], np.nan)
    return pd.to_datetime(series, dayfirst=True, errors='coerce')

def extrair_data_da_lista_dt(texto_lista):
    try:
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', str(texto_lista))
        if match: return pd.to_datetime(match.group(1), dayfirst=True)
    except: pass
    return pd.NaT

def extrair_mes_ano_do_nome_aba(nome_aba):
    try:
        partes = nome_aba.split()
        if len(partes) == 2 and partes[0].capitalize() in MESES_PT_NUM and partes[1].isdigit():
            return MESES_PT_NUM[partes[0].capitalize()], int(partes[1])
    except: pass
    return None

def encontrar_encarregado(sub_lista_val, df_equipes):
    if df_equipes.empty: return ""
    val_limpo = normalizar_texto(sub_lista_val).replace("ATIVIDADES", "").strip()
    if not val_limpo: return ""
    
    partes_busca = val_limpo.split()
    primeiro_nome_busca = partes_busca[0] if partes_busca else ""
    sobrenome_busca = partes_busca[1] if len(partes_busca) > 1 else ""
    
    for nome_real in df_equipes['Nome']:
        partes_real = normalizar_texto(nome_real).split()
        primeiro_nome_real = partes_real[0] if partes_real else ""
        if primeiro_nome_busca == primeiro_nome_real:
            if sobrenome_busca:
                if len(partes_real) > 1 and sobrenome_busca[:4] == partes_real[1][:4]: return nome_real
            else: return nome_real
    return ""

def formatar_dataframe_basecamp(all_tasks):
    df = pd.DataFrame(all_tasks).drop_duplicates(subset='id', keep='last')
    
    df[COL_ID] = df.get('id', '')
    df[COL_NOME_TASK] = df.get('title', '')
    df[COL_ATIV_SEM] = df.get('hierarquia_semana', '')
    df[COL_SUB_LISTA] = df.get('hierarquia_grupo', '')
    
    df = df[df[COL_SUB_LISTA].astype(str).str.upper().str.contains('ATIVIDADES')].copy()
    
    df[COL_LINK] = df.get('app_url', '')
    df[COL_LINK_LISTA] = df.get('parent_list_url', '')
    df[COL_DATA_INI] = pd.to_datetime(df['created_at'], errors='coerce', utc=True).dt.strftime('%d/%m/%Y') if 'created_at' in df.columns else ''

    def get_completion(row):
        if row.get('completed'):
            if row.get('completed_at'): return pd.to_datetime(row['completed_at']).strftime('%d/%m/%Y')
            elif isinstance(row.get('completion'), dict) and row['completion'].get('created_at'):
                return pd.to_datetime(row['completion'].get('created_at')).strftime('%d/%m/%Y')
        return ''
        
    df[COL_DATA_FIM] = df.apply(get_completion, axis=1)

    def get_status(row):
        if row.get('status') == 'archived': return "Arquivado"
        if row.get('trashed'): return "Lixeira"
        if row.get('completed'): return "Fechado"
        return "Aberto"
        
    df[COL_STATUS] = df.apply(get_status, axis=1)
    return df