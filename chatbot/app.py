"""
ChatGPT Bot - Python Backend
Supports: OpenAI, RapidAPI, or Groq (free) — whichever key is configured.
"""
import os
import json
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "chatgpt53.p.rapidapi.com")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")


def _call_openai(messages, model):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, None


def _call_groq(messages, model):
    from openai import OpenAI
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content, None


def _call_rapidapi(messages, model):
    import requests
    url = f"https://{RAPIDAPI_HOST}/v1/chat/completions"
    headers = {
        "content-type": "application/json",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    payload = {"messages": messages, "model": model}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    data = resp.json()
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"], None
    else:
        error = data.get("message") or data.get("error") or json.dumps(data)
        return None, f"RapidAPI error: {error}"


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])
    model = data.get("model", DEFAULT_MODEL)

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Try providers in order: OpenAI > Groq (free) > RapidAPI
    errors = []

    if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
        try:
            content, error = _call_openai(messages, model)
            if error:
                errors.append(error)
            else:
                return jsonify({"choices": [{"message": {"content": content}}]})
        except Exception as e:
            errors.append(f"OpenAI: {e}")

    if GROQ_API_KEY and GROQ_API_KEY.startswith("gsk_"):
        groq_model = data.get("groq_model", GROQ_MODEL)
        try:
            content, error = _call_groq(messages, groq_model)
            if error:
                errors.append(error)
            else:
                return jsonify({"choices": [{"message": {"content": content}}]})
        except Exception as e:
            errors.append(f"Groq: {e}")

    if RAPIDAPI_KEY:
        try:
            content, error = _call_rapidapi(messages, model)
            if error:
                errors.append(error)
            else:
                return jsonify({"choices": [{"message": {"content": content}}]})
        except Exception as e:
            errors.append(f"RapidAPI: {e}")

    return jsonify({
        "error": f"No API key configured or all providers failed. "
                 f"Errors: {'; '.join(errors) if errors else 'Set OPENAI_API_KEY, GROQ_API_KEY, or RAPIDAPI_KEY in .env'}"
    }), 500


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Chatbot running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
