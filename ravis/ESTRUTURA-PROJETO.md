# ESTRUTURA DO PROJETO RAVIS

## Visão Geral

**Ravis** é um assistente virtual de desktop com:
- IA via Groq/Gemini (streaming)
- Síntese de voz (Edge TTS)
- Pesquisa web (Tavily, Serper, DuckDuckGo)
- **Google Lens** (captura de tela + AI Vision com fallback)
- Interface web moderna com Tailwind CSS (visual JARVIS/Iron Man)
- Modo compacto
- Memória persistente com resumos de conversas

---

## Estrutura de Arquivos

```
ravis/
├── .env                          # Configurações (API keys)
├── config.py                     # Configurações Python
├── main.py                       # Entry point (pywebview)
├── server.py                     # Servidor FastAPI + WebSocket
├── requirements.txt              # Dependências Python
│
├── src/                         # Código fonte
│   ├── config.py               # Configurações (dataclasses)
│   ├── core/                   # Módulos Core
│   │   ├── ai.py              # IA (Groq/Gemini)
│   │   ├── intent.py          # Reconhecimento de intenção
│   │   ├── memory.py          # Memória (short-term + long-term)
│   │   ├── router.py          # Roteamento de comandos
│   │   ├── vision.py          # Google Lens (captura + análise)
│   │   └── wake_word.py       # Wake word (opcional)
│   │
│   └── modules/                # Módulos de Sistema
│       ├── computer.py         # Volume, brilho, mute
│       ├── hotkeys.py         # Atalhos globais (PrintScreen)
│       ├── search.py          # Pesquisa web
│       ├── capture.py         # Captura de tela (tkinter)
│       └── startup.py         # Gerenciamento startup Windows
│
├── data/                       # Dados persistidos
│   ├── memory.json            # Memória (informações, resumos de conversas)
│   ├── memory.json.bak*       # Backups rotacionados
│   ├── last_action.json       # Última ação executada
│   └── __pycache__/           # Cache Python (redirecionado)
│
├── ui/                         # Interface Web
│   ├── app.js                # Cliente JavaScript
│   ├── index.html             # Interface principal (Iron Man)
│   ├── compact.html           # Modo compacto
│   └── style.css              # Estilos extras (CSS puro)
│
└── bin/                        # Ferramentas externas
    └── nircmd.exe             # Controle de volume/brilho
```

---

## Sistema de Memória

### Estrutura (data/memory.json)
```json
{
  "informacoes": [...],           // Facts sobre o usuário
  "pesquisas": [...],             // Pesquisas recentes
  "conversas_resumidas": [...],   // Resumos de conversas antigas
  "short_term_backup": [...]      // Últimas mensagens da sessão
}
```

### Fluxo de Memória
1. **Short-term** (RAM): últimas ~15 mensagens da conversa atual
2. **Long-term** (data/memory.json): todas as conversas + facts do usuário
3. **Resumos**: quando short_term > 20 mensagens, as mais antigas são resumidas e salvas em `conversas_resumidas`

---

## Layout da Interface

```
┌─────────────┬────────────────────────┬─────────────┐
│  SIDEBAR   │   ÁREA CENTRAL         │    CHAT    │
│  (widgets) │   (Iron Man SVG)      │  (mensagens)│
│             │                        │             │
│  - Clima   │   [Iron Man Avatar]   │  - Messages │
│  - Rede    │   [Grid 3D]           │  - Input    │
│  - Música  │   [Partículas]        │             │
│  - Disco   │                        │             │
│  - Sistema │                        │             │
└─────────────┴────────────────────────┴─────────────┘
```

### Áreas:
1. **Sidebar (esquerda)** - Widgets de sistema (clima, rede, música, disco, CPU/RAM)
2. **Área central** - Iron Man SVG com grid 3Dperspective minimalista + partículas
3. **Chat (direita)** - Mensagens + input de texto

---

## Tecnologias

### Backend
- **FastAPI** - Servidor web + REST API
- **WebSocket** - Comunicação em tempo real (streaming)
- **Python 3.12** - Linguagem principal

### Frontend
- **Tailwind CSS** - Estilização (CDN)
- **Pywebview** - Interface desktop (Chromium)
- **JavaScript** - Client-side (WebSocket, TTS, Frequency Analyzer)

### IA
- **Groq** - IA principal (rápido, gratuito)
- **Gemini** - IA fallback + Vision
- **Edge TTS** - Síntese de voz (PT-BR)

### Sistema
- **mss** - Captura de tela
- **Pillow** - Processamento de imagem
- **pynput** - Atalhos globais de teclado
- **psutil** - Monitoramento de sistema
- **nircmd** - Controle de volume/brilho (Windows)

---

## API Endpoints

### Chat
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | /chat | Chat HTTP simples |
| GET | /ws | WebSocket para streaming |

### Sistema
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | /status | CPU, RAM, disco |
| GET | /system-info | Rede, música |
| GET | /weather | Clima |
| POST | /computer | Ações (screenshot, explorer, mute) |

### Visão (Google Lens)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | /vision/capture | Captura região específica |
| POST | /vision/analyze | Analisa última captura |
| POST | /vision/selecionar | Seleção tkinter + captura + análise |
| GET | /vision/latest | Última captura |

### Áudio
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | /speak | TTS (Edge) |

---

## Atalhos

| Atalho | Ação |
|--------|------|
| `PrintScreen` | Google Lens - Seleção de área (funciona de qualquer aplicação) |

---

## Fluxo do Chat

```
1. Usuário envia mensagem → WebSocket
2. Servidor detecta intenção (acao/pesquisa/conversa)
3. Envia para IA (Groq → Gemini fallback)
4. Recebe resposta em streaming (chunk por chunk)
5. Exibe no chat progressivamente
6. Toca áudio via Edge TTS
7. Salva contexto na memória (a cada 5 trocas)
```

---

## WebSocket Messages

### Cliente → Servidor
```json
{"type": "chat", "text": "Olá"}
```

### Servidor → Cliente
```json
{"type": "stream", "content": "Olá! "}
{"type": "done", null}
{"type": "vision_result", "text": "Descrição da imagem"}
{"type": "error", "content": "Erro..."}
```

---

## Google Lens

### Como funciona:
1. Pressione **PrintScreen** (de qualquer aplicação)
2. Script `capture.py` abre janela de seleção tkinter (fullscreen transparente)
3. Clique e arraste para selecionar uma região
4. Captura automaticamente a região selecionada
5. Envia para análise de IA com fallback chain: **Groq → OpenRouter → Gemini**
6. Resultado é resumido intelligentemente e aparece no chat + TTS

### Tecnologias:
- **capture.py** - Script standalone com tkinter para seleção de região
- **mss** - Captura de tela
- **Pillow** - Processamento de imagem
- **AI fallback chain** - Groq → OpenRouter → Gemini Vision

---

## Variáveis de Ambiente (.env)

```
GROQ_API_KEY=gs...
GEMINI_API_KEY=AI...
TAVILY_API_KEY=tvly-...
SERPER_API_KEY=...
SEARXNG_URL=http://localhost:8080
RAVIS_MEMORY_FILE=data/memory.json
```

---

## Como Executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python main.py
```

A interface abre em: **http://localhost:8000**

---

## Estados do Assistente (UI)

| Estado | Cor | Descrição |
|--------|-----|-----------|
| idle | #00D4FF (cyan) | Pronto para nova mensagem |
| thinking | #FFD700 (gold) | Processando resposta |
| speaking | #00FF88 (green) | Enviando resposta (stream) |
| searching | #FF6B00 (orange) | Pesquisando na web |
| listening | #00D4FF (cyan) | Recebendo mensagem |
| error | #FF3B3B (red) | Erro detectado |

---

## Personalidade (Carioca)

O Ravis tem personalidade **carioca** com tom refinado:
- **Nascido na Lapa, Rio de Janeiro**
- Humor espontâneo e prestativo
- Vocabulário: patrão, parça, consagrado, meu sangue, tranquilo
- Sem gírias forçadas — respostas 100% espontâneas via IA

---

## Arquivos Importantes

| Arquivo | Descrição |
|---------|-----------|
| server.py | Servidor principal (FastAPI + WebSocket) |
| src/core/ai.py | Integração com Groq/Gemini |
| src/core/memory.py | Sistema de memória persistente |
| src/modules/vision.py | Google Lens (captura + análise) |
| src/modules/hotkeys.py | Atalhos globais (PrintScreen) |
| ui/app.js | Cliente JavaScript |
| ui/index.html | Interface principal (Iron Man) |
| ui/style.css | Estilos CSS extras |
| main.py | Entry point (pywebview) |
