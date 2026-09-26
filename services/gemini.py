# services/gemini.py
# Reusable Gemini AI Service for Roast My GitHub & LinkedIn.
# Provides resilient fallback across available Gemini models, enforce JSON mode,
# and safely strip markdown code fences without crashing.

import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

# Model priority list for resilience
MODELS = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash"]


def get_gemini_api_key() -> str:
    """Retrieve and sanitize GEMINI_API_KEY from environment."""
    return os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")


def is_gemini_configured() -> bool:
    """Checks whether a non-placeholder Gemini API key is configured."""
    key = get_gemini_api_key()
    return bool(key) and "your_gemini_api_key" not in key


def call_gemini(prompt: str, json_mode: bool = False, max_tokens: int = 800) -> str:
    """
    Sends a generation request to the Gemini REST API.
    Iterates through MODELS to handle quotas or temporary model-availability spikes.
    """
    key = get_gemini_api_key()
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85 if json_mode else 0.7,
            "maxOutputTokens": max_tokens,
        },
    }
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    last_err = None
    for model in MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        try:
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(f"Gemini model {model} returned {resp.status_code}")
        except Exception as e:
            last_err = str(e)
            logger.warning(f"Gemini model {model} request error: {e}")

    raise RuntimeError(f"Gemini API request failed across all models: {last_err}")


def parse_gemini_json(raw_text: str) -> dict:
    """
    Safely parses JSON returned by Gemini, stripping any leading/trailing markdown code fences.
    """
    clean_text = raw_text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`")
        if clean_text.startswith("json"):
            clean_text = clean_text[4:].strip()
    return json.loads(clean_text)
