# ============================================
# RAVIS - ASSISTENTE VIRTUAL
# ============================================
# Propósito: Arquivo principal que inicia a aplicação desktop
#
# Fluxo:
#   1. Configura cache Python e recursion limit
#   2. Inicia servidor FastAPI em thread
#   3. Aguarda health-check
#   4. Abre janela desktop (pywebview)
#   5. Mantém aplicação até fechar
#
# Uso: python main.py
# ============================================

import sys
import os

# Redireciona cache Python para data/
pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '__pycache__')
os.environ['PYTHONPYCACHEPREFIX'] = pycache_dir
os.makedirs(pycache_dir, exist_ok=True)

sys.setrecursionlimit(10000)
os.environ['PYWEBVIEW_LOG'] = 'none'

import logging
import time
import requests

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

logging.getLogger('pywebview').setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

BASE_URL = "http://127.0.0.1:8000"
STATUS_URL = f"{BASE_URL}/status"

SERVER_STARTUP_TIMEOUT = 30
SERVER_POLL_INTERVAL = 0.5

WEBVIEW_AVAILABLE = True
try:
    import webview
    from src.config import (
        PROJECT_ROOT, WINDOW_WIDTH, WINDOW_HEIGHT,
        IDLE_COLOR
    )
    from server import start_server
except ImportError as e:
    logger.error(f"Erro ao importar dependências: {e}")
    WEBVIEW_AVAILABLE = False


# ============================================================
# Classe: RavisAPI
# ============================================================
# Propósito: API exposta para interface web controlar a janela
#
# Métodos disponíveis (expostos via pywebview):
#   - bring_to_front(): Traz janela para primeiro plano
#   - cleanup(): Limpa recursos ao fechar
#
# Propriedades:
#   - window: Referência para janela do pywebview
# ============================================================
class RavisAPI:
    """API exposta para a interface web controlar janelas do Ravis."""
    
    # ============================================================
    # __init__()
    # ============================================================
    # Propósito: Inicializa a API com referência da janela
    # Entrada: window (objeto janela do pywebview)
    # Saída: Objeto RavisAPI configurado
    # ============================================================
    def __init__(self, window=None):
        self._window = window
    
    @property
    def window(self):
        return self._window
    
    @window.setter
    def window(self, value):
        self._window = value
    
    # ============================================================
    # bring_to_front()
    # ============================================================
    # Propósito: Traz a janela do Ravis para primeiro plano
    # Entrada: Nenhuma
    # Saída: bool (True se sucesso, False se falha)
    # Notas: Usa win32gui para manipulação de janela Windows
    # ============================================================
    def bring_to_front(self):
        """Traz a janela do Ravis para o foreground."""
        try:
            import win32gui
            import win32con
            
            if self._window and self._window.hwnd:
                hwnd = self._window.hwnd
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                logger.info("[RAVIS] Janela trazida para frente")
                return True
        except ImportError:
            logger.warning("[RAVIS] win32api não disponível")
        except Exception as e:
            logger.error(f"[RAVIS] Erro ao trazer janela para frente: {e}")
        return False
    
    # ============================================================
    # cleanup()
    # ============================================================
    # Propósito: Limpa recursos ao fechar a aplicação
    # Entrada: Nenhuma
    # Saída: Nenhuma
    # ============================================================
    def cleanup(self):
        """Limpa recursos ao fechar."""
        logger.info("[RAVIS] Cleanup executado")


# ============================================================
# wait_for_server()
# ============================================================
# Propósito: Aguarda o servidor FastAPI estar pronto
# Entrada: timeout (int) - tempo máximo em segundos
# Saída: bool (True se servidor respondeu, False se timeout)
# ============================================================
def wait_for_server(timeout: int = SERVER_STARTUP_TIMEOUT) -> bool:
    """Aguarda o servidor FastAPI estar pronto."""
    logger.info(f"[RAVIS] Aguardando servidor em {STATUS_URL}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(STATUS_URL, timeout=1)
            if resp.ok:
                logger.info("[RAVIS] Servidor FastAPI pronto!")
                return True
        except requests.RequestException:
            pass
        time.sleep(SERVER_POLL_INTERVAL)
    
    logger.error(f"[RAVIS] Servidor não respondeu em {timeout}s")
    return False


def create_main_window(api: RavisAPI) -> webview.Window:
    """Cria a janela principal do Ravis."""
    window = webview.create_window(
        title='Ravis - Assistente Virtual',
        url=BASE_URL,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(800, 600),
        background_color=IDLE_COLOR,
        resizable=True,
        js_api=api
    )
    api.window = window
    return window


def main():
    """Função principal: Inicia o Ravis."""
    if not WEBVIEW_AVAILABLE:
        logger.error("[RAVIS] Dependências não encontradas. Execute: pip install webview")
        return
    
    logger.info("=" * 50)
    logger.info("[RAVIS] Iniciando Ravis Assistente Virtual")
    logger.info("=" * 50)
    
    logger.info("[RAVIS] Starting FastAPI server...")
    server_thread = start_server()
    
    if not wait_for_server():
        logger.error("[RAVIS] ERRO: Servidor FastAPI não respondeu.")
        logger.error("[RAVIS] Verifique logs e tente novamente.")
        return
    
    logger.info("=" * 50)
    logger.info(f"[RAVIS] Servidor em {BASE_URL}")
    logger.info(f"[RAVIS] WebSocket em ws://127.0.0.1:8000/ws")
    logger.info("=" * 50)
    
    api = RavisAPI()
    window = create_main_window(api)
    
    try:
        webview.start(debug=False, private_mode=True, http_server=False)
    except KeyboardInterrupt:
        logger.info("[RAVIS] Interrupção pelo usuário")
    except Exception as e:
        logger.error(f"[RAVIS] Erro no webview: {e}")
    finally:
        api.cleanup()
        logger.info("[RAVIS] Aplicação encerrada")


if __name__ == "__main__":
    main()
