import subprocess
import time
from datetime import datetime
import sys
import threading
import os
import signal
import atexit
import traceback
from logger import get_logger

logger = get_logger("system", "system_main.log")
streamlit_process = None
sync_process = None
shutting_down = False
streamlit_log = None

def desligar_sistema(signum=None, frame=None):
    global shutting_down
    
    if shutting_down:
        return
    shutting_down = True
    
    motivo = "Desligamento interno ou Erro (atexit)"
    if signum == signal.SIGINT:
        motivo = "Ctrl+C (SIGINT)"
    elif signum == signal.SIGTERM:
        motivo = "Systemctl (SIGTERM)"
        
    logger.debug(f"[SYSTEM] Iniciando limpeza total. Motivo: {motivo}")
    
    if streamlit_process and streamlit_process.poll() is None:
        logger.debug("[SYSTEM] Matando processo do Dashboard...")
        streamlit_process.terminate()
        
    if sync_process and sync_process.poll() is None:
        logger.debug("[SYSTEM] Matando processo de Sincronizacao...")
        sync_process.terminate()
        
    if streamlit_log and not streamlit_log.closed:
        streamlit_log.close()
        
    logger.debug("[SYSTEM] Processos orfaos eliminados. Orquestrador encerrado.")
    
    if signum is not None:
        sys.exit(0)

atexit.register(desligar_sistema)

signal.signal(signal.SIGINT, desligar_sistema)
signal.signal(signal.SIGTERM, desligar_sistema)

def run_sync_script():
    global sync_process
    logger.debug("[SCHEDULER] Iniciando sincronizacao com o Basecamp...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    
    sync_process = subprocess.Popen([sys.executable, "google_sheet/main_cloud.py"], env=env)
    sync_process.wait()
    
    if shutting_down:
        return
        
    if sync_process.returncode != 0:
        logger.error("[ERROR] A sincronizacao falhou.")
        logger.error("[SYSTEM] Acionando desligamento do sistema devido a falha critica.")
        sys.exit(1) 
    else:
        logger.debug("[SCHEDULER] Sincronizacao concluida com sucesso.")

def scheduler_loop():
    target_times = ["12:30", "16:30", ]
    run_today = set()
    
    logger.debug(f"[SCHEDULER] Ativo. O script rodara as {target_times[0]} e {target_times[1]}.")
    logger.debug("[SCHEDULER] Executando sincronizacao inicial de inicializacao...")
    run_sync_script()
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    if current_time in target_times:
        run_today.add(current_time)
    
    while True:
        if shutting_down:
            break
            
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        if current_time == "00:00":
            run_today.clear()
            
        if current_time in target_times and current_time not in run_today:
            run_sync_script()
            run_today.add(current_time)
            
        current_timestamp = time.time()
        seconds_remaining = 60 - (current_timestamp % 60)
        time.sleep(seconds_remaining)

if __name__ == "__main__":
    logger.debug("[SYSTEM] Iniciando Orquestrador...")
    
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    
    logger.debug("[SYSTEM] Subindo o servidor do Dashboard...")
    
    log_file_path = os.path.join("logs", "system_main.log")
    streamlit_log = open(log_file_path, "a", encoding="utf-8")
    
    streamlit_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/main.py"],
        stdout=streamlit_log,
        stderr=subprocess.STDOUT
    )
    
    logger.debug("[SYSTEM] Dashboard rodando na porta: 8501")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"[ERROR] Ocorreu uma excecao inesperada no Orquestrador: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)