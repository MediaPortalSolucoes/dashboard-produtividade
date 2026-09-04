import asyncio
import os
import pandas as pd
from config import NOME_ABA_EQUIPES
from connections import conectar_google_sheets, obter_token_cloud, descobrir_bucket_ids, process_bucket
from utils import formatar_dataframe_basecamp
from rules import processar_mes_atual, atualizar_aba_geral, atualizar_aba_backlog, consolidar_meses_para_notas
from logger import get_logger

logger = get_logger("sync", "cloud_sync.log")

async def main_process():
    gc = conectar_google_sheets() 
    token = obter_token_cloud()
    if not gc or not token: return

    buckets_ativos = await descobrir_bucket_ids(token)
    if not buckets_ativos: return

    all_tasks = []
    for bucket_id in buckets_ativos:
        all_tasks.extend(await process_bucket(token, bucket_id))
        
    if not all_tasks: return

    df_tarefas = formatar_dataframe_basecamp(all_tasks)
    
    df_equipes = pd.DataFrame()
    try:
        ws_eq = gc.open(title=os.getenv("SPREADSHEET_NAME"), folder_id=os.getenv("FOLDER_ID")).worksheet(NOME_ABA_EQUIPES)
        df_equipes = pd.DataFrame(ws_eq.get_all_records())
    except: pass

    processar_mes_atual(df_tarefas, gc, df_equipes)
    atualizar_aba_geral(df_tarefas, gc, df_equipes)
    atualizar_aba_backlog(df_tarefas, gc, df_equipes)
    
    await consolidar_meses_para_notas(gc, token)
    
    logger.debug("[SYNC] Sincronizacao CLOUD finalizada com sucesso! O historico diario agora e calculado dinamicamente no Dashboard.")

if __name__ == "__main__":
    asyncio.run(main_process())