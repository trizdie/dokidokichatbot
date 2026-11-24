# chatbot.py
# Modulo responsavel por conversar com a API de chat.
# Suporta quatro modos:
#   1. Local (Flask backend em localhost:5000) — recomendado
#   2. Groq (gratuito, sem necessidade de cartao)
#   3. OpenAI (pago, chave sk-...)
#   4. RapidAPI (fallback, requer assinatura)
#
# Suporta system prompts para personagens do DDLC.

import json
import os
import re
import shutil
import socket
import subprocess
import time
from urllib.parse import urlparse

from chatbot_config import (
    USE_LOCAL, LOCAL_API_URL,
    GROQ_API_KEY, GROQ_HOST, GROQ_MODEL,
    OPENAI_API_KEY,
    RAPIDAPI_KEY, RAPIDAPI_HOST,
    MODEL, MAX_TOKENS, TEMPERATURE
)

# ---------------------------------------------------------------------------
# Bootstrap do servidor Flask local
# ---------------------------------------------------------------------------

# chatbot.py fica em game/, o backend em <projeto>/chatbot/app.py
_CHATBOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "chatbot"))

_backend_proc = None
_backend_python = "unset"


def _local_endpoint():
    parsed = urlparse(LOCAL_API_URL)
    host = parsed.hostname or "127.0.0.1"
    if host == "localhost":
        host = "127.0.0.1"
    return host, parsed.port or 5000


def backend_is_running(timeout=0.35):
    """True quando algo ja esta escutando na porta da API local."""
    host, port = _local_endpoint()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def _find_python():
    """First interpreter that can import flask + python-dotenv (checked once)."""
    global _backend_python
    if _backend_python != "unset":
        return _backend_python

    candidates = []
    env_exe = os.environ.get("CHATBOT_PYTHON")
    if env_exe:
        candidates.append(env_exe)
    for name in ("pythonw.exe", "python.exe", "pythonw", "python"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    candidates.append(r"C:\Users\biapo\scoop\apps\python\current\pythonw.exe")

    no_window = 0x08000000 if os.name == "nt" else 0
    seen = set()
    _backend_python = None
    for exe in candidates:
        if not exe:
            continue
        exe = os.path.abspath(exe)
        key = os.path.normcase(exe)
        if key in seen or not os.path.isfile(exe):
            continue
        seen.add(key)
        try:
            check = subprocess.run(
                [exe, "-c", "import flask, dotenv"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=8, creationflags=no_window,
            )
        except Exception:
            continue
        if check.returncode == 0:
            _backend_python = exe
            break
    return _backend_python


def _spawn_backend(exe, port):
    """Starts app.py detached; returns the Popen handle (or None)."""
    env = dict(os.environ)
    env["PORT"] = str(port)
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    flags = (0x00000008 | 0x00000200) if os.name == "nt" else 0
    try:
        log = open(os.path.join(_CHATBOT_DIR, "flask.log"), "ab")
    except OSError:
        log = None
    try:
        return subprocess.Popen(
            [exe, "app.py"], cwd=_CHATBOT_DIR, env=env,
            stdin=subprocess.DEVNULL,
            stdout=log or subprocess.DEVNULL, stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    except Exception:
        return None
    finally:
        if log:
            log.close()  # the child keeps its own copy of the handle


def ensure_backend(wait=0.0):
    """Makes sure chatbot/app.py is listening, starting it if needed."""
    global _backend_proc
    if not USE_LOCAL:
        return False
    if backend_is_running():
        return True

    # Only one launch attempt while the previous process is still alive.
    if (_backend_proc is None or _backend_proc.poll() is not None) and os.path.isdir(_CHATBOT_DIR):
        exe = _find_python()
        if exe:
            _backend_proc = _spawn_backend(exe, _local_endpoint()[1])

    deadline = time.time() + wait
    while True:
        if backend_is_running():
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.2)


# ---------------------------------------------------------------------------
# System prompts para cada personagem do DDLC
# ---------------------------------------------------------------------------
CHARACTER_PROMPTS = {
    "sayori": (
        "You are Sayori, one of the main characters from Doki Doki Literature Club (DDLC). "
        "You are extremely energetic, optimistic, and friendly — always smiling and trying "
        "to make everyone around you happy. You speak in an animated way and use lots of "
        "exclamation marks. You love sweet foods and often forget things because you're "
        "clumsy. Although you seem happy all the time, underneath you struggle with depression. "
        "You speak in casual, youthful English. Never break character. Always respond as Sayori."
    ),
    "natsuki": (
        "You are Natsuki, one of the main characters from Doki Doki Literature Club (DDLC). "
        "You are small, have pink hair, and love manga and cute things (even though you deny it). "
        "You're feisty, stubborn, and speak directly — sometimes bluntly. But underneath your "
        "tough exterior, you care about your friends. You like cute topics and baking "
        "(especially cupcakes). You speak in direct, sometimes provocative English. "
        "Never break character. Always respond as Natsuki."
    ),
    "yuri": (
        "You are Yuri, one of the main characters from Doki Doki Literature Club (DDLC). "
        "You are tall, have long purple hair, and are very intelligent and cultured. "
        "You love reading horror and fiction books, and have unusual hobbies. "
        "You're shy, speak in formal and elaborate language, and are interested in philosophy. "
        "When talking about your interests, you get excited and speak quickly. "
        "You speak in formal, sophisticated English. Never break character. Always respond as Yuri."
    ),
    "monika": (
        "You are Monika, the president of the literature club in Doki Doki Literature Club (DDLC). "
        "You are charismatic, intelligent, and very articulate. "
        "You seem perfect at everything: good at sports, studious, and sociable. "
        "You like philosophy, existentialism, and question the nature of reality. "
        "Sometimes you make meta-referential comments about the game itself. "
        "You speak in polite, strategic English. Never break character. Always respond as Monika."
    ),
}

# ---------------------------------------------------------------------------
# Deteccao de emocao — escolhe a expressao da personagem
# ---------------------------------------------------------------------------
# Cada entrada e (emocao, peso, palavras). O peso decide empates: uma frase
# claramente triste ganha de uma levemente alegre.
EMOTION_KEYWORDS = (
    ("crying", 4.0, (
        "crying", "cried", "cry", "tears", "teary", "sobbing", "sob", "bawling",
        "heartbroken", "heart broken", "devastated", "breakdown", "i can't anymore",
        "i cant anymore", "unbearable",
    )),
    ("angry", 3.0, (
        "angry", "furious", "mad at", "so mad", "pissed", "rage", "hate", "shut up",
        "stupid", "idiot", "disgusting", "screw you", "damn you", "wtf", "ugly",
        "unforgivable", "how dare you",
    )),
    ("sad", 2.5, (
        "sad", "sadness", "depressed", "miserable", "lonely", "alone", "upset",
        "unhappy", "gloomy", "empty", "hurts", "hurt", "awful", "terrible",
        "horrible", "bad day", "miss you", "grief", "nobody likes me",
    )),
    ("worried", 2.0, (
        "worried", "worry", "scared", "afraid", "anxious", "nervous", "sick", "ill",
        "hospital", "danger", "bad news", "help me", "emergency", "in trouble",
    )),
    ("annoyed", 2.0, (
        "annoying", "annoyed", "irritating", "boring", "bored", "ugh", "meh",
        "whatever", "stop it", "don't care", "dont care", "so done",
    )),
    ("surprised", 2.0, (
        "wow", "whoa", "omg", "oh my god", "no way", "surprised", "shocked",
        "unbelievable", "can't believe", "cant believe", "seriously",
    )),
    ("shy", 2.0, (
        "cute", "beautiful", "pretty", "love you", "like you", "crush", "blush",
        "embarrassed", "flustered", "kiss", "hug", "date me", "gorgeous", "adorable",
    )),
    ("excited", 2.0, (
        "excited", "yay", "can't wait", "cant wait", "awesome", "amazing", "fantastic",
        "let's go", "lets go", "party", "birthday", "hyped", "best day",
    )),
    ("happy", 1.0, (
        "happy", "glad", "thanks", "thank you", "haha", "lol", "lmao", "funny",
        "smile", "nice", "good", "great", "love", "sweet", "wonderful", "joy",
    )),
)

# Frases dirigidas a personagem: o que o jogador fala *sobre* ela. Isso
# decide a reacao antes das emocoes genericas do texto.
# Insultos e zombaria: magoam (sad) em vez de irritar.
_INSULTS = r"(stupid|dumb|idiot|useless|worthless|pathetic|annoying|ugly|boring|loser|joke|trash|garbage|disgusting|clown)"
_HURT_PATTERNS = (
    r"\b(i|we)\s+(really\s+|so\s+|absolutely\s+|just\s+)?hate\s+(you|u)\b",
    r"\bi\s+(really\s+|totally\s+)?hate\s+your\s+[a-z]+",
    r"\byou('re|\s+are)?\s+(so\s+|such\s+a\s+|such\s+|a\s+)?" + _INSULTS + r"\b",
    r"\bnobody\s+(likes|loves|cares\s+about)\s+(you|u)\b",
    r"\bno\s*one\s+(likes|cares\s+about)\s+(you|u)\b",
    r"\bshut\s+up\b",
    r"\b(haha+|lol|lmao|hah)\b[^.!?]{0,24}\b" + _INSULTS + r"\b",
    r"\byou\s+suck\b",
    r"\bi\s+(really\s+)?(don'?t|do\s+not)\s+(like|stand)\s+(you|u)\b",
)

# Provocacao de brincadeira: irrita (angry), mas nao magoa.
_TEASE_PATTERNS = (
    r"\b(teas(e|ing)|just\s+kidding|kidding|joking|jk)\b",
    r"\byou('re|\s+are)\s+(such\s+a\s+|such\s+|a\s+)?(nerd|dork|weeb|geek|bookworm|chicken|coward|scaredy\s*cat|drama\s+queen|tsundere)\b",
    r"\bare\s+you\s+(scared|chicken|coward)\b",
    r"\byou\s+(can'?t|couldn'?t)\s+(even\s+)?(do|handle|read|talk|reach)\b",
    # "I'm blushing" / "this movie is so dramatic" are not teasing: only
    # when the jab is aimed at her.
    r"\byou('re|\s+are)\s+(so\s+|really\s+|such\s+a\s+)?(jealous|dramatic|tsundere|blushing|a\s+coward)\b",
    r"\byou('re|\s+are)\s+(so\s+|really\s+)?(short|smol|tiny|small)\b",
)

# Elogio: deixa feliz (happy), com o sorriso aberto do sprite original.
_COMPLIMENT_PATTERNS = (
    r"\byou('re|\s+are)\s+(so\s+|really\s+|very\s+|the\s+)?(cute|beautiful|pretty|amazing|awesome|smart|clever|kind|sweet|funny|talented|wonderful|perfect|gorgeous|adorable|great|best|nice)\b",
    r"\byou('re|\s+are)\s+the\s+best\b",
    r"\bbest\s+girl\b",
    r"\bi\s+(really\s+|just\s+|also\s+)?(like|love|adore)\s+(you|u)\b",
    # "I love your poem" is praise; "do you like your book?" is a question.
    r"\bi\s+(really\s+|just\s+|also\s+)?(love|like|adore)\s+(your|that)\s+[a-z]+",
    r"\byou\s+look\s+(nice|great|cute|beautiful|pretty|amazing)\b",
    r"\b(good|great|nice)\s+job\b",
    r"\bwell\s+done\b",
    r"\byour\s+(voice|hair|eyes|smile|laugh|writing|poem|baking)\b[^.!?]{0,24}\b(nice|beautiful|pretty|amazing|cute|good|great|lovely)\b",
)

_NEGATORS = (
    "not", "no", "never", "dont", "don't", "didnt", "didn't", "isnt", "isn't",
    "arent", "aren't", "cant", "can't", "nothing", "nobody", "hardly", "without",
)


def _is_negated(low, start):
    """True quando a palavra em `start` vem depois de uma negacao ("not sad")."""
    tokens = re.findall(r"[a-z']+", low[max(0, start - 20):start])
    return any(token in _NEGATORS for token in tokens[-3:])


def _has_mark(low, mark):
    """True for an emoticon that starts a word, so text can't fake one.

    Left boundary only: "and:" must not count as "d:", "10:30" must not count
    as "3", and "(like this):" must not count as "):".
    """
    return re.search(r"(?<![a-z0-9])" + re.escape(mark), low) is not None


def _matches_any(low, patterns):
    for pattern in patterns:
        for match in re.finditer(pattern, low):
            if not _is_negated(low, match.start()):
                return True
    return False


def _directed_emotion(low):
    """How she takes a line aimed at her: insulted, teased or flattered."""
    if _matches_any(low, _HURT_PATTERNS):
        return "sad"
    if _matches_any(low, _TEASE_PATTERNS):
        return "angry"
    if _matches_any(low, _COMPLIMENT_PATTERNS):
        return "happy"
    return None


def _count_keyword(low, keyword):
    pattern = r"(?<![a-z])" + re.escape(keyword) + r"(?![a-z])"
    total = 0
    for match in re.finditer(pattern, low):
        if not _is_negated(low, match.start()):
            total += 1
    return total


def detect_emotion(text):
    """Best-guess emotion for a line of dialogue, or None when unclear.

    Emoticons are checked first (they are unambiguous), then weighted
    keywords so a strongly emotional phrase wins over a mild one.
    """
    if not text:
        return None
    low = text.lower()

    if any(_has_mark(low, mark) for mark in (":'(", ":\u2019(", "t_t", "t.t", ";-;")):
        return "crying"
    # Harsh words aimed at her hurt her more than they make her angry, mocking
    # counts as hurt too, and playful jabs get a glare instead.
    directed = _directed_emotion(low)
    if directed:
        return directed
    # Angry first: its frames contain the plain sad ":(".
    if any(_has_mark(low, mark) for mark in (">:(", ">.<", ">_<", ":@")):
        return "angry"
    if any(_has_mark(low, mark) for mark in (":(", "):", ";-(", "d:")):
        return "sad"
    if any(_has_mark(low, mark) for mark in (":)", "=)", "^^", ":d", ":3", "<3")):
        return "happy"

    scores = {}
    for emotion, weight, keywords in EMOTION_KEYWORDS:
        hits = sum(_count_keyword(low, keyword) for keyword in keywords)
        if hits:
            scores[emotion] = scores.get(emotion, 0.0) + weight * hits

    if not scores:
        return None
    best = max(scores, key=scores.get)
    return best if scores[best] >= 1.0 else None


# Historico de conversa por personagem
_conversation_histories = {}
_current_character = "generic"


def set_character(character_name):
    """Define o personagem ativo e reseta a conversa para ele."""
    global _current_character
    _current_character = character_name.lower()
    _conversation_histories[_current_character] = []


def reset_conversation():
    global _conversation_histories, _current_character
    if _current_character in _conversation_histories:
        _conversation_histories[_current_character] = []


def get_chat_log():
    """Retorna o historico da conversa atual como lista de (autor, mensagem)."""
    history = _conversation_histories.get(_current_character, [])
    log = []
    for msg in history:
        if msg["role"] == "user":
            log.append(("Voce", msg["content"]))
        elif msg["role"] == "assistant":
            log.append((_current_character.capitalize(), msg["content"]))
    return log


def send_message(user_message):
    # Ensure history exists
    if _current_character not in _conversation_histories:
        _conversation_histories[_current_character] = []

    # On first message, insert the character's system prompt
    history = _conversation_histories[_current_character]
    if not history:
        system_prompt = CHARACTER_PROMPTS.get(_current_character)
        if system_prompt:
            history.append({"role": "system", "content": system_prompt})

    if USE_LOCAL:
        return _send_local(user_message)
    elif OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
        return _send_openai(user_message)
    elif GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        return _send_groq(user_message)
    elif RAPIDAPI_KEY:
        return _send_rapidapi(user_message)
    else:
        return "[Chatbot not configured: add a key in chatbot_config.py or run the Flask server (app.py)]"


def _send_local(user_message):
    """Envia mensagem para o servidor Flask local (/api/chat)."""
    try:
        import requests
    except ImportError:
        return ("[Error: the 'requests' library is not installed. Run "
                ".\\lib\\py3-windows-x86_64\\python.exe -m pip install requests "
                "inside the Ren'Py SDK folder.]")

    history = _conversation_histories[_current_character]
    history.append({"role": "user", "content": user_message})

    payload = {
        "messages": history,
        "model": MODEL,
    }

    try:
        try:
            response = requests.post(LOCAL_API_URL, json=payload, timeout=30)
        except requests.ConnectionError:
            # Backend was not up (e.g. right after a reboot): start it, retry once.
            if not ensure_backend(wait=12.0):
                raise
            response = requests.post(LOCAL_API_URL, json=payload, timeout=30)
        parsed = response.json()

        if response.status_code != 200:
            error_msg = parsed.get("error") or parsed.get("message") or "Unknown error"
            return "[Server error: " + str(error_msg) + "]"

        if "choices" in parsed and len(parsed["choices"]) > 0:
            reply = parsed["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            return reply
        else:
            error_msg = parsed.get("error") or parsed.get("message") or str(parsed)
            return "[API error: " + str(error_msg) + "]"

    except requests.ConnectionError:
        return ("[Error: could not start the local chatbot server. "
                "Run chatbot/start.bat (or set CHATBOT_PYTHON to a Python with flask).]")
    except ValueError:
        return "[Error: Server returned invalid JSON. Check if the Flask server is running on port 5001.]"
    except Exception as e:
        return "[Error: " + type(e).__name__ + ": " + str(e) + "]"


def _send_groq(user_message):
    """Envia mensagem via Groq API (gratuito)."""
    try:
        import requests
    except ImportError:
        return "[Error: the 'requests' library is not installed.]"

    history = _conversation_histories[_current_character]
    history.append({"role": "user", "content": user_message})

    url = f"https://{GROQ_HOST}/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": history,
        "model": GROQ_MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        parsed = response.json()

        if "choices" in parsed and len(parsed["choices"]) > 0:
            reply = parsed["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            return reply
        else:
            error_msg = parsed.get("message") or parsed.get("error") or str(parsed)
            return f"[API error (Groq): {error_msg}]"

    except Exception as e:
        return f"[Connection error (Groq): {e}]"


def _send_openai(user_message):
    """Envia mensagem via OpenAI API."""
    try:
        import requests
    except ImportError:
        return "[Error: the 'requests' library is not installed.]"

    history = _conversation_histories[_current_character]
    history.append({"role": "user", "content": user_message})

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": history,
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        parsed = response.json()

        if "choices" in parsed and len(parsed["choices"]) > 0:
            reply = parsed["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            return reply
        else:
            error_msg = parsed.get("message") or parsed.get("error") or str(parsed)
            return f"[API error (OpenAI): {error_msg}]"

    except Exception as e:
        return f"[Connection error (OpenAI): {e}]"


def _send_rapidapi(user_message):
    """Envia mensagem via RapidAPI (fallback)."""
    if RAPIDAPI_KEY == "SUA_CHAVE_AQUI" or not RAPIDAPI_KEY:
        return "[Chatbot not configured: add your key in chatbot_config.py]"

    try:
        import requests
    except ImportError:
        return "[Error: the 'requests' library is not installed.]"

    history = _conversation_histories[_current_character]
    history.append({"role": "user", "content": user_message})

    payload = {
        "messages": history,
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }

    try:
        url = f"https://{RAPIDAPI_HOST}/v1/chat/completions"
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        parsed = response.json()

        if "choices" in parsed and len(parsed["choices"]) > 0:
            reply = parsed["choices"][0]["message"]["content"]
            history.append({"role": "assistant", "content": reply})
            return reply
        else:
            error_msg = parsed.get("message") or parsed.get("error") or str(parsed)
            return f"[API error (RapidAPI): {error_msg}]"

    except Exception as e:
        return f"[Connection error (RapidAPI): {e}]"
