# ============================================
# MÓDULO DE MEMÓRIA INTELIGENTE
# ============================================
# Propósito: Sistema de memória persistente do Ravis
#
# Sistema de dois níveis:
#
# 1. SHORT-TERM (RAM):
#    - Últimas ~15 mensagens durante conversa
#    - Contexto imediato
#    - Não persiste entre sessões
#
# 2. LONG-TERM (JSON - data/memory.json):
#    - informacoes: Facts sobre o usuário
#    - pesquisas: Pesquisas recentes
#    - conversas_resumidas: Resumos de conversas antigas
#    - short_term_backup: Backup da última sessão
#
# Fluxo:
# - Início: Carrega long-term do JSON
# - Conversa: Mantém short-term em RAM
# - > 20 msgs: Gera resumo das mais antigas
# - A cada 5 trocas: Salva no JSON
# - get_context(): Retorna contexto para IA
# ============================================

import os
import json
import shutil
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_MEMORY_FILE = os.path.join(BASE_DIR, "data", "memory.json")
MEMORY_FILE = os.getenv("RAVIS_MEMORY_FILE", DEFAULT_MEMORY_FILE)

IMPORTANT_KEYWORDS = [
    'meu nome é', 'me chamo', 'pode me chamar', 'chame-me', 'pode chamar de',
    'eu trabalho', 'trabalho com', 'minha área', 'atuo em', 'sou desenvolvedor',
    'eu moro', 'moro em', 'vivou', 'resido em',
    'tenho anos', 'idade é', 'nasci em',
    'minha preferência', 'eu prefiro', 'eu gosto', 'meu favorito',
    'eu sou', 'eu tenho', 'eu uso', 'app que eu uso', 'site que eu acesso'
]

IMPORTANT_PATTERNS = [
    (r'meu nome é (\w+)', 'Nome: {0}'),
    (r'me chamo (\w+)', 'Nome: {0}'),
    (r'pode me chamar de (\w+)', 'Nome: {0}'),
    (r'trabalho com (\w+)', 'Trabalho: {0}'),
    (r'tenho (\d+) anos', 'Idade: {0} anos'),
    (r'moro em ([^,.]+)', 'Local: {0}'),
]

IMPORTANT_RESEARCH = [
    'preço', 'cotação', 'valor', 'ações', 'bolsa', 'dólar', 'euro',
    'resultado de jogo', 'placar', 'classificação', 'notícia', 'ano'
]


# ============================================================
# Classe: Memory
# ============================================================
# Propósito: Gerenciar memória curto e longo prazo
#
# Atributos:
#   - short_term: Lista de mensagens da conversa (RAM)
#   - long_term: Dicionário com dados persistidos
#   - exchange_count: Contador de trocas de mensagens
#   - _save_errors: Contador de erros de salvamento
# ============================================================
class Memory:
    """
    Sistema de memória com dois níveis de persistência.
    
    Gerencia contexto de conversa e informações
    persistentes do usuário.
    """
    
    def __init__(self):
        """
        Inicializa o sistema de memória.
        
        Carrega memória longa do arquivo JSON.
        """
        self.short_term = []
        self.long_term = {}
        self.exchange_count = 0
        self._save_errors = 0
        self._load_long_term()
    
    
    # ============================================================
    # _load_long_term()
    # ============================================================
    # Propósito: Carregar memória persistente do arquivo JSON
    # ============================================================
    def _load_long_term(self):
        """
        Carrega memória longa do arquivo JSON.
        
        Cria campos obrigatórios se não existirem.
        """
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    self.long_term = json.load(f)
                
                self.long_term.setdefault('informacoes', [])
                self.long_term.setdefault('apps_usados', [])
                self.long_term.setdefault('sites_usados', [])
                self.long_term.setdefault('pesquisas', [])
                self.long_term.setdefault('conversas_resumidas', [])
                self.long_term.setdefault('short_term_backup', [])
                
                print(f"[MEMORY] Memória longa carregada: {len(self.long_term.get('informacoes', []))} infos")
                
                if self.long_term.get('short_term_backup'):
                    self.short_term = self.long_term['short_term_backup']
                    print(f"[MEMORY] Carregadas {len(self.short_term)} mensagens da sessão anterior")
                
                if self.long_term.get('conversas_resumidas'):
                    print(f"[MEMORY] Carregados {len(self.long_term['conversas_resumidas'])} resumos de conversas")
            except Exception as e:
                print(f"[MEMORY] Erro ao carregar memória: {e}")
                self.long_term = {
                    'informacoes': [], 'apps_usados': [], 'sites_usados': [],
                    'pesquisas': [], 'conversas_resumidas': [], 'short_term_backup': []
                }
        else:
            self.long_term = {
                'informacoes': [], 'apps_usados': [], 'sites_usados': [],
                'pesquisas': [], 'conversas_resumidas': [], 'short_term_backup': []
            }
    
    
    # ============================================================
    # save_long_term()
    # ============================================================
    # Propósito: Salvar memória longa com backup rotacionado
    # ============================================================
    def save_long_term(self):
        """
        Salva memória longa com backup rotacionado (5 versões).
        """
        if self._save_errors >= 3:
            print(f"[MEMORY] Erros de salvamento excedem limite (3). Desabilitando salvamento temporário.")
            return
        try:
            if os.path.exists(MEMORY_FILE):
                for i in range(4, 0, -1):
                    old = f"{MEMORY_FILE}.bak{i}"
                    new = f"{MEMORY_FILE}.bak{i+1}"
                    if os.path.exists(old):
                        os.rename(old, new)
                shutil.copy(MEMORY_FILE, f"{MEMORY_FILE}.bak1")
            
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.long_term, f, ensure_ascii=False, indent=2)
            
            self._save_errors = 0
        except Exception as e:
            self._save_errors += 1
            print(f"[MEMORY] Erro ao salvar memória ({self._save_errors}/3): {e}")
    
    
    # ============================================================
    # get_context()
    # ============================================================
    # Propósito: Montar contexto completo para a IA
    #
    # Args:
    #   - system_prompt: Prompt base do sistema
    #   - current_query: Pergunta atual (para filtrar)
    #
    # Retorna:
    #   - list: Lista de mensagens para API
    # ============================================================
    def get_context(self, system_prompt: str, current_query: str = None) -> list:
        """
        Retorna contexto completo para enviar à IA.
        
        Args:
            system_prompt: Prompt base do sistema
            current_query: Pergunta atual (para filtrar memória relevante)
        
        Returns:
            list: Lista de mensagens no formato para API
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if self.long_term.get('conversas_resumidas'):
            summaries = [s['resumo'] for s in self.long_term['conversas_resumidas'][-5:]]
            if summaries:
                context = "Conversas anteriores: " + " | ".join(summaries)
                messages.append({"role": "system", "content": context})
        
        if len(self.short_term) > 15:
            old_messages = self.short_term[:-15]
            summary = self._generate_summary(old_messages)
            if summary:
                messages.append({"role": "system", "content": f"Contexto recente: {summary}"})
        
        if self.long_term.get('informacoes') and current_query:
            relevant_info = self._get_relevant_info(current_query)
            if relevant_info:
                context_info = "Informações relevantes sobre Dodo: " + "; ".join(relevant_info)
                messages.append({"role": "system", "content": context_info})
        elif self.long_term.get('informacoes'):
            infos = self.long_term['informacoes']
            if infos and isinstance(infos[0], dict) and 'texto' in infos[0]:
                info_texts = [info['texto'] for info in infos[-3:]]
            else:
                info_texts = infos[-3:]
            context_info = "Informações sobre Dodo: " + "; ".join(info_texts)
            messages.append({"role": "system", "content": context_info})
        
        for msg in self.short_term[-15:]:
            messages.append(msg)
        
        print(f"[MEMORY] Contexto: {len(messages)} mensagens (resumos: {len(self.long_term.get('conversas_resumidas', []))})")
        return messages
    
    
    # ============================================================
    # _generate_summary()
    # ============================================================
    # Propósito: Gerar resumo das mensagens antigas
    #
    # Args:
    #   - messages: Lista de mensagens
    #
    # Retorna:
    #   - str: Resumo gerado
    # ============================================================
    def _generate_summary(self, messages: list) -> str:
        """
        Gera resumo das mensagens antigas.
        
        Args:
            messages: Lista de mensagens a resumir
        
        Returns:
            str: Resumo das mensagens
        """
        if not messages:
            return ""
        
        if len(messages) > 20:
            start = messages[0].get('content', '')[:40]
            end = messages[-1].get('content', '')[:40]
            return f"Início: {start}... | Recentemente: {end}..."
        
        summary_parts = []
        for msg in messages[:4]:
            content = msg.get('content', '')[:30]
            if content:
                summary_parts.append(content)
        
        return " | ".join(summary_parts) + "..." if summary_parts else ""
    
    
    # ============================================================
    # _generate_and_store_summary()
    # ============================================================
    # Propósito: Gerar resumo e mover para long-term
    # ============================================================
    def _generate_and_store_summary(self):
        """
        Gera resumo das mensagens mais antigas e move para long-term.
        """
        if len(self.short_term) <= 15:
            return
        
        messages_to_summarize = self.short_term[:-10]
        summary_text = self._generate_summary(messages_to_summarize)
        
        if summary_text:
            summary_entry = {
                'timestamp': datetime.now().isoformat(),
                'resumo': summary_text,
                'mensagens_count': len(messages_to_summarize)
            }
            
            self.long_term.setdefault('conversas_resumidas', [])
            self.long_term['conversas_resumidas'].append(summary_entry)
            
            self.short_term = self.short_term[-15:]
            
            print(f"[MEMORY] Resumo gerado e armazenado ({len(messages_to_summarize)} mensagens resumidas)")
    
    
    # ============================================================
    # _get_relevant_info()
    # ============================================================
    # Propósito: Filtrar informações relevantes baseadas na query
    #
    # Args:
    #   - query: Query atual
    #
    # Retorna:
    #   - list: Informações relevantes
    # ============================================================
    def _get_relevant_info(self, query: str) -> list:
        """
        Retorna informações relevantes baseadas na query.
        
        Args:
            query: Pergunta atual do usuário
        
        Returns:
            list: Lista de informações relevantes (máx 3)
        """
        if not query or not self.long_term.get('informacoes'):
            return []
        
        query_lower = query.lower()
        relevant = []
        
        for info in self.long_term['informacoes']:
            info_lower = info.lower()
            
            if any(word in info_lower for word in ['app', 'site', 'programa', 'software']):
                if any(word in query_lower for word in ['abrir', 'app', 'programa', 'site', 'acesso']):
                    relevant.append(info)
            elif any(word in info_lower for word in ['nome', 'chamado']):
                if any(word in query_lower for word in ['quem', 'nome', 'qual seu nome']):
                    relevant.append(info)
            elif any(word in info_lower for word in ['gosto', 'prefiro', 'favorito']):
                if any(word in query_lower for word in ['gosta', 'prefere', 'favorito', 'recomenda']):
                    relevant.append(info)
            else:
                if len(relevant) < 2:
                    relevant.append(info)
        
        return relevant[:3]
    
    
    # ============================================================
    # update()
    # ============================================================
    # Propósito: Atualizar memória após interação
    #
    # Args:
    #   - user_message: Mensagem do usuário
    #   - assistant_message: Resposta do assistente
    # ============================================================
    def update(self, user_message: str, assistant_message: str):
        """
        Atualiza a memória após cada interação.
        
        Args:
            user_message: Mensagem do usuário
            assistant_message: Resposta do assistente
        """
        self.exchange_count += 1
        
        self.short_term.append({"role": "user", "content": user_message})
        self.short_term.append({"role": "assistant", "content": assistant_message})
        
        if len(self.short_term) > 20:
            self._generate_and_store_summary()
        
        self.long_term['short_term_backup'] = self.short_term[-20:]
        
        if self.exchange_count % 5 == 0:
            self.save_long_term()
            print(f"[MEMORY] Histórico salvo ({len(self.short_term)} mensagens)")
        
        self._detect_important_info(user_message)
        self._cleanup()
    
    
    # ============================================================
    # _detect_important_info()
    # ============================================================
    # Propósito: Detectar e salvar informações importantes
    #
    # Args:
    #   - message: Mensagem do usuário
    # ============================================================
    def _detect_important_info(self, message: str):
        """
        Detecta e salva informações importantes com timestamp.
        
        Args:
            message: Mensagem do usuário
        """
        msg_lower = message.lower()
        
        for pattern, template in IMPORTANT_PATTERNS:
            match = re.search(pattern, msg_lower)
            if match:
                info_text = template.format(*match.groups())
                self._add_info_with_limit(info_text)
                return
        
        for keyword in IMPORTANT_KEYWORDS:
            if keyword in msg_lower:
                info = f"{keyword.title()}: {message[:150]}"
                self._add_info_with_limit(info)
                return
        
        for keyword in IMPORTANT_RESEARCH:
            if keyword in msg_lower:
                pesquisa = {
                    'texto': message[:100],
                    'timestamp': datetime.now().isoformat()
                }
                self.long_term.setdefault('pesquisas', [])
                existing_texts = [p['texto'] if isinstance(p, dict) else p for p in self.long_term['pesquisas']]
                if pesquisa['texto'] not in existing_texts:
                    self.long_term['pesquisas'].append(pesquisa)
                    self.long_term['pesquisas'] = self.long_term['pesquisas'][-20:]
                    print(f"[MEMORY] Pesquisa salva: {pesquisa['texto'][:50]}...")
                    self.save_long_term()
                return
    
    
    # ============================================================
    # _add_info_with_limit()
    # ============================================================
    # Propósito: Adicionar informação com limite
    #
    # Args:
    #   - info: Informação a adicionar
    # ============================================================
    def _add_info_with_limit(self, info: str):
        """
        Adiciona informação com limite de 50 itens.
        
        Args:
            info: Informação a adicionar
        """
        self.long_term.setdefault('informacoes', [])
        if info not in self.long_term['informacoes']:
            self.long_term['informacoes'].append(info)
            self.long_term['informacoes'] = self.long_term['informacoes'][-50:]
            print(f"[MEMORY] Informação importante salva: {info[:50]}...")
            self.save_long_term()
    
    
    # ============================================================
    # _cleanup()
    # ============================================================
    # Propósito: Limpar memória de curto prazo preservando contexto
    # ============================================================
    def _cleanup(self):
        """
        Limpa memória de curto prazo preservando contexto importante.
        """
        if len(self.short_term) < 12:
            return
        
        if len(self.short_term) > 20:
            greeting_phrases = ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite', 'e aí', 'opa']
            
            user_msgs = [m for m in self.short_term if m['role'] == 'user']
            
            preserve_user = []
            for msg in user_msgs[:-6]:
                content_lower = msg['content'].lower()
                if any(q in content_lower for q in ['?', 'como', 'por que', 'o que', 'qual', 'quem', 'onde', 'quando']):
                    preserve_user.append(msg)
            
            preserved_count = min(len(preserve_user), 4)
            kept = self.short_term[-6:] + preserve_user[-preserved_count:]
            
            while len(kept) > 6:
                first_msg = kept[0]['content'].lower()
                if any(greet in first_msg for greet in greeting_phrases):
                    kept = kept[2:]
                else:
                    break
            
            removed = len(self.short_term) - len(kept)
            self.short_term = kept
            
            if removed > 0:
                print(f"[MEMORY] Histórico comprimido: {removed} mensagens removidas")
    
    
    # ============================================================
    # clear_short_term()
    # ============================================================
    # Propósito: Limpar memória de curto prazo
    # ============================================================
    def clear_short_term(self):
        """
        Limpa memória de curto prazo mas mantém a longa.
        """
        self.short_term = []
        print("[MEMORY] Memória de curto prazo limpa")
    
    
    # ============================================================
    # clear_all()
    # ============================================================
    # Propósito: Limpar toda a memória
    # ============================================================
    def clear_all(self):
        """
        Limpa toda a memória (curta e longa).
        """
        self.short_term = []
        self.long_term = {'informacoes': [], 'apps_usados': [], 'sites_usados': [], 'pesquisas': []}
        self.save_long_term()
        print("[MEMORY] Toda a memória limpa")
    
    
    # ============================================================
    # add_app_used()
    # ============================================================
    # Propósito: Registrar app usado
    #
    # Args:
    #   - app_name: Nome do app
    # ============================================================
    def add_app_used(self, app_name: str):
        """
        Registra app usado.
        
        Args:
            app_name: Nome do aplicativo
        """
        if app_name not in self.long_term.get('apps_usados', []):
            self.long_term.setdefault('apps_usados', []).append(app_name)
            self.long_term['apps_usados'] = self.long_term['apps_usados'][-10:]
            self.save_long_term()
    
    
    # ============================================================
    # add_site_used()
    # ============================================================
    # Propósito: Registrar site usado
    #
    # Args:
    #   - site_name: Nome do site
    # ============================================================
    def add_site_used(self, site_name: str):
        """
        Registra site usado.
        
        Args:
            site_name: Nome do site
        """
        if site_name not in self.long_term.get('sites_usados', []):
            self.long_term.setdefault('sites_usados', []).append(site_name)
            self.long_term['sites_usados'] = self.long_term['sites_usados'][-10:]
            self.save_long_term()
    
    
    # ============================================================
    # restore_history()
    # ============================================================
    # Propósito: Restaurar histórico de conversa
    #
    # Args:
    #   - messages: Lista de mensagens
    # ============================================================
    def restore_history(self, messages: list):
        """
        Restaura histórico de uma conversa salva.
        
        Args:
            messages: Lista de mensagens a restaurar
        """
        self.short_term = []
        for msg in messages:
            if msg.get('role') in ['user', 'assistant']:
                self.short_term.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        print(f"[MEMORY] Histórico restaurado: {len(self.short_term)} mensagens")
