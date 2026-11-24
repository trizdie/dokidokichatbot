# chatbot_config.py
# Configuracao do chatbot para o Ren'Py.
#
# Modo 1 (recomendado): Flask local — rode "python app.py" na pasta chatbot/
# Modo 2: Groq (gratuito) — pegue sua chave em https://console.groq.com/keys
# Modo 3: OpenAI — pegue sua chave em https://platform.openai.com/api-keys
# Modo 4: RapidAPI — requer assinatura ativa

USE_LOCAL = True

LOCAL_API_URL = "http://localhost:5001/api/chat"

# Groq (gratuito, comeca com gsk_)
GROQ_API_KEY = ""
GROQ_HOST = "api.groq.com"
GROQ_MODEL = "openai/gpt-oss-20b"

# OpenAI (comeca com sk_)
OPENAI_API_KEY = ""

# RapidAPI
RAPIDAPI_KEY = ""
RAPIDAPI_HOST = "chatgpt53.p.rapidapi.com"

# Modelo padrao (para OpenAI/RapidAPI)
MODEL = "gpt-3.5-turbo"
MAX_TOKENS = 150
TEMPERATURE = 0.9
