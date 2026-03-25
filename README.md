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

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves de API
```

## Configuração

Crie um arquivo `.env` com:

```env
OPENAI_API_KEY=sua-chave-aqui
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
- OpenAI API (IA)
- Edge TTS (voz)
- Whisper (voz)

## Licença

MIT
