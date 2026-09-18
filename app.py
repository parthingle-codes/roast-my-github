# app.py
# Flask backend for Roast My GitHub.
#
# Routes:
#   GET  /                          → serves index.html
#   GET  /api/github/<username>     → fetches + normalizes GitHub data
#   POST /api/analyze               → runs rule-based scoring engine
#   POST /api/roast                 → calls Gemini LLM with structured findings
#   POST /api/readme                → (WOW feature) generates a starter README
#
# Why Flask?
#   - Hides the Gemini API key from the browser
#   - Handles GitHub API requests server-side (avoids CORS issues)
#   - Simple enough to explain every line to a judge

import os
import json
import requests

from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

import analyzer
import prompts

load_dotenv(override=True)

app = Flask(__name__, static_folder="static", static_url_path="")

def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()

def get_github_token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()

def is_gemini_configured() -> bool:
    key = get_gemini_api_key()
    return bool(key) and "your_gemini_api_key" not in key

def is_github_token_configured() -> bool:
    token = get_github_token()
    return bool(token) and "your_github_personal" not in token

# If a GitHub token is provided, we get 5,000 requests/hour instead of 60.
# Without a token the app still works — rate limits just apply sooner.
def get_github_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "RoastMyGitHub-Hackathon",
    }
    if is_github_token_configured():
        headers["Authorization"] = f"Bearer {get_github_token()}"
    return headers

GITHUB_HEADERS = get_github_headers()

# Simple in-memory cache: { username: normalized_data }
# Prevents hammering the GitHub API during a demo
_github_cache: dict = {}


# ---------------------------------------------------------------------------
# SERVE FRONTEND
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ---------------------------------------------------------------------------
# DEMO PROFILE (Ensures 100% demoability regardless of rate limits/network)
# ---------------------------------------------------------------------------

@app.route("/api/demo")
def demo_profile():
    """
    Returns realistic sample developer data for testing and demonstrations.
    Guarantees the system is always demoable even if rate-limited or offline.
    """
    sample_data = {
        "is_demo": True,
        "profile": {
            "login": "alex-developer",
            "name": "Alex Chen",
            "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=faces",
            "bio": "Full-stack developer passionate about TypeScript, Python, and open-source tools.",
            "location": "San Francisco, CA",
            "blog": "https://alexchen.dev",
            "followers": 24,
            "following": 18,
            "public_repos": 7,
            "created_at": "2023-03-15T10:20:00Z",
            "html_url": "https://github.com",
        },
        "repos": [
            {
                "name": "dev-metrics-cli",
                "description": "A CLI tool to track daily coding metrics across git repositories",
                "language": "Python",
                "stargazers_count": 18,
                "forks_count": 3,
                "updated_at": "2026-09-02T14:30:00Z",
                "topics": ["cli", "developer-tools", "metrics"],
                "fork": False,
                "readme_checked": True,
                "has_readme": True,
            },
            {
                "name": "react-kanban-board",
                "description": "Minimalist drag-and-drop kanban board built with React and Tailwind",
                "language": "TypeScript",
                "stargazers_count": 7,
                "forks_count": 1,
                "updated_at": "2026-08-20T11:00:00Z",
                "topics": ["react", "kanban", "productivity"],
                "fork": False,
                "readme_checked": True,
                "has_readme": True,
            },
            {
                "name": "express-auth-starter",
                "description": "JWT authentication boilerplate with refresh tokens",
                "language": "JavaScript",
                "stargazers_count": 4,
                "forks_count": 0,
                "updated_at": "2026-07-15T09:45:00Z",
                "topics": ["express", "auth", "jwt"],
                "fork": False,
                "readme_checked": True,
                "has_readme": False,
            },
            {
                "name": "algo-practice",
                "description": "",
                "language": "Python",
                "stargazers_count": 0,
                "forks_count": 0,
                "updated_at": "2026-06-10T16:20:00Z",
                "topics": [],
                "fork": False,
                "readme_checked": True,
                "has_readme": False,
            },
            {
                "name": "personal-portfolio-v1",
                "description": "First iteration of my personal portfolio website",
                "language": "HTML",
                "stargazers_count": 2,
                "forks_count": 0,
                "updated_at": "2026-04-05T18:00:00Z",
                "topics": ["portfolio"],
                "fork": False,
                "readme_checked": True,
                "has_readme": True,
            },
            {
                "name": "dotfiles",
                "description": "My macOS and terminal configuration files",
                "language": "Shell",
                "stargazers_count": 1,
                "forks_count": 0,
                "updated_at": "2026-03-01T12:00:00Z",
                "topics": [],
                "fork": False,
                "readme_checked": True,
                "has_readme": False,
            },
            {
                "name": "scratchpad-temp",
                "description": "",
                "language": "JavaScript",
                "stargazers_count": 0,
                "forks_count": 0,
                "updated_at": "2026-01-15T08:00:00Z",
                "topics": [],
                "fork": False,
                "readme_checked": True,
                "has_readme": False,
            }
        ]
    }
    return jsonify({"ok": True, "data": sample_data})


# ---------------------------------------------------------------------------
# GITHUB DATA FETCH
# ---------------------------------------------------------------------------

@app.route("/api/github/<username>")
def fetch_github(username: str):
    """
    Fetches and normalizes public GitHub data for a given username.

    API calls made:
      1. GET /users/{username}           — profile data
      2. GET /users/{username}/repos     — up to 30 most-recently-updated repos
      3. GET /repos/{owner}/{repo}/readme — checked for up to 10 repos

    Returns a normalized JSON object (not the raw GitHub response).
    """
    username = username.strip().lower()

    # Serve from cache if available
    if username in _github_cache:
        return jsonify({"ok": True, "data": _github_cache[username]})

    base = "https://api.github.com"

    # --- 1. Profile ---
    try:
        profile_resp = requests.get(
            f"{base}/users/{username}",
            headers=GITHUB_HEADERS,
            timeout=10,
        )
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": "GitHub API is unreachable. Check your internet connection."}), 503

    if profile_resp.status_code == 404:
        return jsonify({"ok": False, "error": f"GitHub user '{username}' not found."}), 404
    if profile_resp.status_code == 403:
        return jsonify({
            "ok": False,
            "error": "GitHub unauthenticated rate limit reached (60/hr). Add GITHUB_TOKEN to .env for 5,000/hr, or click 'Try Sample Profile' below to demo immediately!"
        }), 429
    if not profile_resp.ok:
        return jsonify({"ok": False, "error": f"GitHub API error: {profile_resp.status_code}"}), 502

    raw_profile = profile_resp.json()

    # --- 2. Repositories ---
    try:
        repos_resp = requests.get(
            f"{base}/users/{username}/repos",
            headers=GITHUB_HEADERS,
            params={"per_page": 30, "sort": "updated", "type": "owner"},
            timeout=10,
        )
    except requests.RequestException:
        return jsonify({"ok": False, "error": "Could not fetch repositories from GitHub."}), 503

    if repos_resp.status_code == 403:
        return jsonify({
            "ok": False,
            "error": "GitHub repository rate limit reached. Add GITHUB_TOKEN to .env for 5,000/hr, or click 'Try Sample Profile' below to demo immediately!"
        }), 429
    if not repos_resp.ok:
        return jsonify({"ok": False, "error": f"Could not load repositories: {repos_resp.status_code}"}), 502

    raw_repos = repos_resp.json()
    if not isinstance(raw_repos, list):
        raw_repos = []

    # --- Normalize repositories ---
    repos = []
    for r in raw_repos:
        repos.append({
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "stargazers_count": r.get("stargazers_count", 0),
            "forks_count": r.get("forks_count", 0),
            "updated_at": r.get("updated_at", ""),
            "topics": r.get("topics", []),
            "fork": r.get("fork", False),
            "has_issues": r.get("has_issues", False),
            "readme_checked": False,
            "has_readme": False,
        })

    # --- 3. README checks (up to 10 repos) ---
    # We check only the 10 most-recently-updated repos to stay within API limits.
    # Forks are skipped since the README may belong to the original project.
    readme_candidates = [r for r in repos if not r["fork"]][:10]

    for repo in readme_candidates:
        try:
            readme_resp = requests.get(
                f"{base}/repos/{username}/{repo['name']}/readme",
                headers=GITHUB_HEADERS,
                timeout=6,
            )
            repo["readme_checked"] = True
            repo["has_readme"] = readme_resp.status_code == 200
        except requests.RequestException:
            # If the check times out, we skip rather than crash
            repo["readme_checked"] = False
            repo["has_readme"] = False

    # --- Normalize profile ---
    profile = {
        "login": raw_profile.get("login", username),
        "name": raw_profile.get("name") or "",
        "avatar_url": raw_profile.get("avatar_url", ""),
        "bio": raw_profile.get("bio") or "",
        "location": raw_profile.get("location") or "",
        "blog": raw_profile.get("blog") or "",
        "followers": raw_profile.get("followers", 0),
        "following": raw_profile.get("following", 0),
        "public_repos": raw_profile.get("public_repos", 0),
        "created_at": raw_profile.get("created_at", ""),
        "html_url": raw_profile.get("html_url", f"https://github.com/{username}"),
    }

    result = {"profile": profile, "repos": repos}
    _github_cache[username] = result
    return jsonify({"ok": True, "data": result})


# ---------------------------------------------------------------------------
# ANALYSIS ENGINE
# ---------------------------------------------------------------------------

@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Runs the rule-based scoring engine on normalized GitHub data.
    No AI is involved here — every score point is deterministic.
    """
    body = request.get_json(silent=True)
    if not body or "profile" not in body or "repos" not in body:
        return jsonify({"ok": False, "error": "Missing profile or repos in request body."}), 400

    try:
        result = analyzer.analyze(body["profile"], body["repos"])
        return jsonify({"ok": True, "analysis": result})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Analysis failed: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# AI ROAST GENERATION
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, json_mode: bool = False, max_tokens: int = 800) -> str:
    key = get_gemini_api_key()
    models = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash"]
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
    for model in models:
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
                last_err = f"HTTP {resp.status_code}"
                app.logger.warning(f"Gemini model {model} returned {resp.status_code}")
        except Exception as e:
            last_err = str(e)
            app.logger.warning(f"Gemini model {model} request error: {e}")

    raise RuntimeError(f"Gemini API request failed: {last_err}")


# ---------------------------------------------------------------------------
# AI ROAST GENERATION
# ---------------------------------------------------------------------------

@app.route("/api/roast", methods=["POST"])
def roast():
    """
    Calls the Gemini API with a structured prompt built from our analysis.

    The LLM receives ONLY pre-calculated findings — never raw GitHub JSON.
    This prevents hallucination of GitHub facts.

    If the AI fails or is not configured, we return a fallback summary
    so the core product remains completely demoable and usable.
    """
    body = request.get_json(silent=True) or {}
    analysis_data = body.get("analysis", {})
    profile_data = body.get("profile", {})

    weaknesses = analysis_data.get("weaknesses", [])
    strengths = analysis_data.get("strengths", [])

    fallback_response = {
        "ok": True,
        "fallback": True,
        "roast": (
            "Your profile has the energy of an abandoned side quest: great ideas started, "
            "but half the repositories have no README and your bio is quieter than a midnight git commit. "
            "Time to clean house and show recruiters what you can actually build."
        ),
        "top_problems": weaknesses[:3] if weaknesses else [
            "Several repositories are missing README documentation",
            "Repository descriptions are either blank or too brief",
            "Project activity is spread unevenly across repositories"
        ],
        "recommendations": [
            "Add a clear README to your top 3 pinned repositories explaining the problem, features, and setup.",
            "Write a 2-sentence bio stating your primary stack and what kinds of projects you build.",
            "Tag repositories with descriptive GitHub topics so search and recruiters can find them."
        ],
        "encouragement": "The foundation is clearly here. A couple of solid READMEs will immediately elevate your entire profile."
    }

    if not is_gemini_configured():
        return jsonify(fallback_response), 200

    if not analysis_data or not profile_data:
        return jsonify({"ok": False, "error": "Missing analysis or profile in request body."}), 400

    prompt = prompts.build_roast_prompt(analysis_data, profile_data)

    try:
        raw_text = call_gemini(prompt, json_mode=True, max_tokens=800)
        # Strip potential markdown code fences if model enclosed them
        clean_text = raw_text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`")
            if clean_text.startswith("json"):
                clean_text = clean_text[4:].strip()

        ai_result = json.loads(clean_text)

        for field in ("roast", "top_problems", "recommendations", "encouragement"):
            if field not in ai_result:
                raise ValueError(f"Missing field in AI response: {field}")

        return jsonify({"ok": True, "fallback": False, **ai_result})

    except Exception as e:
        app.logger.warning(f"Roast generation using fallback due to: {e}")
        return jsonify(fallback_response), 200


# ---------------------------------------------------------------------------
# WOW FEATURE — README GENERATION (optional)
# ---------------------------------------------------------------------------

@app.route("/api/readme", methods=["POST"])
def generate_readme():
    """
    Generates a starter README for a weak repository.
    Works with Gemini when configured, or provides a structured Markdown template fallback.
    """
    body = request.get_json(silent=True) or {}
    repo = body.get("repo")
    if not repo:
        return jsonify({"ok": False, "error": "Missing repo in request body."}), 400

    repo_name = repo.get("name", "my-project")
    desc = repo.get("description") or "A project built with passion and code."
    lang = repo.get("language") or "General"
    topics = ", ".join(repo.get("topics", [])) or "None specified"

    fallback_template = f"""# {repo_name}

> {desc}

## 📖 About
A {lang} project that solves problems and delivers clean functionality.

## ✨ Features
- [Add primary feature description]
- [Add secondary capability]
- [Add configuration options]

## 🛠️ Tech Stack
- **Primary Language:** {lang}
- **Topics:** {topics}

## 🚀 Getting Started

### Prerequisites
Make sure you have the runtime environment installed for {lang}.

### Installation
```bash
git clone https://github.com/your-username/{repo_name}.git
cd {repo_name}
```

### Usage
```bash
# Add commands to run your application
```

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
"""

    if not is_gemini_configured():
        return jsonify({"ok": True, "readme": fallback_template, "fallback": True})

    prompt = prompts.build_readme_prompt(repo)

    try:
        readme_text = call_gemini(prompt, json_mode=False, max_tokens=1200)
        if not readme_text:
            return jsonify({"ok": True, "readme": fallback_template, "fallback": True})
        return jsonify({"ok": True, "readme": readme_text, "fallback": False})

    except Exception as e:
        app.logger.warning(f"Readme generation using fallback due to: {e}")
        return jsonify({"ok": True, "readme": fallback_template, "fallback": True})


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "gemini_key_set": is_gemini_configured(),
        "github_token_set": is_github_token_configured(),
    })


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
