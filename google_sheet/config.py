import os
import configparser
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

config_file = configparser.ConfigParser()
config_file.read('config.ini')

LIMITE_LISTAS_RECENTES = config_file.getint('Sincronizacao', 'LIMITE_LISTAS_RECENTES', fallback=2)
MAX_RETRIES = config_file.getint('Sincronizacao', 'MAX_RETRIES', fallback=5)

ACCOUNT_ID = "3619571" 
CLIENT_ID = os.getenv("BASECAMP_CLIENT_ID")
CLIENT_SECRET = os.getenv("BASECAMP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("BASECAMP_REDIRECT_URI", "http://localhost:8000/callback")
REFRESH_TOKEN_SECRETO = os.getenv("BASECAMP_REFRESH_TOKEN")


PALAVRAS_CHAVE_PROJETO = ["MEDIA PORTAL", "SPRINT"] 
TERMOS_DE_BUSCA_LISTAS = ["ATIVIDADES DA SEMANA", "BACKLOG"]
LER_ARQUIVADOS = True 

NOME_ABA_EQUIPES = "Equipes"
NOME_ABA_GERAL = "Total BaseCamp Semanas"
NOME_ABA_CONSOLIDADA = "Total BaseCamp para Notas"
NOME_ABA_HISTORICO = "HistoricoDiario"
NOME_ABA_BACKLOG = "Backlog"

COL_ID = 'ID'
COL_STATUS = 'Status'
COL_ATIV_SEM = 'Atividades Semanal'
COL_SUB_LISTA = 'Sub-Lista / Grupo'
COL_NOME_TASK = 'Nome Task'
COL_ENCARREGADO = 'Encarregado'
COL_DATA_INI = 'Data Inicial'
COL_DATA_FIM = 'Data Final'
COL_LINK = 'Link'
COL_LINK_LISTA = 'Link Lista'

COLS_FINAL_EXPORT = [COL_ID, COL_STATUS, COL_ATIV_SEM, COL_SUB_LISTA, COL_NOME_TASK, COL_ENCARREGADO, COL_DATA_INI, COL_DATA_FIM, COL_LINK, COL_LINK_LISTA]

MESES_NUM_PT = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
MESES_PT_NUM = {v: k for k, v in MESES_NUM_PT.items()}