# ============================================
# MÓDULO DE PESQUISA WEB COM FALLBACK
# ============================================
# Propósito: Realizar pesquisas web com múltiplos provedores
#
# Funcionalidades:
#   - Sistema de fallback automático entre provedores
#   - Cache de resultados para evitar pesquisas duplicadas
#   - Filtragem inteligente priorizando fontes confiáveis
#   - Ajuste automático de queries para melhor resultado
#
# Ordem de Tentativa:
#   1. Tavily (IA-powered, melhor qualidade)
#   2. Serper (API Google)
#   3. SearxNG (Meta-search local/privado)
#
# Se todas falharem:
#   - Retorna mensagem de erro amigável
#
# Filtragem de Resultados:
#   - Remove duplicatas por título
#   - Prioriza fontes confiáveis (G1, UOL, BBC, Wikipedia, etc)
#   - Considera resultados dos últimos 2 anos
#
# Uso:
#   search = Search()
#   results = search.search_web("qual o preço da coca?")
# ============================================

import os
import re
import logging
import requests
import concurrent.futures
import threading
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('.env')

logger = logging.getLogger(__name__)

# ============================================================
# Constantes
# ============================================================
TRUSTED_SOURCES = [
    'g1', 'uol', 'globo', 'bbc', 'cnn', 'reuters', 'wikipedia', 'gov.br',
    'espn', 'ge', 'investing', 'tradingview', 'climatempo', 'accuweather',
    'terra', 'ig', 'r7', 'band', 'folha', 'estadao', 'correio',
    'mercadolivre', 'magalu', 'amazon', 'youtube'
]

SEARCH_TIMEOUT = int(os.getenv('SEARCH_TIMEOUT', '10'))
CACHE_TTL_SECONDS = int(os.getenv('SEARCH_CACHE_TTL', '300'))


# ============================================================
# Classe: SearchCache
# ============================================================
# Propósito: Cache em memória para resultados de pesquisa
#
# Funcionalidades:
#   - Armazena resultados com TTL configurável
#   - Thread-safe com lock
#   - Gera keys hash-based para queries
#
# Atributos:
#   - _cache: Dicionário de resultados em cache
#   - _timestamps: Timestamps de cada entrada
#   - _ttl: Tempo de vida de cada entrada
#   - _lock: Lock para thread-safety
# ============================================================
class SearchCache:
    """
    Cache thread-safe para resultados de pesquisa.
    
    Utiliza hash MD5 da query normalizada como chave,
    permitindo buscas case-insensitive sem duplicatas.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Inicializa o cache.
        
        Args:
            ttl_seconds: Tempo de vida de cada entrada em segundos (padrão: 300)
        """
        self._cache = {}
        self._timestamps = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = threading.Lock()
        
    def _make_key(self, query: str) -> str:
        """
        Gera chave de cache a partir da query.
        
        Args:
            query: Termo de pesquisa
            
        Returns:
            Hash MD5 da query em lowercase
        """
        return hashlib.md5(query.lower().encode()).hexdigest()
    
    def get(self, query: str) -> str | None:
        """
        Recupera resultado do cache se ainda válido.
        
        Args:
            query: Termo de pesquisa
            
        Returns:
            Resultado em cache ou None se expirado/inexistente
        """
        key = self._make_key(query)
        with self._lock:
            if key in self._cache:
                if datetime.now() - self._timestamps[key] < self._ttl:
                    logger.debug(f"[SearchCache] Hit: {query[:50]}...")
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._timestamps[key]
        return None
    
    def set(self, query: str, result: str):
        """
        Armazena resultado no cache.
        
        Args:
            query: Termo de pesquisa
            result: Resultado formatado da pesquisa
        """
        key = self._make_key(query)
        with self._lock:
            self._cache[key] = result
            self._timestamps[key] = datetime.now()
            
    def clear(self):
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dicionário com size e oldest timestamp
        """
        with self._lock:
            return {
                'size': len(self._cache),
                'oldest': min(self._timestamps.values()) if self._timestamps else None
            }


# ============================================================
# Classe: Search
# ============================================================
# Propósito: Gerenciar pesquisas web com fallback automático
#
# Funcionalidades:
#   - Executa múltiplos provedores em paralelo
#   - Fallback automático se um provedor falhar
#   - Filtra e prioriza resultados de fontes confiáveis
#   - Cache de resultados para otimização
#
# Atributos:
#   - tavily_key: API key do Tavily
#   - serper_key: API key do Serper
#   - searxng_url: URL do SearxNG local
#   - cache: Instância de SearchCache
# ============================================================
class Search:
    """
    Motor de pesquisa com múltiplos provedores e fallback.
    
    Executa todos os provedores configurados em paralelo,
    utilizando os melhores resultados filtrados por qualidade.
    """
    
    def __init__(self):
        """
        Inicializa o motor de pesquisa.
        
        Carrega API keys do arquivo .env e inicializa cache.
        """
        self.tavily_key = os.getenv('TAVILY_API_KEY', '').strip()
        self.serper_key = os.getenv('SERPER_API_KEY', '').strip()
        self.searxng_url = os.getenv('SEARXNG_URL', '').strip()
        self.cache = SearchCache(ttl_seconds=CACHE_TTL_SECONDS)
        
    def search_web(self, query: str, max_results: int = 10) -> str:
        """
        Executa pesquisa web com fallback automático.
        
        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados por provedor (1-20)
            
        Returns:
            String formatada com os melhores resultados ou mensagem de erro
        """
        max_results = max(1, min(20, max_results))
        logger.info(f"[SEARCH] Iniciando pesquisa: {query}")
        
        cached = self.cache.get(query)
        if cached:
            logger.info("[SEARCH] Retornando resultado do cache")
            return cached
        
        adjusted_query = self._adjust_query_for_climate(query)
        
        all_results = self._execute_parallel_search(adjusted_query, max_results)
        
        if not all_results:
            logger.warning("[SEARCH] Todos os mecanismos de pesquisa falharam")
            return "Desculpe, não consegui encontrar informações sobre isso."
        
        filtered = self._filter_best_results(all_results, top_n=3)
        
        fontes = [r.get('source', 'desconhecido') for r in filtered]
        logger.info(f"[SEARCH] Fontes selecionadas: {fontes}")
        
        synthesis = self._format_results(filtered)
        
        self.cache.set(query, synthesis)
        return synthesis
    
    def _adjust_query_for_climate(self, query: str) -> str:
        """
        Ajusta query para pesquisas de clima/tempo.
        
        Args:
            query: Query original
            
        Returns:
            Query ajustada com "previsão tempo" e "Brasil" se aplicável
        """
        climate_words = ['tempo', 'clima', 'chuva', 'temperatura', 'calor', 'frio']
        if any(word in query.lower() for word in climate_words):
            adjusted = f"previsão tempo {query} Brasil"
            logger.info(f"[SEARCH] Query ajustada para clima: {adjusted}")
            return adjusted
        return query
    
    def _execute_parallel_search(self, query: str, max_results: int) -> list:
        """
        Executa todos os provedores de pesquisa em paralelo.
        
        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados
            
        Returns:
            Lista combinada de resultados de todos os provedores
        """
        all_results = []
        lock = threading.Lock()
        
        def search_tavily():
            if not self.tavily_key:
                return []
            try:
                results = self._search_tavily(query, max_results)
                if results:
                    with lock:
                        all_results.extend(results)
                    logger.info(f"[SEARCH] Tavily retornou {len(results)} resultados")
            except Exception as e:
                logger.error(f"[SEARCH] Tavily erro: {e}")
            return []
        
        def search_serper():
            if not self.serper_key:
                return []
            try:
                results = self._search_serper(query, max_results)
                if results:
                    with lock:
                        all_results.extend(results)
                    logger.info(f"[SEARCH] Serper retornou {len(results)} resultados")
            except Exception as e:
                logger.error(f"[SEARCH] Serper erro: {e}")
            return []
        
        def search_searxng():
            if not self.searxng_url:
                return []
            try:
                results = self._search_searxng(query, max_results)
                if results:
                    with lock:
                        all_results.extend(results)
                    logger.info(f"[SEARCH] SearxNG retornou {len(results)} resultados")
            except Exception as e:
                logger.error(f"[SEARCH] SearxNG erro: {e}")
            return []
        
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            if self.tavily_key:
                futures.append(executor.submit(search_tavily))
            if self.serper_key:
                futures.append(executor.submit(search_serper))
            if self.searxng_url:
                futures.append(executor.submit(search_searxng))
            
            if not futures:
                logger.warning("[SEARCH] Nenhum mecanismo de pesquisa configurado")
                return []
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result(timeout=SEARCH_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.warning("[SEARCH] Uma fonte excedeu timeout")
                except Exception as e:
                    logger.error(f"[SEARCH] Erro em fonte: {e}")
        
        return all_results
    
    def _format_results(self, results: list) -> str:
        """
        Formata lista de resultados em string legível.
        
        Args:
            results: Lista de dicionários com title, content, url, source
            
        Returns:
            String formatada com todos os resultados
        """
        synthesis = ""
        for r in results:
            title = r.get('title', 'Sem título')
            content = r.get('content', 'Sem conteúdo')
            
            if len(content) > 300:
                content = content[:300] + "..."
            
            synthesis += f"【{title}】{content}\n\n"
        
        return synthesis
    
    def _filter_best_results(self, results: list, top_n: int = 8) -> list:
        """
        Filtra e rankeia resultados priorizando fontes confiáveis.
        
        Args:
            results: Lista de resultados brutos
            top_n: Número de resultados a retornar
            
        Returns:
            Lista ordenada com os melhores resultados
        """
        seen_titles = set()
        unique_results = []
        
        for r in results:
            title = r.get('title', '').lower()
            title_norm = re.sub(r'[^a-z0-9]', '', title)
            if title_norm not in seen_titles and len(title) > 5:
                seen_titles.add(title_norm)
                unique_results.append(r)
        
        scored = []
        for r in unique_results:
            score = self._calculate_result_score(r)
            scored.append((score, r))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for score, r in scored[:top_n]]
    
    def _calculate_result_score(self, result: dict) -> int:
        """
        Calcula score de relevância de um resultado.
        
        Args:
            result: Dicionário com title, url, content
            
        Returns:
            Score inteiro (maior = melhor)
        """
        title = result.get('title', '').lower()
        url = result.get('url', '').lower()
        content = str(result.get('content', ''))
        
        score = 0
        
        for fonte in TRUSTED_SOURCES:
            if fonte in title or fonte in url:
                score += 10
                break
        
        current_year = datetime.now().year
        for year in range(current_year - 2, current_year + 1):
            if str(year) in content:
                score += 2
                break
        
        return score
    
    def _search_tavily(self, query: str, max_results: int) -> list:
        """
        Pesquisa usando Tavily API.
        
        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados
            
        Returns:
            Lista de resultados formatados ou lista vazia
        """
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self.tavily_key)
            response = client.search(query=query, max_results=max_results)
            
            results = response.get('results', [])
            if not results:
                return []
            
            return [
                {
                    'title': r.get('title', ''),
                    'content': r.get('content', ''),
                    'url': r.get('url', ''),
                    'source': r.get('source', '')
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"[SEARCH] Tavily erro: {e}")
            return []
    
    def _search_serper(self, query: str, max_results: int) -> list:
        """
        Pesquisa usando Serper API (Google).
        
        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados
            
        Returns:
            Lista de resultados formatados ou lista vazia
        """
        try:
            url = "https://google.serper.dev/search"
            headers = {
                'X-API-KEY': self.serper_key,
                'Content-Type': 'application/json'
            }
            payload = {
                'q': query,
                'num': max_results,
                'gl': 'br',
                'hl': 'pt-BR'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=SEARCH_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"[SEARCH] Serper erro: {response.status_code}")
                return []
            
            data = response.json()
            results = data.get('organic', [])
            
            if not results:
                return []
            
            formatted = []
            for r in results:
                url = r.get('link', '')
                dominio = ''
                if '://' in url:
                    parts = url.split('://')[1].split('/')
                    dominio = parts[0] if parts else ''
                
                formatted.append({
                    'title': r.get('title', ''),
                    'content': r.get('snippet', ''),
                    'url': url,
                    'source': dominio
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"[SEARCH] Serper erro: {e}")
            return []
    
    def _search_searxng(self, query: str, max_results: int) -> list:
        """
        Pesquisa usando SearxNG (meta-search engine local).
        
        Args:
            query: Termo de pesquisa
            max_results: Número máximo de resultados
            
        Returns:
            Lista de resultados formatados ou lista vazia
        """
        try:
            url = f"{self.searxng_url}/search"
            params = {
                'q': query,
                'format': 'json',
                'language': 'pt-BR',
                'num_results': max_results
            }
            
            response = requests.get(url, params=params, timeout=SEARCH_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"[SEARCH] SearxNG erro: {response.status_code}")
                return []
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                return []
            
            formatted = []
            for r in results:
                url = r.get('url', '')
                dominio = ''
                if '://' in url:
                    parts = url.split('://')[1].split('/')
                    dominio = parts[0] if parts else ''
                
                formatted.append({
                    'title': r.get('title', ''),
                    'content': r.get('content', ''),
                    'url': url,
                    'source': dominio
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"[SEARCH] SearxNG erro: {e}")
            return []
    
    def clear_cache(self):
        """Limpa o cache de pesquisa."""
        self.cache.clear()
        logger.info("[SEARCH] Cache limpo")
    
    def get_status(self) -> dict:
        """
        Retorna status do módulo de pesquisa.
        
        Returns:
            Dicionário com configuração de cada provedor e stats do cache
        """
        return {
            'tavily_configured': bool(self.tavily_key),
            'serper_configured': bool(self.serper_key),
            'searxng_configured': bool(self.searxng_url),
            'cache_stats': self.cache.get_stats()
        }
