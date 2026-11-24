# ChatGPT Bot — Python Backend

A Python-powered chatbot using the original AsmrProg ChatGPT Bot frontend.

## How it works

```
Browser (index.js)  ──fetch──▶  adapter.js  ──►  Flask /api/chat  ──►  OpenAI API
                                   (intercepts RapidAPI calls and reroutes locally)
```

The original `index.js`, `style.css`, and `index.html` are **unchanged**.
A lightweight `adapter.js` sits after `index.js` and transparently redirects
API calls from the RapidAPI endpoint to the local Python backend.

## Setup

```bash
cd chatbot

# 1. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your OpenAI API key
cp .env.example .env
# Edit .env and paste your key

# 4. Run the server
python app.py
```

Then open **http://localhost:5000** in your browser.

## Project structure

```
chatbot/
├── app.py              # Flask backend
├── requirements.txt
├── .env.example
└── static/
    ├── index.html      # Original frontend (unchanged)
    ├── style.css       # Original styles  (unchanged)
    ├── index.js         # Original logic   (unchanged)
    └── adapter.js       # Fetch interceptor → routes to Flask
```

## Changing the model

By default the bot uses `gpt-3.5-turbo`. You can change the model in
`app.py` (the default parameter in the `/api/chat` route) or the adapter
can send a custom `model` field in the request body.
