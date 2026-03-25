# ============================================
# GERENCIADOR DE STARTUP DO WINDOWS
# ============================================
# Propósito: Gerencia execução automática do Ravis ao iniciar o Windows
#
# Funcionalidades:
#   - Adiciona Ravis ao startup do Windows
#   - Remove Ravis do startup do Windows
#   - Verifica status de configuração
#   - Suporta delay configurável antes de iniciar
#
# Implementação:
#   - Usa registro do Windows (HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run)
#   - comando com timeout para delay de startup
#
# Uso:
#   python startup.py add    -> Adiciona ao startup
#   python startup.py remove -> Remove do startup
#   python startup.py check  -> Verifica status
#   python startup.py status -> Exibe status detalhado
# ============================================

import winreg
import os
import sys
import logging
import argparse
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# Constantes
# ============================================================
REGISTRY_PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'
APP_NAME = 'Ravis'
DEFAULT_STARTUP_DELAY = 3


# ============================================================
# Função: get_startup_delay()
# ============================================================
# Propósito: Retorna delay de startup configurado
#
# Retorna:
#   - int: Delay em segundos (padrão: 3)
# ============================================================
def get_startup_delay() -> int:
    """
    Retorna o delay de startup em segundos.
    
    Lê do ambiente (STARTUP_DELAY) ou usa valor padrão.
    
    Returns:
        int: Delay em segundos
    """
    try:
        return int(os.getenv('STARTUP_DELAY', str(DEFAULT_STARTUP_DELAY)))
    except ValueError:
        return DEFAULT_STARTUP_DELAY


# ============================================================
# Função: get_python_path()
# ============================================================
# Propósito: Retorna caminho do interpretador Python atual
#
# Retorna:
#   - str: Caminho absoluto do Python
# ============================================================
def get_python_path() -> str:
    """
    Retorna o caminho do interpretador Python em uso.
    
    Returns:
        str: Caminho absoluto do executável Python
    """
    return sys.executable


# ============================================================
# Função: get_python_path_exists()
# ============================================================
# Propósito: Verifica se o Python atual existe no sistema
#
# Retorna:
#   - bool: True se existe
# ============================================================
def get_python_path_exists() -> bool:
    """
    Verifica se o caminho do Python existe no sistema.
    
    Returns:
        bool: True se o executável existe
    """
    return os.path.isfile(get_python_path())


# ============================================================
# Função: get_script_path()
# ============================================================
# Propósito: Retorna caminho do main.py do Ravis
#
# Retorna:
#   - str: Caminho absoluto do main.py
# ============================================================
def get_script_path() -> str:
    """
    Retorna o caminho do arquivo main.py do Ravis.
    
    Assume que startup.py está em src/modules/
    e sobe 2 níveis para encontrar a raiz do projeto.
    
    Returns:
        str: Caminho absoluto do main.py
    """
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file))
    return os.path.join(project_root, 'main.py')


# ============================================================
# Função: script_exists()
# ============================================================
# Propósito: Verifica se arquivo de script existe
#
# Args:
#   - script_path: Caminho do script
#
# Retorna:
#   - bool: True se arquivo existe
# ============================================================
def script_exists(script_path: str) -> bool:
    """
    Verifica se o arquivo de script existe.
    
    Args:
        script_path: Caminho do script a verificar
    
    Returns:
        bool: True se o arquivo existe
    """
    return os.path.isfile(script_path)


# ============================================================
# Função: build_startup_command()
# ============================================================
# Propósito: Constrói comando de startup com delay
#
# Args:
#   - python_path: Caminho do Python
#   - script_path: Caminho do script
#   - delay: Delay em segundos
#
# Retorna:
#   - str: Comando formatado
# ============================================================
def build_startup_command(python_path: str, script_path: str, delay: int) -> str:
    """
    Constrói o comando de startup com delay.
    
    Usa timeout do cmd.exe para esperar antes de executar.
    
    Args:
        python_path: Caminho do executável Python
        script_path: Caminho do script a executar
        delay: Segundos de espera antes de executar
    
    Returns:
        str: Comando formatado para o registro
    """
    return f'cmd /c "timeout /t {delay} /nobreak >nul && "{python_path}" "{script_path}""'


# ============================================================
# Função: _get_registry_value()
# ============================================================
# Propósito: Lê valor do registro do Windows
#
# Args:
#   - name: Nome do valor
#
# Retorna:
#   - str ou None: Valor lido ou None se não existir
# ============================================================
def _get_registry_value(name: str) -> Optional[str]:
    """
    Lê um valor do registro do Windows.
    
    Args:
        name: Nome do valor a ler
    
    Returns:
        str: Valor armazenado, ou None se não existir
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_READ
        ) as chave:
            command, _ = winreg.QueryValueEx(chave, name)
            return command
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f'Erro ao ler registro: {e}')
        return None


# ============================================================
# Função: _set_registry_value()
# ============================================================
# Propósito: Define valor no registro do Windows
#
# Args:
#   - name: Nome do valor
#   - value: Valor a armazenar
#
# Retorna:
#   - bool: True se sucesso
# ============================================================
def _set_registry_value(name: str, value: str) -> bool:
    """
    Define um valor no registro do Windows.
    
    Args:
        name: Nome do valor
        value: Valor a armazenar
    
    Returns:
        bool: True se sucesso, False se erro
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_SET_VALUE
        ) as chave:
            winreg.SetValueEx(chave, name, 0, winreg.REG_SZ, value)
        return True
    except PermissionError:
        logger.error('Permissão negada para modificar o registro')
        return False
    except Exception as e:
        logger.error(f'Erro ao definir registro: {e}')
        return False


# ============================================================
# Função: _delete_registry_value()
# ============================================================
# Propósito: Remove valor do registro do Windows
#
# Args:
#   - name: Nome do valor
#
# Retorna:
#   - bool: True se sucesso
# ============================================================
def _delete_registry_value(name: str) -> bool:
    """
    Remove um valor do registro do Windows.
    
    Args:
        name: Nome do valor a remover
    
    Returns:
        bool: True se sucesso, False se erro
    """
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_SET_VALUE
        ) as chave:
            winreg.DeleteValue(chave, name)
        return True
    except FileNotFoundError:
        return True
    except PermissionError:
        logger.error('Permissão negada para modificar o registro')
        return False
    except Exception as e:
        logger.error(f'Erro ao remover registro: {e}')
        return False


# ============================================================
# Função: adicionar_startup()
# ============================================================
# Propósito: Adiciona Ravis ao startup do Windows
#
# Retorna:
#   - bool: True se sucesso
# ============================================================
def adicionar_startup() -> bool:
    """
    Adiciona Ravis à lista de programas de startup do Windows.
    
    Registra o comando no HKEY_CURRENT_USER para iniciar
    automaticamente após o login.
    
    Returns:
        bool: True se sucesso, False se erro
    """
    python_path = get_python_path()
    script_path = get_script_path()
    delay = get_startup_delay()
    
    if not os.path.isfile(python_path):
        logger.error(f'[STARTUP] Python não encontrado: {python_path}')
        return False
    
    if not script_exists(script_path):
        logger.error(f'[STARTUP] Script não encontrado: {script_path}')
        return False
    
    comando = build_startup_command(python_path, script_path, delay)
    logger.info(f'[STARTUP] Comando: {comando}')
    
    if _set_registry_value(APP_NAME, comando):
        logger.info('[STARTUP] Ravis adicionado ao startup do Windows!')
        return True
    
    return False


# ============================================================
# Função: remover_startup()
# ============================================================
# Propósito: Remove Ravis do startup do Windows
#
# Retorna:
#   - bool: True se sucesso
# ============================================================
def remover_startup() -> bool:
    """
    Remove Ravis da lista de startup do Windows.
    
    Remove a entrada do registro HKEY_CURRENT_USER.
    
    Returns:
        bool: True se sucesso, False se erro
    """
    if _delete_registry_value(APP_NAME):
        logger.info('[STARTUP] Ravis removido do startup do Windows!')
        return True
    return False


# ============================================================
# Função: verificar_startup()
# ============================================================
# Propósito: Verifica status de configuração do startup
#
# Retorna:
#   - dict: Status com enabled, command, script_path, python_path
# ============================================================
def verificar_startup() -> dict:
    """
    Verifica se Ravis está configurado para iniciar automaticamente.
    
    Returns:
        dict: Status contendo:
            - enabled (bool): Se está habilitado
            - command (str ou None): Comando registrado
            - script_path (str): Caminho do script
            - python_path (str): Caminho do Python
    """
    script_path = get_script_path()
    python_path = get_python_path()
    command = _get_registry_value(APP_NAME)
    
    return {
        'enabled': command is not None,
        'command': command,
        'script_path': script_path,
        'python_path': python_path
    }


# ============================================================
# Função: status_startup()
# ============================================================
# Propósito: Exibe status formatado do startup
# ============================================================
def status_startup():
    """Exibe status formatado do startup na saída padrão."""
    status = verificar_startup()
    
    print('\n=== Status do Startup ===')
    print(f'Script: {status["script_path"]}')
    print(f'Python: {status["python_path"]}')
    print(f'Ativado: {"Sim" if status["enabled"] else "Não"}')
    
    if status['enabled'] and status.get('command'):
        print(f'Comando: {status["command"]}')
    
    if status.get('error'):
        print(f'Erro: {status["error"]}')
    print()


# ============================================================
# Ponto de entrada
# ============================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gerencia execução automática do Ravis ao iniciar Windows'
    )
    parser.add_argument(
        'acao',
        choices=['add', 'remove', 'check', 'status'],
        nargs='?',
        default='status'
    )
    args = parser.parse_args()
    
    if args.acao == 'add':
        if adicionar_startup():
            sys.exit(0)
        sys.exit(1)
    elif args.acao == 'remove':
        if remover_startup():
            sys.exit(0)
        sys.exit(1)
    else:
        status_startup()
