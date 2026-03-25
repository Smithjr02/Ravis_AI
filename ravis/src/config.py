# ============================================
# CONFIGURAÇÕES DO ASSISTENTE RAVIS
# ============================================
# Este arquivo centraliza todas as configurações do assistente virtual
# Inclui: IA, interfaces, modelos, prompts, limites de sistema

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional

# --- Caminhos do Projeto (dinâmicos) ---
def get_project_root() -> str:
    """Retorna o diretório raiz do projeto."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = get_project_root()
BIN_DIR = os.path.join(PROJECT_ROOT, 'bin')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
UI_DIR = os.path.join(PROJECT_ROOT, 'ui')
CAPTURES_DIR = os.path.join(UI_DIR, 'assets', 'captures')

for directory in [DATA_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)


# --- Validação de Configurações ---
def validate_range(value: int, min_val: int, max_val: int, name: str) -> int:
    """Valida que um valor está dentro do intervalo esperado."""
    if not min_val <= value <= max_val:
        logging.warning(f'[{name}] Valor {value} fora do intervalo [{min_val}, {max_val}]. Usando {max_val}.')
        return max_val if value > max_val else min_val
    return value


# --- Configurações do Usuário ---
@dataclass
class UserConfig:
    NAME: str = 'Dodo'
    LANGUAGE: str = 'pt-BR'


# --- Configurações de IA ---
@dataclass
class AIConfig:
    MAX_TOKENS: int = 500
    HISTORY_MAX: int = 20
    OLLAMA_URL: str = "http://localhost:11434/api/chat"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    
    def __post_init__(self):
        self.MAX_TOKENS = validate_range(self.MAX_TOKENS, 50, 4096, 'AI_MAX_TOKENS')
        self.HISTORY_MAX = validate_range(self.HISTORY_MAX, 5, 100, 'AI_HISTORY_MAX')


# --- Configurações de Wake Word ---
@dataclass
class WakeWordConfig:
    WORD: str = "ravis"
    ALTERNATIVES: List[str] = field(default_factory=lambda: ["jarvis", "hey ravis", "ei ravis"])
    MODEL: str = "base"
    AUDIO_DURATION: int = 3
    VOICE_THRESHOLD: float = 0.01
    ACTIVATION_COOLDOWN: int = 5
    CONFIDENCE_THRESHOLD: float = -0.5
    
    def __post_init__(self):
        self.AUDIO_DURATION = validate_range(self.AUDIO_DURATION, 1, 10, 'WAKE_WORD_AUDIO_DURATION')
        self.ACTIVATION_COOLDOWN = validate_range(self.ACTIVATION_COOLDOWN, 1, 60, 'WAKE_WORD_ACTIVATION_COOLDOWN')


# --- Configurações de Pesquisa ---
@dataclass
class SearchConfig:
    MAX_RESULTS: int = 5
    TIMEOUT: int = 10
    CACHE_TTL: int = 300
    
    def __post_init__(self):
        self.MAX_RESULTS = validate_range(self.MAX_RESULTS, 1, 20, 'SEARCH_MAX_RESULTS')
        self.TIMEOUT = validate_range(self.TIMEOUT, 3, 60, 'SEARCH_TIMEOUT')
        self.CACHE_TTL = validate_range(self.CACHE_TTL, 60, 3600, 'SEARCH_CACHE_TTL')


# --- Configurações de TTS (Text-to-Speech) ---
@dataclass
class TTSConfig:
    VOICE: str = "pt-BR-AntonioNeural"
    RATE: int = 0
    VOLUME: float = 1.0
    PITCH: int = 0
    
    def __post_init__(self):
        self.RATE = validate_range(self.RATE, -10, 10, 'TTS_RATE')
        self.VOLUME = max(0.0, min(1.0, self.VOLUME))
        self.PITCH = validate_range(self.PITCH, -10, 10, 'TTS_PITCH')


# --- Configurações da Interface Gráfica ---
@dataclass
class WindowConfig:
    WIDTH: int = 500
    HEIGHT: int = 80


@dataclass
class ColorsConfig:
    IDLE: str = "#E6F3FF"
    LISTENING: str = "#4A90D9"
    LISTENING_BG: str = "#B3D9FF"
    SPEAKING: str = "#2ECC71"
    SPEAKING_BG: str = "#A9DFBF"
    PROCESSING: str = "#F39C12"
    PROCESSING_BG: str = "#F9E79F"
    ERROR: str = "#E74C3C"
    ERROR_BG: str = "#F5B7B1"


# --- Configurações de Logging ---
@dataclass
class LoggingConfig:
    LEVEL: int = logging.INFO
    FILE: str = field(default_factory=lambda: os.path.join(LOGS_DIR, 'ravis.log'))
    FORMAT: str = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    MAX_BYTES: int = 10 * 1024 * 1024
    BACKUP_COUNT: int = 5


# --- Tipos de Prompt ---
class PromptTypes:
    CONVERSA: str = 'conversa'
    PESQUISA: str = 'pesquisa'
    ACAO: str = 'acao'
    ANALISE: str = 'analise'


# --- Configurações de Startup ---
@dataclass
class StartupConfig:
    DELAY: int = 3
    ENABLED: bool = False
    
    def __post_init__(self):
        self.DELAY = validate_range(self.DELAY, 1, 30, 'STARTUP_DELAY')


# ============================================
# INSTÂNCIAS GLOBAIS
# ============================================

user = UserConfig()
ai = AIConfig()
wake_word = WakeWordConfig()
search = SearchConfig()
tts = TTSConfig()
window = WindowConfig()
colors = ColorsConfig()
logging_config = LoggingConfig()
startup = StartupConfig()
prompt_types = PromptTypes()


# --- Atalhos para configurações comuns ---
USER_NAME: str = user.NAME
AI_MAX_TOKENS: int = ai.MAX_TOKENS
AI_HISTORY_MAX: int = ai.HISTORY_MAX
OLLAMA_URL: str = ai.OLLAMA_URL
OLLAMA_MODEL: str = ai.OLLAMA_MODEL
WAKE_WORD: str = wake_word.WORD
WAKE_WORD_ALTERNATIVES: List[str] = wake_word.ALTERNATIVES
SEARCH_MAX_RESULTS: int = search.MAX_RESULTS
TTS_VOICE: str = tts.VOICE
WINDOW_WIDTH: int = window.WIDTH
WINDOW_HEIGHT: int = window.HEIGHT
IDLE_COLOR: str = colors.IDLE
LISTENING_COLOR: str = colors.LISTENING
LISTENING_BG: str = colors.LISTENING_BG


# ============================================
# VARIÁVEIS DE AMBIENTE (.env)
# ============================================
# Variáveis que devem estar no arquivo .env:
#
# GROQ_API_KEY=gsk_...          - Chave da API Groq
# GEMINI_API_KEY=AIza...        - Chave da API Gemini
# TAVILY_API_KEY=tvly-...       - Chave da API Tavily
# SERPER_API_KEY=...            - Chave da API Serper
# SEARXNG_URL=http://localhost:8080  - URL do SearxNG
# OPENROUTER_API_KEY=sk-or-...  - Chave da API OpenRouter
# PYTHONDONTWRITEBYTECODE=1     - Não criar arquivos .pyc
# SEARCH_TIMEOUT=10             - Timeout de pesquisa em segundos
# SEARCH_CACHE_TTL=300          - TTL do cache de pesquisa
# STARTUP_DELAY=3               - Delay ao iniciar com Windows


def load_config():
    """Carrega configurações do ambiente."""
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    # Atualizar search config do .env
    search.TIMEOUT = int(os.getenv('SEARCH_TIMEOUT', search.TIMEOUT))
    search.CACHE_TTL = int(os.getenv('SEARCH_CACHE_TTL', search.CACHE_TTL))
    startup.DELAY = int(os.getenv('STARTUP_DELAY', startup.DELAY))
    
    logging.info('[CONFIG] Configurações carregadas')


def setup_logging():
    """Configura o sistema de logging."""
    from logging.handlers import RotatingFileHandler
    
    handler = RotatingFileHandler(
        logging_config.FILE,
        maxBytes=logging_config.MAX_BYTES,
        backupCount=logging_config.BACKUP_COUNT,
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(logging_config.FORMAT))
    
    logging.root.addHandler(handler)
    logging.root.setLevel(logging_config.LEVEL)
    
    logging.info('[CONFIG] Logging configurado')


def get_status() -> dict:
    """Retorna status de todas as configurações."""
    return {
        'user': {
            'name': user.NAME,
            'language': user.LANGUAGE
        },
        'ai': {
            'max_tokens': ai.MAX_TOKENS,
            'history_max': ai.HISTORY_MAX,
            'model': ai.OLLAMA_MODEL
        },
        'wake_word': {
            'word': wake_word.WORD,
            'alternatives': wake_word.ALTERNATIVES,
            'cooldown': wake_word.ACTIVATION_COOLDOWN
        },
        'search': {
            'max_results': search.MAX_RESULTS,
            'timeout': search.TIMEOUT,
            'cache_ttl': search.CACHE_TTL
        },
        'paths': {
            'root': PROJECT_ROOT,
            'bin': BIN_DIR,
            'data': DATA_DIR,
            'logs': LOGS_DIR,
            'ui': UI_DIR
        }
    }
