# ============================================
# MÓDULO DE ATALHOS GLOBAIS DO SISTEMA
# ============================================
# Propósito: Gerencia atalhos de teclado globais
#
# Funcionalidades:
#   - Detecta PrintScreen em qualquer aplicação
#   - Executa callback (capture de tela) quando ativado
#   - Thread-safe com lock
#
# Uso:
#   hotkeys = GlobalHotkeys()
#   hotkeys.register_callback('print_screen', minha_funcao)
#   hotkeys.start()
# ============================================

import threading
import logging
from pynput import keyboard
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================
# Enum: HotkeyAction
# ============================================================
# Propósito: Define ações disponíveis para atalhos globais
# ============================================================
class HotkeyAction(Enum):
    SCREEN_CAPTURE = 'screen_capture'

# ============================================================
# Classe: GlobalHotkeys
# ============================================================
# Propósito: Gerencia atalhos de teclado globais do sistema
#
# Atributos:
#   - listener: Listener do pynput para detectar teclas
#   - callbacks: Dicionário de callbacks registrados (name -> function)
#   - running: Flag indicando se o listener está ativo
#   - _lock: Lock para thread-safety
# ============================================================
class GlobalHotkeys:
    """Classe para gerenciar atalhos globais do sistema"""
    
    def __init__(self):
        self.listener = None
        self.callbacks = {}
        self.running = False
        self._lock = threading.Lock()
        
    # ============================================================
    # start()
    # ============================================================
    # Propósito: Inicia o listener de atalhos globais
    # Entrada: Nenhuma
    # Saída: Nenhuma
    # ============================================================
    def start(self):
        """Inicia o listener de atalhos globais"""
        with self._lock:
            if self.running:
                logger.warning("[Hotkeys] Listener já está rodando")
                return
                
            try:
                self.running = True
                logger.info('[Hotkeys] Iniciando listener global...')
                
                def on_press(key):
                    try:
                        self._handle_key_press(key)
                    except Exception as e:
                        logger.error(f'[Hotkeys] Erro ao processar tecla: {e}')
                
                self.listener = keyboard.Listener(
                    on_press=on_press,
                    daemon=True
                )
                self.listener.start()
                
                if self._is_listener_alive():
                    logger.info('[Hotkeys] Listener global iniciado!')
                else:
                    logger.error('[Hotkeys] Listener falhou ao iniciar')
                    self.running = False
                    
            except Exception as e:
                logger.error(f'[Hotkeys] Erro ao iniciar: {e}')
                self.running = False
                
    def _handle_key_press(self, key):
        """Processa tecla pressionada"""
        if key == keyboard.Key.print_screen:
            logger.info('[Hotkeys] PrintScreen detectado!')
            if 'screen_capture' in self.callbacks:
                logger.info('[Hotkeys] Executando screen_capture...')
                self._run_callback_async('screen_capture')
                
    def _run_callback_async(self, callback_name):
        """Executa callback em thread separada para não bloquear o listener"""
        def run():
            try:
                self.callbacks[callback_name]()
            except Exception as e:
                logger.error(f'[Hotkeys] Erro no callback {callback_name}: {e}')
                
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        
    def _is_listener_alive(self) -> bool:
        """Verifica se o listener está ativo"""
        return self.listener is not None and self.listener.is_alive()
        
    def stop(self):
        """Para o listener"""
        with self._lock:
            if self.listener:
                try:
                    self.listener.stop()
                    self.listener = None
                    self.running = False
                    logger.info('[Hotkeys] Listener global parado!')
                except Exception as e:
                    logger.error(f'[Hotkeys] Erro ao parar: {e}')
                    
    def register_callback(self, name: str, callback):
        """Registra um callback para um atalho"""
        with self._lock:
            self.callbacks[name] = callback
            logger.info(f'[Hotkeys] Callback registrado: {name}')
            
    def unregister_callback(self, name: str):
        """Remove um callback"""
        with self._lock:
            if name in self.callbacks:
                del self.callbacks[name]
                logger.info(f'[Hotkeys] Callback removido: {name}')
                
    def is_running(self) -> bool:
        """Retorna se o listener está ativo"""
        return self.running and self._is_listener_alive()
        
    def get_status(self) -> dict:
        """Retorna status do módulo"""
        return {
            'running': self.is_running(),
            'callbacks': list(self.callbacks.keys()),
            'listener_alive': self._is_listener_alive()
        }

_global_hotkeys = None
_lock = threading.Lock()

def get_global_hotkeys():
    """Retorna a instância global de hotkeys (singleton thread-safe)"""
    global _global_hotkeys
    if _global_hotkeys is None:
        with _lock:
            if _global_hotkeys is None:
                _global_hotkeys = GlobalHotkeys()
    return _global_hotkeys

def start_global_hotkeys():
    """Inicia os atalhos globais"""
    hotkeys = get_global_hotkeys()
    hotkeys.start()
    return hotkeys

def stop_global_hotkeys():
    """Para os atalhos globais"""
    hotkeys = get_global_hotkeys()
    hotkeys.stop()
