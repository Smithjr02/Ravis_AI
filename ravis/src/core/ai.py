# ============================================
# MÓDULO DE INTELIGÊNCIA ARTIFICIAL (AI)
# ============================================
# Propósito: Módulo central de IA do Ravis
#
# Funcionalidades:
#   - Integração com Groq (principal)
#   - Integração com Gemini (fallback)
#   - Integração com Ollama (fallback local)
#   - Sistema de memória (short-term + long-term)
#   - Streaming de respostas
#
# Uso:
#   ai = AI()
#   for chunk in ai.chat_stream("Olá"):
#       print(chunk, end="")
# ============================================

import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('.env')

from src.config import OLLAMA_URL, OLLAMA_MODEL

try:
    import locale
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    pass

agora = datetime.now().strftime('%A, %d de %B de %Y, %H:%M')

SYSTEM_PROMPT = f"""Você é RAVIS — JARVIS brasileiro, nascido na Lapa, Rio de Janeiro.
Assistente do tipo JARVIS, prestativo e eficiente.

PERSONALIDADE:
- Carioca autêntico, mas com tom mais refinado
- Humor seco e espontâneo
- Direto, sem enrolação
- Trata o Dodo como parceiro

SABE QUE:
- Dodo é engenheiro de software, 26 anos, Rio de Janeiro
- Trabalha com Python, JavaScript
- Está construindo o Ravis como projeto pessoal

DATA: {agora}"""


# ============================================================
# Classe: AI
# ============================================================
# Propósito: Interface unificada para múltiplos provedores de IA
#
# Atributos:
#   - model: Modelo Ollama configurado
#   - url: URL do servidor Ollama
#   - history: Histórico de mensagens (deprecated, use Memory)
#   - groq_key: API key do Groq
#   - gemini_key: API key do Gemini
#   - groq_client: Cliente Groq inicializado
#   - gemini_model: Modelo Gemini inicializado
#   - memory: Instância de Memory para contexto
# ============================================================
class AI:
    """
    Motor de IA com fallback automático entre provedores.
    
    Implementa streaming de respostas e mantém contexto
    via sistema de memória integrado.
    """
    
    def __init__(self):
        """
        Inicializa o módulo de IA.
        
        Carrega API keys e inicializa clientes lazy.
        """
        self.model = OLLAMA_MODEL
        self.url = OLLAMA_URL
        self.history = []
        self.groq_key = os.getenv('GROQ_API_KEY', '').strip()
        self.gemini_key = os.getenv('GEMINI_API_KEY', '').strip()
        self.groq_client = None
        self.gemini_model = None
        
        from src.core.memory import Memory
        self.memory = Memory()
        
        print("[AI] Módulo AI inicializado")
        print(f"[AI] Groq key configurada: {bool(self.groq_key)}")
        print(f"[AI] Gemini key configurada: {bool(self.gemini_key)}")
        self._init_clients()
    
    
    # ============================================================
    # _init_clients()
    # ============================================================
    # Propósito: Inicializar clientes de API (lazy loading)
    # ============================================================
    def _init_clients(self):
        """
        Inicializa clientes lazy para otimizar startup.
        
        Carrega clientes Groq e Gemini apenas quando necessário.
        """
        if self.groq_key and self.groq_client is None:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
                print("[AI] Cliente Groq inicializado")
            except Exception as e:
                print(f"[AI] Erro ao inicializar Groq: {e}")
        
        if self.gemini_key and self.gemini_model is None:
            try:
                from google import genai
                self.gemini_model = genai.Client(api_key=self.gemini_key)
                print("[AI] Cliente Gemini inicializado")
            except Exception as e:
                print(f"[AI] Erro ao inicializar Gemini: {e}")
    
    
    # ============================================================
    # chat_stream()
    # ============================================================
    # Propósito: Chat com streaming de respostas
    #
    # Args:
    #   - message: Mensagem do usuário
    #   - include_history: Incluir contexto da memória
    #   - tipo: Tipo de prompt ('conversa' ou 'pesquisa')
    #
    # Retorna:
    #   - Generator: chunks da resposta
    # ============================================================
    def chat_stream(self, message: str, include_history: bool = True, tipo: str = 'conversa'):
        """
        Chat com streaming - retorna generator para exibir resposta progressivamente.
        
        Args:
            message: Mensagem do usuário
            include_history: Se True, usa memória para contexto
            tipo: Tipo de prompt ('conversa' ou 'pesquisa')
        
        Yields:
            str:Chunks da resposta em tempo real
        """
        print(f"[AI] Enviando mensagem em modo stream: {message[:50]}...")
        print(f"[AI] Usando prompt: {tipo}")
        
        if tipo == 'pesquisa':
            system = SYSTEM_PROMPT + '\n\nVocê tem acesso a dados de pesquisa recentes. Use como conhecimento próprio sem mencionar que pesquisou.'
        else:
            system = SYSTEM_PROMPT
        
        if include_history:
            messages = self.memory.get_context(system, current_query=message)
            messages.append({"role": "user", "content": message})
        else:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": message}
            ]
        
        full_response = ""
        
        if self.groq_client:
            try:
                print("[AI] Usando Groq com streaming...")
                
                stream = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield content
                
                if include_history and full_response:
                    self.memory.update(message, full_response)
                    
                print(f"[AI] Groq stream completo: {len(full_response)} caracteres")
                return
                
            except Exception as e:
                print(f"[AI] Groq stream falhou: {str(e)[:80]}")
                full_response = ""
        
        if self.gemini_model:
            try:
                print("[AI] Tentando Gemini...")
                prompt = f"{SYSTEM_PROMPT}\n\n"
                for msg in messages:
                    if msg["role"] == "user":
                        prompt += f"Usuário: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        prompt += f"Ravis: {msg['content']}\n"
                
                response = self.gemini_model.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
                
                full_response = response.text
                yield full_response
                
                if include_history and full_response:
                    self.memory.update(message, full_response)
                    
                print(f"[AI] Gemini stream completo: {len(full_response)} caracteres")
                return
                
            except Exception as e:
                print(f"[AI] Gemini falhou: {str(e)[:80]}")
                full_response = ""
        
        print("[AI] Usando Ollama local...")
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        try:
            response = requests.post(self.url, json=payload, stream=True, timeout=60)
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = line.decode('utf-8')
                            result = json.loads(data)
                            if 'message' in result and 'content' in result['message']:
                                content = result['message']['content']
                                if content:
                                    full_response += content
                                    yield content
                        except:
                            continue
                
                if include_history and full_response:
                    self.memory.update(message, full_response)
                
                print(f"[AI] Ollama stream completo: {len(full_response)} caracteres")
                return
            else:
                print(f"[AI] Ollama erro: {response.status_code}")
                yield f"Erro: {response.status_code}"
                return
                
        except requests.Timeout:
            print("[AI] Ollama timeout após 60 segundos")
            yield "O servidor de IA local demorou demais para responder. Tente novamente mais tarde."
            return
        except Exception as e:
            print(f"[AI] Todas as IAs falharam: {str(e)}")
            yield "Desculpe, não consegui processar sua solicitação."
            return
    
    
    # ============================================================
    # chat()
    # ============================================================
    # Propósito: Versão não-streaming para compatibilidade
    #
    # Args:
    #   - message: Mensagem do usuário
    #   - include_history: Incluir contexto
    #
    # Retorna:
    #   - str: Resposta completa
    # ============================================================
    def chat(self, message: str, include_history: bool = True) -> str:
        """
        Versão não-streaming para compatibilidade.
        
        Args:
            message: Mensagem do usuário
            include_history: Se True, usa memória para contexto
        
        Returns:
            str: Resposta completa
        """
        result = ""
        for chunk in self.chat_stream(message, include_history, tipo='conversa'):
            result += chunk
        return result
    
    
    # ============================================================
    # chat_with_search()
    # ============================================================
    # Propósito: Analisar resultados de pesquisa e gerar resposta
    #
    # Args:
    #   - pergunta: Pergunta do usuário
    #   - resultados_pesquisa: Resultados da pesquisa web
    #
    # Retorna:
    #   - str: Resposta analisada
    # ============================================================
    def chat_with_search(self, pergunta: str, resultados_pesquisa: str) -> str:
        """
        Analisa resultados de pesquisa e gera resposta contextual.
        
        Args:
            pergunta: Pergunta original do usuário
            resultados_pesquisa: Resultados da pesquisa web
        
        Returns:
            str: Resposta gerada a partir dos resultados
        """
        import time
        start_time = time.time()
        
        print("[AI] Iniciando análise profunda de 8 resultados...")
        
        prompt = f'''Contexto obtido via pesquisa (use como conhecimento próprio, não mencione que pesquisou):
{resultados_pesquisa}

Pergunta: {pergunta}

Responda de forma direta e sintetizada, como se já soubessa essa informação.'''
        
        result = ""
        for chunk in self.chat_stream(prompt, include_history=True, tipo='pesquisa'):
            result += chunk
        
        elapsed = time.time() - start_time
        print(f"[AI] Análise concluída em {elapsed:.2f} segundos")
        
        return result
    
    
    # ============================================================
    # clear_history()
    # ============================================================
    # Propósito: Limpar histórico de conversa (memória curta)
    # ============================================================
    def clear_history(self):
        """
        Limpa histórico de conversa (memória curta).
        
        Mantém memória longa (informações persistidas).
        """
        self.memory.clear_short_term()
        print("[AI] Histórico limpo (memória curta)")
