import os
import time

import requests
from flask import Flask, request, jsonify, render_template

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "800"))
MAX_HISTORY_TURNS = int(os.environ.get("MAX_HISTORY_TURNS", "6"))
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a professional AI assistant. Give clear, accurate and complete answers.",
)
# Public-facing name shown in the UI (kept separate from the underlying
# model/provider so the frontend never mentions Gemini by name).
BRAND_NAME = os.environ.get("BRAND_NAME", "Omslawhouse")

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

app = Flask(__name__)

# No local model to load anymore -- the app is "ready" as soon as an API key
# is configured. Kept as a dict (rather than plain globals) so /api/status
# can report a helpful message if the key is missing.
state = {
    "status": "ready" if GEMINI_API_KEY else "error",
    "message": (
        "Ready."
        if GEMINI_API_KEY
        else "OMSLAWHOUSE_API_KEY is not set. Add it in your host's environment settings."
    ),
}


# ---------------------------------------------------------------------------
# Gemini API call
# ---------------------------------------------------------------------------
def build_contents(history, user_message):
    """Convert our {role: 'user'|'assistant', content} history into Gemini's
    {role: 'user'|'model', parts: [...]} format."""
    contents = []
    trimmed = history[-MAX_HISTORY_TURNS:] if history else []
    for turn in trimmed:
        role = turn.get("role")
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": text}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return contents


def generate_response(history, user_message):
    payload = {
        "contents": build_contents(history, user_message),
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    resp = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates") or []
    if not candidates:
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidates returned")
        raise RuntimeError(f"Model returned no response ({reason}).")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("Model returned an empty response.")
    return text


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", brand_name=BRAND_NAME)


@app.route("/api/status")
def status():
    return jsonify({"status": state["status"], "message": state["message"]})


@app.route("/api/chat", methods=["POST"])
def chat():
    if not GEMINI_API_KEY:
        return jsonify({
            "error": "not_ready",
            "message": "OMSLAWHOUSE_API_KEY is not set. Add it in your host's environment settings.",
        }), 503

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({"error": "empty_message"}), 400

    start = time.time()
    try:
        reply = generate_response(history, user_message)
    except requests.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            detail = exc.response.text if exc.response is not None else str(exc)
        return jsonify({"error": "generation_failed", "message": detail or str(exc)}), 502
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": "generation_failed", "message": str(exc)}), 500

    return jsonify({
        "reply": reply,
        "elapsed_seconds": round(time.time() - start, 2),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    app.run(host="0.0.0.0", port=port)
