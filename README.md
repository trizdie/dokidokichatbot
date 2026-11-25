<div align="center">
 <img src="https://raw.githubusercontent.com/SecondThundeR/DokiDoki-RenPy/your-reality/readme_files/logos/ddlc_logo.png" width="256px" height="256px" alt="DDLC-Logo">
 <h1>Doki Doki Literature Club — Ren'Py Chatbot Mod</h1>
 <blockquote><b>Warning! These files contain many spoilers <i>(obviously)</i>. <br>If you haven't played DDLC yet, play the original game first to get the true experience.</b></blockquote>
</div>

This repository is a DDLC (1.1.1) decompiled project extended with an AI chatbot mod.
You pick one of the four girls (Sayori, Natsuki, Yuri, Monika) and chat with her:
her sprite reacts emotionally to what you write (compliments make her happy, teasing makes
her angry, insults make her sad, etc.) and she replies in character through an AI backend.

> Secrets: the real API keys live only in `chatbot/.env` (gitignored). The committed
> `chatbot/.env.example` has blank values. Never commit a filled `.env`.

---

## English — How to use the chatbot

### 1. Prerequisites
- Ren'Py SDK (or an installed copy of DDLC) to run `ddlc-renpy-project/`.
- Python 3.9+ for the backend in `chatbot/`.
- An API key for one provider (any one is enough):
  - **Groq** (free): https://console.groq.com/keys — key starts with `gsk_`
  - **OpenAI**: https://platform.openai.com/api-keys — key starts with `sk-`
  - **RapidAPI**: requires an active subscription.

### 2. Configure the backend
```bash
cd chatbot
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and paste at least one key. Example (Groq, free):
#   GROQ_API_KEY=gsk_...
#   GROQ_MODEL=openai/gpt-oss-20b
#   PORT=5001
```

You can also tune the model in `ddlc-renpy-project/game/chatbot_config.py`
(`USE_LOCAL`, `LOCAL_API_URL`, `MODEL`, `MAX_TOKENS`, `TEMPERATURE`).

### 3. Start the backend
```bash
python app.py
```
You should see `Chatbot running on http://localhost:5001`. Leave this terminal open.

### 4. Run the game
1. Open the Ren'Py Launcher.
2. Point it at the `ddlc-renpy-project/` folder (or create a project and copy its contents in).
3. Launch the project.
4. On first run, type your name and press OK.
5. Choose a girl from the character selection screen.

### 5. Chat
- Type your message in the input box (top-left of the dialogue panel) and press **Enter** or click **Send**.
- Your line appears first, then her AI reply appears automatically (the “next” arrow shows up once it’s ready).
- Click the **next arrow** (▶) to dismiss the reply and get the input back. Her expression returns to neutral.
- **Log** opens the chat history; **Clear** wipes the conversation; **Back** returns to character selection.
- Her sprite changes while chatting: compliments → happy, teasing → angry, insults/mockery → sad, etc.

### 6. Troubleshooting
- “No API key configured…” → fill `chatbot/.env` and restart `app.py`.
- Backend not reachable → make sure `app.py` is running on the port in `chatbot_config.py` (`LOCAL_API_URL`).
- Lint check: `DDLC.exe <project> lint` should report 0 errors.

---

## Português — Como usar o chatbot

### 1. Pré-requisitos
- Ren'Py SDK (ou uma cópia instalada de DDLC) para rodar `ddlc-renpy-project/`.
- Python 3.9+ para o backend em `chatbot/`.
- Uma chave de API de um provedor (qualquer um basta):
  - **Groq** (grátis): https://console.groq.com/keys — chave começa com `gsk_`
  - **OpenAI**: https://platform.openai.com/api-keys — chave começa com `sk-`
  - **RapidAPI**: requer assinatura ativa.

### 2. Configurar o backend
```bash
cd chatbot
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edite .env e cole pelo menos uma chave. Exemplo (Groq, grátis):
#   GROQ_API_KEY=gsk_...
#   GROQ_MODEL=openai/gpt-oss-20b
#   PORT=5001
```

Você também pode ajustar o modelo em `ddlc-renpy-project/game/chatbot_config.py`
(`USE_LOCAL`, `LOCAL_API_URL`, `MODEL`, `MAX_TOKENS`, `TEMPERATURE`).

### 3. Iniciar o backend
```bash
python app.py
```
Você deve ver `Chatbot running on http://localhost:5001`. Deixe esse terminal aberto.

### 4. Rodar o jogo
1. Abra o Ren'Py Launcher.
2. Aponte para a pasta `ddlc-renpy-project/` (ou crie um projeto e copie o conteúdo).
3. Inicie o projeto.
4. Na primeira execução, digite seu nome e pressione OK.
5. Escolha uma das garotas na tela de seleção de personagem.

### 5. Conversar
- Digite sua mensagem na caixa de entrada (canto superior esquerdo do painel de diálogo) e pressione **Enter** ou clique em **Send**.
- Sua fala aparece primeiro, depois a resposta da IA aparece automaticamente (a seta “próximo” aparece quando estiver pronta).
- Clique na **seta de próximo** (▶) para dispensar a resposta e voltar a digitar. A expressão dela volta ao neutro.
- **Log** abre o histórico da conversa; **Clear** apaga a conversa; **Back** volta à seleção de personagem.
- O sprite dela muda enquanto conversa: elogios → feliz, provocações → brava, insultos/zombarias → triste, etc.

### 6. Solução de problemas
- “No API key configured…” → preencha `chatbot/.env` e reinicie `app.py`.
- Backend inacessível → verifique se `app.py` está rodando na porta de `chatbot_config.py` (`LOCAL_API_URL`).
- Verificação de lint: `DDLC.exe <projeto> lint` deve reportar 0 erros.

---

## Project layout
- `ddlc-renpy-project/` — Ren'Py project (game scripts, sprites, UI).
- `chatbot/` — Flask backend + original web frontend.
- `chatbot/.env` — your secrets (gitignored). `chatbot/.env.example` — template.
- The `oi/` folder and `README_RU.md` are intentionally excluded from the repository.

## License
Decompiled sources are licensed under the MIT License and provided "AS IS". All rights reserved by Team Salvato.
Also thanks to Ren'Py, unrpa and unrpyc authors.