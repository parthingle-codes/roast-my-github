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

from flask import Flask, jsonify, request, send_from_directory, session, redirect
from dotenv import load_dotenv

import analyzer
import prompts

# Platform services & LinkedIn package
from services.gemini import (
    call_gemini,
    is_gemini_configured,
    get_gemini_api_key,
    parse_gemini_json,
)
import linkedin.auth
import linkedin.connector
import linkedin.normalizer
import linkedin.analyzer
import prompts_linkedin

load_dotenv(override=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-roast-my-profile-12345")

def get_github_token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()

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
# GITHUB AI ROAST GENERATION
# ---------------------------------------------------------------------------
# AI ROAST GENERATION
# ---------------------------------------------------------------------------

@app.route("/api/roast", methods=["POST"])
def roast():
    """
    Calls the Gemini API with a structured prompt built from our analysis.

    The LLM receives ONLY pre-calculated findings — never raw GitHub JSON.
    This prevents hallucination of GitHub facts.

    New output structure:
    - roast_headline: short funny one-liner
    - roast: 2-4 sentences with a real fact + funny comparison
    - what_it_means: one plain-English sentence explaining the actual problem
    - fix: one clear action to take right now
    - top_problems, recommendations, encouragement: same as before
    """
    body = request.get_json(silent=True) or {}
    analysis_data = body.get("analysis", {})
    profile_data = body.get("profile", {})

    weaknesses = analysis_data.get("weaknesses", [])
    strengths = analysis_data.get("strengths", [])

    fallback_response = {
        "ok": True,
        "fallback": True,
        "roast_headline": "Your README took the day off. 😴",
        "roast": (
            "Half your projects have no README. "
            "They're basically asking visitors to guess what they do — "
            "like a restaurant with no menu. 😂"
        ),
        "what_it_means": "People visiting your profile can't quickly understand what your projects are about.",
        "fix": "Add a short README to your 3 best projects explaining what they do and how to run them.",
        "top_problems": weaknesses[:3] if weaknesses else [
            "Several repositories are missing a README file",
            "Repository descriptions are blank or too short",
            "Profile bio doesn't tell visitors what you do"
        ],
        "recommendations": [
            "Add a simple README to your top 3 repos — just explain what it does and how to use it.",
            "Write a 2-sentence bio saying what you build and what tech you use.",
            "Add topic tags to your repos so people can actually find them."
        ],
        "encouragement": "Honestly, you're not far off. A couple small changes and this profile looks way better."
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

        # Validate required fields from new prompt format
        required = ("roast", "top_problems", "recommendations", "encouragement")
        for field in required:
            if field not in ai_result:
                raise ValueError(f"Missing field in AI response: {field}")

        # Ensure new fields have sensible defaults if model omitted them
        if "roast_headline" not in ai_result:
            ai_result["roast_headline"] = ""
        if "what_it_means" not in ai_result:
            ai_result["what_it_means"] = ""
        if "fix" not in ai_result:
            ai_result["fix"] = ""

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
# LINKEDIN PLATFORM LAYER ROUTES
# ---------------------------------------------------------------------------

@app.route("/api/linkedin/auth-url")
def linkedin_auth_url():
    """
    Returns official LinkedIn OAuth 2.0 / OpenID Connect authorization URL.
    Stores CSRF state in server session.
    """
    if not linkedin.auth.is_linkedin_configured():
        return jsonify({
            "ok": False,
            "configured": False,
            "error": "LinkedIn OAuth credentials not set in .env. Please use Profile Import or Demo Mode."
        }), 200

    try:
        url, state = linkedin.auth.generate_authorization_url()
        session["linkedin_oauth_state"] = state
        return jsonify({"ok": True, "configured": True, "auth_url": url})
    except Exception as e:
        return jsonify({"ok": False, "configured": False, "error": str(e)}), 500


@app.route("/api/linkedin/callback")
def linkedin_callback():
    """
    Handles LinkedIn OAuth redirect callback.
    Validates CSRF state and exchanges code for access token server-side.
    """
    code = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")
    error_desc = request.args.get("error_description", "")

    if error:
        return redirect(f"/?linkedin_error={error}&msg={error_desc}")

    saved_state = session.get("linkedin_oauth_state")
    if not state or state != saved_state:
        return redirect("/?linkedin_error=state_mismatch&msg=Security+state+validation+failed.")

    try:
        token_data = linkedin.auth.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        profile = linkedin.connector.fetch_member_profile(access_token)
        session["linkedin_profile"] = profile
        return redirect("/?linkedin_auth=success")
    except Exception as e:
        return redirect(f"/?linkedin_error=exchange_failed&msg={str(e)}")


@app.route("/api/linkedin/demo")
def linkedin_demo():
    """
    Provides sample demo profile data (Jordan Patel, 2nd-year student aiming for ML Intern).
    Enables instant demonstration and testing under any network conditions.
    """
    profile = linkedin.connector.get_demo_linkedin_profile()
    intent = {
        "stage": "2nd year student",
        "domain": "AI / Machine Learning",
        "target_role": "ML Engineer Intern",
        "goals": ["Internship"],
        "timeline_months": 6
    }
    return jsonify({
        "ok": True,
        "data": {
            "profile": profile,
            "intent": intent,
            "is_demo": True
        }
    })


@app.route("/api/linkedin/import", methods=["POST"])
def linkedin_import():
    """
    Path B: Manual Profile Data Import fallback.
    Normalizes user-provided profile data and career intent.
    Never pretends manual data came from LinkedIn's API.
    """
    body = request.get_json(silent=True) or {}
    import_data = body.get("profile", {})
    intent_data = body.get("intent", {})

    profile = linkedin.normalizer.normalize_user_import(import_data)
    intent = linkedin.normalizer.validate_career_intent(intent_data)
    return jsonify({"ok": True, "data": {"profile": profile, "intent": intent}})


@app.route("/api/linkedin/analyze", methods=["POST"])
def linkedin_analyze():
    """
    Deterministic Goal-Aware LinkedIn Analysis Engine.
    Evaluates 5 pillars (Total 100) and computes gap analysis against career intent.
    """
    body = request.get_json(silent=True) or {}
    profile = body.get("profile", {})
    intent = body.get("intent", {})

    if not profile:
        return jsonify({"ok": False, "error": "Missing profile data in request body."}), 400

    intent = linkedin.normalizer.validate_career_intent(intent)
    try:
        analysis_result = linkedin.analyzer.analyze(profile, intent)
        return jsonify({"ok": True, "analysis": analysis_result})
    except Exception as e:
        return jsonify({"ok": False, "error": f"LinkedIn analysis failed: {str(e)}"}), 500


@app.route("/api/linkedin/roast", methods=["POST"])
def linkedin_roast():
    """
    Calls Gemini with structured findings and career intent to produce a goal-aware roast,
    what it means, and actionable next steps.
    """
    body = request.get_json(silent=True) or {}
    analysis_data = body.get("analysis", {})
    profile_data = body.get("profile", {})
    intent_data = body.get("intent", {})

    target_role = intent_data.get("target_role", "your target role")
    timeline = intent_data.get("timeline_months", 6)
    gaps = analysis_data.get("gap_analysis", {}).get("top_3_gaps", [])

    fallback_response = {
        "ok": True,
        "fallback": True,
        "roast_headline": f"Aiming for {target_role}, but your profile took a detour. 🗺️",
        "roast": (
            f"You want to land a {target_role} in {timeline} months, but your headline and projects read "
            f"like a general study guide. Recruiters glance at your profile for 6 seconds — right now they're "
            f"guessing what you actually want to do. 😂"
        ),
        "what_it_means": f"Recruiters looking for a {target_role} won't see immediate proof in your headline or projects.",
        "fix": f"Rewrite your headline to explicitly state '{target_role}' and highlight your top 2 relevant skills.",
        "top_problems": gaps[:3] if gaps else [
            f"Headline does not clearly position you for {target_role}",
            "Projects lack direct domain evidence",
            "About section is generic"
        ],
        "recommendations": [
            f"Update your headline to: '{target_role} | Core Stack & Key Specialization'",
            "Rewrite your best project with problem-action-result bullet points",
            "Add 3-5 core technical skills matching your chosen domain"
        ],
        "next_3_actions": [
            "Headline: State your target role directly instead of passive terms like 'aspiring'",
            "Projects: Add 1 flagship project demonstrating your domain tools",
            "About: Tell recruiters your specific technical focus in 2 short paragraphs"
        ],
        "encouragement": f"You have plenty of time. A focused headline and one good project rewrite will immediately shift your profile into gear."
    }

    if not is_gemini_configured():
        return jsonify(fallback_response), 200

    prompt = prompts_linkedin.build_linkedin_roast_prompt(analysis_data, profile_data, intent_data)
    try:
        raw_text = call_gemini(prompt, json_mode=True, max_tokens=900)
        ai_result = parse_gemini_json(raw_text)

        for field in ("roast_headline", "roast", "what_it_means", "fix", "recommendations", "encouragement"):
            if field not in ai_result:
                ai_result[field] = fallback_response[field]
        if "next_3_actions" not in ai_result:
            ai_result["next_3_actions"] = fallback_response["next_3_actions"]

        return jsonify({"ok": True, "fallback": False, **ai_result})
    except Exception as e:
        app.logger.warning(f"LinkedIn roast using fallback: {e}")
        return jsonify(fallback_response), 200


@app.route("/api/linkedin/rewrite", methods=["POST"])
def linkedin_rewrite():
    """
    Profile Rewriting Engine: generates recruiter-optimized revisions for headline,
    about, or project descriptions.
    """
    body = request.get_json(silent=True) or {}
    field_type = body.get("field_type", "headline")
    current_text = body.get("current_text", "")
    intent = body.get("intent", {})
    analysis = body.get("analysis", {})

    target_role = intent.get("target_role", "Developer")
    domain = intent.get("domain", "Software")

    fallback_rewrites = {
        "headline": {
            "current": current_text or "Student / Developer",
            "improved": f"{target_role} | {domain} Specialist | Building High-Impact Solutions",
            "why_this_is_better": "Replaces passive student phrasing with an active professional title that recruiter search algorithms index immediately."
        },
        "about": {
            "current": current_text or "Passionate student looking for opportunities.",
            "improved": (
                f"I am a {domain} enthusiast preparing for a {target_role} role. "
                f"My focus is on designing scalable tools, solving real-world challenges, and mastering modern frameworks.\n\n"
                f"Currently building hands-on projects and actively seeking internship opportunities where I can deliver measurable value."
            ),
            "why_this_is_better": "Directly links your current studies to your target role, highlighting initiative, specific domain focus, and clear readiness."
        },
        "project": {
            "current": current_text or "Built a project using coding tools.",
            "improved": f"Designed and deployed a {domain} tool solving key workflow bottlenecks. Integrated modern APIs and improved performance by 30%.",
            "why_this_is_better": "Uses an active Problem-Action-Result format with quantifiable evidence rather than passive descriptions."
        }
    }

    default_val = fallback_rewrites.get(field_type, fallback_rewrites["headline"])
    if not is_gemini_configured():
        return jsonify({"ok": True, "fallback": True, **default_val})

    prompt = prompts_linkedin.build_rewrite_prompt(field_type, current_text, intent, analysis)
    try:
        raw_text = call_gemini(prompt, json_mode=True, max_tokens=600)
        ai_result = parse_gemini_json(raw_text)
        return jsonify({"ok": True, "fallback": False, **ai_result})
    except Exception as e:
        app.logger.warning(f"LinkedIn rewrite fallback: {e}")
        return jsonify({"ok": True, "fallback": True, **default_val})


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "gemini_key_set": is_gemini_configured(),
        "github_token_set": is_github_token_configured(),
        "linkedin_configured": linkedin.auth.is_linkedin_configured(),
    })


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
