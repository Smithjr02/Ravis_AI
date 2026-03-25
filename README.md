# Ravis AI Assistant

Assistente virtual JARVIS-style com personalidade Carioca (Rio de Janeiro).

## Funcionalidades

- 🎙️ **Reconhecimento de Voz** - Ativação por hotword ("E aí, Ravis")
- 🧠 **IA Conversacional** - Chat inteligente com memória persistente
- 👁️ **Visão Computacional** - Análise de tela e capturas
- 💻 **Controle do Computador** - Automação de tarefas
- 🔍 **Busca na Web** - Pesquisas em tempo real
- 🔊 **TTS (Text-to-Speech)** - Voz sintética estilo JARVIS

## Instalação

```bash
# Clone o repositório
git clone https://github.com/Smithjr02/Ravis_AI.git
cd Ravis_AI

# Crie ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes chaves de API:

| Variável | Descrição | Onde obter |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | OpenAI (GPT) | https://platform.openai.com/api-keys |
| `GROQ_API_KEY` | Groq (LLMs rápidos) | https://console.groq.com/keys |
| `GEMINI_API_KEY` | Google Gemini | https://aistudio.google.com/app/apikey |
| `TAVILY_API_KEY` | Tavily Search | https://tavily.com/ |
| `SERPER_API_KEY` | Serper Search | https://serper.dev/ |
| `OPENROUTER_API_KEY` | OpenRouter (agregador) | https://openrouter.ai/ |

Exemplo de `.env`:
```env
OPENAI_API_KEY=sua-chave-openai
GROQ_API_KEY=sua-chave-groq
GEMINI_API_KEY=sua-chave-gemini
TAVILY_API_KEY=sua-chave-tavily
SERPER_API_KEY=sua-chave-serper
OPENROUTER_API_KEY=sua-chave-openrouter
PYTHONDONTWRITEBYTECODE=1
SEARCH_TIMEOUT=10
SEARCH_CACHE_TTL=300
```

## Uso

```bash
python main.py
```

Acesse a interface em: http://localhost:8000

## Comandos de Voz

- "E aí, Ravis" - Ativar assistente
- "tchau" / "encerrar" - Desativar

## Tech Stack

- Python 3.12+
- FastAPI (servidor)
- OpenAI / Groq / Gemini (IA)
- Edge TTS (voz)
- Whisper (voz)

## Licença

MIT
