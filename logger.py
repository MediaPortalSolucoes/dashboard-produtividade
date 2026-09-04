import os
import logging
from logging.handlers import TimedRotatingFileHandler
import gzip
import shutil

os.makedirs("logs", exist_ok=True)

def compactar_log(source, dest):
    try:
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)  
        try:
            os.remove(source)
        except PermissionError:
            with open(source, 'w', encoding='utf-8') as f_clear:
                f_clear.truncate(0)
    except Exception as e:
        print(f"Falha na compactação do log: {e}")

def renomear_log(nome_arquivo):
    return nome_arquivo + ".gz"

def get_logger(nome_modulo, nome_arquivo):
    logger = logging.getLogger(nome_modulo)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)
    caminho_log = os.path.join("logs", nome_arquivo)
    
    handler_arquivo = TimedRotatingFileHandler(
        filename=caminho_log,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    
    handler_arquivo.rotator = compactar_log
    handler_arquivo.namer = renomear_log
    
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler_arquivo.setFormatter(formato)
    
    handler_console = logging.StreamHandler()
    handler_console.setFormatter(formato)
    
    logger.addHandler(handler_arquivo)
    logger.addHandler(handler_console)
    
    return logger