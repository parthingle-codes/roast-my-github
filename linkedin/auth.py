# linkedin/auth.py
# Server-side LinkedIn OAuth 2.0 / OpenID Connect authorization handler.
# Handles state generation, redirect URI construction, and token exchange.
# Client secrets remain strictly on the backend.

import os
import secrets
import urllib.parse
import requests
from typing import Dict, Any, Tuple


def get_linkedin_credentials() -> Dict[str, str]:
    """Retrieves and sanitizes LinkedIn OAuth credentials from environment."""
    return {
        "client_id": os.getenv("LINKEDIN_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:5000/api/linkedin/callback").strip(),
    }


def is_linkedin_configured() -> bool:
    """Checks whether LinkedIn OAuth credentials are present and non-placeholder."""
    creds = get_linkedin_credentials()
    has_id = bool(creds["client_id"]) and "your_linkedin" not in creds["client_id"]
    has_secret = bool(creds["client_secret"]) and "your_linkedin" not in creds["client_secret"]
    return has_id and has_secret


def generate_authorization_url() -> Tuple[str, str]:
    """
    Constructs the official LinkedIn OAuth 2.0 / OpenID Connect authorization URL.
    Returns: (auth_url, state_token)
    Scope used: 'openid profile email' (Standard OpenID Connect)
    """
    creds = get_linkedin_credentials()
    if not is_linkedin_configured():
        raise ValueError("LinkedIn Client ID or Client Secret is not configured in .env")

    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": creds["client_id"],
        "redirect_uri": creds["redirect_uri"],
        "state": state,
        "scope": "openid profile email",
    }
    query_string = urllib.parse.urlencode(params)
    auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{query_string}"
    return auth_url, state


def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Exchanges the authorization code for an access token via LinkedIn's token endpoint.
    Performs server-to-server POST request; client secret is never sent to the browser.
    """
    creds = get_linkedin_credentials()
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri": creds["redirect_uri"],
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    resp = requests.post(token_url, data=payload, headers=headers, timeout=15)
    if resp.status_code != 200:
        error_msg = resp.json().get("error_description") or resp.text
        raise RuntimeError(f"LinkedIn token exchange failed ({resp.status_code}): {error_msg}")

    return resp.json()
