// ============================================
// RAVIS - CLIENTE JAVASCRIPT
// ============================================
// Propósito: Interface cliente para o assistente virtual Ravis
//
// Funcionalidades:
//   - WebSocket: Comunicação em tempo real
//   - Chat: Mensagens com streaming
//   - TTS: Síntese de voz (Edge TTS)
//   - Frequency Analyzer: Visualização de áudio
//   - Estados: Interface responsiva com estados visuais
//
// Fluxo:
//   1. DOM carregado -> Inicializa WebSocket
//   2. Usuário envia mensagem -> Servidor processa
//   3. Resposta streaming -> Exibe progressivamente
//   4. Resposta completa -> Toca áudio TTS
//   5. Áudio termina -> Estado idle
//
// Estados do Assistente:
//   - idle: Pronto (cyan)
//   - thinking: Processando (gold)
//   - speaking: Falando (green)
//   - searching: Pesquisando (orange)
//   - listening: Escutando (cyan)
//   - error: Erro (red)
// ============================================
// Propósito: Interface cliente para o assistente virtual Ravis
//
// Funcionalidades:
//   - WebSocket: Comunicação em tempo real
//   - Chat: Mensagens com streaming
//   - TTS: Síntese de voz (Edge TTS)
//   - Frequency Analyzer: Visualização de áudio
//   - Estados: Interface responsiva com estados visuais
//
// Fluxo:
//   1. DOM carregado -> Inicializa WebSocket
//   2. Usuário envia mensagem -> Servidor processa
//   3. Resposta streaming -> Exibe progressivamente
//   4. Resposta completa -> Toca áudio TTS
//   5. Áudio termina -> Estado idle
//
// Estados do Assistente:
//   - idle: Pronto (cyan)
//   - thinking: Processando (gold)
//   - speaking: Falando (green)
//   - searching: Pesquisando (orange)
//   - listening: Escutando (cyan)
//   - error: Erro (red)
//
// Uso:
//   -gerenciado automaticamente pelo DOM
//   - Funções expostas globalmente para eventos HTML
// ============================================
// Propósito: Cliente JavaScript para interface do Ravis
//
// Funcionalidades principais:
//   - WebSocket: Comunicação em tempo real com servidor
//   - Chat: Envio e recebimento de mensagens
//   - TTS: Síntese de voz (Edge TTS)
//   - Frequency Analyzer: Visualização de áudio em tempo real
//   - UI: Interface responsiva com estados do assistente
//
// Fluxo principal:
//   1. Carrega página -> Inicializa WebSocket
//   2. Usuário envia mensagem -> Envia via WebSocket
//   3. Servidor responde em streaming -> Exibe progressivamente
//   4. Resposta completa -> Toca áudio TTS
//   5. Áudio termina -> Volta para estado idle
//
// Estados do Assistente:
//   - idle: Pronto para nova mensagem
//   - listening: Recebendo mensagem
//   - thinking: Processando resposta
//   - speaking: Enviando resposta (stream)
//   - searching: Pesquisando na web
//   - error: Erro detectado
// ============================================

const API_URL = 'http://localhost:8000';
const WS_PATH = '/ws';
const STATUS_INTERVAL_MS = 10000;
const WEATHER_INTERVAL_MS = 300000;

let ws = null;
let isProcessing = false;
let audioEnabled = true;
let audioPlayer = null;
let audioContext = null;
let analyser = null;
let animationFrameId = null;
let currentSpeakingColor = '#00FF88';
let currentResponseText = "";
let wsReconnectAttempts = 0;
const WS_MAX_RECONNECT_ATTEMPTS = 10;
let wsErrorNotified = false;
let messageQueue = [];  // Fila de mensagens quando offline
let latestCapturePath = null;
let latestCaptureTimestamp = null;
let mediaWindowDragging = false;
let mediaWindowOffset = { x: 0, y: 0 };
let selectionStart = null;
let selectionEnd = null;

// ============================================
// AI ACTIVITY - Visualizador de Atividade JARVIS
// ============================================

const AI_COLORS = {
    idle: '#00D4FF',
    thinking: '#FFD700',
    speaking: '#00FF88',
    searching: '#FF6B00',
    listening: '#00D4FF',
    error: '#FF3B3B'
};

const AI_CONFIG = {
    idle: { label: 'STANDBY', icon: '●', log: ['> STANDBY MODE', '> INITIALIZED'], eqClass: 'eq-idle' },
    thinking: { label: 'PROCESSANDO', icon: '◈', log: ['> NEURAL PROCESSING...', '> ANALYZING INPUT'], eqClass: 'eq-thinking' },
    speaking: { label: 'TRANSMITINDO', icon: '▶', log: ['> TRANSMITTING RESPONSE', '> AUDIO OUTPUT'], eqClass: 'eq-speaking' },
    searching: { label: 'PESQUISANDO', icon: '⌕', log: ['> QUERYING DATABASES', '> SEARCHING WEB'], eqClass: 'eq-searching' },
    listening: { label: 'OUVINDO', icon: '◎', log: ['> AUDIO INPUT ACTIVE', '> PROCESSING VOICE'], eqClass: 'eq-listening' },
    error: { label: 'ERRO', icon: '⚠️', log: ['> AUDIO ERROR', '> SYSTEM FAILURE'], eqClass: 'eq-error' }
};

// Inicializar equalizer ao carregar página
document.addEventListener('DOMContentLoaded', () => {
    initEqualizer();
});

function initEqualizer() {
    const eqContainer = document.getElementById('equalizer-bars');
    const refContainer = document.getElementById('equalizer-reflection');
    
    if (!eqContainer || !refContainer) return;
    
    // Limpar barras existentes
    eqContainer.innerHTML = '';
    refContainer.innerHTML = '';
    
    // Criar 20 barras (otimizado para análise de frequência)
    for (let i = 0; i < 20; i++) {
        const bar = document.createElement('div');
        bar.className = 'eq-bar eq-idle rounded-sm';
        bar.style.height = (10 + Math.random() * 15) + '%';
        bar.dataset.index = i;
        eqContainer.appendChild(bar);
        
        const ref = document.createElement('div');
        ref.className = 'eq-bar-reflection eq-idle rounded-sm';
        ref.style.height = bar.style.height;
        refContainer.appendChild(ref);
    }
}

// ============================================================
// setAIActivity()
// ============================================================
// Propósito: Atualiza a interface para refletir o estado atual do assistente
// Entrada:
//   - estado (str): Estado do assistente ('idle', 'thinking', 'speaking', etc)
//   - dados (obj): Dados adicionais (inference, memory, tokens)
// Saída: Nenhuma
// Notas: Atualiza cores, animações, ícones e texto do UI
// ============================================================
function setAIActivity(estado, dados = {}) {
    const config = AI_CONFIG[estado] || AI_CONFIG.idle;
    const cor = AI_COLORS[estado] || AI_COLORS.idle;
    
    // Atualiza laboratório - SEMPRE visível, com opacidade variável por estado
    const body = document.body;
    const scannerRing = document.getElementById('scanner-ring');
    const labFrame = document.getElementById('laboratory-frame');
    
    // Remove classes de estado anteriores
    body.classList.remove('lab-idle', 'lab-thinking', 'lab-speaking', 'lab-searching', 'lab-listening', 'lab-error');
    
    // Adiciona classe de estado atual para opacidade
    body.classList.add(`lab-${estado}`);
    
    // Scanner ring visível apenas em speaking/searching
    if (estado === 'speaking' || estado === 'searching') {
        if (scannerRing) scannerRing.classList.remove('hidden');
    } else {
        if (scannerRing) scannerRing.classList.add('hidden');
    }
    
    // Salva cor do speaking para usar no analyzer
    if (estado === 'speaking') {
        currentSpeakingColor = cor;
    }
    
    // Atualiza ícones e cores do header
    const hexIcon = document.getElementById('ai-hex-icon');
    if (hexIcon) {
        hexIcon.style.color = cor;
    }
    
    // Atualiza reator do header (logo) - usando variáveis CSS
    const headerReactor = document.getElementById('header-reactor');
    if (headerReactor) {
        // Usa variável CSS para cor - muito mais simples!
        headerReactor.style.setProperty('--reactor-color', cor);
        
        // Atualiza animação do core conforme estado
        const core = headerReactor.querySelector('.core');
        if (core) {
            core.style.animation = estado === 'speaking' 
                ? 'reactor-flicker 0.15s infinite' 
                : 'reactor-flicker 0.2s infinite';
        }
    }
    
    const aiStatus = document.getElementById('ai-status');
    if (aiStatus) {
        aiStatus.innerHTML = `<span class="text-xs" style="color:${cor}">${config.icon}</span><span class="text-xs font-orbitron" style="color:${cor}">${config.label}</span>`;
    }
    
    // Atualiza barras de Neural Net
    if (dados.inference !== undefined) {
        updateBar('bar-inference', dados.inference, cor);
        document.getElementById('nn-inference').textContent = dados.inference + '%';
        document.getElementById('nn-inference').style.color = cor;
    }
    if (dados.memory !== undefined) {
        updateBar('bar-memory', dados.memory, cor);
        document.getElementById('nn-memory').textContent = dados.memory + '%';
        document.getElementById('nn-memory').style.color = cor;
    }
    if (dados.response !== undefined) {
        updateBar('bar-response', dados.response, cor);
        document.getElementById('nn-response').textContent = dados.response + '%';
        document.getElementById('nn-response').style.color = cor;
    }
    
    // Atualiza equalizer
    animateEqualizer(estado, cor);
    
    // Atualiza system log
    updateSystemLog(config.log);
    
    // Atualiza tokens
    if (dados.tokens !== undefined) {
        const tokenBar = document.getElementById('token-bar');
        const tokenCount = document.getElementById('token-count');
        if (tokenBar) {
            tokenBar.style.width = Math.min(100, (dados.tokens.used / dados.tokens.total) * 100) + '%';
            tokenBar.style.backgroundColor = cor;
        }
        if (tokenCount) {
            tokenCount.textContent = dados.tokens.used + '/' + dados.tokens.total;
        }
    }
    
    // Atualiza power (simulado)
    const power = document.getElementById('ai-power');
    if (power) {
        power.style.color = cor;
    }
    
    // Atualiza reator do Iron Man
    const reactor = document.getElementById('reactor');
    if (reactor) {
        reactor.className = `reactor-${estado}`;
    }
    
    // Atualiza olhos do Iron Man
    const eyes = document.getElementById('Eyes');
    if (eyes) {
        eyes.setAttribute('class', `eyes-${estado}`);
        console.log(`[Ravis] Eyes set to: eyes-${estado}`);
    } else {
        console.warn('[Ravis] Eyes element not found!');
    }
    
    // Debug: verificar se o SVG está carregado
    const ironmanSvg = document.getElementById('ironman-svg');
    if (!ironmanSvg) {
        console.warn('[Ravis] IronMan SVG not found!');
    }
}

function updateBar(id, value, color) {
    const bar = document.getElementById(id);
    if (bar) {
        bar.style.width = Math.min(100, value) + '%';
        bar.style.backgroundColor = color;
    }
}

function animateEqualizer(estado, cor) {
    // Se o estado for speaking, a análise de frequência do Web Audio API controla as barras
    // Não aplicamos animação CSS nesse caso
    const bars = document.querySelectorAll('.eq-bar');
    const refs = document.querySelectorAll('.eq-bar-reflection');
    
    // Se está em speaking, pausa a animação CSS e deixa o analyzer controlar
    if (estado === 'speaking') {
        bars.forEach(bar => {
            bar.style.animationPlayState = 'running';
            bar.style.animation = 'none';
        });
        return;
    }
    
    // Classes CSS para cada estado
    const stateClasses = {
        idle: 'eq-idle',
        thinking: 'eq-thinking',
        speaking: 'eq-speaking',
        searching: 'eq-searching',
        listening: 'eq-listening',
        error: 'eq-error'
    };

    const stateClass = stateClasses[estado] || 'eq-idle';

    // Durações harmoniosas por estado (em ms)
    const durations = {
        idle: 800,
        thinking: 150,
        speaking: 350,
        searching: 200,
        listening: 500,
        error: 200
    };

    const duration = durations[estado] || 400;

    // Se está em speaking, o Web Audio API controla as barras - não usa animação CSS
    if (estado === 'speaking') {
        bars.forEach(bar => {
            bar.style.animation = 'none';
        });
        return;
    }

    // Pausa animação quando idle para economizar CPU
    const shouldPause = (estado === 'idle');
    
    // Aplica animação CSS para os outros estados (todas as 20 barras)
    bars.forEach((bar, i) => {
        bar.style.animation = 'none';
        bar.className = `eq-bar rounded-sm ${stateClass}`;
        bar.style.backgroundColor = cor;
        bar.style.animationPlayState = shouldPause ? 'paused' : 'running';
        
        // Delay harmônico distribuído para 20 barras
        const delay = i * 35;
        
        if (estado === 'idle') {
            // Ondas suaves estilo respiração - cada barra com timing diferente
            bar.style.animation = `eq-idle ${duration + i * 20}ms ease-in-out infinite alternate`;
        } 
        else if (estado === 'thinking') {
            // Agitado caótico - todas barras diferentes
            bar.style.animation = `eq-thinking ${duration + i * 10}ms ease-in-out infinite`;
            bar.style.animationDelay = `${delay}ms`;
        } 
        else if (estado === 'searching') {
            // Varredura sequencial da barra 1 até 20
            bar.style.animation = `eq-searching ${duration}ms ease-in-out infinite`;
            bar.style.animationDelay = `${i * 40}ms`;
        } 
        else if (estado === 'listening') {
            // Barras médias pulsando esperando input
            bar.style.animation = `eq-listening ${duration}ms ease-in-out infinite`;
            bar.style.animationDelay = `${delay}ms`;
        }
        else if (estado === 'error') {
            // Erro - alarme pulsando
            bar.style.animation = `eq-error ${duration}ms ease-in-out infinite`;
            bar.style.animationDelay = `${delay}ms`;
        }
    });
    
    // Atualiza reflection
    refs.forEach((ref, i) => {
        ref.style.animation = 'none';
        ref.className = `eq-bar-reflection rounded-sm ${stateClass}`;
        ref.style.backgroundColor = cor;
        ref.style.animationPlayState = shouldPause ? 'paused' : 'running';
    });
}

// ============================================
// SYSTEM LOG - Logs em tempo real do servidor
// ============================================

const logHistory = [];

function addLogToSystem(level, message, timestamp) {
    const logEntry = {
        level: level,
        text: message,
        timestamp: timestamp || ''
    };
    
    logHistory.push(logEntry);
    
    // Mantém máximo 4 linhas
    if (logHistory.length > 4) {
        logHistory.shift();
    }
    
    updateSystemLogDisplay();
}

function updateSystemLogDisplay() {
    const logEl = document.getElementById('system-log');
    if (!logEl) return;
    
    logEl.innerHTML = logHistory.map(l => {
        let color = '#00D4FF'; // info - azul
        if (l.level === 'warning') color = '#FFD700';
        if (l.level === 'error') color = '#FF3B3B';
        return `<div style="color:${color};font-size:9px;">${l.text}</div>`;
    }).join('') + '<span class="system-cursor"></span>';
}

function updateSystemLog(linhas) {
    const log = document.getElementById('system-log');
    if (log) {
        // Converte linhas tradicionais para formato de log
        linhas.forEach((l, i) => {
            const level = l.includes('ERROR') ? 'error' : (l.includes('WARNING') ? 'warning' : 'info');
            addLogToSystem(level, l, '');
        });
    }
}

// Função simples para backward compatibility
function setAIActivitySimple(estado) {
    setAIActivity(estado, {});
}

// ============================================
// CHAT TOOLS - Funções de Gerenciamento
// ============================================

let messageCount = 0;

async function salvarConversa() {
    const messages = document.querySelectorAll('#messages > div');
    if (messages.length <= 1) return;
    
    const msgs = [];
    let titulo = 'Nova conversa';
    
    messages.forEach(msg => {
        const isUser = msg.querySelector('.justify-end');
        const content = msg.querySelector('p.text-white, p.text-\\[\\#00D4FF\\]');
        if (content) {
            const role = isUser ? 'user' : 'assistant';
            const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            msgs.push({ role, content: content.textContent, timestamp: time });
            
            if (role === 'user' && titulo === 'Nova conversa') {
                titulo = content.textContent.slice(0, 40);
            }
        }
    });
    
    if (msgs.length < 2) return;
    
    try {
        const res = await fetch(`${API_URL}/conversation/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo, mensagens: msgs })
        });
        const data = await res.json();
        if (data.success) {
            console.log(`[HISTORY] Conversa salva: ${data.id}`);
        }
    } catch (err) {
        console.error('[HISTORY] Erro ao salvar:', err);
    }
}

async function listarConversas() {
    try {
        const res = await fetch(`${API_URL}/conversation/list`);
        return await res.json();
    } catch (err) {
        console.error('[HISTORY] Erro ao listar:', err);
        return [];
    }
}

async function getConversa(id) {
    try {
        const res = await fetch(`${API_URL}/conversation/${id}`);
        return await res.json();
    } catch (err) {
        console.error('[HISTORY] Erro ao carregar:', err);
        return null;
    }
}

async function deletarConversa(id) {
    if (!confirm('Tem certeza que deseja excluir esta conversa?')) return;
    
    try {
        const res = await fetch(`${API_URL}/conversation/${id}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            console.log(`[HISTORY] Conversa ${id} excluída`);
            loadHistory();
        }
    } catch (err) {
        console.error('[HISTORY] Erro ao deletar:', err);
    }
}

function copyConversation() {
    const messages = document.querySelectorAll('#messages > div');
    let text = 'Ravis - Conversa\n' + '='.repeat(30) + '\n\n';
    
    messages.forEach(msg => {
        // Detecta role pelo justify-end (mensagens do usuário)
        const isUser = msg.classList.contains('justify-end');
        const role = isUser ? 'Usuário' : 'Ravis';
        
        // Pega o conteúdo da mensagem
        const content = msg.querySelector('.message-content p.text-sm');
        if (content) {
            text += `${role}: ${content.textContent}\n\n`;
        }
    });
    
    navigator.clipboard.writeText(text).then(() => {
        addMessage('assistant', 'Conversa copiada para a área de transferência!');
    });
}

function copySingleMessage(btn) {
    // Encontra o elemento da mensagem
    const msgDiv = btn.closest('.message-content');
    if (!msgDiv) return;
    
    const content = msgDiv.querySelector('p.text-sm');
    if (!content) return;
    
    navigator.clipboard.writeText(content.textContent).then(() => {
        // Feedback visual temporário
        const originalColor = btn.innerHTML;
        btn.innerHTML = '<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
        setTimeout(() => {
            btn.innerHTML = originalColor;
        }, 1000);
    });
}

function toggleSearch() {
    const searchDiv = document.getElementById('chat-search');
    searchDiv.classList.toggle('hidden');
    if (!searchDiv.classList.contains('hidden')) {
        document.getElementById('search-input').focus();
    }
}

function searchMessages(query) {
    const messages = document.querySelectorAll('#messages > div');
    query = query.toLowerCase();
    
    messages.forEach(msg => {
        const content = msg.querySelector('p');
        if (content) {
            const text = content.textContent.toLowerCase();
            if (query && text.includes(query)) {
                msg.style.background = 'rgba(255, 200, 0, 0.2)';
            } else {
                msg.style.background = '';
            }
        }
    });
}

function newConversation() {
    if (confirm('Iniciar uma nova conversa? A conversa atual será salva no histórico.')) {
        salvarConversa();
        
        const messages = document.getElementById('messages');
        messages.innerHTML = '';
        
        initSessionTimer();
        messageCount = 0;
        
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'new_conversation' }));
            ws.send(JSON.stringify({ type: 'message', text: 'oi' }));
        }
        
        setAIActivity('idle');
    }
}

function toggleHistory() {
    const panel = document.getElementById('history-panel');
    panel.classList.toggle('translate-x-full');
    
    if (!panel.classList.contains('translate-x-full')) {
        loadHistory();
    }
}

async function loadHistory() {
    const list = document.getElementById('history-list');
    const conversas = await listarConversas();
    
    if (conversas.length === 0) {
        list.innerHTML = '<div class="text-cyan-500/50 text-sm text-center p-4">Nenhuma conversa salva</div>';
        return;
    }
    
    list.innerHTML = conversas.map(conv => `
        <div class="p-3 bg-[#031525] rounded border border-[#00D4FF]/20 hover:border-[#00D4FF] transition-colors">
            <div class="flex justify-between items-start">
                <div class="flex-1 cursor-pointer" onclick="loadConversation('${conv.id}')">
                    <div class="text-sm text-white font-semibold">${escapeHtml(conv.titulo)}</div>
                    <div class="text-xs text-cyan-500/50 mt-1">${conv.data}</div>
                    <div class="text-xs text-cyan-500/40 mt-1">${conv.totalMensagens} mensagens</div>
                </div>
                <button onclick="deletarConversa('${conv.id}')" class="text-red-500/60 hover:text-red-500 p-1" title="Excluir">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                </button>
            </div>
            <button onclick="loadConversation('${conv.id}')" class="w-full mt-2 py-1.5 bg-[#00D4FF]/10 border border-[#00D4FF]/30 text-[#00D4FF] rounded text-xs hover:bg-[#00D4FF]/20 transition-colors font-orbitron">
                ABRIR
            </button>
        </div>
    `).join('');
}

async function loadConversation(id) {
    const conv = await getConversa(id);
    if (!conv || conv.error) {
        alert('Erro ao carregar conversa');
        return;
    }
    
    salvarConversa();
    
    const messages = document.getElementById('messages');
    messages.innerHTML = '';
    
    conv.mensagens.forEach(msg => {
        addMessage(msg.role === 'user' ? 'user' : 'assistant', msg.content);
    });
    
    messageCount = conv.mensagens.length;
    
    toggleHistory();
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'load_conversation', mensagens: conv.mensagens }));
    }
}

function filterHistory(query) {
    const items = document.querySelectorAll('#history-list > div');
    query = query.toLowerCase();
    
    items.forEach(item => {
        const title = item.querySelector('.text-white');
        if (title) {
            const text = title.textContent.toLowerCase();
            item.style.display = text.includes(query) ? 'block' : 'none';
        }
    });
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Vision] DOM carregado!');
    console.log('[Vision] selection-overlay:', document.getElementById('selection-overlay'));
    console.log('[Vision] selection-box:', document.getElementById('selection-box'));
    console.log('[Vision] media-window:', document.getElementById('media-window'));
    
    initClock();
    initSessionTimer();
    initWebSocket();
    
    // Espera animação de desenho do Iron Man (3.5s) antes de ativar estados
    console.log('[Ravis] Waiting for Iron Man draw animation...');
    setTimeout(() => {
        setAIActivity('idle');
        
        const reactor = document.getElementById('reactor');
        if (reactor) {
            reactor.className = 'reactor-idle';
        }
        
        const eyes = document.getElementById('Eyes');
        if (eyes) {
            eyes.setAttribute('class', 'eyes-idle');
        }
        
        console.log('[Ravis] Iron Man states activated: idle');
    }, 3500);
    
    // Debug: verificar elementos do SVG
    console.log('[Ravis] IronMan SVG:', document.getElementById('ironman-svg'));
    console.log('[Ravis] Reactor:', document.getElementById('reactor'));
    console.log('[Ravis] Eyes:', document.getElementById('Eyes'));
    
    // Saudação automática via WebSocket (IA gera a resposta)
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'message', text: 'oi' }));
    } else {
        ws.addEventListener('open', () => {
            ws.send(JSON.stringify({ type: 'message', text: 'oi' }));
        }, { once: true });
    }
    
    initChatResizer();
    updateWeather();
    updateStatus();
    updateSystemInfo();
    
    // Atualiza status a cada 10 segundos (otimizado)
    setInterval(updateStatus, STATUS_INTERVAL_MS);
    // Atualiza system-info a cada 30 segundos (otimizado)
    setInterval(updateSystemInfo, 30000);
    // Atualiza clima a cada 5 minutos (otimizado)
    setInterval(updateWeather, WEATHER_INTERVAL_MS);
    
    // Foca no input (se existir no DOM)
    const inputEl = document.getElementById('message-input');
    if (inputEl) {
        inputEl.focus();
    } else {
        console.warn('[UI] Elemento #message-input não encontrado. Entrada de texto desativada.');
    }
    
    // Inicializar drag da janela de mídia
    initMediaWindowDrag();
    
    // OBS: O atalho PrintScreen agora é detectado globalmente pelo pynput (modules/hotkeys.py)
    // Não precisa de listener no JavaScript - funciona em qualquer janela do Windows
    
    // Verificar última captura ao iniciar
    fetch(`${API_URL}/vision/latest`)
        .then(r => r.json())
        .then(data => {
            if (data.path) {
                latestCapturePath = data.path;
                latestCaptureTimestamp = data.timestamp;
                updateMediaImage(data.path, data.timestamp);
            }
        })
        .catch(() => {});
    
    window.addEventListener('beforeunload', () => {
        salvarConversa();
    });
});

// ============================================
// ============================================
// RELÓGIO - Relógio e data em tempo real
// ============================================
// Inicializa relógio digital que atualiza a cada segundo
// ============================================
function initClock() {
    function update() {
        const now = new Date();
        const clockEl = document.getElementById('clock');
        const dateEl = document.getElementById('date');
        if (clockEl) {
            clockEl.textContent = now.toLocaleTimeString('pt-BR');
        }
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('pt-BR');
        }
    }
    update();
    setInterval(update, 1000);
}

// ============================================
// WEBSOCKET - Conexão em tempo real
// ============================================
// Banner de conexão - Exibe banner de status
// ============================================
function showBanner(message, type) {
    const banner = document.getElementById('connection-banner');
    if (!banner) return;
    
    const text = document.getElementById('banner-text');
    banner.className = `fixed top-0 left-0 right-0 p-3 text-center z-50 ${type === 'success' ? 'bg-green-600' : 'bg-yellow-600'}`;
    text.textContent = message;
    banner.classList.remove('hidden');
    
    if (type === 'success') {
        setTimeout(() => banner.classList.add('hidden'), 3000);
    }
}

// Helpers de UI e WebSocket
function getRequiredElement(id, context) {
    const el = document.getElementById(id);
    if (!el) {
        console.warn(`[UI] Elemento #${id} não encontrado (${context}).`);
    }
    return el;
}

function showTypingIndicator() {
    const messages = getRequiredElement('messages', 'showTypingIndicator');
    if (!messages) return;
    
    if (document.getElementById('typing-indicator-row')) {
        return;
    }
    
    const div = document.createElement('div');
    div.id = 'typing-indicator-row';
    div.className = 'flex items-start';
    div.innerHTML = `
        <div class="flex items-start gap-2 max-w-[85%]">
            <div class="w-6 h-6 flex-shrink-0 mt-1">
                <svg viewBox="0 0 24 24" fill="none" stroke="#00D4FF" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <div class="bg-[#041525] rounded-lg p-3 border border-[#00D4FF]/40 shadow-[0_0_10px_rgba(0,212,255,0.1)]">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function hideTypingIndicator() {
    const row = document.getElementById('typing-indicator-row');
    if (row && row.parentNode) {
        row.parentNode.removeChild(row);
    }
}

// ============================================================
// initWebSocket()
// ============================================================
// Propósito: Inicializa conexão WebSocket com servidor
// Entrada: Nenhuma
// Saída: Nenhuma
// Fluxo:
//   1. Cria nova conexão WebSocket
//   2. Define handlers: onopen, onmessage, onclose, onerror
//   3. onmessage: Processa diferentes tipos de mensagem
//   4. onclose: Implementa reconexão automática
//   5. onerror: Log de erros
// ============================================================
function initWebSocket() {
    console.log('[WS] Iniciando conexão WebSocket...');
    ws = new WebSocket(`ws://${window.location.host}${WS_PATH}`);
    
    ws.onopen = () => {
        console.log('[WS] ✓ Conectado ao Ravis');
        wsReconnectAttempts = 0;
        wsErrorNotified = false;
        showBanner('✅ Conexão restaurada', 'success');
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('[WS] Recebido:', data.type, data.content ? data.content.substring(0, 50) : '');
            
            if (data.type === 'stream') {
                // Se é primeiro chunk, criar mensagem do assistente
                if (!currentResponseText) {
                    addMessage('assistant', '');
                    setAIActivity('speaking');
                    console.log('[WS] Mensagem do assistente criada');
                }
                currentResponseText += data.content;
                appendToLastMessage(data.content);
            } else if (data.type === 'response') {
                // Resposta completa (não-streaming)
                addMessage('assistant', data.content);
                setAIActivity('speaking');
                speakText(data.content);
                isProcessing = false;
                hideTypingIndicator();
                // setAIActivity('idle') será chamado pelo onended do áudio
            } else if (data.type === 'done') {
                // Streaming completo - exibe texto final e toca áudio
                console.log('[WS] ✓ Resposta completa, texto:', currentResponseText.substring(0, 50));
                if (currentResponseText) {
                    // Garante que a mensagem final está no chat
                    const messages = document.getElementById('messages');
                    const lastMsg = messages.lastElementChild;
                    if (lastMsg) {
                        const p = lastMsg.querySelector('.message-content p');
                        if (p && p.textContent !== currentResponseText) {
                            p.textContent = currentResponseText;
                        }
                    }
                    // Define como speaking ANTES de tocar áudio
                    setAIActivity('speaking');
                    // Toca áudio
                    speakText(currentResponseText);
                }
                isProcessing = false;
                hideTypingIndicator();
                // setAIActivity('idle') será chamado pelo onended do áudio
                currentResponseText = "";
                
                messageCount += 2;
                if (messageCount >= 2) {
                    salvarConversa();
                }
            } else if (data.type === 'error') {
                addMessage('assistant', `Erro: ${data.content}`);
                isProcessing = false;
                hideTypingIndicator();
                setAIActivity('error');
                // Após 5 segundos, volta para idle automaticamente
                setTimeout(() => setAIActivity('idle'), 5000);
                currentResponseText = "";
            } else if (data.type === 'vision_result') {
                addMessage('assistant', data.text);
                setAIActivity('speaking');
                speakText(data.text);
                // setAIActivity('idle') será chamado pelo onended do áudio
            } else if (data.type === 'hotkey_capture') {
                console.log('[Vision] Captura via hotkey global recebida:', data.path);
                // Mostrar overlay de seleção
                startSelection();
            } else if (data.type === 'log') {
                // Log em tempo real do servidor
                addLogToSystem(data.level, data.message, data.timestamp);
                // Se for erro, ativa estado de erro
                if (data.level === 'error') {
                    setAIActivity('error');
                    setTimeout(() => setAIActivity('idle'), 5000);
                }
            } else if (data.type === 'activity') {
                // Atualiza visualizador de atividade
                setAIActivity(data.state, data.data || {});
            }
        } catch (err) {
            console.error('[WS] Erro ao processar mensagem:', err);
            setAIActivity('error');
            // Após 5 segundos, volta para idle automaticamente
            setTimeout(() => setAIActivity('idle'), 5000);
        }
    };
    
    ws.onclose = () => {
        console.log('[WS] ✗ Desconectado, tentando reconectar...');
        wsReconnectAttempts += 1;
        
        showBanner('⚠️ Conexão perdida. Reconectando...', 'warning');

        if (wsReconnectAttempts === 1) {
            addMessage('assistant', 'Conexão com o servidor perdida. Tentando reconectar...');
        }

        if (wsReconnectAttempts > WS_MAX_RECONNECT_ATTEMPTS) {
            console.log('[WS] Número máximo de tentativas de reconexão atingido.');
            addMessage('assistant', 'Não consegui reconectar ao servidor. Verifique se o Ravis está em execução.');
            hideTypingIndicator();
            return;
        }

        // Backoff exponencial: 1s, 2s, 4s, 8s, 16s, 30s (máximo)
        const delay = Math.min(30000, Math.pow(2, wsReconnectAttempts - 1) * 1000);
        console.log(`[WS] Tentando reconectar em ${delay}ms (tentativa ${wsReconnectAttempts})`);
        setTimeout(initWebSocket, delay);
    };
    
    ws.onerror = (error) => {
        console.error('[WS] Erro na conexão:', error);
        setAIActivity('error');
        // Após 5 segundos, volta para idle automaticamente
        setTimeout(() => setAIActivity('idle'), 5000);
        if (!wsErrorNotified) {
            addMessage('assistant', 'Houve um erro na conexão em tempo real. Vou tentar reconectar automaticamente.');
            wsErrorNotified = true;
        }
    };
}

// ============================================
// FREQUENCY ANALYZER - Análise de áudio em tempo real (20 barras)
// ============================================

// Throttle para requestAnimationFrame - 30fps idle, 60fps speaking
let lastFrameTime = 0;
const FPS_IDLE = 30;
const FPS_SPEAKING = 60;
let currentFPS = FPS_IDLE;

function getTargetFPS(estado) {
    return estado === 'speaking' ? FPS_SPEAKING : FPS_IDLE;
}

function shouldRender(timestamp) {
    const interval = 1000 / currentFPS;
    return timestamp - lastFrameTime >= interval;
}

function startFrequencyAnalysis() {
    if (!analyser) return;
    
    const bars = document.querySelectorAll('.eq-bar');
    const refs = document.querySelectorAll('.eq-bar-reflection');
    const bufferLength = analyser.frequencyBinCount; // 128 para FFT 256
    const dataArray = new Uint8Array(bufferLength);
    currentFPS = FPS_SPEAKING;
    
    // Mapeia as 20 barras para faixas de frequência (espectro completo)
    // 1-4: graves, 5-8: médio-graves, 9-12: médios, 13-16: médio-agudos, 17-20: agudos
    function getFrequencyIndex(barIndex) {
        // Distribuição非线性 - mais pesos para médias frequências (voz humana)
        if (barIndex < 4) {
            // Graves: índices 0-20
            return Math.floor(barIndex * 5);
        } else if (barIndex < 8) {
            // Médio-graves: índices 20-50
            return Math.floor(20 + (barIndex - 4) * 8);
        } else if (barIndex < 12) {
            // Médios: índices 50-90 (voz)
            return Math.floor(50 + (barIndex - 8) * 10);
        } else if (barIndex < 16) {
            // Médio-agudos: índices 90-110
            return Math.floor(90 + (barIndex - 12) * 5);
        } else {
            // Agudos: índices 110-127
            return Math.floor(110 + (barIndex - 16) * 4);
        }
    }
    
    // Suavização entre frames
    const smoothedValues = new Array(20).fill(15);
    const smoothingFactor = 0.3;
    
    function updateBars() {
        if (!analyser || !audioPlayer || audioPlayer.paused || audioPlayer.ended) {
            // Audio parou - sai do loop
            return;
        }
        
        analyser.getByteFrequencyData(dataArray);
        
        bars.forEach((bar, i) => {
            // Obtém o índice de frequência para esta barra
            const freqIndex = getFrequencyIndex(i);
            const value = dataArray[Math.min(freqIndex, bufferLength - 1)];
            
            // Normaliza para altura (15-95%)
            const targetHeight = Math.max(15, Math.min(95, (value / 255) * 100));
            
            // Aplica suavização
            smoothedValues[i] = smoothedValues[i] * (1 - smoothingFactor) + targetHeight * smoothingFactor;
            
            bar.style.height = smoothedValues[i] + '%';
            bar.style.backgroundColor = currentSpeakingColor;
        });
        
        // Atualiza reflection
        refs.forEach((ref, i) => {
            ref.style.height = bars[i].style.height;
            ref.style.backgroundColor = currentSpeakingColor;
        });
        
        // Sincroniza reator e olhos com o áudio
        const reactor = document.getElementById('reactor');
        const eyes = document.getElementById('Eyes');
        
        if (reactor || eyes) {
            // Calcula volume médio
            const avgVolume = smoothedValues.reduce((a, b) => a + b, 0) / smoothedValues.length;
            const glowIntensity = 5 + (avgVolume / 100) * 20;
            
            // Atualiza reator com brilho basado no áudio
            if (reactor) {
                reactor.style.filter = `drop-shadow(0 0 ${glowIntensity}px #00FF88)`;
            }
            
            // Atualiza olhos com brilho basado no áudio
            if (eyes) {
                eyes.style.filter = `drop-shadow(0 0 ${glowIntensity * 0.5}px #00FF88)`;
            }
        }
        
        // Throttle: 60fps speaking, 30fps idle
        currentFPS = FPS_SPEAKING;
        const now = performance.now();
        if (shouldRender(now)) {
            lastFrameTime = now;
            animationFrameId = requestAnimationFrame(updateBars);
        } else {
            animationFrameId = requestAnimationFrame(updateBars);
        }
    }
    
    currentFPS = FPS_SPEAKING;
    updateBars();
}

function stopFrequencyAnalysis() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
    currentFPS = FPS_IDLE;
}

// ============================================
// TTS - Text to Speech
// ============================================
// speakText()
// ============================================
// Propósito: Reproduz texto como áudio usando Edge TTS
// Entrada: text (str) - Texto para converter em áudio
// Saída: Nenhuma
// Fluxo:
//   1. Envia texto para servidor (/speak)
//   2. Recebe áudio (blob)
//   3. Cria AudioContext e Analyser
//   4. Reproduz áudio e visualiza frequência
//   5. Quando termina, volta para estado idle
// ============================================
async function speakText(text) {
    if (!text || text.length < 3) return;
    
    // Verificar se áudio está habilitado
    if (!audioEnabled) {
        console.log('[TTS] Áudio desabilitado. Clique em "Ativar Áudio" para habilitar.');
        return;
    }
    
    // Limite de segurança para TTS removido - texto ilimitado
    let textoParaFalar = text;
    
    console.log('[TTS] Reproduzindo:', textoParaFalar.substring(0, 50) + '...');
    
    try {
        const response = await fetch(`${API_URL}/speak`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: textoParaFalar })
        });
        
        if (!response.ok) {
            console.log('[TTS] Erro na resposta');
            addMessage('assistant', 'Não consegui gerar o áudio desta resposta.');
            return;
        }
        
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        
        if (audioPlayer) {
            audioPlayer.pause();
            // Para o analyzer se estiver ativo
            if (audioContext) {
                audioContext.close();
                audioContext = null;
                analyser = null;
            }
        }
        
        // Criar AudioContext e Analyser para análise em tempo real
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256; // 128 frequency bins para 20 barras
        analyser.smoothingTimeConstant = 0.8;
        
        audioPlayer = new Audio(audioUrl);
        
        // Conectar áudio ao analyser e ao destino
        const source = audioContext.createMediaElementSource(audioPlayer);
        source.connect(analyser);
        analyser.connect(audioContext.destination);
        
        // Iniciar análise de frequência quando o áudio começar
        audioPlayer.onplay = () => {
            console.log('[TTS] ✓ Áudio começou a tocar');
            setAIActivity('speaking');
            startFrequencyAnalysis();
        };

        audioPlayer.onended = () => {
            console.log('[TTS] ✓ Áudio terminado');
            stopFrequencyAnalysis();
            setAIActivity('idle');
        };

        audioPlayer.onerror = () => {
            console.log('[TTS] Erro no áudio');
            stopFrequencyAnalysis();
            setAIActivity('error');
            // Após 5 segundos, volta para idle automaticamente
            setTimeout(() => setAIActivity('idle'), 5000);
        };

        audioPlayer.onpause = () => {
            console.log('[TTS] Áudio pausado');
            stopFrequencyAnalysis();
            setAIActivity('idle');
        };

        audioPlayer.play().catch(err => {
            console.log('[TTS] Erro ao reproduzir:', err);
            setAIActivity('error');
            // Após 5 segundos, volta para idle automaticamente
            setTimeout(() => setAIActivity('idle'), 5000);
        });
        
        console.log('[TTS] ✓ Reproduzindo áudio');
        
    } catch (err) {
        console.log('[TTS] Erro:', err);
        setAIActivity('error');
        addMessage('assistant', 'Ocorreu um erro ao reproduzir o áudio.');
        // Após 5 segundos, volta para idle automaticamente
        setTimeout(() => setAIActivity('idle'), 5000);
    }
}

// ============================================
// SESSION TIMER
// ============================================

let sessionStartTime = null;

function initSessionTimer() {
    sessionStartTime = new Date();
    
    // Generate session ID
    const sessionId = Math.random().toString(36).substring(2, 8).toUpperCase();
    const sessionIdEl = document.getElementById('session-id');
    if (sessionIdEl) {
        sessionIdEl.textContent = sessionId;
    }
    
    function update() {
        if (!sessionStartTime) return;
        
        const now = new Date();
        const diff = Math.floor((now - sessionStartTime) / 1000);
        
        const hours = Math.floor(diff / 3600).toString().padStart(2, '0');
        const minutes = Math.floor((diff % 3600) / 60).toString().padStart(2, '0');
        const seconds = (diff % 60).toString().padStart(2, '0');
        
        const timerEl = document.getElementById('session-timer');
        if (timerEl) {
            timerEl.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }
    
    update();
    setInterval(update, 1000);
}

// ============================================
// UPLOAD DE ARQUIVOS
// ============================================

let uploadedFileContent = null;
let uploadedFileName = null;

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    console.log('[Upload] Arquivo selecionado:', file.name, file.type);
    
    // Limpa arquivo anterior
    uploadedFileContent = null;
    uploadedFileName = null;
    
    // Mostrar indicador de upload
    addMessage('user', `📎 Anexando: ${file.name}...`);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            uploadedFileContent = data.content;
            uploadedFileName = file.name;
            
            // Atualiza a mensagem com o conteúdo
            const messages = document.getElementById('messages');
            const lastMsg = messages.lastElementChild;
            if (lastMsg) {
                const p = lastMsg.querySelector('p');
                if (p) {
                    let preview = data.content.substring(0, 100);
                    if (data.file_type === 'imagem') {
                        p.textContent = `📎 ${file.name} (${data.file_type}) - Analisando...`;
                    } else {
                        p.textContent = `📎 ${file.name} (${data.file_type}): ${preview}...`;
                    }
                }
            }
            
            console.log('[Upload] Sucesso:', data.file_type);
        } else {
            // Erro
            const lastMsg = document.getElementById('messages').lastElementChild;
            if (lastMsg) {
                const p = lastMsg.querySelector('p');
                if (p) p.textContent = `❌ Erro ao processar: ${data.error}`;
            }
            console.error('[Upload] Erro:', data.error);
        }
        
    } catch (err) {
        console.error('[Upload] Erro:', err);
        const lastMsg = document.getElementById('messages').lastElementChild;
        if (lastMsg) {
            const p = lastMsg.querySelector('p');
            if (p) p.textContent = `❌ Erro ao enviar arquivo`;
        }
    }
    
    // Limpa o input para permitir re-selecionar o mesmo arquivo
    input.value = '';
}

// ============================================
// MENSAGENS
// ============================================
// sendMessage()
// ============================================
// Propósito: Envia mensagem do usuário para o servidor
// Entrada: Nenhuma (pega do input)
// Saída: Nenhuma (envia via WebSocket)
// Fluxo:
//   1. Peg texto do input
//   2. Adiciona mensagem na UI
//   3. Envia via WebSocket
//   4. Exibe indicador de "typing"
//   5. Ativa estado "thinking"
// ============================================
function sendMessage() {
    const input = getRequiredElement('message-input', 'sendMessage');
    if (!input) return;
    const text = input.value.trim();
    
    if (!text || isProcessing) return;
    
    // Verifica se há arquivo anexado
    let mensagemCompleta = text;
    if (uploadedFileContent) {
        mensagemCompleta = `${text}\n\n[Arquivo anexado: ${uploadedFileName}]\n\n${uploadedFileContent}`;
        uploadedFileContent = null;
        uploadedFileName = null;
    }
    
    // Adiciona mensagem do usuário
    addMessage('user', text);
    input.value = '';
    
    // Marca como processando
    isProcessing = true;
    showTypingIndicator();
    setAIActivity('thinking');
    
    // Envia via WebSocket ou adiciona à fila
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Envia mensagem atual
        ws.send(JSON.stringify({
            type: 'chat',
            text: mensagemCompleta
        }));
        
        // Envia mensagens da fila
        while (messageQueue.length > 0 && ws.readyState === WebSocket.OPEN) {
            const queuedMsg = messageQueue.shift();
            ws.send(JSON.stringify(queuedMsg));
            console.log('[WS] Enviando mensagem da fila');
        }
    } else {
        // Adiciona à fila para quando reconectar
        messageQueue.push({ type: 'chat', text: mensagemCompleta });
        console.log('[WS] Mensagem adicionada à fila. Fila:', messageQueue.length);
        
        // Fallback para HTTP
        fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: mensagemCompleta })
        })
        .then(res => res.json())
        .then(data => {
            addMessage('assistant', data.response);
            isProcessing = false;
            hideTypingIndicator();
        })
        .catch(err => {
            addMessage('assistant', 'Erro de conexão');
            isProcessing = false;
            hideTypingIndicator();
        });
    }
}

// ============================================
// addMessage() - Adiciona mensagem ao chat
// ============================================
// Propósito: Cria e exibe mensagem no chat
// Args:
//   - role: 'user' ou 'assistant'
//   - content: Texto da mensagem
// ============================================
function addMessage(role, content) {
    const messages = getRequiredElement('messages', 'addMessage');
    if (!messages) return;
    const time = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    
    const div = document.createElement('div');
    div.className = 'flex items-start group';  // Added group for hover
    
    // Função para copiar mensagem específica
    const copyBtn = `
        <button onclick="copySingleMessage(this)" class="opacity-0 group-hover:opacity-100 absolute top-1 right-1 p-1 hover:bg-[#00D4FF]/20 rounded transition-opacity" title="Copiar">
            <svg class="w-4 h-4 text-[#00D4FF]/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
        </button>
    `;
    
    if (role === 'user') {
        // Usuário: alinhado à direita, borda verde neon
        div.className += ' justify-end relative';
        div.innerHTML = `
            <div class="flex items-start gap-2 max-w-[85%] justify-end">
                <div class="bg-[#041525] rounded-lg p-3 border border-[#00FF88]/40 shadow-[0_0_10px_rgba(0,255,136,0.1)] message-content relative">
                    ${copyBtn}
                    <p class="text-sm text-white pr-6"></p>
                    <p class="text-xs text-[#00FF88]/40 mt-1 font-mono">${time}</p>
                </div>
                <div class="w-6 h-6 flex-shrink-0 mt-1">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#00FF88" stroke-width="2">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                </div>
            </div>
        `;
        messages.appendChild(div);
        div.querySelector('.message-content p').textContent = content;
        messages.scrollTop = messages.scrollHeight;
        return;
    } else {
        // Assistente: alinhado à esquerda, borda cyan neon
        div.className += ' relative';
        div.innerHTML = `
            <div class="flex items-start gap-2 max-w-[85%]">
                <div class="w-6 h-6 flex-shrink-0 mt-1">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#00D4FF" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div class="bg-[#041525] rounded-lg p-3 border border-[#00D4FF]/40 shadow-[0_0_10px_rgba(0,212,255,0.1)] message-content relative">
                    ${copyBtn}
                    <p class="text-sm text-[#00D4FF] pr-6"></p>
                    <p class="text-xs text-[#00D4FF]/40 mt-1 font-mono">${time}</p>
                </div>
            </div>
        `;
        messages.appendChild(div);
        div.querySelector('.message-content p').textContent = content;
        messages.scrollTop = messages.scrollHeight;
        return;
    }
    
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function appendToLastMessage(content) {
    const messages = getRequiredElement('messages', 'appendToLastMessage');
    if (!messages) return;
    const lastMsg = messages.lastElementChild;
    
    if (lastMsg) {
        // Verifica se a última mensagem é do assistente
        const isAssistant = lastMsg.querySelector('.message-content');
        
        if (isAssistant) {
            const p = lastMsg.querySelector('.message-content p');
            if (p) {
                p.textContent += content;
                messages.scrollTop = messages.scrollHeight;
                return;
            }
        }
        
        // Se não for do assistente, cria nova mensagem
        console.log('[WS] Criando mensagem do assistente (fallback)');
        addMessage('assistant', content);
    }
}

// ============================================
// UTILITÁRIOS
// ============================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// STATUS DO SISTEMA - CPU, RAM, Disco
// ============================================
// Atualiza indicadores de uso do sistema
// ============================================

async function updateStatus() {
    try {
        const res = await fetch(`${API_URL}/status`);
        const data = await res.json();
        
        // CPU
        const cpuValueEl = document.getElementById('cpu-value');
        const cpuBarEl = document.getElementById('cpu-bar');
        if (cpuValueEl && cpuBarEl && typeof data.cpu === 'number') {
            cpuValueEl.textContent = `${Math.round(data.cpu)}%`;
            cpuBarEl.style.width = `${data.cpu}%`;
        }
        
        // RAM
        const ramValueEl = document.getElementById('ram-value');
        const ramBarEl = document.getElementById('ram-bar');
        if (ramValueEl && ramBarEl && typeof data.ram === 'number') {
            ramValueEl.textContent = `${Math.round(data.ram)}%`;
            ramBarEl.style.width = `${data.ram}%`;
        }
        
        // Disk
        const diskValueEl = document.getElementById('disk-value');
        const diskBarEl = document.getElementById('disk-bar');
        if (diskValueEl && diskBarEl && typeof data.disk === 'number') {
            diskValueEl.textContent = `${Math.round(data.disk)}%`;
            diskBarEl.style.width = `${data.disk}%`;
        }
        
        // Uptime
        const uptimeEl = document.getElementById('uptime');
        if (uptimeEl && data.uptime) {
            uptimeEl.textContent = data.uptime;
        }
        
        // Commands
        const commandsEl = document.getElementById('commands');
        if (commandsEl && typeof data.commands !== 'undefined') {
            commandsEl.textContent = data.commands;
        }
        
        // Mic
        updateIndicator('mic-indicator', data.mic_active);
        
        // Camera
        updateIndicator('camera-indicator', data.camera_active);
        
    } catch (err) {
        console.error('Erro ao buscar status:', err);
    }
}

// ============================================
// SYSTEM INFO - Rede, Música, Discos
// ============================================
// Atualiza widgets adicionais do sistema
// ============================================

async function updateSystemInfo() {
    try {
        const res = await fetch(`${API_URL}/system-info`);
        const data = await res.json();
        
        // Rede - WiFi ou Ethernet
        const wifiNameEl = document.getElementById('wifi-name');
        const netDownEl = document.getElementById('net-down');
        const netUpEl = document.getElementById('net-up');
        const netPingEl = document.getElementById('net-ping');
        
        // Ícone e nome da conexão
        if (wifiNameEl && data.connection_name) {
            const connType = data.connection_type;
            const connName = data.connection_name;
            
            // Define ícone baseado no tipo
            let icon = '🌐';
            if (connType === 'wifi') {
                icon = '📶';
            } else if (connType === 'ethernet') {
                icon = '🔌';
            }
            
            wifiNameEl.textContent = `${icon} ${connName}`;
        }
        
        // Velocidade de download
        if (netDownEl) {
            netDownEl.textContent = data.download !== undefined ? `${data.download} MB/s` : '--';
        }
        
        // Velocidade de upload
        if (netUpEl) {
            netUpEl.textContent = data.upload !== undefined ? `${data.upload} MB/s` : '--';
        }
        
        // Ping
        if (netPingEl) {
            netPingEl.textContent = data.ping !== undefined ? `${data.ping}ms` : '--';
        }
        
        // Música
        const musicPlayingEl = document.getElementById('music-playing');
        const musicIdleEl = document.getElementById('music-idle');
        const musicSongEl = document.getElementById('music-song');
        const musicArtistEl = document.getElementById('music-artist');
        const musicAppEl = document.getElementById('music-app');
        
        if (data.music && data.music.playing) {
            if (musicPlayingEl) musicPlayingEl.classList.remove('hidden');
            if (musicIdleEl) musicIdleEl.classList.add('hidden');
            if (musicSongEl) musicSongEl.textContent = data.music.song || data.music.title || '--';
            if (musicArtistEl) musicArtistEl.textContent = data.music.artist || '--';
            if (musicAppEl) musicAppEl.textContent = data.music.app || 'Player';
        } else {
            if (musicPlayingEl) musicPlayingEl.classList.add('hidden');
            if (musicIdleEl) musicIdleEl.classList.remove('hidden');
        }
        
        // Discos
        const disksEl = document.getElementById('disks');
        if (disksEl && data.disks && data.disks.length > 0) {
            let disksHtml = '';
            data.disks.forEach(disk => {
                const colorClass = disk.percent > 90 ? 'text-red-500' : disk.percent > 70 ? 'text-yellow-500' : 'text-ravis-blue';
                disksHtml += `
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-gray-400">${disk.name}</span>
                            <span class="${colorClass}">${disk.percent}%</span>
                        </div>
                        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                            <div class="h-full ${colorClass} transition-all duration-500" style="width: ${disk.percent}%"></div>
                        </div>
                        <div class="text-xs text-gray-500 mt-0.5">${disk.used}/${disk.total} GB</div>
                    </div>
                `;
            });
            disksEl.innerHTML = disksHtml;
        }
        
    } catch (err) {
        console.error('Erro ao buscar system-info:', err);
    }
}

function updateIndicator(id, active) {
    const el = document.getElementById(id);
    if (!el) return;
    if (active) {
        el.classList.remove('bg-gray-500');
        el.classList.add('bg-ravis-green', 'animate-pulse');
    } else {
        el.classList.remove('bg-ravis-green', 'animate-pulse');
        el.classList.add('bg-gray-500');
    }
}

// ============================================
// CLIMA - Temperatura, humidade, vento
// ============================================
// Atualiza informações meteorológicas
// ============================================

async function updateWeather() {
    try {
        const res = await fetch(`${API_URL}/weather`);
        const data = await res.json();
        
        if (!data.error) {
            const tempEl = document.getElementById('temp');
            const humidityEl = document.getElementById('humidity');
            const windEl = document.getElementById('wind');
            const locationEl = document.getElementById('location');

            if (tempEl && typeof data.temperature === 'number') {
                tempEl.textContent = `${Math.round(data.temperature)}°C`;
            }
            if (humidityEl && typeof data.humidity !== 'undefined') {
                humidityEl.textContent = data.humidity;
            }
            if (windEl && typeof data.wind === 'number') {
                windEl.textContent = Math.round(data.wind);
            }
            if (locationEl && data.location) {
                locationEl.textContent = data.location;
            }
        }
    } catch (err) {
        console.error('Erro ao buscar clima:', err);
    }
}

// ============================================
// AÇÕES
// ============================================

function toggleVoiceInput() {
    const btn = document.getElementById('voice-btn');
    if (!btn) return;
    
    btn.classList.toggle('bg-[#00FF88]/20');
    btn.classList.toggle('border-[#00FF88]');
    btn.classList.toggle('text-[#00FF88]');
    btn.classList.toggle('animate-pulse');
    
    if (btn.classList.contains('animate-pulse')) {
        addMessage('assistant', 'Modo de entrada de voz ativado. Fale agora...');
        // Aqui você pode adicionar integração com reconhecimento de voz
        // if ('webkitSpeechRecognition' in window) { ... }
    } else {
        addMessage('assistant', 'Modo de entrada de voz desativado.');
    }
}

async function toggleMic() {
    try {
        const res = await fetch(`${API_URL}/computer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'toggle_mic' })
        });
        const data = await res.json();
        
        if (data.success) {
            const status = data.active ? 'ativado' : 'desativado';
            addMessage('assistant', `Microfone ${status}.`);
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao togglar microfone.');
    }
}

async function toggleCamera() {
    try {
        const res = await fetch(`${API_URL}/computer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'toggle_camera' })
        });
        const data = await res.json();
        
        if (data.success) {
            const status = data.active ? 'ativada' : 'desativada';
            addMessage('assistant', `Câmera ${status}.`);
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao togglar câmera.');
    }
}

function toggleMute() {
    // Alterna apenas o áudio local do Ravis (TTS)
    audioEnabled = !audioEnabled;
    
    const status = audioEnabled ? 'ativado' : 'desativado';
    addMessage('assistant', `Áudio do Ravis ${status}.`);
    
    // Atualiza ícone
    const muteIcon = document.getElementById('mute-icon');
    if (muteIcon) {
        if (!audioEnabled) {
            muteIcon.innerHTML = '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>';
            muteIcon.classList.add('text-red-500');
        } else {
            muteIcon.innerHTML = '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>';
            muteIcon.classList.remove('text-red-500');
        }
    }
    
    console.log('[Ravis] Áudio:', audioEnabled ? 'ativado' : 'desativado');
}

async function takeScreenshot() {
    try {
        const res = await fetch(`${API_URL}/computer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'screenshot' })
        });
        const data = await res.json();
        
        if (data.success) {
            addMessage('assistant', `Screenshot salva: ${data.filename}`);
        } else {
            addMessage('assistant', 'Erro ao capturar screenshot.');
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao capturar screenshot.');
    }
}

async function openExplorer() {
    try {
        const res = await fetch(`${API_URL}/computer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'open_explorer' })
        });
        const data = await res.json();
        
        if (data.success) {
            addMessage('assistant', 'Explorador de arquivos aberto.');
        } else {
            addMessage('assistant', 'Erro ao abrir explorador.');
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao abrir explorador.');
    }
}

async function openSettings() {
    try {
        const res = await fetch(`${API_URL}/computer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'open_settings' })
        });
        const data = await res.json();
        
        if (data.success) {
            addMessage('assistant', 'Configurações do sistema abertas.');
        } else {
            addMessage('assistant', 'Erro ao abrir configurações.');
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao abrir configurações.');
    }
}

// ============================================
// CHAT REDIMENSIONÁVEL
// ============================================

const CHAT_MIN_WIDTH = 250;
const CHAT_MAX_WIDTH = 600;
const CHAT_STORAGE_KEY = 'ravis-chat-width';

let isResizing = false;
let chatPanel = null;
let resizer = null;

// ============================================
// CHAT REDIMENSIONÁVEL
// ============================================
// Permite redimensionar o painel de chat
// ============================================

function initChatResizer() {
    chatPanel = document.getElementById('chat-panel');
    resizer = document.getElementById('chat-resizer');
    
    if (!chatPanel || !resizer) {
        console.warn('[Resizer] Elementos não encontrados');
        return;
    }
    
    // Restaurar largura salva
    const savedWidth = localStorage.getItem(CHAT_STORAGE_KEY);
    if (savedWidth) {
        const width = parseInt(savedWidth);
        if (width >= CHAT_MIN_WIDTH && width <= CHAT_MAX_WIDTH) {
            chatPanel.style.width = width + 'px';
        }
    }
    
    // Event listeners para redimensionamento
    resizer.addEventListener('mousedown', startResize);
    document.addEventListener('mousemove', doResize);
    document.addEventListener('mouseup', stopResize);
    
    // Cursor states
    resizer.addEventListener('mouseenter', () => {
        document.body.style.cursor = 'col-resize';
    });
    resizer.addEventListener('mouseleave', () => {
        if (!isResizing) {
            document.body.style.cursor = '';
        }
    });
}

function startResize(e) {
    isResizing = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    resizer.style.background = 'rgba(0, 212, 255, 0.5)';
}

function doResize(e) {
    if (!isResizing || !chatPanel) return;
    
    const containerRect = chatPanel.parentElement.getBoundingClientRect();
    const newWidth = containerRect.right - e.clientX;
    
    if (newWidth >= CHAT_MIN_WIDTH && newWidth <= CHAT_MAX_WIDTH) {
        chatPanel.style.width = newWidth + 'px';
    }
}

function stopResize(e) {
    if (!isResizing) return;
    
    isResizing = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    resizer.style.background = '';
    
    // Salvar largura no localStorage
    if (chatPanel && chatPanel.style.width) {
        const width = parseInt(chatPanel.style.width);
        localStorage.setItem(CHAT_STORAGE_KEY, width);
    }
}

// ============================================
// SELEÇÃO DE REGIÃO
// ============================================

async function startSelection() {
    console.log('[Vision] startSelection() chamada - usando seleção Python!');
    
    // Trazer janela para frente antes de capturar
    if (window.pywebview && window.pywebview.api && window.pywebview.api.bring_to_front) {
        console.log('[Vision] Trazendo janela para frente...');
        window.pywebview.api.bring_to_front();
        // Pequeno delay para garantir que a janela veio para frente
        await new Promise(r => setTimeout(r, 300));
    }
    
    // Chamar a rota que abre seleção com tkinter
    try {
        addMessage('assistant', 'Selecione uma região na tela...');
        
        const response = await fetch(`${API_URL}/vision/selecionar`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        console.log('[Vision] Resultado:', data);
        
        if (data.success) {
            latestCapturePath = data.path;
            latestCaptureTimestamp = data.timestamp;
            // Atualiza imagem na janela de mídia com cache bust
            const img = document.querySelector('#media-window img');
            if (img) {
                img.src = data.path + '?t=' + Date.now();
            }
            updateMediaImage(data.path, data.timestamp);
            toggleMediaWindow(true);
            
            // Análise já foi feita e enviada via WebSocket
            if (data.analysis) {
                addMessage('assistant', data.analysis);
            }
        } else {
            addMessage('assistant', data.error || 'Erro ao capturar tela');
        }
        
    } catch (err) {
        console.error('[Vision] Erro ao selecionar:', err);
        addMessage('assistant', 'Erro ao abrir seleção de tela');
    }
}

// ============================================
// JANELA DE MÍDIA
// ============================================

function toggleMediaWindow(show) {
    const win = document.getElementById('media-window');
    if (show === undefined) show = win.classList.contains('hidden');
    
    if (show) {
        win.classList.remove('hidden');
    } else {
        win.classList.add('hidden');
    }
}

function minimizeMediaWindow() {
    const win = document.getElementById('media-window');
    const body = document.getElementById('media-body');
    const footer = document.getElementById('media-footer');
    
    if (footer.classList.contains('hidden')) {
        footer.classList.remove('hidden');
        body.classList.remove('hidden');
    } else {
        footer.classList.add('hidden');
        body.classList.add('hidden');
    }
}

function updateMediaImage(path, timestamp) {
    const img = document.getElementById('media-image');
    const placeholder = document.getElementById('media-placeholder');
    const ts = document.getElementById('media-timestamp');
    
    if (path) {
        img.src = path;
        img.classList.remove('hidden');
        placeholder.classList.add('hidden');
        ts.textContent = timestamp || '--';
    } else {
        img.classList.add('hidden');
        placeholder.classList.remove('hidden');
        ts.textContent = '--';
    }
}

function openImageFullscreen() {
    const img = document.getElementById('media-image');
    const modal = document.getElementById('fullscreen-modal');
    const fullImg = document.getElementById('fullscreen-image');
    
    if (!img.src || img.classList.contains('hidden')) return;
    
    fullImg.src = img.src;
    modal.classList.remove('hidden');
}

function closeFullscreen() {
    document.getElementById('fullscreen-modal').classList.add('hidden');
}

async function analyzeLatestCapture() {
    if (!latestCapturePath) {
        addMessage('assistant', 'Nenhuma captura disponível para análise.');
        return;
    }
    
    addMessage('assistant', 'Analisando imagem...');
    
    try {
        const response = await fetch(`${API_URL}/vision/analyze`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessage('assistant', data.text);
            speakText(data.text);
        } else {
            addMessage('assistant', `Erro ao analisar: ${data.error}`);
        }
    } catch (err) {
        addMessage('assistant', 'Erro ao analisar imagem.');
    }
}

// ============================================
// DRAG DA JANELA DE MÍDIA
// ============================================

function initMediaWindowDrag() {
    const header = document.getElementById('media-header');
    const win = document.getElementById('media-window');
    
    if (!header || !win) return;
    
    header.addEventListener('mousedown', (e) => {
        if (e.target.tagName === 'BUTTON') return;
        
        mediaWindowDragging = true;
        const rect = win.getBoundingClientRect();
        mediaWindowOffset = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
        win.style.transform = 'none';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!mediaWindowDragging) return;
        
        win.style.left = (e.clientX - mediaWindowOffset.x) + 'px';
        win.style.top = (e.clientY - mediaWindowOffset.y) + 'px';
    });
    
    document.addEventListener('mouseup', () => {
        mediaWindowDragging = false;
    });
}

// ============================================
// EXPOSIÇÃO GLOBAL DE FUNÇÕES
// ============================================
window.sendMessage = sendMessage;
window.toggleMic = toggleMic;
window.toggleCamera = toggleCamera;
window.toggleMute = toggleMute;
window.takeScreenshot = takeScreenshot;
window.openExplorer = openExplorer;
window.openSettings = openSettings;
window.toggleMediaWindow = toggleMediaWindow;
window.minimizeMediaWindow = minimizeMediaWindow;
window.analyzeLatestCapture = analyzeLatestCapture;
window.startSelection = startSelection;
window.initMediaWindowDrag = initMediaWindowDrag;
window.updateMediaImage = updateMediaImage;
