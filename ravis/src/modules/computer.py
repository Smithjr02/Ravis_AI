# ============================================
# MÓDULO DE CONTROLE DO COMPUTADOR
# ============================================
# Propósito: Executa ações no computador do usuário
#
# Funcionalidades:
#   - Abrir aplicativos pelo nome
#   - Abrir URLs no navegador
#   - Controle de volume e brilho
#   - Captura de tela
#   - Controle de sistema (shutdown, lock, restart)
#   - Pastas especiais do Windows
#   - Criação de notas
#   - Controle de Spotify
#   - Tradução e pesquisa
#
# Estratégia de busca de apps (11 níveis):
#   1. Apps conhecidos (dicionário pré-definido)
#   2. Menu Iniciar (atalhos)
#   3. Program Files / Program Files (x86)
#   4. AppData\Local\Programs
#   5. shutil.which()
#   6. subprocess.Popen
#   7. webbrowser module
#
# Uso:
#   computer = Computer()
#   computer.open_app("chrome")
#   computer.open_url("https://google.com")
#   computer.set_volume(50)
# ============================================

import subprocess
import os
import webbrowser
import shutil
import re
from datetime import datetime


# ============================================================
# Constantes
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NIRCMD_PATH = os.path.join(PROJECT_ROOT, 'bin', 'nircmd.exe')


# ============================================================
# Dicionários de URLs e Pastas
# ============================================================
PYTHONSITES = {
    'globo': 'https://globo.com',
    'g1': 'https://g1.globo.com',
    'youtube': 'https://youtube.com',
    'gmail': 'https://gmail.com',
    'github': 'https://github.com',
    'linkedin': 'https://linkedin.com',
    'twitter': 'https://twitter.com',
    'x': 'https://twitter.com',
    'netflix': 'https://netflix.com',
    'spotify': 'https://open.spotify.com',
    'whatsapp': 'https://web.whatsapp.com',
    'chatgpt': 'https://chat.openai.com',
    'claude': 'https://claude.ai',
    'google': 'https://google.com',
    'maps': 'https://maps.google.com',
    'drive': 'https://drive.google.com',
    'translate': 'https://translate.google.com',
    'discord': 'https://discord.com',
    'reddit': 'https://reddit.com',
    'amazon': 'https://amazon.com.br',
    'wikipedia': 'https://wikipedia.org',
}

SPECIAL_FOLDERS = {
    'downloads': os.path.expanduser('~/Downloads'),
    'download': os.path.expanduser('~/Downloads'),
    'documentos': os.path.expanduser('~/Documents'),
    'imagens': os.path.expanduser('~/Pictures'),
    'fotos': os.path.expanduser('~/Pictures'),
    'desktop': os.path.expanduser('~/Desktop'),
    'músicas': os.path.expanduser('~/Music'),
    'vídeos': os.path.expanduser('~/Videos'),
    'videos': os.path.expanduser('~/Videos'),
}


# ============================================================
# Classe: Computer
# ============================================================
# Propósito: Interface unificada para controle do computador
#
# Atributos:
#   - pyautogui: Instância lazy-load de pyautogui
#   - pending_shutdown: Flag para confirmação de shutdown
#   - chrome_paths: Lista de caminhos possíveis do Chrome
#   - known_apps: Dicionário de apps conhecidos
# ============================================================
class Computer:
    """
    Interface para controle de diversas funcionalidades do sistema.
    
    Inclui abertura de apps, URLs, controle de volume/brilho,
    captura de tela, gerenciamento de sistema e mais.
    """
    
    def __init__(self):
        """
        Inicializa o módulo de controle do computador.
        
        Configura caminhos de apps conhecidos e inicializa flags.
        """
        self.pyautogui = None
        self.pending_shutdown = False
        print("[COMPUTER] Módulo Computer inicializado")
        
        self.chrome_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', r'C:\Program Files'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
        
        self.known_apps = {
            "chrome": "chrome",
            "navegador": "chrome",
            "firefox": "firefox",
            "spotify": "spotify",
            "discord": "discord",
            "notepad": "notepad",
            "bloco de notas": "notepad",
            "calculadora": "calc",
            "explorador": "explorer",
            "vscode": "code",
            "visual studio": "devenv",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "task manager": "taskmgr",
            "gerenciador de tarefas": "taskmgr",
            "prompt": "cmd",
            "terminal": "cmd",
            "cmd": "cmd",
        }
    
    
    # ==================== BUSCA DE APLICATIVOS ====================
    
    def _find_chrome(self) -> str | None:
        """
        Localiza executável do Google Chrome no sistema.
        
        Returns:
            str: Caminho do Chrome ou None se não encontrado
        """
        for path in self.chrome_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _search_in_start_menu(self, app_name: str) -> str | None:
        """
        Busca aplicativo nos atalhos do Menu Iniciar.
        
        Args:
            app_name: Nome do aplicativo a buscar
        
        Returns:
            str: Caminho do atalho ou None
        """
        app_lower = app_name.lower().replace(" ", "")
        
        try:
            for root, dirs, files in os.walk(r'C:\ProgramData\Microsoft\Windows\Start Menu'):
                for f in files:
                    if f.endswith('.lnk'):
                        name = f.replace('.lnk', '').lower().replace(" ", "")
                        if app_lower in name:
                            return os.path.join(root, f)
        except:
            pass
        
        try:
            user_start = os.path.expanduser(r'~\AppData\Roaming\Microsoft\Windows\Start Menu')
            for root, dirs, files in os.walk(user_start):
                for f in files:
                    if f.endswith('.lnk'):
                        name = f.replace('.lnk', '').lower().replace(" ", "")
                        if app_lower in name:
                            return os.path.join(root, f)
        except:
            pass
        
        return None
    
    def _search_in_programs(self, app_name: str) -> str | None:
        """
        Busca executável em Program Files e AppData.
        
        Args:
            app_name: Nome do aplicativo
        
        Returns:
            str: Caminho do executável ou None
        """
        app_lower = app_name.lower()
        
        folders = [
            os.environ.get('PROGRAMFILES', r'C:\Program Files'),
            os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'),
            os.path.expanduser(r"~\AppData\Local\Programs"),
            os.path.expanduser(r"~\AppData\Local\Apps"),
        ]
        
        for folder in folders:
            if not os.path.exists(folder):
                continue
            try:
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        if f.lower().startswith(app_lower) and (f.endswith('.exe') or f.endswith('.lnk')):
                            exe_path = os.path.join(root, f)
                            if f.endswith('.exe'):
                                return exe_path
            except:
                continue
        
        return None
    
    def _find_app_executable(self, app_name: str) -> str | None:
        """
        Encontra o executável de um aplicativo usando múltiplas estratégias.
        
        Args:
            app_name: Nome do aplicativo
        
        Returns:
            str: Caminho do executável ou None
        """
        app_key = app_name.lower().strip()
        
        if app_key in self.known_apps:
            command = self.known_apps[app_key]
            if os.path.exists(command):
                return command
            return command
        
        result = shutil.which(app_key)
        if result:
            return result
        
        shortcut = self._search_in_start_menu(app_key)
        if shortcut:
            return shortcut
        
        exe = self._search_in_programs(app_key)
        if exe:
            return exe
        
        return None
    
    
    # ==================== CONTROLE DE VOLUME ====================
    
    def set_volume(self, delta: int) -> str:
        """
        Aumenta ou diminui o volume em delta pontos.
        
        Args:
            delta: Valores positivos aumentam, negativos diminuem
                  Ex: +5 (mais alto), -10 (mais baixo)
        
        Returns:
            str: Resultado da operação
        """
        nir_delta = int(abs(delta) * 655.35)
        nircmd = NIRCMD_PATH
        
        try:
            if delta > 0:
                subprocess.Popen([nircmd, 'changesysvolume', str(nir_delta)])
            else:
                subprocess.Popen([nircmd, 'changesysvolume', str(-nir_delta)])
            return f"Volume {'aumentado' if delta > 0 else 'diminuído'}."
        except FileNotFoundError:
            return "nircmd.exe não encontrado na pasta bin do projeto."
        except Exception as e:
            return f"Erro ao ajustar volume: {str(e)}"
    
    def set_volume_to(self, level: int) -> str:
        """
        Define o volume para um valor específico.
        
        Args:
            level: Valor de 0 a 100
        
        Returns:
            str: Resultado da operação
        """
        level = max(0, min(100, level))
        nir_level = int(level * 655.35)
        nircmd = NIRCMD_PATH
        
        try:
            subprocess.Popen([nircmd, 'setsysvolume', str(nir_level)])
            return f"Volume definido para {level}%."
        except FileNotFoundError:
            return "nircmd.exe não encontrado na pasta bin do projeto."
        except Exception as e:
            return f"Erro ao definir volume: {str(e)}"
    
    def set_mute(self, muted: bool = None) -> str:
        """
        Muta ou desmuta o áudio do sistema.
        
        Args:
            muted: True para mutar, False para desmutar, None para alternar
        
        Returns:
            str: Resultado da operação
        """
        nircmd = NIRCMD_PATH
        try:
            subprocess.Popen([nircmd, 'mutesysvolume', '2'])
            return "Mudo alternado."
        except FileNotFoundError:
            return "nircmd.exe não encontrado na pasta bin do projeto."
        except Exception as e:
            return f"Erro ao mutar: {str(e)}"
    
    def get_volume(self) -> int:
        """
        Retorna o volume atual em percentual.
        
        Returns:
            int: Volume atual (0-100), fallback 50
        """
        return 50
    
    def get_volume_real(self) -> int:
        """
        Lê volume real do sistema via PowerShell.
        
        Returns:
            int: Volume atual (0-100), fallback 50
        """
        try:
            result = subprocess.run([
                'powershell', '-Command',
                '(Get-AudioDevice -PlaybackVolume *).Volume * 100'
            ], capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                return int(float(result.stdout.strip()))
        except:
            pass
        return 50
    
    
    # ==================== CONTROLE DE BRILHO ====================
    
    def set_brightness(self, level: int) -> str:
        """
        Define o brilho para valor específico.
        
        Args:
            level: Valor de 0 a 100
        
        Returns:
            str: Resultado da operação
        """
        level = max(0, min(100, level))
        
        try:
            subprocess.run([
                'powershell', '-Command',
                f'Set-Brightness -Level {level}'
            ], capture_output=True, timeout=3)
            return f"Brilho definido para {level}%."
        except:
            pass
        
        nircmd = NIRCMD_PATH
        try:
            subprocess.Popen([nircmd, 'monitor', 'setbrightness', str(level)])
            return f"Brilho definido para {level}%."
        except:
            pass
        
        return "Controle de brilho não disponível."
    
    def adjust_brightness(self, delta: int) -> str:
        """
        Aumenta ou diminui o brilho.
        
        Args:
            delta: Quantidade a aumentar (+) ou diminuir (-)
        
        Returns:
            str: Resultado da operação
        """
        current = self.get_brightness()
        new_level = max(0, min(100, current + delta))
        
        try:
            subprocess.run([
                'powershell', '-Command',
                f'Set-Brightness -Level {new_level}'
            ], capture_output=True, timeout=3)
            return f"Brilho definido para {new_level}%."
        except:
            pass
        
        nircmd = NIRCMD_PATH
        try:
            subprocess.Popen([nircmd, 'monitor', 'setbrightness', str(new_level)])
            return f"Brilho definido para {new_level}%."
        except:
            pass
        
        return "Controle de brilho não disponível neste sistema."
    
    def get_brightness(self) -> int:
        """
        Retorna o brilho atual em percentual.
        
        Returns:
            int: Brilho atual (0-100), fallback 50
        """
        try:
            result = subprocess.run([
                'powershell', '-Command',
                '(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
        except:
            pass
        return 50
    
    
    # ==================== MODO NOTURNO ====================
    
    def toggle_night_light(self) -> str:
        """
        Ativa ou desativa o Modo Noturno (Night Light) do Windows.
        
        Returns:
            str: Resultado da operação
        """
        try:
            subprocess.run(
                ['powershell', '-Command', 'Set-NightLight -Mode Toggle'],
                capture_output=True, timeout=5
            )
            return "Modo noturno alternado."
        except:
            try:
                subprocess.run(
                    ['powershell', '-Command', 
                     '$key = Get-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default$windows.data.bluelightreduction.bluelightreductionstates\\windows.data.bluelightreduction.bluelightreductionstate"; '
                     '$current = [byte[]]($key.Data)[12]; '
                     'if ($current[0] -eq 1) { $current[0] = 0 } else { $current[0] = 1 }; '
                     '$key.Data[12..31] = $current; Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default$windows.data.bluelightreduction.bluelightreductionstates\\windows.data.bluelightreduction.bluelightreductionstate" -Name Data -Value $key.Data'],
                    capture_output=True, timeout=5
                )
                return "Modo noturno alternado."
            except:
                return "Modo noturno não disponível."
    
    
    # ==================== CAPTURA DE TELA ====================
    
    def take_screenshot(self, save_to: str = None) -> str:
        """
        Tira um screenshot da tela principal.
        
        Args:
            save_to: Caminho opcional. Se None, salva em Downloads
        
        Returns:
            str: Caminho do arquivo salvo ou mensagem de erro
        """
        try:
            import mss
            from PIL import Image
            
            if save_to is None:
                save_to = os.path.join(os.path.expanduser('~'), 'Downloads')
            
            os.makedirs(save_to, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(save_to, filename)
            
            with mss.mss() as sct:
                sct.shot(mon=-1, output=filepath)
            
            return filepath
            
        except Exception as e:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
                filepath = os.path.join(downloads, f"screenshot_{timestamp}.png")
                
                subprocess.run(
                    ['powershell', '-Command', 
                     f'Add-Type -AssemblyName System.Windows.Forms; '
                     f'$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; '
                     f'$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height); '
                     f'$g = [System.Drawing.Graphics]::FromImage($bmp); '
                     f'$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size); '
                     f'$bmp.Save("{filepath}"); '
                     f'$g.Dispose(); $bmp.Dispose()'],
                    capture_output=True, timeout=10
                )
                return filepath
            except:
                return f"Erro ao capturar tela: {str(e)}"
    
    
    # ==================== CONTROLE DE SISTEMA ====================
    
    def lock_screen(self) -> str:
        """
        Bloqueia a tela do Windows.
        
        Returns:
            str: Resultado da operação
        """
        try:
            subprocess.run(['rundll32.exe', 'user32.dll,LockWorkStation'], check=True)
            return "Tela bloqueada."
        except Exception as e:
            return f"Erro ao bloquear: {str(e)}"
    
    def shutdown_pc(self) -> str:
        """
        Desliga o PC (com confirmação em duas etapas).
        
        Returns:
            str: Mensagem de confirmação ou erro
        """
        if self.pending_shutdown:
            self.pending_shutdown = False
            try:
                subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
                return "Desligando agora..."
            except Exception as e:
                return f"Erro ao desligar: {str(e)}"
        else:
            self.pending_shutdown = True
            return "Confirma o desligamento? Diga 'sim' para confirmar."
    
    def confirm_shutdown(self) -> str:
        """
        Confirma desligamento pendente.
        
        Returns:
            str: Resultado da operação
        """
        self.pending_shutdown = True
        return self.shutdown_pc()
    
    def restart_pc(self) -> str:
        """
        Reinicia o PC com delay de 30 segundos.
        
        Returns:
            str: Mensagem de confirmação
        """
        try:
            subprocess.run(['shutdown', '/r', '/t', '/c', '"Ravis: reiniciando em 30 segundos"'], check=True)
            return "Reiniciando em 30 segundos. Cancele com 'shutdown -a' no terminal."
        except Exception as e:
            return f"Erro ao reiniciar: {str(e)}"
    
    def cancel_shutdown(self) -> str:
        """
        Cancela desligamento/reinício pendente.
        
        Returns:
            str: Resultado da operação
        """
        try:
            subprocess.run(['shutdown', '/a'], check=True)
            return "Desligamento cancelado."
        except:
            return "Nada para cancelar."
    
    
    # ==================== ABRIR PASTAS ESPECIAIS ====================
    
    def open_special_folder(self, folder_name: str) -> str:
        """
        Abre uma pasta especial do Windows pelo nome.
        
        Args:
            folder_name: 'downloads', 'documentos', 'imagens', 'desktop', etc.
        
        Returns:
            str: Resultado da operação
        """
        folder_key = folder_name.lower().strip()
        
        for article in ['a ', 'o ', 'minha ', 'minhas ', 'pasta ']:
            if folder_key.startswith(article):
                folder_key = folder_key[len(article):].strip()
        
        if folder_key in SPECIAL_FOLDERS:
            path = SPECIAL_FOLDERS[folder_key]
            return self.open_folder(path)
        
        return f"Pasta '{folder_name}' não reconhecida."
    
    
    # ==================== CRIAR NOTAS ====================
    
    def create_note(self, title: str, content: str = "") -> str:
        """
        Cria uma nota de texto na área de trabalho.
        
        Args:
            title: Nome/título do arquivo (sem extensão)
            content: Conteúdo da nota
        
        Returns:
            str: Resultado da operação
        """
        try:
            desktop = os.path.expanduser('~/Desktop')
            
            safe_title = "".join(c for c in title if c.isalnum() or c in ' -_').strip()
            if not safe_title:
                safe_title = f"nota_{datetime.now().strftime('%H%M%S')}"
            
            filepath = os.path.join(desktop, f"{safe_title}.txt")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Nota criada: {safe_title}.txt"
        except Exception as e:
            return f"Erro ao criar nota: {str(e)}"
    
    
    # ==================== PESQUISA ====================
    
    def search_google(self, query: str) -> str:
        """
        Abre o Google com uma pesquisa.
        
        Args:
            query: Termo de pesquisa
        
        Returns:
            str: Confirmação da ação
        """
        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://google.com/search?q={encoded_query}"
        return self.open_url(url)
    
    def search_youtube(self, query: str) -> str:
        """
        Pesquisa no YouTube.
        
        Args:
            query: Termo de pesquisa
        
        Returns:
            str: Confirmação da ação
        """
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        self.open_url(url)
        return f"Pesquisando '{query}' no YouTube..."
    
    
    # ==================== TRADUÇÃO ====================
    
    def translate_text(self, text: str = "") -> str:
        """
        Abre o Google Translate.
        
        Args:
            text: Texto opcional para traduzir
        
        Returns:
            str: Confirmação da ação
        """
        if text:
            import urllib.parse
            encoded = urllib.parse.quote_plus(text)
            url = f"https://translate.google.com/?sl=auto&tl=pt&text={encoded}&op=translate"
        else:
            url = "https://translate.google.com/"
        return self.open_url(url)
    
    
    # ==================== INFORMAÇÃO DO SISTEMA ====================
    
    def get_time(self) -> str:
        """
        Retorna a hora atual formatada.
        
        Returns:
            str: Hora no formato HH:MM
        """
        return datetime.now().strftime("%H:%M")
    
    def get_date(self) -> str:
        """
        Retorna a data atual formatada em português.
        
        Returns:
            str: Data no formato "dd de Mês de YYYY"
        """
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except:
            pass
        return datetime.now().strftime("%d de %B de %Y")
    
    def calculate(self, expression: str) -> str:
        """
        Avalia uma expressão matemática simples.
        
        Args:
            expression: Expressão como "2+2", "10*5" ou "15% de 300"
        
        Returns:
            str: Resultado da avaliação
        """
        try:
            pct_match = re.search(r'(\d+(?:[.,]\d+)?)\s*%\s*(?:de|of)?\s*(\d+(?:[.,]\d+)?)', expression)
            if pct_match:
                pct = float(pct_match.group(1).replace(',', '.')) / 100
                base = float(pct_match.group(2).replace(',', '.'))
                result = base * pct
                return f"{pct_match.group(1)}% de {pct_match.group(2)} = {result}"
            
            safe_expr = ''.join(c for c in expression if c in '0123456789+-*/.() ')
            safe_expr = safe_expr.replace('x', '*')
            result = eval(safe_expr)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Não consegui calcular: {str(e)}"
    
    
    # ==================== ABRIR URLs ====================
    
    def open_url(self, url: str) -> str:
        """
        Abre URL no navegador padrão ou em navegador específico.
        
        Args:
            url: Endereço a abrir
        
        Returns:
            str: Confirmação da ação
        """
        print(f"[COMPUTER] Tentando abrir URL: {url}")
        chrome = self._find_chrome()
        
        if chrome:
            try:
                subprocess.Popen([chrome, url])
                print(f"[COMPUTER] Sucesso ao abrir URL")
                return f"Abrindo {url}..."
            except:
                pass
        
        try:
            edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            if os.path.exists(edge_path):
                subprocess.Popen([edge_path, url])
                return f"Abrindo no Edge: {url}..."
        except:
            pass
        
        try:
            firefox_path = os.path.expanduser(r"~\AppData\Local\Mozilla Firefox\firefox.exe")
            if os.path.exists(firefox_path):
                subprocess.Popen([firefox_path, url])
                return f"Abrindo no Firefox: {url}..."
        except:
            pass
        
        try:
            webbrowser.open(url)
            print(f"[COMPUTER] Sucesso ao abrir URL via webbrowser")
            return f"Abrindo {url}..."
        except:
            pass
        
        try:
            os.system(f'start "" "{url}"')
            return f"Abrindo {url}..."
        except:
            pass
        
        return f"Erro ao abrir navegador: não foi possível abrir {url}"
    
    def open_new_tab(self, url: str) -> str:
        """
        Abre URL em nova aba do Chrome.
        
        Args:
            url: Endereço a abrir
        
        Returns:
            str: Confirmação da ação
        """
        chrome = self._find_chrome()
        if chrome:
            try:
                subprocess.Popen([chrome, '--new-tab', url])
                return f"Abrindo nova aba: {url}..."
            except:
                pass
        return self.open_url(url)
    
    def open_url_python_site(self, site_name: str) -> str:
        """
        Abre um site da lista de sites conhecidos.
        
        Args:
            site_name: Nome do site (globo, youtube, gmail, etc)
        
        Returns:
            str: Resultado da operação
        """
        site_key = site_name.lower().strip()
        
        for article in ['o ', 'a ', 'o site ', 'o site da ', 'o ']:
            if site_key.startswith(article):
                site_key = site_key[len(article):].strip()
        
        if site_key in PYTHONSITES:
            url = PYTHONSITES[site_key]
            return self.open_url(url)
        
        for name, url in PYTHONSITES.items():
            if name in site_key or site_key in name:
                return self.open_url(url)
        
        return f"Site '{site_name}' não reconhecido."
    
    
    # ==================== ABRIR APLICATIVOS ====================
    
    def open_app(self, app_name: str) -> str:
        """
        Abre um aplicativo pelo nome.
        
        Args:
            app_name: Nome do aplicativo
        
        Returns:
            str: Resultado da operação
        """
        print(f"[COMPUTER] Tentando abrir: {app_name}")
        
        app_key = app_name.lower().strip()
        
        if app_key in ['chrome', 'navegador']:
            chrome_path = self._find_chrome()
            if chrome_path:
                subprocess.Popen([chrome_path])
                print(f"[COMPUTER] Sucesso ao abrir: {app_name}")
                return f"{app_name} aberto."
        
        exe_path = self._find_app_executable(app_key)
        
        if exe_path:
            try:
                if exe_path.endswith('.lnk'):
                    os.startfile(exe_path)
                else:
                    subprocess.Popen([exe_path])
                print(f"[COMPUTER] Sucesso ao abrir: {app_key} ({exe_path})")
                return f"{app_name} aberto."
            except Exception as e:
                print(f"[COMPUTER] Erro ao executar: {e}")
        
        try:
            os.startfile(app_key)
            print(f"[COMPUTER] Sucesso ao abrir (startfile): {app_key}")
            return f"{app_name} aberto."
        except:
            pass
        
        print(f"[COMPUTER] App não encontrado: {app_key}")
        return f"'{app_name}' não encontrado."
    
    
    # ==================== ABRIR ARQUIVOS E PASTAS ====================
    
    def open_file(self, path: str) -> str:
        """
        Abre um arquivo com o aplicativo padrão.
        
        Args:
            path: Caminho do arquivo
        
        Returns:
            str: Resultado da operação
        """
        try:
            if os.path.exists(path):
                os.startfile(path)
                return f"Arquivo aberto: {path}"
            else:
                return f"Arquivo não encontrado: {path}"
        except Exception as e:
            return f"Erro ao abrir arquivo: {str(e)}"
    
    def open_folder(self, path: str) -> str:
        """
        Abre uma pasta no Explorer.
        
        Args:
            path: Caminho da pasta
        
        Returns:
            str: Resultado da operação
        """
        try:
            if os.path.exists(path):
                os.startfile(path)
                return f"Pasta aberta: {path}"
            else:
                return f"Pasta não encontrada: {path}"
        except Exception as e:
            return f"Erro ao abrir pasta: {str(e)}"
    
    
    # ==================== CONTROLE DE TECLADO ====================
    
    def type_text(self, text: str) -> str:
        """
        Digita texto usando pyautogui.
        
        Args:
            text: Texto a digitar
        
        Returns:
            str: Resultado da operação
        """
        try:
            import pyautogui
            pyautogui.write(text)
            return "Texto digitado."
        except Exception as e:
            return f"Erro ao digitar: {str(e)}"
    
    def press_key(self, key: str) -> str:
        """
        Pressiona uma tecla usando pyautogui.
        
        Args:
            key: Nome da tecla
        
        Returns:
            str: Resultado da operação
        """
        try:
            import pyautogui
            pyautogui.press(key)
            return f"Tecla {key} pressionada."
        except Exception as e:
            return f"Erro ao pressionar tecla: {str(e)}"
    
    
    # ==================== CONTROLE DE JANELAS ====================
    
    def close_window(self) -> str:
        """
        Fecha a janela atual usando Alt+F4.
        
        Returns:
            str: Resultado da operação
        """
        try:
            if not self.pyautogui:
                import pyautogui
                self.pyautogui = pyautogui
            self.pyautogui.hotkey('alt', 'f4')
            return "Janela fechada."
        except:
            return "Erro ao fechar janela."
    
    
    # ==================== ÁREA DE TRANSFERÊNCIA ====================
    
    def copy_to_clipboard(self, text: str) -> str:
        """
        Copia texto para a área de transferência.
        
        Args:
            text: Texto a copiar
        
        Returns:
            str: Resultado da operação
        """
        try:
            import pyperclip
            pyperclip.copy(text)
            return "Copiado para área de transferência."
        except:
            try:
                subprocess.run(['powershell', f'-Command', f'Set-Clipboard -Value "{text}"'], check=True)
                return "Copiado para área de transferência."
            except:
                return "Erro ao copiar para clipboard."
    
    
    # ==================== CONTROLE DE SPOTIFY ====================
    
    def spotify_control(self, action: str) -> str:
        """
        Controla Spotify via teclas de mídia ou abre web.
        
        Args:
            action: 'play', 'pause', 'next', 'previous'
        
        Returns:
            str: Resultado da operação
        """
        try:
            if not self.pyautogui:
                import pyautogui
                self.pyautogui = pyautogui
            
            if action == 'play' or action == 'pause':
                self.pyautogui.press('playpause')
            elif action == 'next':
                self.pyautogui.press('nexttrack')
            elif action == 'previous':
                self.pyautogui.press('prevtrack')
            return f"Spotify: {action}"
        except:
            webbrowser.open("https://open.spotify.com")
            return "Abrindo Spotify Web..."
