# ============================================
# MÓDULO DE VISÃO COMPUTACIONAL (VISION)
# ============================================
# Propósito: Captura e análise de imagens via IA Vision
#
# Funcionalidades:
#   - Captura de região específica da tela (selection)
#   - Captura de tela inteira (screenshot)
#   - Análise de imagens com IA (Groq, OpenRouter, Gemini)
#   - Fallback automático entre provedores
#   - Scan completo da tela
#
# Ordem de Análise:
#   1. Groq llama-3.2-90b-vision
#   2. OpenRouter (múltiplos modelos gratuitos)
#   3. Gemini 1.5 Flash
#
# Uso:
#   from src.core.vision import capturar_tela, analyze_image
#   path = capturar_tela()
#   result = analyze_image(path)
# ============================================

import os
import sys
import re
import subprocess
import base64
from datetime import datetime
from dotenv import load_dotenv
import mss
from PIL import Image
from google import genai
import groq
from openai import OpenAI

load_dotenv()

CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "assets", "captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)


# ============================================================
# Constantes: Prompts
# ============================================================
VISION_PROMPT = """Analise esta imagem de forma DIRETA e OBJETIVA.
Responda em MÁXIMO 3 FRASES.

O que é importante:
- O que está na tela (site, app, documento, código, etc)
- Informações relevantes (textos principais, dados, alertas)
- Sugestão de ação se necessário

Não seja verboso. Vá direto ao ponto."""

SCAN_TELA_PROMPT = """ANÁLISE ESTREITA DA TELA. RESPONDA APENAS COM:

1. O que está visível (máximo 5 palavras)
2. Dado importante se houver (máximo 5 palavras)

EXEMPLO ÚNICO CORRETO:
"Chrome + Spotify abertos. CPU 40%."
"Nenhuma aba aberta. Bateria 98%."

RESPONDA EXATAMENTE NESSE FORMATO. SEM PONTOS EXTRAS. SEM DESCRIÇÃO. SÓ 2 PARTES."""


# ============================================================
# Função: _clean_markdown()
# ============================================================
# Propósito: Limpar formatação Markdown da resposta da IA
#
# Args:
#   - text: Texto com formatação
#
# Retorna:
#   - str: Texto limpo e limitado a ~100 caracteres
# ============================================================
def _clean_markdown(text: str) -> str:
    """
    Remove formatação Markdown e limita resposta a 2 frases curtas.
    
    Remove asteriscos, hashtags, bullets, listas e normaliza espaços.
    
    Args:
        text: Texto com formatação Markdown
    
    Returns:
        str: Texto limpo limitado a ~100 caracteres
    """
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'^[\s]*[-*•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+[\.\)]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'(Visão geral|Sistema|Informação|Descrição|Resumo)[:\s]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\|+', '', text)
    text = re.sub(r'\s\s+', ' ', text)
    text = text.strip()
    
    if len(text) > 100:
        text = text[:100].rsplit(' ', 1)[0] + '.'
    return text


# ============================================================
# Função: _load_image()
# ============================================================
# Propósito: Carregar imagem e converter para base64
#
# Args:
#   - image_path: Caminho da imagem
#
# Retorna:
#   - str: String base64 da imagem
#
# Exceções:
#   - FileNotFoundError: Se imagem não existir
# ============================================================
def _load_image(image_path: str) -> str:
    """
    Lê imagem do disco e converte para base64.
    
    Args:
        image_path: Caminho absoluto da imagem
    
    Returns:
        str: String base64 da imagem
    
    Raises:
        FileNotFoundError: Se arquivo não existir
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")
    
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ============================================================
# Função: _analyze_groq()
# ============================================================
# Propósito: Analisar imagem com Groq Vision
#
# Args:
#   - image_path: Caminho da imagem
#   - prompt: Prompt personalizado (opcional)
#
# Retorna:
#   - dict: {"success": bool, "text": str, "provider": str}
# ============================================================
def _analyze_groq(image_path: str, prompt: str = None) -> dict:
    """
    Analisa imagem usando Groq Vision (llama-3.2-90b-vision).
    
    Args:
        image_path: Caminho para a imagem
        prompt: Prompt personalizado (opcional, usa VISION_PROMPT se None)
    
    Returns:
        dict: {"success": True, "text": str, "provider": str}
    """
    if prompt is None:
        prompt = VISION_PROMPT
    
    print("[Vision] 🔄 Tentando Groq Vision (llama-3.2-90b-vision)...")
    
    image_data = _load_image(image_path)
    client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    response = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        temperature=0.5,
        max_tokens=256
    )
    
    texto = response.choices[0].message.content
    print("[Vision] ✅ Groq Vision (llama-3.2-90b-vision) funcionou!")
    
    return {"success": True, "text": texto, "provider": "Groq (llama-3.2-90b-vision)"}


# ============================================================
# Função: _analyze_openrouter()
# ============================================================
# Propósito: Analisar imagem com OpenRouter (múltiplos modelos)
#
# Args:
#   - image_path: Caminho da imagem
#   - prompt: Prompt personalizado (opcional)
#
# Retorna:
#   - dict: {"success": bool, "text": str, "provider": str}
#
# Exceções:
#   - Exception: Se todos os modelos falharem
# ============================================================
def _analyze_openrouter(image_path: str, prompt: str = None) -> dict:
    """
    Analisa imagem usando OpenRouter (múltiplos modelos gratuitos).
    
    Args:
        image_path: Caminho para a imagem
        prompt: Prompt personalizado (opcional)
    
    Returns:
        dict: {"success": True, "text": str, "provider": str}
    
    Raises:
        Exception: Se todos os modelos falharem
    """
    if prompt is None:
        prompt = VISION_PROMPT
    
    print("[Vision] 🔄 Tentando OpenRouter...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("OPENROUTER_API_KEY não configurada")
    
    client = OpenAI(
        base_url='https://openrouter.ai/api/v1',
        api_key=api_key
    )
    
    image_data = _load_image(image_path)
    image_url = f"data:image/png;base64,{image_data}"
    
    modelos = [
        'google/gemini-2.0-flash-001',
        'anthropic/claude-3.5-sonnet:free',
        'openai/gpt-4o-mini:free',
        'qwen/qwen2-vl-72b-instruct:free',
        'deepseek/deepseek-chat:free',
        'openrouter/free'
    ]
    
    for modelo in modelos:
        try:
            print(f"[Vision] 🔄 Tentando OpenRouter ({modelo})...")
            
            response = client.chat.completions.create(
                model=modelo,
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'image_url', 'image_url': {'url': image_url}},
                        {'type': 'text', 'text': prompt}
                    ]
                }],
                max_tokens=256
            )
            
            texto = response.choices[0].message.content
            print(f"[Vision] ✅ OpenRouter {modelo} funcionou!")
            
            return {"success": True, "text": texto, "provider": f"OpenRouter ({modelo})"}
            
        except Exception as e:
            print(f"[Vision] ❌ OpenRouter {modelo} falhou: {e}")
            continue
    
    raise Exception("Todos os modelos OpenRouter falharam")


# ============================================================
# Função: _analyze_gemini()
# ============================================================
# Propósito: Analisar imagem com Gemini Vision
#
# Args:
#   - image_path: Caminho da imagem
#   - model: Modelo Gemini (padrão: gemini-1.5-flash)
#   - prompt: Prompt personalizado (opcional)
#
# Retorna:
#   - dict: {"success": bool, "text": str, "provider": str}
# ============================================================
def _analyze_gemini(image_path: str, model: str = "gemini-1.5-flash", prompt: str = None) -> dict:
    """
    Analisa imagem usando Gemini Vision.
    
    Args:
        image_path: Caminho para a imagem
        model: Modelo Gemini (padrão: gemini-1.5-flash)
        prompt: Prompt personalizado (opcional)
    
    Returns:
        dict: {"success": True, "text": str, "provider": str}
    """
    if prompt is None:
        prompt = VISION_PROMPT
    
    print(f"[Vision] 🔄 Tentando Gemini {model}...")
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    image_data = _load_image(image_path)
    
    response = client.models.generate_content(
        model=model,
        contents=[
            {"mime_type": "image/png", "data": image_data},
            prompt
        ]
    )
    
    texto = response.text
    print(f"[Vision] ✅ Gemini {model} funcionou!")
    
    return {"success": True, "text": texto, "provider": f"Gemini ({model})"}


# ============================================================
# Função: capturar_tela()
# ============================================================
# Propósito: Executar captura de tela via seleção de região
#
# Retorna:
#   - str: Caminho da imagem capturada ou None se cancelado
# ============================================================
def capturar_tela() -> str:
    """
    Executa script externo de captura de tela com seleção de região.
    
    Abre janela fullscreen transparente para usuário selecionar área.
    
    Returns:
        str: Caminho da imagem capturada, ou None se cancelado/erro
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    capture_script = os.path.join(script_dir, 'modules', 'capture.py')
    
    print(f"[Vision] Preparando para executar capture.py...", flush=True)
    print(f"[Vision] Script: {capture_script}", flush=True)
    print(f"[Vision] Python: {sys.executable}", flush=True)
    
    try:
        print("[Vision] === INICIANDO subprocess ===", flush=True)
        print("[Vision] Abrindo janela de seleção... (aguarde interação)", flush=True)
        
        env = os.environ.copy()
        
        result = subprocess.run(
            [sys.executable, capture_script],
            cwd=script_dir,
            env=env,
            timeout=60
        ).returncode
        
        print(f"[Vision] === FIM subprocess.call === returncode: {result}", flush=True)
        
        output_path = os.path.join(CAPTURES_DIR, "ultima_captura.png")
        
        if os.path.exists(output_path):
            print(f"[Vision] SUCESSO! Arquivo encontrado: {output_path}", flush=True)
            return output_path
        else:
            print("[Vision] ERRO: Arquivo de captura não encontrado", flush=True)
            return None
        
    except subprocess.TimeoutExpired:
        print("[Vision] Timeout na captura", flush=True)
        return None
    except Exception as e:
        print(f"[Vision] Erro ao capturar: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# Função: capture_region()
# ============================================================
# Propósito: Capturar região específica da tela
#
# Args:
#   - x: Posição X inicial
#   - y: Posição Y inicial
#   - width: Largura da região
#   - height: Altura da região
#
# Retorna:
#   - dict: {"success": bool, "path": str, "timestamp": str}
# ============================================================
def capture_region(x: int, y: int, width: int, height: int) -> dict:
    """
    Captura uma região específica da tela usando mss.
    
    Args:
        x: Posição X inicial
        y: Posição Y inicial
        width: Largura da região em pixels
        height: Altura da região em pixels
    
    Returns:
        dict: {"success": bool, "path": str, "latest_path": str, "timestamp": str}
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captura_{timestamp}.png"
        filepath = os.path.join(CAPTURES_DIR, filename)
        
        with mss.mss() as sct:
            monitor = {"top": y, "left": x, "width": width, "height": height}
            img = sct.grab(monitor)
            
            pil_img = Image.frombytes("RGB", img.size, img.rgb)
            pil_img.save(filepath, "PNG")
            
            latest_path = os.path.join(CAPTURES_DIR, "ultima_captura.png")
            pil_img.save(latest_path, "PNG")
            
            return {
                "success": True,
                "path": f"/assets/captures/{filename}",
                "latest_path": "/assets/captures/ultima_captura.png",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# Função: analyze_image()
# ============================================================
# Propósito: Sistema de fallback para análise de imagens
#
# Args:
#   - image_path: Caminho da imagem (opcional)
#
# Retorna:
#   - dict: {"success": bool, "text": str, "provider": str, "error": str}
#
# Ordem de tentativa:
#   1. Groq llama-3.2-90b-vision
#   2. OpenRouter (múltiplos modelos)
#   3. Gemini 1.5 Flash
# ============================================================
def analyze_image(image_path: str = None) -> dict:
    """
    Analisa imagem com fallback automático entre provedores de IA.
    
    Args:
        image_path: Caminho para a imagem (opcional, usa última captura se None)
    
    Returns:
        dict: {"success": bool, "text": str, "provider": str, "error": str}
    """
    if image_path is None:
        image_path = os.path.join(CAPTURES_DIR, "ultima_captura.png")
    else:
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), image_path.lstrip("/"))
    
    if not os.path.exists(image_path):
        return {"success": False, "error": "Imagem não encontrada"}
    
    erros = []
    
    try:
        resultado = _analyze_groq(image_path)
        print(f"[Vision] ✅ Sucesso com: {resultado.get('provider')}")
        return resultado
    except Exception as e:
        erro_msg = str(e)
        print(f"[Vision] ❌ Groq llama-3.2-90b-vision falhou: {erro_msg}")
        erros.append(f"Groq: {erro_msg}")
    
    try:
        resultado = _analyze_openrouter(image_path)
        print(f"[Vision] ✅ Sucesso com: {resultado.get('provider')}")
        return resultado
    except Exception as e:
        erro_msg = str(e)
        print(f"[Vision] ❌ OpenRouter falhou: {erro_msg}")
        erros.append(f"OpenRouter: {erro_msg}")
    
    try:
        resultado = _analyze_gemini(image_path, "gemini-1.5-flash")
        print(f"[Vision] ✅ Sucesso com: {resultado.get('provider')}")
        return resultado
    except Exception as e:
        erro_msg = str(e)
        print(f"[Vision] ❌ Gemini 1.5 Flash falhou: {erro_msg}")
        erros.append(f"Gemini Flash: {erro_msg}")
    
    erro_final = f"Não foi possível analisar a imagem. Erros: {'; '.join(erros)}"
    print(f"[Vision] ❌ TODOS OS PROVEDORES FALHARAM: {erros}")
    
    return {
        "success": False, 
        "error": erro_final,
        "text": "Desculpe, não consegui analisar a imagem no momento. Todos os serviços de IA estão temporariamente indisponíveis."
    }


# ============================================================
# Função: get_latest_capture()
# ============================================================
# Propósito: Obter informações da última captura
#
# Retorna:
#   - dict ou None: Informações da captura ou None se não existir
# ============================================================
def get_latest_capture() -> dict | None:
    """
    Retorna informações da última captura de tela.
    
    Returns:
        dict: {"path": str, "timestamp": str} ou None se não existir
    """
    latest_path = os.path.join(CAPTURES_DIR, "ultima_captura.png")
    
    if os.path.exists(latest_path):
        timestamp = datetime.fromtimestamp(os.path.getmtime(latest_path))
        return {
            "path": "/assets/captures/ultima_captura.png",
            "timestamp": timestamp.strftime("%d/%m/%Y %H:%M:%S")
        }
    return None


# ============================================================
# Função: scan_tela_completa()
# ============================================================
# Propósito: Capturar e analisar tela inteira automaticamente
#
# Retorna:
#   - dict: {"success": bool, "path": str, "text": str, "provider": str}
# ============================================================
def scan_tela_completa() -> dict:
    """
    Captura a tela inteira e analisa com IA Vision.
    
    Usa mss para screenshot instantâneo sem seleção do usuário.
    Salva em ui/assets/captures/scan_[timestamp].png
    
    Returns:
        dict: {"success": bool, "path": str, "text": str, "provider": str, "error": str}
    """
    print("[Vision] Iniciando scan completo da tela...")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scan_{timestamp}.png"
        filepath = os.path.join(CAPTURES_DIR, filename)
        
        with mss.mss() as sct:
            sct.shot(mon=-1, output=filepath)
            print(f"[Vision] Screenshot salvo em: {filepath}")
        
        latest_path = os.path.join(CAPTURES_DIR, "ultima_captura.png")
        try:
            img = Image.open(filepath)
            img.save(latest_path, "PNG")
        except:
            pass
        
        print("[Vision] Analisando screenshot com IA...")
        
        try:
            resultado = _analyze_groq(filepath, SCAN_TELA_PROMPT)
            texto_limpo = _clean_markdown(resultado["text"])
            return {
                "success": True,
                "path": filepath,
                "relative_path": f"/assets/captures/{filename}",
                "latest_path": "/assets/captures/ultima_captura.png",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "text": texto_limpo,
                "provider": resultado.get("provider", "Groq")
            }
        except Exception as e:
            print(f"[Vision] Groq falhou no scan: {e}")
        
        try:
            resultado = _analyze_openrouter(filepath, SCAN_TELA_PROMPT)
            texto_limpo = _clean_markdown(resultado["text"])
            return {
                "success": True,
                "path": filepath,
                "relative_path": f"/assets/captures/{filename}",
                "latest_path": "/assets/captures/ultima_captura.png",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "text": texto_limpo,
                "provider": resultado.get("provider", "OpenRouter")
            }
        except Exception as e:
            print(f"[Vision] OpenRouter falhou no scan: {e}")
        
        try:
            resultado = _analyze_gemini(filepath, "gemini-1.5-flash", SCAN_TELA_PROMPT)
            texto_limpo = _clean_markdown(resultado["text"])
            return {
                "success": True,
                "path": filepath,
                "relative_path": f"/assets/captures/{filename}",
                "latest_path": "/assets/captures/ultima_captura.png",
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "text": texto_limpo,
                "provider": resultado.get("provider", "Gemini")
            }
        except Exception as e:
            print(f"[Vision] Gemini falhou no scan: {e}")
        
        return {
            "success": False,
            "path": filepath,
            "relative_path": f"/assets/captures/{filename}",
            "error": "Todos os provedores de IA falharam na análise."
        }
        
    except Exception as e:
        print(f"[Vision] Erro no scan_tela_completa: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }
