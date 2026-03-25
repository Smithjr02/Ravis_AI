🤖 Ravis — Assistente Virtual Desktop (Estilo JARVIS)
🚀 Visão Geral

O Ravis é um assistente virtual de desktop inspirado no JARVIS (Iron Man), com foco em:


💬 Chat com IA (streaming em tempo real)
🧠 Memória persistente inteligente
🔊 Síntese de voz (TTS)
🌐 Pesquisa web integrada
👁️ Google Lens (captura + análise de tela)
🖥️ Interface moderna estilo futurista (HUD)
🧩 Funcionalidades
🤖 Inteligência Artificial
Integração com Groq (principal) e Gemini (fallback)
Respostas em streaming (tempo real)
Detecção de intenção (ação, conversa, pesquisa)
🧠 Memória
Curto prazo (RAM)
Longo prazo (JSON persistente)
Resumos automáticos de conversas
👁️ Visão (Google Lens)
Captura de tela com PrintScreen
Seleção de área
Análise com IA (multi-engine fallback)
🔊 Áudio
TTS com voz natural (Edge TTS)
Respostas faladas automaticamente
⚙️ Sistema
Controle de volume/brilho
Monitoramento (CPU, RAM, disco)
Atalhos globais
⚙️ Tecnologias
Backend
Python 3.12
FastAPI
WebSocket
Frontend
HTML + CSS + JavaScript
Tailwind CSS
PyWebView (desktop app)
IA
Groq
Gemini
Edge TTS
Sistema
mss (screenshot)
Pillow (imagem)
psutil (monitoramento)
pynput (hotkeys)
🔌 API Endpoints
Chat
POST /chat
GET  /ws  (WebSocket)
Sistema
GET  /status
GET  /system-info
GET  /weather
POST /computer
Visão
POST /vision/capture
POST /vision/analyze
GET  /vision/latest
Áudio
POST /speak
🧠 Sistema de Memória
{
  "informacoes": [],
  "pesquisas": [],
  "conversas_resumidas": [],
  "short_term_backup": []
}
Fluxo:
Guarda mensagens recentes (RAM)
Resume automaticamente conversas antigas
Persiste tudo em JSON
🎮 Atalhos
Tecla	Ação
PrintScreen	Ativa Google Lens
🔄 Fluxo do Chat
Usuário → WebSocket → IA → Streaming → UI → TTS → Memória
🌐 Variáveis de Ambiente

Crie um .env:

GROQ_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=
SERPER_API_KEY=
SEARXNG_URL=http://localhost:8080
RAVIS_MEMORY_FILE=data/memory.json
▶️ Como Executar
# Instalar dependências
pip install -r requirements.txt

# Rodar aplicação
python main.py

Acesse:

http://localhost:8000
🎨 Interface

Layout dividido em 3 áreas:

📊 Sidebar (status do sistema)
🤖 Centro (avatar + HUD futurista)
💬 Chat (mensagens)
🧠 Personalidade

O Ravis possui personalidade:

😎 Estilo carioca refinado
🧠 Inteligente e direto
🗣️ Comunicação natural e fluida
📌 Roadmap (Ideias Futuras)
 Comando por voz (speech-to-text)
 Plugins externos
 Integração com IoT
 Controle remoto de dispositivos
 Sistema de automação (tipo Jarvis real)
