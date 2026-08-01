---
title: Omslawhouse Chat Console
emoji: 💬
colorFrom: yellow
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Omslawhouse Chat Console

A small Flask app that wraps the **Gemini API** (`gemini-3.5-flash` by default) behind a branded web chat UI. No local model is downloaded or loaded — every reply is a request to Google's Gemini API, so the app starts instantly and needs very little RAM.

## Required: set your API key

1. Get a key from Google AI Studio: https://aistudio.google.com/apikey
2. Set it as an environment variable named `GEMINI_API_KEY` wherever you deploy (see host-specific steps below). **Do not** commit it to git.

Without this key set, the app will start but `/api/chat` will return a 503 until it's configured.

## How it's structured

```
app.py                Flask server: calls the Gemini API and exposes
                       /api/status and /api/chat
templates/index.html  Page shell (branded, no mention of the underlying provider)
static/style.css      Console-style dark UI
static/script.js      Polls /api/status, sends chat turns, renders replies
requirements.txt      Python deps (flask, gunicorn, requests — no torch needed)
render.yaml            Render blueprint (build + start commands, env vars)
```

The frontend intentionally shows the brand name ("Omslawhouse") rather than "Gemini" anywhere — the model name and provider live only in backend env vars (`GEMINI_MODEL`), never in the UI or API responses sent to the browser.

## Run locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
python app.py
```

Open http://localhost:7860 — the app is ready immediately since there's no model to download.

## Deploy on Hugging Face Spaces

1. Go to https://huggingface.co/new-space
2. Pick a name, set **SDK** to **Docker**, set visibility, click **Create Space**
3. Push this project folder to the Space's git repo:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push hf main
   ```
4. In the Space's **Settings → Repository secrets**, add `GEMINI_API_KEY` with your key.
5. The Space builds the `Dockerfile` automatically and starts on port 7860.

## Deploy to Render

1. Push this folder to a GitHub repo.
2. In Render, choose **New → Blueprint** and point it at the repo — it reads `render.yaml` automatically. Or create a **Web Service** manually with:
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
3. In the Render dashboard, go to **Environment** and add `GEMINI_API_KEY` as a secret (it's marked `sync: false` in `render.yaml` so it's never stored in the repo).
4. Deploy. Since there's no local model, the free plan is enough.

### About the free tier — this now works fine on it

Unlike the old local-model version, this app makes lightweight API calls, so:

- **RAM**: a few hundred MB is plenty — no more OOM kills on free/starter tiers.
- **Cold start**: seconds, not minutes — there's nothing to download.
- **Generation speed**: depends on Gemini's API latency, typically 1–5 seconds for a normal reply, not the 20–60s of CPU-bound local inference.

## Customizing

- `GEMINI_API_KEY` — **required**, your Gemini API key.
- `GEMINI_MODEL` — defaults to `gemini-3.5-flash`. Check https://ai.google.dev/gemini-api/docs/deprecations before pinning a different model, as Google retires model IDs on a rolling schedule.
- `BRAND_NAME` — defaults to `Omslawhouse`; what's shown in the UI header and page title.
- `MAX_NEW_TOKENS`, `MAX_HISTORY_TURNS`, `SYSTEM_PROMPT` — same behavior as before: cap reply length, cap conversation history sent per request, and set the system prompt.
- Conversation history is kept in the browser tab (not persisted) and replayed with each request, capped at `MAX_HISTORY_TURNS` turns to bound prompt length.
