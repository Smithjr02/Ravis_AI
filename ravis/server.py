# ============================================
# SERVIDOR FASTAPI DO RAVIS
# ============================================
# Propósito: Servidor web principal do assistente virtual Ravis
#
# Funcionalidades:
#   - API REST para chat, status, sistema
#   - WebSocket para streaming em tempo real
#   - Upload de arquivos
#   - TTS (Edge)
#   - Visão computacional
#   - Captura de tela
#
# Endpoints principais:
#   - GET /: Interface principal
#   - POST /chat: Chat com IA
#   - GET /status: Status do sistema
#   - POST /speak: TTS
#   - WebSocket /ws: Streaming
#
# Porta: 8000
# ============================================

import os
import sys
import threading
import time
import json
import traceback
import asyncio
import tempfile
from datetime import datetime
from typing import Optional

# Redireciona cache Python para data/
pycache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '__pycache__')
os.environ['PYTHONPYCACHEPREFIX'] = pycache_dir
os.makedirs(pycache_dir, exist_ok=True)

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Carrega .env
from dotenv import load_dotenv
load_dotenv('.env')

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# ============================================
# SISTEMA DE LOGGING
# ============================================

def get_timestamp():
    """Retorna timestamp formatado"""
    return datetime.now().strftime("%H:%M:%S")

async def _broadcast_log(level: str, message: str):
    """Transmite log para o frontend se houver conexões ativas"""
    try:
        await log_broadcaster.broadcast_if_active(level, message)
    except:
        pass  # Silencioso se não conseguir transmitir

def log_request(method: str, path: str, ip: str, body: Optional[str] = None):
    """Log de requisição recebida"""
    if body and len(body) > 100:
        body = body[:100] + "..."
    body_str = f"\n    BODY: '{body}'" if body else ""
    msg = f"--> {method} {path} | IP: {ip}"
    print(f"[{get_timestamp()}] {msg}{body_str}")
    # Transmite para frontend
    asyncio.create_task(_broadcast_log("info", msg))

def log_response(status: int, path: str, duration: float, bytes_size: int = 0):
    """Log de resposta enviada"""
    msg = f"<-- {status} {path} | {bytes_size} bytes | {duration:.3f}s"
    print(f"[{get_timestamp()}] {msg}")
    asyncio.create_task(_broadcast_log("info", msg))

def log_error(path: str, error: Exception):
    """Log de erro com traceback"""
    tb = traceback.format_exc()
    msg = f"[ERROR] {path} | {type(error).__name__}: {str(error)}"
    print(f"[{get_timestamp()}] {msg}")
    print(f"[{get_timestamp()}]   Traceback:\n{tb}")
    asyncio.create_task(_broadcast_log("error", msg))

def log_websocket(event: str, ip: str = "", extra: str = ""):
    """Log de eventos WebSocket"""
    extra_str = f" | {extra}" if extra else ""
    msg = f"[WS] {event}{extra_str} | IP: {ip}"
    print(f"[{get_timestamp()}] {msg}")
    asyncio.create_task(_broadcast_log("info", msg))

def log_static(path: str, status: int, duration: float):
    """Log de arquivo estático"""
    msg = f"[STATIC] GET {path} -> {status} ({duration*1000:.1f}ms)"
    print(f"[{get_timestamp()}] {msg}")

def log_search(provider: str, results: int, duration: float):
    """Log de busca"""
    msg = f"SEARCH: {provider} -> {results} resultados ({duration:.3f}s)"
    print(f"[{get_timestamp()}]   {msg}")
    asyncio.create_task(_broadcast_log("info", msg))

def log_ai(provider: str, model: str, duration: float):
    """Log de IA"""
    msg = f"AI: {provider} {model} ({duration:.3f}s)"
    print(f"[{get_timestamp()}]   {msg}")
    asyncio.create_task(_broadcast_log("info", msg))

def log_router(category: str, duration: float):
    """Log de categorização"""
    msg = f"ROUTER: {category} ({duration:.3f}s)"
    print(f"[{get_timestamp()}]   {msg}")

# ============================================
# LOG BROADCASTER - Transmite logs para frontend
# ============================================

class LogBroadcaster:
    """Transmite logs em tempo real para todos os clientes WebSocket conectados"""
    
    def __init__(self):
        self.connections = set()
    
    def add(self, websocket):
        self.connections.add(websocket)
    
    def remove(self, websocket):
        self.connections.discard(websocket)
    
    async def broadcast(self, level: str, message: str):
        """Envia log para todos os clientes conectados"""
        timestamp = get_timestamp()
        for ws in list(self.connections):
            try:
                await ws.send_json({
                    "type": "log",
                    "level": level,
                    "message": message,
                    "timestamp": timestamp
                })
            except:
                self.remove(ws)
    
    async def broadcast_if_active(self, level: str, message: str):
        """Envia log apenas se houver conexões ativas"""
        if self.connections:
            await self.broadcast(level, message)

log_broadcaster = LogBroadcaster()

# ============================================
# VARIÁVEIS GLOBAIS E ESTADO DO SERVIDOR
# ============================================

# Tempo de início do servidor (para logging de uptime)
start_time = time.time()

# Contador de comandos processados nesta sessão
commands_count = 0

# Status dos periféricos
mic_active = False      # Microfone ativo?
camera_active = False   # Câmera ativa?

# Import módulos
from src.core.vision import capture_region, analyze_image, get_latest_capture, scan_tela_completa
from src.modules.hotkeys import start_global_hotkeys, get_global_hotkeys
import threading

# WebSocket global para envio de vision results
_websocket_instance = None

def set_websocket(ws):
    """Define a instância global do WebSocket para envio de mensagens"""
    global _websocket_instance
    _websocket_instance = ws

def _hotkey_screen_capture_callback():
    """Callback chamado quando PrintScreen é pressionado globalmente"""
    print('[Server] PrintScreen detectado - iniciando seleção!', flush=True)
    
    try:
        from src.core.vision import capturar_tela, analyze_image, get_latest_capture
        
        print('[Server] Chamando capturar_tela()...', flush=True)
        caminho = capturar_tela()
        
        if not caminho:
            print('[Server] Captura cancelada ou falhou', flush=True)
            return
        
        print(f'[Server] Captura realizada: {caminho}', flush=True)
        
        analise = analyze_image()
        
        if analise.get('success'):
            # Resumir o texto com IA
            texto_resumido = resumir_texto(analise['text'])
            
            if _websocket_instance:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_websocket_instance.send_json({
                        "type": "vision_result",
                        "text": texto_resumido
                    }))
                except Exception as e:
                    print(f'[Server] Erro ao enviar via WS: {e}', flush=True)
                finally:
                    loop.close()
        else:
            print(f'[Server] Erro na análise: {analise}', flush=True)
                    
    except Exception as e:
        print(f'[Server] Erro na seleção: {e}', flush=True)

# Iniciar hotkeys globais em thread separada
def _start_hotkeys_thread():
    """Inicia os hotkeys globais em thread separada"""
    try:
        hotkeys = get_global_hotkeys()
        hotkeys.register_callback('screen_capture', _hotkey_screen_capture_callback)
        hotkeys.start()
        print('[Server] Hotkeys globais iniciados! (pressione PrintScreen em qualquer janela)')
    except Exception as e:
        print(f'[Server] Erro ao iniciar hotkeys: {e}')

# Iniciar hotkeys automaticamente
_hotkeys_thread = threading.Thread(target=_start_hotkeys_thread, daemon=True)
_hotkeys_thread.start()

# ============================================
# LIMITES DE SEGURANÇA
# ============================================
# Evita processamento de entradas mal-intencionadas ou muito grandes

MAX_CHAT_TEXT_LENGTH = 4000    # Máx 4000 caracteres para mensagens de chat
MAX_SPEAK_TEXT_LENGTH = 1000   # Máx 1000 caracteres para TTS (síntese de fala)

# ============================================
# INSTÂNCIAS SINGLETONS (LAZY LOADING)
# ============================================
# Inicializam apenas quando primeiro requisitadas
# Evita overhead no início do servidor

_ai_instance = None       # Singleton: AI (inteligência artificial)
_intent_instance = None   # Singleton: Intent (reconhecimento de intenção)

# Cache de HTMLs estáticos (servidos repetidamente)
_html_cache = {}

# ============================================
# FUNÇÕES DE ACESSO AOS SINGLETONS
# ============================================

def get_ai():
    """Retorna instância singleton de AI (lazy initialization)"""
    global _ai_instance
    if _ai_instance is None:
        from src.core.ai import AI
        _ai_instance = AI()
    return _ai_instance

def resumir_texto(texto: str) -> str:
    """Resume o texto usando IA para ser mais objetivo
    
    Args:
        texto: Texto original da análise
    
    Returns:
        Texto resumido e objetivo
    """
    try:
        ai = get_ai()
        
        prompt_resumo = f"""Você é um assistente que resume análises de imagens.
Extraia os PONTOS PRINCIPAIS da análise abaixo de forma clara e objetiva.

Para cada ponto importante:
- Seja específico sobre o que foi identificado
- Inclua detalhes relevantes
- Mantenha clareza

Análise Original:
{texto}

Forneça um resumo estruturado com os pontos mais importantes em 3-4 frases."""
        
        resposta = ai.chat(prompt_resumo)
        return resposta.strip()
    except Exception as e:
        print(f"[Server] ERRO no resumo: {e}", flush=True)
        import traceback
        traceback.print_exc()
        # Se falhar, retorna texto original truncado
        resultado = texto[:200] + "..." if len(texto) > 200 else texto
        print(f"[Server] Usando fallback truncado: {resultado}", flush=True)
        return resultado

def get_intent():
    """Retorna instância singleton de Intent (lazy initialization)"""
    global _intent_instance
    if _intent_instance is None:
        from src.core.intent import Intent
        _intent_instance = Intent()
    return _intent_instance

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(title="Ravis API", docs=None, redoc=None)

# Exception handler para silenciar logs de 404
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "not found"})

# Servir arquivos estáticos da pasta ui/
ui_path = os.path.join(os.path.dirname(__file__), "ui")
if os.path.exists(ui_path):
    app.mount("/static", StaticFiles(directory=ui_path), name="static")

# Servir arquivos da pasta assets (para modelos 3D)
assets_path = os.path.join(os.path.dirname(__file__), "ui", "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("[SERVER] FastAPI inicializado com logging completo")

# ==================== ROTAS ====================

@app.get("/")
async def serve_html(request: Request):
    """Serve o index.html com cache"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    if "index" not in _html_cache:
        html_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            _html_cache["index"] = f.read()
    
    log_request("GET", "/", ip)
    response = HTMLResponse(_html_cache["index"])
    log_response(200, "/", time.time() - start, len(_html_cache["index"]))
    return response

@app.get("/favicon.ico")
async def serve_favicon(request: Request):
    """Serve o favicon.ico"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    log_request("GET", "/favicon.ico", ip)
    
    favicon_path = os.path.join(os.path.dirname(__file__), "ui", "favicon.ico")
    if os.path.exists(favicon_path):
        response = FileResponse(favicon_path)
        log_response(200, "/favicon.ico", time.time() - start)
        return response
    
    from fastapi.responses import Response
    response = Response(
        content=b'\x00\x00\x01\x00\x01\x00\x01\x01\x00\x00\x01\x00\x18\x00\x30\x00\x00\x00\x16\x00\x00\x00\x28\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x00\x18\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        media_type='image/x-icon'
    )
    log_response(200, "/favicon.ico", time.time() - start)
    return response

# ==================== ROTA: UPLOAD DE ARQUIVO ====================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Recebe arquivo anexado e extrai texto"""
    import io
    
    filename = (file.filename or "unknown").lower()
    content = ""
    file_type = "desconhecido"
    
    try:
        # Lê o conteúdo do arquivo
        file_content = await file.read()
        
        # Limita tamanho do arquivo (10MB)
        max_size = 10 * 1024 * 1024
        if len(file_content) > max_size:
            return {"success": False, "error": f"Arquivo muito grande. Máximo: 10MB (arquivo: {len(file_content)//1024}KB)"}
        
        # Processa berdasarkan tipo
        if filename.endswith('.txt'):
            file_type = "texto"
            content = file_content.decode('utf-8', errors='ignore')
            
        elif filename.endswith('.pdf'):
            file_type = "PDF"
            try:
                import PyPDF2
                with io.BytesIO(file_content) as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    for page in reader.pages:
                        content += page.extract_text() + "\n"
            except ImportError:
                content = f"[PDF] {filename} - PyPDF2 não instalado. Instale com: pip install PyPDF2"
            except Exception as e:
                content = f"[PDF] Erro ao ler {filename}: {str(e)}"
                
        elif filename.endswith('.docx'):
            file_type = "Word"
            try:
                from docx import Document
                with io.BytesIO(file_content) as doc_file:
                    doc = Document(doc_file)
                    for para in doc.paragraphs:
                        content += para.text + "\n"
            except ImportError:
                content = f"[DOCX] {filename} - python-docx não instalado. Instale com: pip install python-docx"
            except Exception as e:
                content = f"[DOCX] Erro ao ler {filename}: {str(e)}"
                
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            file_type = "imagem"
            try:
                from src.core.vision import analyze_image
                
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, f"upload_{filename}")
                with open(temp_path, 'wb') as f:
                    f.write(file_content)
                
                # Analisa com IA de visão
                result = analyze_image(temp_path)
                content = result.get('text', result.get('error', 'Erro desconhecido'))
                
                # Remove arquivo temporário
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
            except Exception as e:
                content = f"[IMAGEM] Erro ao analisar {filename}: {str(e)}"
            
        else:
            content = f"[ARQUIVO] {filename} - Tipo não suportado para extração de texto."
            
        # Limita tamanho do conteúdo
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[... conteúdo truncado ({len(content)} caracteres)]"
            
        return {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "content": content.strip()
        }
        
    except Exception as e:
        log_error("/upload", e)
        return {"success": False, "error": str(e)}
# Endpoint REST tradicional para chat (single resposta)
# URL: POST http://localhost:8000/chat
# Payload: {"text": "ola ravis"} ou {"message": "ola ravis"}
# Retorna: {"response": "...", "type": "conversa|pesquisa|acao"}

@app.post("/chat")
async def chat(request: Request):
    """Recebe mensagem e retorna resposta da IA"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        message = json.loads(body_str)
        # Aceita tanto "text" quanto "message" como chave
        text = message.get("text", "") or message.get("message", "")
        if isinstance(text, str):
            text = text.strip()
        else:
            text = ""
        log_request("POST", "/chat", ip, text)
    except Exception as e:
        text = ""
        log_request("POST", "/chat", ip)
        log_error("/chat", e)

    # Validação robusta de tamanho e tipo de texto
    if not text or not isinstance(text, str):
        return {"response": "Mensagem vazia ou inválida.", "type": "error"}
    if len(text) > MAX_CHAT_TEXT_LENGTH:
        msg = "Sua mensagem é muito longa. Tente resumir o que você quer perguntar."
        log_error("/chat", ValueError("Texto de chat excedeu limite máximo"))
        return {"response": msg, "type": "error"}
    
    global commands_count
    commands_count += 1
    
    try:
        ai = get_ai()
        intent = get_intent()
        
        # Intent processing
        intent_start = time.time()
        intent_type, intent_result = intent.process(text)
        log_router(intent_type if intent_type else "conversa", time.time() - intent_start)
        
        resposta = ""
        
        if intent_type == 'acao':
            if intent_result:
                resposta = intent_result
            else:
                short_responses = ['sim', 'não', 'nao', 'ok', 'beleza', 'blz', 'valeu', 'oi', 'ola', 'eai', 'oii', 'eu', 'tu', 'ele', 'ela', 'a', 'e', 'o', 'mas', 'porque', 'pq', 'como', 'o que', 'oque', 'quem', 'onde', 'quando', 'quer', 'quero', 'pode', 'poderia']
                continuation_words = ['mais', 'outra', 'outro', 'de novo', 'repete', 'e aí', 'e depois', 'depois', 'então', 'mas', 'porém', 'só', 'também', 'inclusive', 'ademais']
                is_short = len(text.strip().split()) <= 2
                has_continuation = any(w in text.lower() for w in continuation_words)
                
                if is_short or has_continuation:
                    print(f"[SERVER] Mensagem ambígua ou continuação → passando para IA (texto: '{text}')")
                    intent_type = 'conversa'
                    ai_start = time.time()
                    resposta = ""
                    for chunk in ai.chat_stream(text, include_history=True, tipo='conversa'):
                        resposta += chunk
                    log_ai("Ollama/Groq", "conversa", time.time() - ai_start)
                else:
                    resposta = "Ação executada."
            
        elif intent_type == 'pesquisa':
            search_start = time.time()
            resposta = ai.chat_with_search(text, intent_result)
            log_search("Tavily/SearX", 5, time.time() - search_start)
            
        else:
            tipo = intent_type if intent_type else 'conversa'
            ai_start = time.time()
            resposta = ""
            for chunk in ai.chat_stream(text, tipo=tipo):
                resposta += chunk
            log_ai("Ollama/Groq", tipo, time.time() - ai_start)
        
        response_data = {"response": resposta, "type": intent_type}
        response_json = json.dumps(response_data)
        log_response(200, "/chat", time.time() - start, len(response_json))
        return response_data
        
    except Exception as e:
        log_error("/chat", e)
        return {"response": f"Erro: {str(e)}", "type": "error"}

# ==================== STATUS ====================

# Cache de temperatura (atualiza a cada 30 segundos)
_temp_cache = {
    'cpu_temp': None,
    'gpu_temp': None,
    'gpu_name': None,
    'last_update': 0
}
TEMP_CACHE_DURATION = 30

def get_cpu_temp():
    """Obtém temperatura da CPU - múltiplas tentativas"""
    import time
    current_time = time.time()
    
    if (_temp_cache['cpu_temp'] is not None and 
        current_time - _temp_cache['last_update'] < TEMP_CACHE_DURATION):
        return _temp_cache['cpu_temp']
    
    try:
        import subprocess
        result = subprocess.run(
            ['wmic', '/namespace:\\\\root\\wmi', 'path', 
             'MSAcpi_ThermalZoneTemperature', 'get', 'CurrentTemperature'],
            capture_output=True, text=True, timeout=2
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2 and lines[1].strip().isdigit():
            temp_kelvin = int(lines[1].strip()) / 10.0
            cpu_temp = int(temp_kelvin - 273.15)
            _temp_cache['cpu_temp'] = cpu_temp
            _temp_cache['last_update'] = current_time
            return cpu_temp
    except:
        pass
    
    _temp_cache['cpu_temp'] = None
    return None

def get_gpu_info():
    """Obtém info da GPU via wmic"""
    import time
    current_time = time.time()
    
    gpu_name = _temp_cache.get('gpu_name')
    gpu_temp = _temp_cache.get('gpu_temp')
    
    if (gpu_name and current_time - _temp_cache['last_update'] < TEMP_CACHE_DURATION):
        return gpu_name, gpu_temp
    
    try:
        import subprocess
        result = subprocess.run(
            ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
            capture_output=True, text=True, timeout=2
        )
        lines = result.stdout.replace('\r\n', '\n').replace('\r', '\n').strip().split('\n')
        lines = [l.strip() for l in lines if l.strip()]
        if len(lines) >= 2:
            gpu_name = lines[1].strip()
    except:
        pass
    
    _temp_cache['gpu_name'] = gpu_name
    _temp_cache['gpu_temp'] = None
    _temp_cache['last_update'] = current_time
    
    return gpu_name, gpu_temp

@app.get("/status")
async def get_status(request: Request):
    """
    Retorna status do sistema em tempo real
    
    Resposta inclui:
    - CPU %: Percentual de uso do processador
    - RAM %: Percentual de uso de memória
    - Disco %: Percentual de uso do disco
    - Temp CPU: Temperatura do processador (°C)
    - Temp GPU: Temperatura da placa de vídeo (°C) 
    - Nome GPU: Nome da placa de vídeo detectada
    - Uptime: Tempo que o servidor está rodando (Xh Ymin)
    - Comandos: Total de comandos processados nesta sessão
    """
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    log_request("GET", "/status", ip)
    
    global commands_count
    
    import psutil
    
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    ram_percent = memory.percent

    # Uso de disco – tenta detectar unidade do sistema e trata falhas
    try:
        system_drive = os.environ.get("SYSTEMDRIVE", "C:")
        disk = psutil.disk_usage(system_drive + '\\')
        disk_percent = disk.percent
    except Exception:
        disk_percent = None
    
    cpu_temp = get_cpu_temp()
    gpu_name, gpu_temp = get_gpu_info()
    
    uptime_seconds = int(time.time() - start_time)
    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    uptime_str = f"{hours}h {minutes}min"
    
    response_data = {
        "cpu": cpu_percent,
        "ram": ram_percent,
        "disk": disk_percent,
        "cpu_temp": cpu_temp,
        "gpu_temp": gpu_temp,
        "gpu_name": gpu_name,
        "uptime": uptime_str,
        "commands": commands_count,
        "mic_active": mic_active,
        "camera_active": camera_active,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    
    response_json = json.dumps(response_data)
    log_response(200, "/status", time.time() - start, len(response_json))
    
    return response_data

# ==================== SYSTEM INFO (Widgets) ====================

# Cache de velocidade de rede
_net_cache = {
    'bytes_sent': 0,
    'bytes_recv': 0,
    'last_time': 0,
    'download_speed': 0,
    'upload_speed': 0,
    'connection_type': None,  # 'wifi', 'ethernet', ou None
    'connection_name': None,    # Nome da rede ou "Ethernet"
    'ping': 0
}
_PING_HOST = "8.8.8.8"

def get_network_info():
    """Detecta tipo de conexão (WiFi ou Ethernet)"""
    import subprocess
    
    # Primeiro tenta WiFi
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout
        if "SSID" in output:
            for line in output.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    ssid = line.split(":", 1)[1].strip() if ":" in line else "WiFi"
                    return 'wifi', ssid if ssid else "WiFi"
    except:
        pass
    
    # Se não tem WiFi, verifica Ethernet
    try:
        result = subprocess.run(
            ['netsh', 'interface', 'show', 'interface'],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout
        lines = output.split('\n')
        for line in lines:
            if 'Ethernet' in line or 'LAN' in line or 'Gigabit' in line:
                if 'Connected' in line or 'Conectado' in line:
                    return 'ethernet', 'Ethernet'
    except:
        pass
    
    # Verifica se tem alguma conexão de rede ativa
    try:
        import psutil
        net_if = psutil.net_if_stats()
        for iface, stats in net_if.items():
            if stats.isup and iface != 'Loopback Pseudo-Interface 1':
                if 'Wi-Fi' in iface or 'Wireless' in iface:
                    return 'wifi', iface
                elif 'Ethernet' in iface or 'LAN' in iface:
                    return 'ethernet', 'Ethernet'
        # Se tem qualquer interface ativa
        for iface, stats in net_if.items():
            if stats.isup and iface != 'Loopback':
                return 'ethernet', 'Ethernet'
    except:
        pass
    
    return None, "Sem conexão"

@app.get("/system-info")
async def get_system_info(request: Request):
    """
    Retorna informações adicionais do sistema para widgets
    
    Inclui:
    - Rede: Tipo (WiFi/Ethernet), velocidade, ping
    - Música: Player ativo e música tocando
    - Discos: Uso de cada partição
    """
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    log_request("GET", "/system-info", ip)
    
    try:
        import psutil
        
        current_time = time.time()
        
        # Rede - Velocidade (síncrono, rápido)
        net_io = psutil.net_io_counters()
        
        if _net_cache['last_time'] > 0:
            time_diff = current_time - _net_cache['last_time']
            if time_diff > 0:
                bytes_recv_diff = net_io.bytes_recv - _net_cache['bytes_recv']
                bytes_sent_diff = net_io.bytes_sent - _net_cache['bytes_sent']
                _net_cache['download_speed'] = round((bytes_recv_diff / time_diff) / 1024 / 1024, 1)
                _net_cache['upload_speed'] = round((bytes_sent_diff / time_diff) / 1024 / 1024, 1)
        
        _net_cache['bytes_recv'] = net_io.bytes_recv
        _net_cache['bytes_sent'] = net_io.bytes_sent
        _net_cache['last_time'] = current_time
        
        # Tipo de conexão (WiFi ou Ethernet) - verifica a cada 60 segundos
        if _net_cache['connection_type'] is None or (current_time - _net_cache.get('_conn_last_check', 0)) > 60:
            conn_type, conn_name = get_network_info()
            _net_cache['connection_type'] = conn_type
            _net_cache['connection_name'] = conn_name
            _net_cache['_conn_last_check'] = current_time
        
        # Ping - cache por 30 segundos
        if _net_cache.get('_ping_last_check', 0) == 0 or (current_time - _net_cache.get('_ping_last_check', 0)) > 30:
            ping_result = await asyncio.to_thread(_get_ping)
            _net_cache['ping'] = ping_result
            _net_cache['_ping_last_check'] = current_time
        else:
            ping_result = _net_cache.get('ping', None)
        
        # Música e discos em paralelo
        music_result, disks_result = await asyncio.gather(
            asyncio.to_thread(get_current_music),
            asyncio.to_thread(_get_disks)
        )
        
        response_data = {
            "connection_type": _net_cache['connection_type'],
            "connection_name": _net_cache['connection_name'],
            "download": _net_cache['download_speed'],
            "upload": _net_cache['upload_speed'],
            "ping": _net_cache['ping'],
            "disks": disks_result,
            "music": music_result,
        }
        
        response_json = json.dumps(response_data)
        log_response(200, "/system-info", time.time() - start, len(response_json))
        
        return response_data
    
    except Exception as e:
        log_error("/system-info", e)
        return {
            "connection_type": None,
            "connection_name": "Erro",
            "download": 0,
            "upload": 0,
            "ping": 0,
            "disks": [],
            "music": None,
        }

def _get_ping() -> int:
    """Executa ping em thread separada"""
    try:
        import subprocess
        result = subprocess.run(
            ['ping', '-n', '1', '-w', '1000', _PING_HOST],
            capture_output=True, text=True, timeout=2
        )
        output = result.stdout
        if "time=" in output or "tempo=" in output:
            for line in output.split('\n'):
                if "time=" in line.lower():
                    ping_str = line.lower().split("time=")[1].split()[0]
                    return int(float(ping_str))
                elif "tempo=" in line.lower():
                    ping_str = line.lower().split("tempo=")[1].split()[0]
                    return int(float(ping_str))
    except:
        pass
    return 0

def _get_disks() -> list:
    """Obtém informações dos discos em thread separada"""
    import psutil
    disks = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_name = partition.device
            if len(disk_name) == 2 and disk_name.endswith(':'):
                disk_label = f"Disco ({disk_name})"
            else:
                disk_label = partition.mountpoint
            disks.append({
                "name": disk_label,
                "total": round(usage.total / (1024**3), 1),
                "used": round(usage.used / (1024**3), 1),
                "free": round(usage.free / (1024**3), 1),
                "percent": usage.percent
            })
        except:
            pass
    return disks

def get_current_music():
    """Tenta detectar música tocando"""
    try:
        import subprocess
        
        # Tenta Spotify
        try:
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-Process -Name Spotify -ErrorAction SilentlyContinue | '
                 'Where-Object {$_.MainWindowTitle -ne \"\"} | '
                 'Select-Object -ExpandProperty MainWindowTitle'],
                capture_output=True, text=True, timeout=2
            )
            if result.stdout.strip():
                title = result.stdout.strip()
                if " - " in title:
                    artist, song = title.rsplit(" - ", 1)
                    return {"app": "Spotify", "artist": artist.strip(), "song": song.strip(), "playing": True}
                return {"app": "Spotify", "song": title.strip(), "playing": True}
        except:
            pass
        
        # Tenta qualquer player de áudio
        players = ["Spotify", "WMPlayer", "Music", "VLC"]
        for player in players:
            try:
                result = subprocess.run(
                    ['powershell', '-Command', 
                     f'Get-Process -Name \"{player}\" -ErrorAction SilentlyContinue | '
                     'Where-Object {$_.MainWindowTitle -ne \"\"} | '
                     'Select-Object -First 1 -ExpandProperty MainWindowTitle'],
                    capture_output=True, text=True, timeout=2
                )
                if result.stdout.strip():
                    return {"app": player, "song": result.stdout.strip(), "playing": True}
            except:
                continue
        
        return None
    except:
        return None

# ==================== WEATHER ====================

@app.get("/weather")
async def get_weather(request: Request):
    """Retorna clima de Nilópolis RJ"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    log_request("GET", "/weather", ip)
    
    try:
        import requests
        
        lat = -22.90
        lon = -43.40
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        
        search_start = time.time()
        response = requests.get(url, timeout=5)
        log_search("Open-Meteo", 1, time.time() - search_start)
        
        data = response.json()
        current = data.get("current", {})
        
        temp = current.get("temperature_2m", 0)
        humidity = current.get("relative_humidity_2m", 0)
        wind = current.get("wind_speed_10m", 0)
        feel = current.get("apparent_temperature", 0)
        
        response_data = {
            "temperature": temp,
            "humidity": humidity,
            "wind": wind,
            "feels_like": feel,
            "location": "Nilópolis, RJ",
            "timestamp": datetime.now().strftime("%H:%M")
        }
        
        response_json = json.dumps(response_data)
        log_response(200, "/weather", time.time() - start, len(response_json))
        return response_data
        
    except Exception as e:
        log_error("/weather", e)
        return {"error": str(e)}

# ==================== COMPUTER ====================

@app.post("/computer")
async def computer_action(request: Request):
    """Executa ação no computador"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        action = json.loads(body_str)
        log_request("POST", "/computer", ip, body_str)
    except:
        action = {}
        log_request("POST", "/computer", ip)
    
    try:
        from src.modules.computer import Computer
        
        computer = Computer()
        
        action_type = action.get("type", "")
        
        if action_type == "open_app":
            app_name = action.get("app", "")
            result = computer.open_app(app_name)
            response_data = {"success": True, "result": result}
            
        elif action_type == "open_url":
            url = action.get("url", "")
            result = computer.open_url(url)
            response_data = {"success": True, "result": result}
            
        elif action_type == "toggle_mic":
            global mic_active
            mic_active = not mic_active
            response_data = {"success": True, "active": mic_active}
            
        elif action_type == "toggle_camera":
            global camera_active
            camera_active = not camera_active
            response_data = {"success": True, "active": camera_active}
            
        elif action_type == "screenshot":
            import subprocess
            import os
            from datetime import datetime
            screenshot_dir = os.path.join(os.path.dirname(__file__), "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(screenshot_dir, filename)
            subprocess.run(['powershell', '-Command', f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds | ForEach-Object {{ $bmp = New-Object System.Drawing.Bitmap $_.Height); $g = [System.Drawing.Graphics]::FromImage($bmp);($_.Width, $g.CopyFromScreen($_.Location, [System.Drawing.Point]::Empty, $_.Size); $bmp.Save(\"{filepath}\"); $g.Dispose(); $bmp.Dispose() }}'], capture_output=True)
            response_data = {"success": True, "path": filepath, "filename": filename}
            
        elif action_type == "open_explorer":
            import subprocess
            subprocess.Popen('explorer')
            response_data = {"success": True, "result": "Explorador aberto"}
            
        elif action_type == "open_settings":
            import subprocess
            subprocess.Popen(['start', 'ms-settings:'], shell=True)
            response_data = {"success": True, "result": "Configurações abertas"}
            
        else:
            response_data = {"success": False, "error": "Ação desconhecida"}
        
        response_json = json.dumps(response_data)
        log_response(200, "/computer", time.time() - start, len(response_json))
        return response_data
        
    except Exception as e:
        log_error("/computer", e)
        return {"success": False, "error": str(e)}

# ==================== CONVERSATIONS ====================

@app.post("/conversation/save")
async def save_conversation(request: Request):
    """Salva uma conversa no disco"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        data = json.loads(body_str)
        log_request("POST", "/conversation/save", ip)
    except:
        data = {}
        log_request("POST", "/conversation/save", ip)
    
    try:
        titulo = data.get("titulo", "Nova conversa")
        mensagens = data.get("mensagens", [])
        
        # Cria diretório se não existir
        conv_dir = os.path.join(os.path.dirname(__file__), "conversations")
        os.makedirs(conv_dir, exist_ok=True)
        
        # Gera ID único
        conv_id = str(int(time.time() * 1000))
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Formato do arquivo
        conv_data = {
            "id": conv_id,
            "titulo": titulo[:50] if titulo else "Nova conversa",
            "data": data_formatada,
            "mensagens": mensagens
        }
        
        # Salva arquivo
        filepath = os.path.join(conv_dir, f"{conv_id}.json")
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)
        
        log_response(200, "/conversation/save", time.time() - start)
        return {"success": True, "id": conv_id, "path": filepath}
    
    except Exception as e:
        log_error("/conversation/save", e)
        return {"success": False, "error": str(e)}


@app.get("/conversation/list")
async def list_conversations():
    """Lista todas as conversas salvas"""
    try:
        conv_dir = os.path.join(os.path.dirname(__file__), "conversations")
        
        if not os.path.exists(conv_dir):
            return []
        
        conversas = []
        for filename in os.listdir(conv_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(conv_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        conversas.append({
                            "id": data.get("id", filename.replace('.json', '')),
                            "titulo": data.get("titulo", "Sem título"),
                            "data": data.get("data", ""),
                            "totalMensagens": len(data.get("mensagens", []))
                        })
                except:
                    continue
        
        # Ordena por data (mais recente primeiro)
        conversas.sort(key=lambda x: x["id"], reverse=True)
        return conversas
    
    except Exception as e:
        log_error("/conversation/list", e)
        return []


@app.get("/conversation/{conv_id}")
async def get_conversation(conv_id: str):
    """Retorna uma conversa pelo ID"""
    try:
        conv_dir = os.path.join(os.path.dirname(__file__), "conversations")
        filepath = os.path.join(conv_dir, f"{conv_id}.json")
        
        if not os.path.exists(filepath):
            return {"error": "Conversa não encontrada"}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    except Exception as e:
        log_error(f"/conversation/{conv_id}", e)
        return {"error": str(e)}


@app.delete("/conversation/{conv_id}")
async def delete_conversation(conv_id: str):
    """Deleta uma conversa pelo ID"""
    try:
        conv_dir = os.path.join(os.path.dirname(__file__), "conversations")
        filepath = os.path.join(conv_dir, f"{conv_id}.json")
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "Conversa não encontrada"}
        
        os.remove(filepath)
        return {"success": True, "deleted": conv_id}
    
    except Exception as e:
        log_error(f"/conversation/{conv_id} (DELETE)", e)
        return {"success": False, "error": str(e)}

# ==================== TTS ====================

@app.post("/speak")
async def speak(request: Request):
    """Gera áudio TTS usando edge-tts"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
        message = json.loads(body_str)
        # Aceita tanto "text" quanto "message" como chave
        text = message.get("text", "") or message.get("message", "")
        if isinstance(text, str):
            text = text.strip()
        else:
            text = ""
        log_request("POST", "/speak", ip, text[:50] if text else "")
    except Exception as e:
        log_request("POST", "/speak", ip)
        log_error("/speak", e)
        text = ""
    
    if not text:
        log_error("/speak", ValueError("Texto vazio"))
        return {"error": "Texto vazio. Forneça 'text' ou 'message' no corpo da requisição."}
    if len(text) > MAX_SPEAK_TEXT_LENGTH:
        msg = "O texto para fala é muito longo. Tente usar frases mais curtas."
        log_error("/speak", ValueError("Texto de TTS excedeu limite máximo"))
        return {"error": msg}
    
    try:
        import edge_tts
        import io
        
        # Voz JARVIS-style: mais lenta e grave (pt-BR)
        communicate = edge_tts.Communicate(
            text,
            voice='pt-BR-AntonioNeural',
            rate='-5%',
            pitch='-15Hz',
            volume='+0%'
        )
        audio_data = io.BytesIO()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        audio_bytes = audio_data.getvalue()
        
        log_response(200, "/speak", time.time() - start, len(audio_bytes))
        
        from fastapi.responses import Response
        return Response(
            content=audio_bytes,
            media_type="audio/mp3",
            headers={"Content-Disposition": "inline"}
        )
        
    except ImportError:
        log_error("/speak", ImportError("edge_tts não instalado"))
        return {"error": "edge_tts não está instalado. Execute: pip install edge-tts"}
    except Exception as e:
        log_error("/speak", e)
        return {"error": f"Erro ao gerar áudio: {str(e)}"}

# ==================== VISÃO COMPUTACIONAL ====================

@app.post("/vision/capture")
async def vision_capture(request: Request):
    """Captura uma região da tela"""
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    
    try:
        body = await request.json()
        x = body.get("x", 0)
        y = body.get("y", 0)
        width = body.get("width", 100)
        height = body.get("height", 100)
        
        result = capture_region(x, y, width, height)
        
        log_response(200, "/vision/capture", time.time() - start)
        return result
    except Exception as e:
        log_error("/vision/capture", e)
        return {"success": False, "error": str(e)}

@app.post("/vision/analyze")
async def vision_analyze():
    """Analisa a última captura com Gemini Vision"""
    # Primeiro captura análise
    result = analyze_image("ui/assets/captures/ultima_captura.png")
    
    # Se há WebSocket conectado, envia o resultado
    if result.get("success") and _websocket_instance:
        try:
            await _websocket_instance.send_json({
                "type": "vision_result",
                "text": result["text"]
            })
        except Exception:
            pass
    
    return result

@app.get("/vision/latest")
async def vision_latest():
    """Retorna informações da última captura"""
    latest = get_latest_capture()
    if latest:
        return latest
    return {"path": None, "timestamp": None}

@app.post("/vision/selecionar")
async def vision_selecionar():
    """Abre seleção de região com script externo e captura automaticamente"""
    print("[Server] === INICIO /vision/selecionar ===", flush=True)
    
    from src.core.vision import capturar_tela, analyze_image, get_latest_capture
    
    try:
        print("[Server] Step 1: Chamando capturar_tela()...", flush=True)
        caminho = await asyncio.to_thread(capturar_tela)
        
        print(f"[Server] Step 1 COMPLETO: caminho = {caminho}", flush=True)
        
        if not caminho:
            print("[Server] ERRO: caminho é None - retornando cancelada", flush=True)
            return {"success": False, "error": "Captura cancelada"}
        
        print("[Server] Step 2: Chamando analyze_image()...", flush=True)
        analise = await asyncio.to_thread(analyze_image)
        
        print(f"[Server] Step 2 COMPLETO: analise = {analise}", flush=True)
        
        if analise.get('success'):
            print("[Server] Step 3: Resumindo texto com IA...", flush=True)
            texto_resumido = await asyncio.to_thread(resumir_texto, analise['text'])
            print(f"[Server] Texto resumido: {texto_resumido[:100]}...", flush=True)
            
            print("[Server] Step 4: Enviando via WebSocket...", flush=True)
            # Enviar resultado via WebSocket
            if _websocket_instance:
                try:
                    await _websocket_instance.send_json({
                        "type": "vision_result",
                        "text": texto_resumido
                    })
                    print("[Server] Step 4 COMPLETO: WS enviado!", flush=True)
                except Exception as e:
                    print(f"[Server] Step 4 ERRO no WS: {e}", flush=True)
            
            latest = get_latest_capture()
            
            print(f"[Server] Step 5: Retornando sucesso! latest={latest}", flush=True)
            return {
                "success": True,
                "path": latest['path'] if latest else "/assets/captures/ultima_captura.png",
                "timestamp": latest['timestamp'] if latest else datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "analysis": texto_resumido
            }
        else:
            print(f"[Server] ERRO: analise falhou: {analise}", flush=True)
            return analise
            
    except Exception as e:
        print(f"[Server] ERRO Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        log_error("/vision/selecionar", e)
        return {"success": False, "error": str(e)}

@app.post("/vision/scan")
async def vision_scan():
    """Captura a tela inteira e analisa com IA Vision (scan completo)"""
    print("[Server] === INICIO /vision/scan ===", flush=True)
    
    try:
        print("[Server] Step 1: Capturando tela inteira...", flush=True)
        resultado = await asyncio.to_thread(scan_tela_completa)
        
        print(f"[Server] Step 1 COMPLETO: success={resultado.get('success')}", flush=True)
        
        if resultado.get('success'):
            print("[Server] Step 2: Enviando resultado via WebSocket...", flush=True)
            
            # Envia resultado via WebSocket
            if _websocket_instance:
                try:
                    await _websocket_instance.send_json({
                        "type": "vision_result",
                        "text": resultado["text"]
                    })
                    print("[Server] Step 2 COMPLETO: WS enviado!", flush=True)
                except Exception as e:
                    print(f"[Server] Step 2 ERRO no WS: {e}", flush=True)
            
            return {
                "success": True,
                "path": resultado.get("relative_path"),
                "timestamp": resultado.get("timestamp"),
                "analysis": resultado.get("text"),
                "provider": resultado.get("provider")
            }
        else:
            print(f"[Server] ERRO: scan falhou: {resultado}", flush=True)
            return resultado
            
    except Exception as e:
        print(f"[Server] ERRO Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        log_error("/vision/scan", e)
        return {"success": False, "error": str(e)}

# ==================== DETECÇÃO DE EMOÇÃO ====================

def detect_user_emotion(text: str) -> str | None:
    """Detecta emoção baseada em palavras-chave"""
    text_lower = text.lower()
    
    # Palavras positivas (feliz)
    happy_keywords = [
        'feliz', 'alegre', 'contente', 'satisfeito', 'otimo', 'ótimo', 'maravilhoso',
        'incrivel', 'incrível', 'perfeito', 'excelente', 'bom', 'boa', 'adorei',
        'amei', 'love', 'happy', 'obrigado', 'obrigada', 'grato', 'grata', 'legal',
        'show', 'top', 'massa', 'demais', 'felicidade', 'sucesso', 'vingança',
        'parabens', 'parabéns', 'comemorar', 'festa', 'presente', 'surpresa',
        'legal', 'que legal', 'que bom', 'que ótimo', 'perfeito', 'maravilhoso'
    ]
    
    # Palavras negativas (triste)
    sad_keywords = [
        'triste', 'deprimido', 'deprimida', 'decepcionado', 'decepcionada', 'chateado',
        'chateada', 'raiva', 'odio', 'ódio', 'pior', 'mal', 'ruim', 'nunca',
        'nada', 'ninguem', 'ninguém', 'sozinho', 'solitário', 'tristeza', 'dor',
        'luto', 'perda', 'sentimento', 'problema', 'falha', 'erro', 'fracasso',
        'desanimado', 'desanimada', 'desesperado', 'desesperada', 'cansado',
        'estressado', 'estressada', 'ansiético', 'ansiosa', 'medo', 'temor',
        'choro', 'chorar', 'sangue', 'morte', 'matar', 'suicidio', 'suicídio'
    ]
    
    # Verifica palavras positivas
    for keyword in happy_keywords:
        if keyword in text_lower:
            return 'happy'
    
    # Verifica palavras negativas
    for keyword in sad_keywords:
        if keyword in text_lower:
            return 'sad'
    
    return None

# ==================== WEBSOCKET: CHAT STREAMING ====================
# Connect: WebSocket ws://localhost:8000/ws
# Enviar: {"type": "chat", "text": "ola ravis"}
# Receber: {"type": "stream", "content": "Ola!"} (múltiplos chunks)
#          {"type": "done", ...} (fim da resposta)
#
# Diferente de /chat (REST) que retorna resposta completa no final,
# WebSocket permite streaming progressivo (tela atualiza conforme recebe)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para streaming de respostas em tempo real
    
    Fluxo:
    1. Cliente conecta ao /ws
    2. Envia mensagem JSON: {"type": "chat", "text": "..."}
    3. Servidor processa e envia múltiplos chunks com "type": "stream"
    4. No final, envia {"type": "done"} para sinalizar conclusão
    5. Cliente renderiza cada chunk progressivamente
    
    Vantagem: Resposta aparece gradualmente na tela (UX melhor)
    """
    await websocket.accept()
    set_websocket(websocket)
    log_broadcaster.add(websocket)  # Adiciona ao broadcaster de logs
    
    ip = websocket.client.host if websocket.client else "unknown"
    log_websocket("CONNECT", ip)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "JSON inválido"})
                continue
            
            # Handle new conversation (limpa contexto)
            if message.get("type") == "new_conversation":
                ai = get_ai()
                ai.clear_history()
                log_websocket("NEW_CONVERSATION", ip)
                await websocket.send_json({"type": "system", "content": "Contexto limpo. Nova conversa iniciada."})
                continue
            
            # Handle load conversation (restaura histórico)
            if message.get("type") == "load_conversation":
                mensagens = message.get("mensagens", [])
                ai = get_ai()
                ai.memory.restore_history(mensagens)
                log_websocket("LOAD_CONVERSATION", ip, f"{len(mensagens)} mensagens")
                await websocket.send_json({"type": "system", "content": f"Histórico restaurado: {len(mensagens)} mensagens carregadas."})
                continue
            
            # Handle both 'chat' and 'message' types from frontend
            msg_type = message.get("type")
            if msg_type == "message":
                message["type"] = "chat"  # Convert to chat for processing
            
            if message.get("type") == "chat":
                # Aceita tanto "text" quanto "message" como chave
                text = message.get("text", "") or message.get("message", "")
                if isinstance(text, str):
                    text = text.strip()
                else:
                    text = ""
                
                if not text:
                    await websocket.send_json({"type": "error", "content": "Mensagem vazia"})
                    continue
                
                log_websocket("MESSAGE", ip, f"'{text[:50]}...'")
                print(f"[SERVER] Mensagem recebida: {text[:50]}...", flush=True)
                
                # Detectar emoção do usuário
                user_emotion = detect_user_emotion(text)
                
                ai = get_ai()
                intent = get_intent()
                
                # Intent processing
                intent_start = time.time()
                intent_type, intent_result = intent.process(text)
                log_router(intent_type, time.time() - intent_start)
                
                print(f"[SERVER] Intent detectado: {intent_type}, resultado: {str(intent_result)[:50] if intent_result else 'None'}...", flush=True)
                
                # Todas as mensagens agora passam pela IA (sem cache de saudações)
                if intent_type == 'acao':
                    # Estado speaking
                    await websocket.send_json({
                        "type": "response",
                        "content": intent_result or "Ação executada."
                    })
                    # Envia estado de activity
                    await websocket.send_json({
                        "type": "activity",
                        "state": "idle",
                        "data": {"inference": 0, "memory": 10, "response": 0}
                    })
                    # Envia done para encerrar processamento
                    await websocket.send_json({"type": "done"})
                    log_websocket("SEND", ip, "acao response")
                
                elif intent_type == 'info':
                    # Informações rápidas (hora, data, cálculo)
                    await websocket.send_json({
                        "type": "response",
                        "content": intent_result or ""
                    })
                    await websocket.send_json({
                        "type": "activity",
                        "state": "idle",
                        "data": {"inference": 0, "memory": 5, "response": 0}
                    })
                    # Envia done para encerrar processamento
                    await websocket.send_json({"type": "done"})
                    log_websocket("SEND", ip, "info response")
                
                elif intent_type == 'pesquisa':
                    # Estado searching (pesquisando)
                    search_start = time.time()
                    # Envia estado searching
                    await websocket.send_json({
                        "type": "activity",
                        "state": "searching",
                        "data": {"inference": 75, "memory": 45, "response": 0}
                    })
                    response = ai.chat_with_search(text, intent_result)
                    log_search("Tavily/SearX", 5, time.time() - search_start)
                    
                    await websocket.send_json({
                        "type": "response",
                        "content": response
                    })
                    # Envia estado idle
                    await websocket.send_json({
                        "type": "activity",
                        "state": "idle",
                        "data": {"inference": 0, "memory": 20, "response": 100}
                    })
                    # Envia done para encerrar processamento
                    await websocket.send_json({"type": "done"})
                    log_websocket("SEND", ip, f"pesquisa response ({len(response)} chars)")
                
                elif intent_type == 'scan':
                    # Scan da tela
                    print(f"[WS] Iniciando scan da tela...", flush=True)
                    await websocket.send_json({
                        "type": "activity",
                        "state": "thinking",
                        "data": {"inference": 90, "memory": 30, "response": 0}
                    })
                    resultado = await asyncio.to_thread(scan_tela_completa)
                    
                    if resultado.get('success'):
                        await websocket.send_json({
                            "type": "vision_result",
                            "text": resultado["text"]
                        })
                    else:
                        await websocket.send_json({
                            "type": "response",
                            "content": f"Erro no scan: {resultado.get('error', 'Desconhecido')}"
                        })
                    
                    await websocket.send_json({
                        "type": "activity",
                        "state": "idle",
                        "data": {"inference": 0, "memory": 15, "response": 100}
                    })
                    # Envia done para encerrar processamento
                    await websocket.send_json({"type": "done"})
                    log_websocket("SEND", ip, "scan response")
                else:
                    # Streaming normal
                    tipo = intent_type if intent_type else 'conversa'
                    
                    ai_start = time.time()
                    chunk_count = 0
                    full_response = ""
                    
                    # Envia estado thinking
                    await websocket.send_json({
                        "type": "activity",
                        "state": "thinking",
                        "data": {"inference": 85, "memory": 50, "response": 0}
                    })
                    
                    for chunk in ai.chat_stream(text, tipo=tipo):
                        full_response += chunk
                        chunk_count += 1
                        await websocket.send_json({
                            "type": "stream",
                            "content": chunk
                        })
                    
                    log_ai("Ollama/Groq", tipo, time.time() - ai_start)
                    log_websocket("STREAM", ip, f"{chunk_count} chunks, {len(full_response)} chars")
                    
                    # Envia estado idle após completar
                    await websocket.send_json({
                        "type": "done"
                    })
                    
                    # Envia estado idle com tokens
                    await websocket.send_json({
                        "type": "activity",
                        "state": "idle",
                        "data": {"inference": 0, "memory": 15, "response": 100, "tokens": {"used": len(full_response), "total": 2048}}
                    })
                    
                    log_websocket("COMPLETE", ip)
                    
    except WebSocketDisconnect:
        log_websocket("DISCONNECT", ip)
        log_broadcaster.remove(websocket)  # Remove do broadcaster de logs
    except Exception as e:
        log_error("/ws", e)
        await websocket.send_json({
            "type": "error",
            "content": str(e)
        })

# ==================== HEALTH CHECK APIs ====================

def check_api_health():
    """Verifica saúde das APIs na inicialização"""
    print("\n" + "="*50)
    print("[HEALTH CHECK] Verificando APIs disponíveis...")
    
    # Groq
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            test = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
                timeout=5
            )
            print("  ✓ Groq API: ONLINE")
        except Exception as e:
            print(f"  ✗ Groq API: OFFLINE ({type(e).__name__})")
    else:
        print("  - Groq API: NÃO CONFIGURADA")
    
    # Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            print("  ✓ Gemini API: ONLINE")
        except Exception as e:
            print(f"  ✗ Gemini API: OFFLINE ({type(e).__name__})")
    else:
        print("  - Gemini API: NÃO CONFIGURADA")
    
    # Tavily
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if tavily_key:
        print("  ✓ Tavily API: CONFIGURADA")
    else:
        print("  - Tavily API: NÃO CONFIGURADA")
    
    print("="*50 + "\n")

# ==================== INICIAR SERVIDOR ====================

def start_server():
    """Inicia o servidor FastAPI otimizado"""
    # Executa health check primeiro
    check_api_health()
    
    def run():
        uvicorn.run(
            app, 
            host="127.0.0.1", 
            port=8000, 
            log_level="error",
            loop="asyncio",
            limit_concurrency=10,
            access_log=False
        )
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    print(f"[{get_timestamp()}] [SERVER] FastAPI rodando em http://localhost:8000")
    print(f"[{get_timestamp()}] [SERVER] WebSocket em ws://localhost:8000/ws")
    print("=" * 60)
    return thread


if __name__ == "__main__":
    start_server()
    print(f"[{get_timestamp()}] [SERVER] Acesse http://localhost:8000")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[{get_timestamp()}] [SERVER] Encerrado")
