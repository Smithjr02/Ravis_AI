# ============================================
# MÓDULO DE ROTEAMENTO DE MENSAGENS (ROUTER)
# ============================================
# Propósito: Classificar intenção da mensagem antes de processar
#
# Categorias:
#   1. conversa: Conversa casual (default)
#   2. pesquisa: Buscar informação (clima, preços, notícias)
#   3. acao: Executar ação (abrir app, site)
#   4. analise: Pergunta complexa que precisa de raciocínio
#
# Estratégia:
#   1. Cache em memória (TTL 5 min, max 1000 itens)
#   2. Shortcut para mensagens curtas óbvias (<=2 palavras)
#   3. Timeout de 2s no Groq com retry (2 tentativas)
#   4. Fallback por keywords se Groq falhar
#
# Uso:
#   router = Router()
#   categoria = router.classify("qual o preço da coca?")  # -> "pesquisa"
# ============================================

import os
import time
from dotenv import load_dotenv

load_dotenv('.env')

MAX_CACHE_SIZE = 1000
CACHE_CLEANUP_THRESHOLD = 800
MAX_RETRIES = 2
VALID_CATEGORIES = {'conversa', 'pesquisa', 'acao', 'analise'}


# ============================================================
# Classe: Router
# ============================================================
# Propósito: Classificar mensagens em categorias de intenção
#
# Atributos:
#   - groq_key: API key do Groq
#   - client: Cliente Groq inicializado
#   - _cache: Cache de classificações
#   - _cache_ttl: TTL do cache em segundos
#   - _shortcut_words: Palavras para shortcut
# ============================================================
class Router:
    """
    Classificador de mensagens por intenção.
    
    Utiliza cache, shortcut e IA para classificar
    mensagens em categorias específicas.
    """
    
    def __init__(self):
        """
        Inicializa o router.
        
        Carrega API key e inicializa cliente se disponível.
        """
        self.groq_key = os.getenv('GROQ_API_KEY', '').strip()
        self.client = None
        self._cache = {}
        self._cache_ttl = 300
        self._shortcut_words = {
            'oi', 'olá', 'ola', 'oi.', 'obrigado', 'obrigada', 'tchau', 'até', 'thanks',
            'hi', 'hello', 'bom dia', 'boa tarde', 'boa noite', 'eai', 'e aí',
            'blz', 'beleza', 'vlw', 'tmj', 'flw', 'xau', 'opa', 'fala', 'falae',
            'valeu', 'abs', 'mah', 'yss', 'show', 'legal', 'bom', 'boa'
        }
        
        if self.groq_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.groq_key)
                print("[ROUTER] Cliente Groq inicializado")
            except Exception as e:
                print(f"[ROUTER] Erro ao inicializar Groq: {e}")
    
    
    # ============================================================
    # _normalize_message()
    # ============================================================
    # Propósito: Normalizar mensagem para cache
    #
    # Args:
    #   - msg: Mensagem original
    #
    # Retorna:
    #   - str: Mensagem normalizada
    # ============================================================
    def _normalize_message(self, msg: str) -> str:
        """
        Normaliza mensagem para uso como chave de cache.
        
        Args:
            msg: Mensagem original
        
        Returns:
            str: Mensagem normalizada (lowercase, limitada a 100 chars)
        """
        return msg.strip().lower()[:100]
    
    
    # ============================================================
    # _get_from_cache()
    # ============================================================
    # Propósito: Recuperar categoria do cache
    #
    # Args:
    #   - msg: Mensagem a buscar
    #
    # Retorna:
    #   - str ou None: Categoria em cache ou None
    # ============================================================
    def _get_from_cache(self, msg: str) -> str | None:
        """
        Recupera categoria do cache se ainda válida.
        
        Args:
            msg: Mensagem a buscar no cache
        
        Returns:
            str: Categoria em cache, ou None se expirada/inexistente
        """
        normalized = self._normalize_message(msg)
        if normalized in self._cache:
            categoria, timestamp = self._cache[normalized]
            if time.time() - timestamp < self._cache_ttl:
                return categoria
            else:
                del self._cache[normalized]
        return None
    
    
    # ============================================================
    # _save_to_cache()
    # ============================================================
    # Propósito: Salvar classificação no cache
    #
    # Args:
    #   - msg: Mensagem
    #   - categoria: Categoria classificada
    # ============================================================
    def _save_to_cache(self, msg: str, categoria: str):
        """
        Salva classificação no cache com limite de tamanho.
        
        Args:
            msg: Mensagem classificada
            categoria: Categoria resultante
        """
        normalized = self._normalize_message(msg)
        self._cache[normalized] = (categoria, time.time())
        
        if len(self._cache) > CACHE_CLEANUP_THRESHOLD:
            self._cleanup_cache()
    
    
    # ============================================================
    # _cleanup_cache()
    # ============================================================
    # Propósito: Limpar entradas antigas do cache
    # ============================================================
    def _cleanup_cache(self):
        """
        Remove entradas antigas do cache, mantendo metade do limite.
        """
        items = sorted(self._cache.items(), key=lambda x: x[1][1])
        keep_count = MAX_CACHE_SIZE // 2
        self._cache = dict(items[-keep_count:])
        print(f"[ROUTER] Cache limpo: {keep_count} itens restantes")
    
    
    # ============================================================
    # _is_shortcut()
    # ============================================================
    # Propósito: Verificar se é mensagem curta óbvia
    #
    # Args:
    #   - msg: Mensagem a verificar
    #
    # Retorna:
    #   - bool: True se pode usar shortcut
    # ============================================================
    def _is_shortcut(self, msg: str) -> bool:
        """
        Verifica se é mensagem curta óbvia que pode pular o router.
        
        Args:
            msg: Mensagem a verificar
        
        Returns:
            bool: True se tem até 2 palavras e é greeting/thanks
        """
        words = msg.strip().lower().split()
        if len(words) <= 2:
            if any(w in self._shortcut_words for w in words):
                return True
        return False
    
    
    # ============================================================
    # classify()
    # ============================================================
    # Propósito: Classificar mensagem em categoria
    #
    # Args:
    #   - message: Mensagem a classificar
    #
    # Retorna:
    #   - str: Categoria (conversa, pesquisa, acao, analise)
    # ============================================================
    def classify(self, message: str) -> str:
        """
        Classifica mensagem usando cache, shortcut ou Groq.
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            str: Categoria classificada (conversa, pesquisa, acao, analise)
        """
        if not message or not isinstance(message, str):
            print("[ROUTER] Mensagem inválida recebida")
            return self._fallback_classify("")
        
        start_time = time.time()
        
        cached = self._get_from_cache(message)
        if cached:
            elapsed = int((time.time() - start_time) * 1000)
            print(f"[ROUTER] Cache hit: {cached} ({elapsed}ms)")
            return cached
        
        if self._is_shortcut(message):
            categoria = self._fallback_classify(message)
            elapsed = int((time.time() - start_time) * 1000)
            print(f"[ROUTER] Shortcut: {categoria} ({elapsed}ms)")
            self._save_to_cache(message, categoria)
            return categoria
        
        if self.client:
            system_prompt = """Classifique a mensagem em uma destas categorias:
- conversa: Cumprimento, agradecimento, conversa casual
- pesquisa: Pergunta sobre fatos, preços, notícias, clima, informações
- acao: Comando para abrir app, site, arquivo, executar algo no computador
- analise: Pergunta complexa que precisa de raciocínio

Responda APENAS com uma palavra: conversa, pesquisa, acao ou analise"""
            
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Classifique: {message[:200]}"}
                        ],
                        temperature=0.1,
                        max_tokens=10,
                        timeout=2
                    )
                    
                    categoria = response.choices[0].message.content
                    
                    if categoria:
                        categoria = categoria.strip().lower()
                    
                    if categoria in VALID_CATEGORIES:
                        elapsed = int((time.time() - start_time) * 1000)
                        print(f"[ROUTER] Classificada como: {categoria} ({elapsed}ms)")
                        self._save_to_cache(message, categoria)
                        return categoria
                    
                    print(f"[ROUTER] Resposta inválida do Groq: '{categoria}', tentando fallback...")
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"[ROUTER] Tentativa {attempt + 1} falhou: {e}, tentando novamente...")
                    else:
                        print(f"[ROUTER] Todas tentativas falharam: {e}")
        
        categoria = self._fallback_classify(message)
        elapsed = int((time.time() - start_time) * 1000)
        print(f"[ROUTER] Mensagem classificada como (fallback): {categoria}")
        print(f"[ROUTER] Tempo de classificação: {elapsed}ms")
        self._save_to_cache(message, categoria)
        return categoria
    
    
    # ============================================================
    # _fallback_classify()
    # ============================================================
    # Propósito: Classificar por keywords se Groq falhar
    #
    # Args:
    #   - message: Mensagem a classificar
    #
    # Retorna:
    #   - str: Categoria classificada
    # ============================================================
    def _fallback_classify(self, message: str) -> str:
        """
        Fallback por palavras-chave se Groq falhar.
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            str: Categoria baseada em keywords
        """
        msg = message.lower()
        
        action_keywords = ['abre', 'abrir', 'vai para', 'abra', 'inicia', 'executa', 'abre o', 'vá para', 'entra no']
        if any(kw in msg for kw in action_keywords):
            return 'acao'
        
        research_keywords = ['pesquisar', 'buscar', 'procurar', 'notícia', 'clima', 'tempo', 'preço', 'valor', 'cotação', 'quem é', 'o que é', 'como fazer', 'onde fica', 'qual é', 'quantos', 'resultado', 'jogo', 'placar']
        if any(kw in msg for kw in research_keywords):
            return 'pesquisa'
        
        analysis_keywords = ['por que', 'pq', 'qual a melhor', 'qual é melhor', 'me recomenda', 'o que acontece se', 'e se', 'compare', 'diferença', 'explique']
        if any(kw in msg for kw in analysis_keywords):
            return 'analise'
        
        return 'conversa'
