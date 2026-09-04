import pandas as pd
import gspread
import calendar
import requests
import time
import re
import asyncio
from datetime import datetime, timedelta
from config import *
from utils import *
from connections import safe_gspread_update

def processar_mes_atual(df_completo, gc, df_equipes):
    hoje = datetime.now()
    mes_atual, ano_atual = hoje.month, hoje.year
    nome_aba_atual = f"{MESES_NUM_PT[mes_atual]} {ano_atual}"

    df_completo['Data_Ref_Lista'] = df_completo[COL_ATIV_SEM].apply(extrair_data_da_lista_dt)
    df_completo['Sexta_Ref_Lista'] = df_completo['Data_Ref_Lista'] + pd.Timedelta(days=4)

    mask_mes_atual = (((df_completo['Data_Ref_Lista'].dt.month == mes_atual) & (df_completo['Data_Ref_Lista'].dt.year == ano_atual)) |
                      ((df_completo['Sexta_Ref_Lista'].dt.month == mes_atual) & (df_completo['Sexta_Ref_Lista'].dt.year == ano_atual)))
    df_mes = df_completo[mask_mes_atual].copy()
    
    if df_mes.empty: return

    if COL_DATA_FIM in df_mes.columns:
        df_mes['Data_Final_Obj'] = pd.to_datetime(df_mes[COL_DATA_FIM], dayfirst=True, errors='coerce')
        df_mes['Sexta_Limite'] = df_mes['Data_Ref_Lista'] + pd.Timedelta(days=4)
        mask_ajuste = (df_mes['Data_Final_Obj'].notna()) & (df_mes['Data_Final_Obj'] > df_mes['Sexta_Limite'])
        df_mes.loc[mask_ajuste, COL_DATA_FIM] = df_mes.loc[mask_ajuste, 'Sexta_Limite'].dt.strftime('%d/%m/%Y')

    df_mes['Data_Ref_Tarefa'] = pd.to_datetime(df_mes[COL_DATA_FIM], dayfirst=True, errors='coerce').fillna(pd.to_datetime(df_mes[COL_DATA_INI], dayfirst=True, errors='coerce'))
    mask_cirurgica = ((df_mes['Data_Ref_Tarefa'].dt.month == mes_atual) & (df_mes['Data_Ref_Tarefa'].dt.year == ano_atual)) | df_mes['Data_Ref_Tarefa'].isna()
    df_mes = df_mes[mask_cirurgica].copy()
    
    if df_mes.empty: return
    if not df_equipes.empty: df_mes[COL_ENCARREGADO] = df_mes[COL_SUB_LISTA].apply(lambda x: encontrar_encarregado(x, df_equipes))

    df_upload = df_mes[[c for c in COLS_FINAL_EXPORT if c in df_mes.columns]]
    if df_upload.empty: return

    try:
        spreadsheet = gc.open(title=os.getenv("SPREADSHEET_NAME"), folder_id=os.getenv("FOLDER_ID"))
        try: worksheet = spreadsheet.worksheet(nome_aba_atual)
        except gspread.exceptions.WorksheetNotFound: worksheet = spreadsheet.add_worksheet(title=nome_aba_atual, rows=len(df_upload)+100, cols=20)
        safe_gspread_update(worksheet, df_para_dados_planilha(df_upload))
    except Exception: pass

def atualizar_aba_geral(df_global, gc, df_equipes):
    if not df_equipes.empty:
        df_global[COL_ENCARREGADO] = df_global[COL_SUB_LISTA].apply(lambda x: encontrar_encarregado(x, df_equipes))
    
    df_upload = df_global[[c for c in COLS_FINAL_EXPORT if c in df_global.columns]]
    if not df_upload.empty:
        try:
            ss = gc.open(title=os.getenv("SPREADSHEET_NAME"), folder_id=os.getenv("FOLDER_ID"))
            safe_gspread_update(ss.worksheet(NOME_ABA_GERAL), df_para_dados_planilha(df_upload))
        except Exception: pass

def atualizar_aba_backlog(df_global, gc, df_equipes):
    mask_backlog = df_global[COL_ATIV_SEM].astype(str).str.contains("BACKLOG", case=False, na=False)
    df_backlog = df_global[mask_backlog].copy()
    if df_backlog.empty: return

    if not df_equipes.empty: df_backlog[COL_ENCARREGADO] = df_backlog[COL_SUB_LISTA].apply(lambda x: encontrar_encarregado(x, df_equipes))

    for c in COLS_FINAL_EXPORT:
        if c not in df_backlog.columns: df_backlog[c] = ""
    
    df_upload = df_backlog[COLS_FINAL_EXPORT]
    if df_upload.empty: return

    try:
        spreadsheet = gc.open(title=os.getenv("SPREADSHEET_NAME"), folder_id=os.getenv("FOLDER_ID"))
        try: worksheet = spreadsheet.worksheet(NOME_ABA_BACKLOG)
        except gspread.exceptions.WorksheetNotFound: worksheet = spreadsheet.add_worksheet(title=NOME_ABA_BACKLOG, rows=len(df_upload)+100, cols=20)
        safe_gspread_update(worksheet, df_para_dados_planilha(df_upload))
    except Exception: pass

async def fetch_single_ghost(url, token, idx):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = await asyncio.to_thread(requests.get, url, headers=headers)
        if resp.status_code == 404: return idx, "404", None
        elif resp.status_code == 200:
            data = resp.json()
            if data.get('completed'):
                comp_at = data.get('completed_at') or (data.get('completion') or {}).get('created_at')
                if comp_at: return idx, "200", pd.to_datetime(comp_at).strftime('%d/%m/%Y')
    except: pass
    return idx, "ERROR", None

async def limpar_tarefas_fantasmas_async(df_final, token):
    if COL_DATA_FIM not in df_final.columns: return df_final
    df_final[COL_DATA_FIM] = df_final[COL_DATA_FIM].fillna("").astype(str)
    indices_abertos = df_final[df_final[COL_DATA_FIM].str.strip() == ""].index.tolist()
    if not indices_abertos: return df_final

    tasks = []
    for idx in indices_abertos:
        row = df_final.loc[idx]
        link, task_id = str(row.get(COL_LINK, '')), str(row.get(COL_ID, ''))
        match = re.search(r'buckets/(\d+)', link)
        if match and task_id:
            url = f"https://3.basecampapi.com/{ACCOUNT_ID}/buckets/{match.group(1)}/todos/{task_id}.json"
            tasks.append(fetch_single_ghost(url, token, idx))

    if not tasks: return df_final
    results = await asyncio.gather(*tasks)
    
    to_drop, updates = [], {}
    for idx, status, dt_str in results:
        if status == "404": to_drop.append(idx)
        elif status == "200" and dt_str: updates[idx] = dt_str

    if to_drop: df_final = df_final.drop(index=to_drop)
    for idx, dt_str in updates.items():
        df_final.at[idx, COL_DATA_FIM] = dt_str
        df_final.at[idx, COL_STATUS] = "Fechado"
        
    return df_final

async def consolidar_meses_para_notas(gc, token):
    try: spreadsheet = gc.open(title=os.getenv("SPREADSHEET_NAME"), folder_id=os.getenv("FOLDER_ID"))
    except: return

    df_final = pd.DataFrame()
    try: df_final = pd.DataFrame(spreadsheet.worksheet(NOME_ABA_CONSOLIDADA).get_all_records())
    except gspread.exceptions.WorksheetNotFound: pass

    if df_final.empty:
        dfs_fallback = []
        for ws in spreadsheet.worksheets():
            if extrair_mes_ano_do_nome_aba(ws.title):
                try:
                    raw = ws.get_all_values()
                    if len(raw) > 1: dfs_fallback.append(pd.DataFrame(raw[1:], columns=raw[0]))
                except: pass
        if dfs_fallback: df_final = pd.concat(dfs_fallback, ignore_index=True)

    if df_final.empty: return

    try:
        df_semanas = pd.DataFrame(spreadsheet.worksheet(NOME_ABA_GERAL).get_all_records())
        if not df_semanas.empty:
            df_final[COL_ID] = df_final[COL_ID].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_semanas[COL_ID] = df_semanas[COL_ID].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_final = df_final[~df_final[COL_ID].isin(df_semanas[COL_ID].unique())]
            df_final = pd.concat([df_final, df_semanas], ignore_index=True)
            df_final = df_final.drop_duplicates(subset=[COL_ID], keep='last')
    except Exception: pass

    df_final = await limpar_tarefas_fantasmas_async(df_final, token)

    try:
        try: ws_cons = spreadsheet.worksheet(NOME_ABA_CONSOLIDADA)
        except gspread.exceptions.WorksheetNotFound: ws_cons = spreadsheet.add_worksheet(title=NOME_ABA_CONSOLIDADA, rows=len(df_final)+500, cols=20)
        safe_gspread_update(ws_cons, df_para_dados_planilha(df_final))
    except Exception: pass