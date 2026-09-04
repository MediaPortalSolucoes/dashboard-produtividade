import time
import asyncio
import requests
import gspread
import pandas as pd
from config import *
from utils import *
from logger import get_logger

logger = get_logger("sync", "cloud_sync.log")

def conectar_google_sheets():
    return gspread.service_account(filename="google_credentials.json")

def safe_gspread_update(worksheet, data):
    worksheet.clear()
    try: worksheet.update(values=data, range_name="A1", value_input_option='USER_ENTERED')
    except TypeError:
        try: worksheet.update("A1", data, value_input_option='USER_ENTERED')
        except Exception: worksheet.update(data, value_input_option='USER_ENTERED')

def obter_token_cloud():
    if not REFRESH_TOKEN_SECRETO: return None
    url = "https://launchpad.37signals.com/authorization/token"
    payload = {"type": "refresh", "refresh_token": REFRESH_TOKEN_SECRETO, "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "redirect_uri": REDIRECT_URI}
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200: return resp.json()["access_token"]
        return None
    except Exception: return None

async def fetch_greedy_async(token, url):
    items, page = [], 1
    if not url.startswith("http"): url = f"https://3.basecampapi.com/{ACCOUNT_ID}{url}"
    connector = "&" if "?" in url else "?"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    while True:
        target_url = f"{url}{connector}page={page}"
        success = False
        page_has_data = False
        
        for _ in range(MAX_RETRIES):
            try:
                response = await asyncio.to_thread(requests.get, target_url, headers=headers)
                if response.status_code == 404: 
                    success = True
                    break
                if response.status_code != 200: 
                    time.sleep(.3)
                    continue
                    
                data = response.json()
                success = True
                if not data: 
                    break
                    
                items.extend(data)
                page += 1
                page_has_data = True
                await asyncio.to_thread(time.sleep, 0.05)
                break 
            except: 
                time.sleep(.3)
        
        if not success or not page_has_data: 
            break 
            
    return items

async def descobrir_bucket_ids(token):
    all_projects = await fetch_greedy_async(token, "/projects.json")
    ids_encontrados = []
    for p in all_projects:
        pid, pname = p.get('id'), p.get('name', '').upper()
        if any(chave in pname for chave in PALAVRAS_CHAVE_PROJETO): 
            ids_encontrados.append(pid)
            logger.info(f"[SYNC] Projeto Encontrado: {pname}")
    return ids_encontrados

async def extract_tasks_complete(token, bucket_id, todolist):
    tasks_bucket = []
    list_id, list_name, list_app_url = todolist.get('id'), todolist.get('title'), todolist.get('app_url')
    todos_url = todolist.get('todos_url') or f"https://3.basecampapi.com/{ACCOUNT_ID}/buckets/{bucket_id}/todolists/{list_id}/todos.json"
    
    logger.info(f"[SYNC] Iniciando leitura da lista: {list_name}")
    
    all_items = await fetch_greedy_async(token, todos_url) + await fetch_greedy_async(token, todos_url + "?completed=true")
    if LER_ARQUIVADOS:
        all_items += await fetch_greedy_async(token, todos_url + "?status=archived")
        
    for t in all_items:
        t['hierarquia_semana'] = list_name
        t['parent_list_url'] = list_app_url
        
        parent_data = t.get('parent', {})
        t['hierarquia_grupo'] = parent_data.get('title', '(Raiz)')
            
    tasks_bucket.extend(all_items)

    groups_url = f"https://3.basecampapi.com/{ACCOUNT_ID}/buckets/{bucket_id}/todolists/{list_id}/groups.json"
    all_groups = await fetch_greedy_async(token, groups_url)
    if LER_ARQUIVADOS:
        all_groups += await fetch_greedy_async(token, groups_url + "?status=archived")
    
    for g in all_groups:
        target_link = g.get('todos_url')
        if target_link:
            group_items = await fetch_greedy_async(token, target_link) + await fetch_greedy_async(token, target_link + "?completed=true")
            if LER_ARQUIVADOS:
                group_items += await fetch_greedy_async(token, target_link + "?status=archived")
                
            for t in group_items:
                t['hierarquia_semana'] = list_name
                t['hierarquia_grupo'] = g.get('title', '(Raiz)')
                t['parent_list_url'] = list_app_url
            tasks_bucket.extend(group_items)
            
    unique_tasks = {t['id']: t for t in tasks_bucket}.values()
            
    logger.info(f"[SYNC] Leitura da lista concluida com {len(unique_tasks)} tarefas totais.")
    return list(unique_tasks)

async def process_bucket(token, bucket_id):
    api_base = f"https://3.basecampapi.com/{ACCOUNT_ID}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{api_base}/projects/{bucket_id}.json", headers=headers)
        todoset_id = next((t['id'] for t in r.json().get('dock', []) if t['name'] == 'todoset'), None)
    except: return []
    if not todoset_id: return []

    url_lists = f"{api_base}/buckets/{bucket_id}/todosets/{todoset_id}/todolists.json"
    
    all_lists = await fetch_greedy_async(token, url_lists)
    all_lists += await fetch_greedy_async(token, url_lists + "?status=completed")
    
    if LER_ARQUIVADOS:
        all_lists += await fetch_greedy_async(token, url_lists + "?status=archived")
        all_lists += await fetch_greedy_async(token, url_lists + "?status=trashed")
    
    mapa_unicas = {}
    for l in all_lists:
        if 'id' in l: 
            mapa_unicas[l['id']] = l
    all_lists_clean = list(mapa_unicas.values())
    
    listas_alvo = [l for l in all_lists_clean if any(termo in l.get('title', '').upper() for termo in TERMOS_DE_BUSCA_LISTAS)]
    backlogs = [l for l in listas_alvo if "BACKLOG" in l.get('title', '').upper()]
    semanas  = [l for l in listas_alvo if "BACKLOG" not in l.get('title', '').upper()]
    
    from utils import extrair_data_da_lista_dt
    
    if LIMITE_LISTAS_RECENTES > 0:
        semanas_validas = []
        hoje = pd.Timestamp.now().normalize()
        
        segunda_atual = hoje - pd.Timedelta(days=hoje.dayofweek)
        data_corte = segunda_atual - pd.Timedelta(weeks=LIMITE_LISTAS_RECENTES - 1)
        
        for s in semanas:
            dt = extrair_data_da_lista_dt(s.get('title'))
            if pd.notnull(dt) and dt >= data_corte:
                semanas_validas.append(s)
                
        semanas = semanas_validas
    else:
        semanas.sort(key=lambda x: extrair_data_da_lista_dt(x.get('title')) if pd.notnull(extrair_data_da_lista_dt(x.get('title'))) else pd.Timestamp.min, reverse=True)

    bucket_tasks = []
    for todolist in (backlogs + semanas): 
        bucket_tasks.extend(await extract_tasks_complete(token, bucket_id, todolist))
    return bucket_tasks