# ============================================
# MÓDULO DE RECONHECIMENTO DE INTENÇÕES
# ============================================
# Propósito: Processar intenções do usuário e rotear para módulos
#
# Funcionalidades:
#   - Keywords implícitas para contexto
#   - Detecção de intensidade emocional
#   - Negação e urgência
#   - Fuzzy matching (tolerância a erros)
#   - Contexto da conversa anterior
#   - Continuação de comandos
#
# Categorias processadas:
#   - conversa: Chat casual
#   - pesquisa: Pesquisa web
#   - acao: Ações (abrir apps, volume, brilho, etc)
#   - scan: Análise de tela
#   - info: Informações rápidas (hora, data, cálculo)
#
# Uso:
#   intent = Intent()
#   categoria, resposta = intent.process("qual a hora?")
# ============================================

import re
import os
import json
from difflib import get_close_matches
from datetime import datetime


# ============================================================
# Classe: Intent
# ============================================================
# Propósito: Recognizer de intenções do usuário
#
# Atributos:
#   - computer: Instância de Computer (lazy load)
#   - search: Instância de Search (lazy load)
#   - router: Instância de Router (lazy load)
#   - last_action: Última ação executada
#
# Métodos principais:
#   - process(): Processa mensagem e retorna (categoria, resposta)
#   - needs_research(): Verifica se precisa de pesquisa web
#   - has_action_intent(): Verifica se é intenção de ação
# ============================================================
class Intent:
    """
    Recognizer de intenções do usuário.
    
    Processa mensagens e roteia para módulos apropriados
    baseados em keywords, padrões e contexto.
    """
    # Palavras-chave que disparam uma AÇÃO (abrir app, site, arquivo)
    ACTION_KEYWORDS = ['abre', 'abrir', 'entra no', 'vai para', 'vá para', 'acessar', 'abra', 'inicia', 'iniciar', 'executa', 'rode']
    
    RESEARCH_KEYWORDS = [
        'pesquisar', 'buscar', 'procurar', 'notícias', 'clima', 'tempo',
        'preço', 'valor', 'cotação', 'quem é', 'o que é', 'como fazer',
        'onde fica', 'qual é', 'quantos', 'hoje', 'atual',
        'quanto ta', 'quanto está', 'quanto fica', 'quanto custa', 'custando',
        'valor do', 'preço do', 'cotação do', 'preço da', 'valor da',
        'em quanto', 'qual o preço', 'qual o valor', 'quantos custa'
    ]
    
    # Palavras que NÃO devem trigger pesquisa
    NO_SEARCH_KEYWORDS = [
        'ok', 'okay', 'tá bom', 'ta bom', 'blz', 'beleza', 'entendi',
        'entende', 'como assim', 'pq', 'porque', 'né', 'não', 'sim',
        'ola', 'oi', 'eai', 'bom dia', 'boa tarde', 'boa noite',
        'ele', 'ela', 'eles', 'elas', 'dele', 'dela', 'deles', 'delas',
    ]
    
    # ==================== INFO RÁPIDA ====================
    TIME_KEYWORDS = [
        'que horas', 'que hora', 'horas agora', 'que horas são', 'são horas',
        'que horas é', 'sao que horas', 'q horas', 'q hora',
        'me diz as horas', 'me diz as hora', 'fala as horas', 'diz as horas',
        'fala as hora', 'hora certa', 'qual a hora', 'hora é', 'que hora é',
        'me diz que horas', 'pode me dizer as horas', 'me fala as horas',
        'hora atual', 'que horas são agora', 'que hora agora',
        'que horas agora', 'q sao as horas', 'ta q horas', 'tá q horas',
        'sabe q horas', 'sabe que horas', 'vc sabe q horas'
    ]
    
    DATE_KEYWORDS = [
        'qual a data', 'que dia', 'que dia é hoje', 'que dia hoje',
        'data de hoje', 'hoje é', 'que data', 'qual a data de hoje',
        'me diz a data', 'que dia é', 'dia', 'data atual',
        'q dia é hoje', 'hoje é q dia', 'q data é hoje',
        'que dia é hj', 'hj é q dia'
    ]
    
    CALCULATE_KEYWORDS = [
        'quanto é', 'calcular', 'quanto dá', 'me calcula',
        'faça a conta', 'faz a conta', 'resultado de',
        'quanto resulta', 'operação', 'conta'
    ]
    
    # ==================== SCAN DA TELA ====================
    SCAN_KEYWORDS = [
        'scan', 'scan da tela', 'scaneia', 'scaneia a tela',
        'escaneia', 'escaneia a tela', 'escaneia tela', 'escaneio',
        'esaneia', 'escanear', 'escania', 'escanear',
        'analisa', 'analisa a tela', 'analisa tela', 'analise',
        'analise a tela', 'me fala o que tá na tela', 'me diz o que tem na tela',
        'o que tem na tela', 'o que tá na tela', 'o que está na tela',
        'veja a tela', 'veja isso', 've o que tem na tela',
        'olha a tela', 'olha isso', 'olha o que tem na tela',
        'captura a tela', 'captura tela', 'leia a tela', 'ler a tela',
        'ler tela', 'ver tela', 'verificar tela', 'ver a tela',
        'faz um scan', 'faz scan', 'tira foto da tela'
    ]
    
    # ==================== SPOTIFY ====================
    SPOTIFY_KEYWORDS = [
        'play', 'pause', 'toca', 'pausa', 'próxima música', 'proxima musica',
        'música anterior', 'musica anterior', 'próxima', 'anterior',
        'pula essa', 'pula música', 'toca essa', 'toca uma música',
        'stop', 'para música'
    ]
    
    # ==================== FECHAR JANELA ====================
    CLOSE_WINDOW_KEYWORDS = [
        'fecha isso', 'fecha a janela', 'fecha a aba', 'fechar janela',
        'fecha a tela', 'fecha tudo', 'encerra isso', 'encerra a janela',
        'fecha aba', 'encerra aba'
    ]
    
    # ==================== CLIPBOARD ====================
    CLIPBOARD_KEYWORDS = [
        'copia isso', 'copia o texto', 'copiar para clipboard', 'copiar texto',
        'copia o que', 'salva isso na memória', 'memória', 'copia',
        'salva na área de transferência', 'copia pra memória'
    ]
    
    # ==================== YOUTUBE ====================
    YOUTUBE_SEARCH_KEYWORDS = [
        'pesquisa no youtube', 'busca no youtube', 'procura no youtube',
        'pesquisa youtube', 'busca youtube', 'procura no yt',
        'pesquisar no youtube', 'buscar no youtube', 'busca no yt'
    ]
    
    # ==================== CONTROLE DE VOLUME (EXPANDIDO) ====================
    VOLUME_UP_KEYWORDS = [
        'aumente', 'aumente o', 'aumentar', 'aumenta', 'aumenta o', 'aumenta o volume',
        'sobe', 'subi', 'sube', 'sobe o', 'sobe o volume', 'subir o volume',
        'mais alto', 'mais alto o', 'volume mais alto', 'volume alto',
        'aumenta volume', 'sobe volume', 'mais alto volume',
        'volume up', 'aumenta o som', 'sobe o som', 'mais alto o som',
        'coloca mais alto', 'deixa mais alto', 'em cima', 'pau no volume',
        'queria mais alto', 'podia aumentar', 'sobe ai', 'aumenta ai'
    ]
    
    VOLUME_DOWN_KEYWORDS = [
        'diminua', 'diminua o', 'diminui', 'diminuir', 'diminui o', 'diminui o volume',
        'desce', 'descer', 'desce o', 'desce o volume',
        'abaixa', 'abaixar', 'abaixa o', 'abaixa o volume',
        'mais baixo', 'mais baixo o', 'volume mais baixo', 'volume baixo',
        'diminui volume', 'desce volume', 'mais baixo volume',
        'diminui o som', 'desce o som', 'mais baixo o som',
        'coloca mais baixo', 'deixa mais baixo', 'em baixo',
        'queria mais baixo', 'podia diminuir', 'abaixa ai', 'desce ai'
    ]
    
    MUTE_KEYWORDS = [
        'muta', 'mute', 'mutar', 'desmuta', 'desmute', 'desmutar',
        'silencia', 'silenciar', 'sem som', 'tira o som', 'tirar o som',
        'coloca no mudo', 'em mudo', 'no mudo', 'no mudo',
        'desliga o som', 'som desligado', 'som off'
    ]
    
    # ==================== CONTEXTO IMPLÍCITO DE VOLUME ====================
    VOLUME_CONTEXT_UP = [
        'mais alto', 'mais alto o', 'muito alto', 'tá muito alto',
        'alto demais', 'demais', 'intenso', 'barulhento', 'barulho',
        'ruidoso', 'tá fazendo barulho', 'preciso de mais volume',
        'aumenta isso', 'sobe isso', 'coloca mais', 'mais volume',
        'na moral', 'tá zuando', 'muito', 'excessivo'
    ]
    
    VOLUME_CONTEXT_DOWN = [
        'mais baixo', 'mais baixo o', 'muito baixo', 'tá muito baixo',
        'baixo demais', 'preciso de silêncio', 'silêncio aqui',
        'calma o barulho', 'diminui isso', 'desce isso', 'abaixa isso',
        'abaixo', 'abaixe', 'não consigo ouvir', 'difícil ouvir',
        'mto alto', 'oferecendo', 'não consigo escutar'
    ]
    
    # ==================== CONTEXTO IMPLÍCITO DE BRILHO ====================
    BRILHO_CONTEXT_UP = [
        'escuro', 'escura', 'dark', 'tá escuro', 'não consigo ver',
        'difícil ver', 'não tô vendo', 'não vejo', 'cegos',
        'preciso de luz', 'mais claridade', 'clara essa tela',
        'escuro demais', 'escura demais', 'muito escuro',
        'quarto escuro', 'sala escura', 'ambiente escuro',
        'não tá enxergando', 'não dá pra ver', 'tá péssimo pra ver',
        'preciso ver isso', 'queria ver melhor', 'melhora a visão'
    ]
    
    BRILHO_CONTEXT_DOWN = [
        'muito claro', 'tá clarão', 'brilhante', 'ofuscante',
        'dói os olhos', 'cansando a vista', 'vista cansada',
        'muito brilho', 'glare', 'ofuscando', 'não aguento',
        'claro demais', 'muito branco', 'cega', 'dói', 'queima',
        'tá ofuscante', 'luminosidade alta', 'luz demais'
    ]
    
    # ==================== EMERGÊNCIA/URGÊNCIA ====================
    URGENCY_WORDS = [
        'agora', 'já', 'rápido', 'urgente', 'imediatamente',
        'socorro', 'help', 'ajuda', 'emergência', 'eita',
        'pqp', 'caralho', 'puta', 'merda', 'fuck', 'damn',
        'gente', 'meu deus', 'senhor', 'crl', 'krl', 'vsf'
    ]
    
    # ==================== NEGAÇÃO ====================
    NEGATION_WORDS = [
        'não', 'nao', 'nunca', 'jamais', 'nem', 'nenhum',
        'cancela', 'para', 'para isso', 'para tudo',
        'esquece', 'deixa', 'não precisa', 'dispensável',
        'n', 'ñ', 'nunk', 'unk'
    ]
    
    # ==================== CONTINUAÇÃO ====================
    CONTINUATION_WORDS = [
        'mais', 'mais ainda', 'outra vez', 'de novo', 'repete',
        'deixa', 'só', 'só que', 'porém', 'mas', 'então',
        'o que', 'quem', 'onde', 'por que', 'pq', 'como',
        'e aí', 'e depois', 'depois disso', 'e também',
        'ademais', 'além disso', 'incluindo', 'inclusive'
    ]
    
    # ==================== DESFAZER ====================
    UNDO_WORDS = [
        'desfaz', 'volta', 'cancela', 'desfazer', 'reverte',
        'desfaz isso', 'volta atrás', 'cancela isso', 'para isso',
        'interrompe', 'para de fazer', 'para tudo', 'chega'
    ]
    
    # ==================== BRILHO ====================
    BRIGHTNESS_UP_KEYWORDS = [
        'aumenta o brilho', 'sobe o brilho', 'mais claro', 'brilho mais alto',
        'aumenta brilho', 'sobe brilho', 'claridade mais', 'aumentar brilho'
    ]
    
    BRIGHTNESS_DOWN_KEYWORDS = [
        'diminui o brilho', 'desce o brilho', 'mais escuro', 'brilho mais baixo',
        'diminui brilho', 'desce brilho', 'claridade menos', 'diminuir brilho'
    ]
    
    NIGHT_LIGHT_KEYWORDS = [
        'modo noturno', 'night light', 'luz noturna', 'noturno',
        'ativa noturno', 'desativa noturno', 'ativar modo noturno'
    ]
    
    # ==================== SCREENSHOT ====================
    SCREENSHOT_KEYWORDS = [
        'tira um print', 'tira print', 'print', 'screenshot', 'captura tela',
        'fotografia da tela', 'foto da tela', 'imagem da tela',
        'tira uma foto da tela', 'print da tela'
    ]
    
    # ==================== SISTEMA ====================
    LOCK_KEYWORDS = [
        'bloqueia o pc', 'bloqueia pc', 'bloqueia', 'tranca', 'trancar',
        'bloquear pc', 'lock', 'lock screen', 'tela bloqueada',
        'bloqueia a tela', 'segura a tela', 'segurar'
    ]
    
    SHUTDOWN_KEYWORDS = [
        'desliga', 'desligar', 'desliga o pc', 'desliga pc',
        'shutdown', 'desligando', 'desliga aí', 'desliga isso'
    ]
    
    RESTART_KEYWORDS = [
        'reinicia', 'reiniciar', 'reinicia o pc', 'reinicia pc',
        'restart', 'reinício', 'reboot'
    ]
    
    # ==================== PASTAS ====================
    FOLDER_KEYWORDS = [
        'pasta', 'pasta de', 'pasta do', 'diretorio', 'diretório',
        'minha pasta', 'abre a pasta', 'abre a', 'abre minha'
    ]
    
    # ==================== PESQUISA GOOGLE ====================
    SEARCH_GOOGLE_KEYWORDS = [
        'pesquisa', 'busca', 'procurar', 'pesquisar',
        'pesquisa no google', 'busca no google', 'procurar no google',
        'busca no google', 'pesquisa google', 'busca google',
        'pesquisa no', 'busca no', 'procurar no'
    ]
    
    SEARCH_GOOGLE_PATTERNS = [
        r'google\s+e\s+(?:pesquis[ae]|busca|procura)\s+(?:o\s+)?(.+)',
        r'google\s+(?:pesquis[ae]|busca|procura)\s+(?:o\s+)?(.+)',
        r'pesquis[ae]\s+(?:o\s+)?(.+?)\s+no\s+google',
        r'busca\s+(?:o\s+)?(.+?)\s+no\s+google',
        r'procura\s+(?:o\s+)?(.+?)\s+no\s+google',
        r'^(?:pesquis[ae]|busca|procura)\s+(?:o\s+)?(?:google\s+)?(?:por\s+)?(.+)',
    ]
    
    # ==================== TRADUÇÃO ====================
    TRANSLATE_KEYWORDS = [
        'traduz', 'traduzir', 'tradução', 'traduz isso',
        'me traduz', 'traduz para mim', 'ingles', 'espanhol'
    ]
    
    # ==================== CRIAR NOTA ====================
    CREATE_NOTE_KEYWORDS = [
        'cria uma nota', 'criar nota', 'anotação', 'faz uma nota',
        'cria um lembrete', 'salva isso', 'anota isso', 'grave isso',
        'cria nota', 'nova nota', 'escreve isso'
    ]
    
    # ==================== EMAIL ====================
    EMAIL_KEYWORDS = [
        'email', 'e-mail', 'gmail', 'correio', 'caixa de entrada',
        'meu email', 'abrir email', 'abrir gmail', 'ver emails'
    ]
    
    SITES = {
        'gmail': 'https://mail.google.com', 'google': 'https://www.google.com',
        'youtube': 'https://www.youtube.com', 'spotify': 'https://open.spotify.com',
        'netflix': 'https://www.netflix.com', 'facebook': 'https://www.facebook.com',
        'instagram': 'https://www.instagram.com', 'twitter': 'https://twitter.com',
        'whatsapp': 'https://web.whatsapp.com', 'telegram': 'https://web.telegram.org',
        'globo': 'https://globo.com', 'g1': 'https://g1.globo.com',
        'github': 'https://github.com', 'linkedin': 'https://linkedin.com',
        'chatgpt': 'https://chat.openai.com', 'claude': 'https://claude.ai',
        'maps': 'https://maps.google.com', 'drive': 'https://drive.google.com',
    }
    
    APPS = {
        'chrome': 'chrome', 'navegador': 'chrome', 'firefox': 'firefox',
        'spotify': 'spotify', 'discord': 'discord', 'notepad': 'notepad',
        'calculadora': 'calc', 'explorador': 'explorer', 'vscode': 'code',
        'logitech': 'Logitech G Hub', 'logitech hub': 'Logitech G Hub',
        'logitech g hub': 'Logitech G Hub',
        'steam': 'steam', 'epic': 'Epic Games Launcher', 'epic games': 'Epic Games Launcher',
        'whatsapp': 'WhatsApp', 'telegram': 'Telegram', 'teams': 'Teams',
        'zoom': 'Zoom', 'skype': 'Skype',
        'obs': 'obs64', 'obs studio': 'obs64',
        'vlc': 'vlc', 'vlc media player': 'vlc',
        'winrar': 'winrar', '7zip': '7zFM',
        'word': 'winword', 'excel': 'excel', 'powerpoint': 'powerpnt',
        'blender': 'blender', 'photoshop': 'Photoshop', 'figma': 'Figma',
        'claude': 'Claude', 'claude desktop': 'Claude',
        'chatgpt': 'ChatGPT', 'copilot': 'Copilot',
        'task manager': 'taskmgr', 'gerenciador de tarefas': 'taskmgr',
        'terminal': 'cmd', 'prompt': 'cmd', 'cmd': 'cmd',
    }
    
    def __init__(self):
        self.computer = None
        self.search = None
        self.router = None
        self.last_action = None  # Salva última ação
        self._load_last_action()
    
    def _load_last_action(self):
        """Carrega última ação do arquivo"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            action_file = os.path.join(base_dir, 'data', 'last_action.json')
            if os.path.exists(action_file):
                with open(action_file, 'r') as f:
                    self.last_action = json.load(f)
        except:
            self.last_action = None
    
    def _save_last_action(self, action_type, params):
        """Salva última ação"""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            action_file = os.path.join(base_dir, 'data', 'last_action.json')
            self.last_action = {
                'type': action_type,
                'params': params,
                'timestamp': datetime.now().isoformat()
            }
            with open(action_file, 'w') as f:
                json.dump(self.last_action, f)
        except:
            pass
    
    def _get_router(self):
        if self.router is None:
            from src.core.router import Router
            self.router = Router()
        return self.router
    
    def _get_computer(self):
        if self.computer is None:
            from src.modules.computer import Computer
            self.computer = Computer()
        return self.computer
    
    def _get_search(self):
        if self.search is None:
            from src.modules.search import Search
            self.search = Search()
        return self.search
    
    def _fix_common_typos(self, text):
        """Corrige erros comuns de digitação"""
        typos = {
            'vc ': 'você ',
            'vcs ': 'vocês ',
            'tb ': 'também ',
            'tbm ': 'também ',
            'pq ': 'porque ',
            'qdo ': 'quando ',
            'qd ': 'quando ',
            'ngm ': 'ninguém ',
            'tlg ': 'tá logo ',
            'gnt ': 'gente ',
            'msm ': 'mesmo ',
            'cmg ': 'comigo ',
            'ctza ': 'certeza ',
            'vlw ': 'valeu ',
            'flw ': 'falou ',
            'obg ': 'obrigado ',
            'tmj ': 'tamo junto ',
            'sj ': 'será que ',
            'nd ': 'nada ',
            'blz ': 'beleza ',
        }
        for typo, correct in typos.items():
            text = text.replace(typo, correct)
        return text
    
    def _fuzzy_match_any(self, text, keywords):
        """Faz matching fuzzy-tolerant"""
        text_lower = text.lower()
        
        # Tenta match direto
        for kw in keywords:
            if kw in text_lower or text_lower in kw:
                return True
        
        # Tenta fuzzy
        for kw in keywords:
            if get_close_matches(text_lower, [kw], n=1, cutoff=0.8):
                return True
        
        return False
    
    def _detect_negation(self, text):
        """Detecta se há negação no texto"""
        text_lower = text.lower()
        for neg in self.NEGATION_WORDS:
            if neg in text_lower:
                return True
        return False
    
    def _detect_urgency(self, text):
        """Detecta urgência no texto"""
        text_lower = text.lower()
        for urg in self.URGENCY_WORDS:
            if urg in text_lower:
                return True
        return False
    
    def _detect_continuation(self, text):
        """Detecta se é continuação"""
        text_lower = text.lower()
        for cont in self.CONTINUATION_WORDS:
            if cont in text_lower:
                return True
        return False
    
    def _detect_intensity(self, text):
        """Detecta nível de intensidade (1-5)"""
        high_intensity = ['muito', 'demais', 'super', 'ultra', 'mega', 
                         'extremamente', 'incrivelmente', 'tão', 'demaiss',
                         'pac<PAD>', ' demais']
        medium_intensity = ['um pouco', 'ligeiramente', 'algum', 'bastante', 'mais']
        low_intensity = ['só', 'apenas', 'quase', 'nem', 'pouco']
        
        text_lower = text.lower()
        
        if any(w in text_lower for w in high_intensity):
            return 5
        elif any(w in text_lower for w in medium_intensity):
            return 3
        elif any(w in text_lower for w in low_intensity):
            return 1
        return 2
    
    def _check_keywords(self, text_lower, keywords):
        """Verifica se alguma keyword está no texto"""
        for kw in keywords:
            if kw in text_lower:
                return True
        return False
    
    def _extract_query(self, text, remove_words):
        """Extrai query removendo palavras específicas"""
        result = text.lower()
        for word in remove_words:
            result = result.replace(word, '')
        return result.strip()
    
    def _is_math(self, text):
        """Verifica se o texto contém cálculo matemático"""
        tem_numero = bool(re.search(r'\d', text))
        tem_operador = any(op in text for op in ['+', '-', '*', '/', '%', 'x'])
        palavras_calculo = ['quanto é', 'calcul', 'quanto dá', 'me calcula', 'faz a conta', 'resultado de']
        tem_palavra = any(p in text for p in palavras_calculo)
        return (tem_numero and tem_palavra) or (tem_numero and tem_operador)
    
    def needs_research(self, text):
        text_lower = text.lower()
        
        for kw in self.NO_SEARCH_KEYWORDS:
            if text_lower == kw:
                return False
        
        if len(text_lower.strip()) < 5:
            return False
        
        price_triggers = ['quanto ta', 'quanto está', 'quanto fica', 'quanto custa', 'custando',
                         'preço', 'valor', 'cotação', 'preço do', 'valor do', 'cotação do',
                         'preço da', 'valor da', 'em quanto', 'qual o preço', 'qual o valor']
        for kw in price_triggers:
            if kw in text_lower:
                return True
        
        for kw in self.RESEARCH_KEYWORDS:
            if kw in text_lower:
                return True
        
        question_starts = ['o que é', 'quem é', 'onde fica', 'qual é', 'quando foi',
                   'por que', 'como fazer', 'como funciona', 'como instalar',
                   'como usar', 'como configurar']
        for qs in question_starts:
            if text_lower.startswith(qs):
                return True
        
        return False
    
    def has_action_intent(self, text):
        text_lower = text.lower()
        for keyword in self.ACTION_KEYWORDS:
            if keyword in text_lower:
                return True
        return False
    
    def process(self, text: str) -> tuple:
        """
        Processa mensagem do usuário e retorna categoria e resposta.
        
        Args:
            text: Mensagem do usuário
        
        Returns:
            tuple: (categoria, resposta)
                - categoria: 'conversa', 'pesquisa', 'acao', 'scan', 'info'
                - resposta: Resposta imediata ou None
        
        Fluxo:
            1. Pré-processamento (correção de typos)
            2. Detecção de características (negação, urgência, intensidade)
            3. Classificação via Router
            4. Verificações prioritárias (agradecimentos, scan, etc)
            5. Ações específicas (volume, brilho, sistema)
            6. Fallback para Router categorizar
        """
        print(f"[INTENT] Mensagem recebida: {text}")
        
        text_lower = text.lower().strip()
        
        # PRÉ-PROCESSAMENTO
        text_lower = self._fix_common_typos(text_lower)
        
        print(f"[INTENT] Processando mensagem: {text_lower[:50]}...")
        
        # Detecta características da mensagem
        has_negation = self._detect_negation(text_lower)
        has_urgency = self._detect_urgency(text_lower)
        has_continuation = self._detect_continuation(text_lower)
        intensity = self._detect_intensity(text_lower)
        
        # Usa o router para classificar a mensagem
        router = self._get_router()
        router_category = router.classify(text)
        
        # ==================== VERIFICAÇÕES PRIORITÁRIAS ====================
        
        # 0. AGRADECIMENTOS vão para conversa
        agradecimentos = ['obrigado', 'obrigada', 'valeu', 'vlw', 'tmj', 'muito obrigado', 'grato']
        if any(a in text_lower for a in agradecimentos):
            print(f"[INTENT] Categoria: agradecimento → conversa")
            return ('conversa', None)
        
        # 1. SCAN DA TELA (com fuzzy + verificação de tamanho)
        if len(text_lower) > 5 and self._fuzzy_match_any(text_lower, self.SCAN_KEYWORDS):
            print(f"[INTENT] Categoria: scan_tela")
            return ('scan', None)
        
        # 2. ABRIR GOOGLE COM PESQUISA (alta prioridade)
        is_google_search = 'google' in text_lower or self._check_keywords(text_lower, self.SEARCH_GOOGLE_KEYWORDS)
        if is_google_search and len(text_lower) > 15:
            print(f"[INTENT] Categoria: search_google")
            computer = self._get_computer()
            
            # Tenta extrair query com os patterns
            query = None
            for pattern in self.SEARCH_GOOGLE_PATTERNS:
                match = re.search(pattern, text_lower)
                if match and match.group(1).strip():
                    query = match.group(1).strip()
                    print(f"[INTENT] Query extraída via pattern: {query}")
                    break
            
            # Fallback: pega tudo após "pesquisa"/"busca"/"google"
            if not query or len(query) < 2:
                for trigger in ['pesquisa', 'busca', 'procura', 'google']:
                    if trigger in text_lower:
                        idx = text_lower.find(trigger) + len(trigger)
                        query = text_lower[idx:].strip()
                        for prep in [' no ', ' na ', ' por ', ' o ', ' a ', ' e ']:
                            if query.startswith(prep):
                                query = query[len(prep):]
                        break
            
            # Remove artigos e preposições do início
            if query:
                query = query.strip()
                for article in ['o ', 'a ', 'os ', 'as ', 'no ', 'na ', 'por ', 'para ']:
                    if query.startswith(article):
                        query = query[len(article):]
                query = query.strip()
            
            if query and len(query) > 1:
                print(f"[INTENT] Pesquisando no Google: {query}")
                result = computer.search_google(query)
                self._save_last_action('search', {'query': query})
                return ('acao', f"Pesquisando '{query}' no Google...")
            return ('acao', "O que você quer pesquisar?")
        
        # 3. CONTINUAÇÃO/INCREMENTO
        if has_continuation and self.last_action:
            print(f"[INTENT] Categoria: continuação")
            result = self._handle_continuation(text_lower, intensity)
            if result:
                return result
        
        # 4. DESFAZER
        if self._check_keywords(text_lower, self.UNDO_WORDS):
            print(f"[INTENT] Categoria: desfazer")
            if self.last_action:
                result = self._handle_undo()
                if result:
                    return result
        
        # 5. INFORMAÇÕES RÁPIDAS (não precisa IA)
        if self._check_keywords(text_lower, self.TIME_KEYWORDS):
            print(f"[INTENT] Categoria: info_hora")
            computer = self._get_computer()
            hora = computer.get_time()
            return ('info', f"São {hora}.")
        
        if self._check_keywords(text_lower, self.DATE_KEYWORDS):
            print(f"[INTENT] Categoria: info_data")
            computer = self._get_computer()
            data = computer.get_date()
            return ('info', f"Hoje é {data}.")
        
        # 6. CÁLCULO
        if self._check_keywords(text_lower, self.CALCULATE_KEYWORDS):
            print(f"[INTENT] Categoria: calcular")
            computer = self._get_computer()
            expr = self._extract_query(text, ['quanto é', 'calcular', 'quanto dá', 'me calcula',
                                               'faça a conta', 'faz a conta', 'resultado de'])
            if expr:
                result = computer.calculate(expr)
                return ('info', result)
        
        # 6. CONTEXTO IMPLÍCITO DE VOLUME (detecção de "mente")
        cortesia = ['obrigado', 'obrigada', 'valeu', 'vlw', 'tmj', 'tamo junto', 'muito obrigado']
        if any(c in text_lower for c in cortesia):
            pass  # pula verificação de volume
        elif self._check_keywords(text_lower, self.VOLUME_CONTEXT_UP) or \
           self._check_keywords(text_lower, self.VOLUME_CONTEXT_DOWN):
             
            if has_negation:
                # "não quero barulho" → mutar
                print(f"[INTENT] Categoria: volume_contexto (negação) → mute")
                computer = self._get_computer()
                result = computer.set_mute()
                self._save_last_action('mute', {})
                return ('acao', result)
            
            elif self._check_keywords(text_lower, self.VOLUME_CONTEXT_UP) or \
                 'mais alto' in text_lower or intensity >= 4:
                # "tá muito barulhento" → aumentar volume
                delta = intensity * 2  # 2-10%
                print(f"[INTENT] Categoria: volume_contexto_up ({delta}%)")
                computer = self._get_computer()
                result = computer.set_volume(delta)
                self._save_last_action('volume', {'delta': delta})
                return ('acao', result)
            else:
                # "preciso de silêncio" → diminuir volume
                delta = intensity * 2
                print(f"[INTENT] Categoria: volume_contexto_down ({delta}%)")
                computer = self._get_computer()
                result = computer.set_volume(-delta)
                self._save_last_action('volume', {'delta': -delta})
                return ('acao', result)
        
        # 7. CONTEXTO IMPLÍCITO DE BRILHO (detecção de "mente")
        if self._check_keywords(text_lower, self.BRILHO_CONTEXT_UP) or \
           self._check_keywords(text_lower, self.BRILHO_CONTEXT_DOWN):
            
            if self._check_keywords(text_lower, self.BRILHO_CONTEXT_UP) or \
               any(w in text_lower for w in ['escuro', 've', 'visão', 'ver', 'enxergar']):
                # "não consigo ver" → aumentar brilho
                delta = intensity * 2
                print(f"[INTENT] Categoria: brilho_contexto_up ({delta}%)")
                computer = self._get_computer()
                result = computer.adjust_brightness(delta)
                self._save_last_action('brilho', {'delta': delta})
                return ('acao', result)
            else:
                # "muito claro" → diminuir brilho
                delta = intensity * 2
                print(f"[INTENT] Categoria: brilho_contexto_down ({delta}%)")
                computer = self._get_computer()
                result = computer.adjust_brightness(-delta)
                self._save_last_action('brilho', {'delta': -delta})
                return ('acao', result)
        
        # 8. CONTROLE DE BRILHO (explícito)
        # Brilho direto - "brilho em 80%", "brilho pra 50%"
        if 'brilho' in text_lower:
            brightness_match = re.search(r'(?:em|para|pra|no)\s*(\d+)%?', text_lower)
            if brightness_match:
                value = int(brightness_match.group(1))
                if 0 <= value <= 100:
                    print(f"[INTENT] Categoria: brilho_direto")
                    computer = self._get_computer()
                    result = computer.set_brightness(value)
                    self._save_last_action('brilho', {'level': value})
                    return ('acao', result)
        
        if self._check_keywords(text_lower, self.BRIGHTNESS_UP_KEYWORDS):
            print(f"[INTENT] Categoria: brilho_up")
            computer = self._get_computer()
            result = computer.adjust_brightness(10)
            self._save_last_action('brilho', {'delta': 10})
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.BRIGHTNESS_DOWN_KEYWORDS):
            print(f"[INTENT] Categoria: brilho_down")
            computer = self._get_computer()
            result = computer.adjust_brightness(-10)
            self._save_last_action('brilho', {'delta': -10})
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.NIGHT_LIGHT_KEYWORDS):
            print(f"[INTENT] Categoria: night_light")
            computer = self._get_computer()
            result = computer.toggle_night_light()
            return ('acao', result)
        
        # 9. CONTROLE DE VOLUME (explícito)
        # Volume direto - "volume em 50%", "volta pra 80%"
        if 'volume' in text_lower:
            direct_match = re.search(r'(?:em|para|pra|no)\s*(\d+)%?', text_lower)
            if direct_match:
                value = int(direct_match.group(1))
                if 0 <= value <= 100:
                    print(f"[INTENT] Categoria: volume_direto")
                    computer = self._get_computer()
                    result = computer.set_volume_to(value)
                    self._save_last_action('volume', {'level': value})
                    return ('acao', result)
        
        # Aumenta para X%
        volume_up = re.search(r'(aument[ae]|sobe|subi|sube|sai|a\+\+)\s*(?:o\s*)?(?:volume\s*)?(?:para|pra|no|)\s*(\d+)%?', text_lower)
        if volume_up:
            print(f"[INTENT] Categoria: volume_up_com_valor")
            computer = self._get_computer()
            value = int(volume_up.group(2))
            result = computer.set_volume_to(value)
            self._save_last_action('volume', {'level': value})
            return ('acao', result)
        
        # Diminui para X% ou em X%
        volume_down = re.search(r'(diminui|desce|abaixa|reduz)\s*(?:o\s*)?(?:volume\s*)?(?:para|pra|em|no|)\s*(\d+)%?', text_lower)
        if volume_down:
            print(f"[INTENT] Categoria: volume_down_com_valor")
            computer = self._get_computer()
            value = int(volume_down.group(2))
            result = computer.set_volume_to(value)
            self._save_last_action('volume', {'level': value})
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.VOLUME_UP_KEYWORDS):
            print(f"[INTENT] Categoria: volume_up")
            computer = self._get_computer()
            result = computer.set_volume(5)
            self._save_last_action('volume', {'delta': 5})
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.VOLUME_DOWN_KEYWORDS):
            print(f"[INTENT] Categoria: volume_down")
            computer = self._get_computer()
            result = computer.set_volume(-5)
            self._save_last_action('volume', {'delta': -5})
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.MUTE_KEYWORDS):
            print(f"[INTENT] Categoria: mute")
            computer = self._get_computer()
            result = computer.set_mute()
            self._save_last_action('mute', {})
            return ('acao', result)
        
        # 10. SCREENSHOT
        if self._check_keywords(text_lower, self.SCREENSHOT_KEYWORDS):
            print(f"[INTENT] Categoria: screenshot")
            computer = self._get_computer()
            result = computer.take_screenshot()
            if result and not result.startswith("Erro"):
                self._save_last_action('screenshot', {'path': result})
                return ('acao', f"Print salvo em: {result}")
            return ('acao', result)
        
        # 10.1 SPOTIFY
        if self._check_keywords(text_lower, self.SPOTIFY_KEYWORDS):
            print(f"[INTENT] Categoria: spotify")
            computer = self._get_computer()
            action = 'play'
            if 'pause' in text_lower or 'pausa' in text_lower:
                action = 'pause'
            elif 'próxima' in text_lower or 'proxima' in text_lower or 'pula' in text_lower:
                action = 'next'
            elif 'anterior' in text_lower:
                action = 'previous'
            result = computer.spotify_control(action)
            return ('acao', result)
        
        # 10.2 FECHAR JANELA
        if self._check_keywords(text_lower, self.CLOSE_WINDOW_KEYWORDS):
            print(f"[INTENT] Categoria: close_window")
            computer = self._get_computer()
            result = computer.close_window()
            return ('acao', result)
        
        # 10.3 CLIPBOARD
        if self._check_keywords(text_lower, self.CLIPBOARD_KEYWORDS):
            print(f"[INTENT] Categoria: clipboard")
            computer = self._get_computer()
            text_to_copy = self._extract_query(text, ['copia', 'copiar', 'copia isso', 'copia o', 'copia pra'])
            if text_to_copy:
                result = computer.copy_to_clipboard(text_to_copy)
                return ('acao', result)
            return ('acao', "O que você quer copiar?")
        
        # 10.4 YOUTUBE
        if self._check_keywords(text_lower, self.YOUTUBE_SEARCH_KEYWORDS):
            print(f"[INTENT] Categoria: youtube_search")
            computer = self._get_computer()
            query = self._extract_query(text, ['youtube', 'pesquisa', 'busca', 'procura', 'pesquisar', 'buscar'])
            if query:
                result = computer.search_youtube(query)
                return ('acao', result)
            return ('acao', "O que você quer pesquisar no YouTube?")
        
        # 11. BLOQUEAR PC
        if self._check_keywords(text_lower, self.LOCK_KEYWORDS):
            print(f"[INTENT] Categoria: lock")
            computer = self._get_computer()
            result = computer.lock_screen()
            return ('acao', result)
        
        # 12. DESLIGAR / REINICIAR
        if self._check_keywords(text_lower, self.SHUTDOWN_KEYWORDS):
            print(f"[INTENT] Categoria: shutdown")
            computer = self._get_computer()
            result = computer.shutdown_pc()
            return ('acao', result)
        
        if self._check_keywords(text_lower, self.RESTART_KEYWORDS):
            print(f"[INTENT] Categoria: restart")
            computer = self._get_computer()
            result = computer.restart_pc()
            return ('acao', result)
        
        # 14. TRADUZIR
        if self._check_keywords(text_lower, self.TRANSLATE_KEYWORDS):
            print(f"[INTENT] Categoria: traduzir")
            computer = self._get_computer()
            text_to_translate = self._extract_query(text, ['traduz', 'traduzir', 'tradução',
                                                           'traduz isso', 'me traduz', 'traduz para mim'])
            if text_to_translate and len(text_to_translate) > 1:
                result = computer.translate_text(text_to_translate)
                return ('acao', f"Traduzindo '{text_to_translate}'...")
            result = computer.translate_text()
            return ('acao', "Abrindo tradutor...")
        
        # 15. CRIAR NOTA
        if self._check_keywords(text_lower, self.CREATE_NOTE_KEYWORDS):
            print(f"[INTENT] Categoria: criar_nota")
            computer = self._get_computer()
            note_content = self._extract_query(text, ['cria uma nota', 'criar nota', 'anotação',
                                                       'faz uma nota', 'cria um lembrete', 'salva isso',
                                                       'anota isso', 'grave isso', 'cria nota', 'nova nota',
                                                       'escreve isso'])
            if note_content:
                result = computer.create_note(note_content, note_content)
                self._save_last_action('create_note', {'content': note_content})
                return ('acao', result)
            return ('acao', "O que você quer anotar?")
        
        # 16. ABRIR PASTA ESPECIAL
        special_folders = ['downloads', 'download', 'documentos', 'imagens', 'fotos', 
                          'desktop', 'músicas', 'vídeos', 'videos', 'pasta de downloads',
                          'pasta de documentos', 'pasta de imagens', 'pasta do desktop']
        for folder in special_folders:
            if folder in text_lower:
                print(f"[INTENT] Categoria: abrir_pasta ({folder})")
                computer = self._get_computer()
                folder_name = folder.replace('pasta de ', '').replace('pasta do ', '').replace('pasta ', '')
                result = computer.open_special_folder(folder_name)
                self._save_last_action('open_folder', {'folder': folder_name})
                return ('acao', result)
        
        # 17. ABRIR EMAIL
        if self._check_keywords(text_lower, self.EMAIL_KEYWORDS):
            print(f"[INTENT] Categoria: abrir_email")
            computer = self._get_computer()
            result = computer.open_url('https://mail.google.com')
            self._save_last_action('open_url', {'url': 'gmail'})
            return ('acao', "Abrindo Gmail...")
        
        # 18. AÇÃO (Router)
        if router_category == 'acao':
            print(f"[INTENT] Categoria: ação (router)")
            
            result = self._handle_open_site(text, text_lower)
            if result:
                self._save_last_action('open_url', {'text': text})
                return ('acao', result)
            
            result = self._handle_open_app(text, text_lower)
            if result:
                self._save_last_action('open_app', {'text': text})
                return ('acao', result)
            
            return ('acao', None)
        
        # 19. PESQUISA
        if router_category == 'pesquisa' or self.needs_research(text):
            print(f"[INTENT] Categoria: pesquisa")
            print(f"[INTENT] Chamando módulo: search")
            result = self._handle_search(text, text_lower)
            if result:
                self._save_last_action('search', {'text': text})
                return ('pesquisa', result)
            return ('pesquisa', None)
        
        # 20. Conversa ou Análise
        print(f"[INTENT] Categoria: {router_category}")
        return (router_category, None)
    
    def _handle_continuation(self, text_lower, intensity):
        """Trata continuação de comandos anteriores"""
        if not self.last_action:
            return None
        
        action_type = self.last_action.get('type')
        params = self.last_action.get('params', {})
        
        # "mais" → incrementa baseado na última ação
        if 'mais' in text_lower or intensity > 2:
            if action_type == 'volume':
                computer = self._get_computer()
                delta = intensity * 2
                result = computer.set_volume(delta)
                self._save_last_action('volume', {'delta': delta})
                return ('acao', result)
            
            elif action_type == 'brilho':
                computer = self._get_computer()
                delta = intensity * 2
                result = computer.adjust_brightness(delta)
                self._save_last_action('brilho', {'delta': delta})
                return ('acao', result)
        
        return None
    
    def _handle_undo(self):
        """Desfaz última ação"""
        if not self.last_action:
            return ('acao', "Não tenho nada para desfazer.")
        
        action_type = self.last_action.get('type')
        params = self.last_action.get('params', {})
        
        if action_type == 'volume':
            computer = self._get_computer()
            delta = params.get('delta', 5)
            # Desfaz invertendo o delta
            result = computer.set_volume(-delta)
            return ('acao', f"Desfeito. {result}")
        
        elif action_type == 'brilho':
            computer = self._get_computer()
            delta = params.get('delta', 10)
            result = computer.adjust_brightness(-delta)
            return ('acao', f"Desfeito. {result}")
        
        elif action_type == 'mute':
            computer = self._get_computer()
            result = computer.set_mute()
            return ('acao', f"Desfeito. {result}")
        
        return ('acao', "Não consegui desfazer essa ação.")
    
    def _handle_open_site(self, text, text_lower):
        computer = self._get_computer()
        
        for kw in self.ACTION_KEYWORDS:
            text_lower = text_lower.replace(kw, '')
        
        text_lower = text_lower.strip()
        
        for site_name, url in self.SITES.items():
            if site_name in text_lower:
                return computer.open_url_python_site(site_name)
        
        if 'http://' in text or 'https://' in text:
            url_match = re.search(r'https?://[^\s]+', text)
            if url_match:
                url = url_match.group(0)
                return computer.open_url(url)
        
        return None
    
    def _handle_open_app(self, text, text_lower):
        computer = self._get_computer()
        
        if text.startswith('file://') or text.startswith('C:') or text.startswith('/'):
            path = text
            if text.startswith('file://'):
                path = text.replace('file:///', '').replace('/', '\\')
            return computer.open_file(path)
        
        for kw in self.ACTION_KEYWORDS:
            text_lower = text_lower.replace(kw, '')
        
        app_name = text_lower.strip()
        
        if app_name.startswith('o '):
            app_name = app_name[2:].strip()
        if app_name.startswith('a '):
            app_name = app_name[2:].strip()
        app_name = app_name.replace(' o ', ' ').replace(' a ', ' ').strip()
        
        for known_app, command in self.APPS.items():
            if known_app in app_name:
                result = computer.open_app(command)
                return result
        
        # Fuzzy match para apps
        for known_app, command in self.APPS.items():
            if get_close_matches(app_name, [known_app], n=1, cutoff=0.6):
                print(f"[INTENT] Fuzzy match: {app_name} → {known_app}")
                result = computer.open_app(command)
                return result
        
        if app_name:
            result = computer.open_app(app_name)
            if result and 'não encontrado' not in result.lower():
                return result
        
        return None
    
    def _handle_search(self, text, text_lower):
        search = self._get_search()
        
        query = text_lower
        remove_words = ['pesquisar', 'buscar', 'procurar', 'pesquisa', 'busca', 
                       'na web', 'sobre', 'o que é', 'quem é', 'qual é']
        for word in remove_words:
            query = query.replace(word, '')
        
        query = query.strip()
        
        if not query or len(query) < 2:
            query = text_lower
        
        print(f"[SEARCH] Resultados brutos: {query[:100]}...")
        result = search.search_web(query)
        print(f"[SEARCH] Primeira pesquisa feita")
        
        weak_indicators = ['não há informações', 'não encontrei', 'sem resultados', 
                          'nenhum resultado', 'não foi possível', 'erro na pesquisa']
        if any(indicator in result.lower() for indicator in weak_indicators):
            print(f"[SEARCH] Primeira pesquisa fraca, tentando alternativa...")
            
            alt_queries = [
                f"{query} Brasil",
                f"{query} agora",
                f"info {query}"
            ]
            
            for alt_query in alt_queries:
                alt_result = search.search_web(alt_query)
                if not any(indicator in alt_result.lower() for indicator in weak_indicators):
                    print(f"[SEARCH] Pesquisa alternativa funcionou")
                    result = alt_result
                    break
        
        print(f"[INTENT] Chamando chat_with_search com pergunta: {text}")
        return result
