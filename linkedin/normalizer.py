# linkedin/normalizer.py
# Canonical profile and career intent data models for LinkedIn.
# Enforces exact status tracking: 'available', 'user_provided', 'missing', 'not_authorized', 'not_supported'.

from typing import Dict, Any, List


def create_empty_profile() -> Dict[str, Any]:
    """Returns the canonical internal normalized LinkedIn profile model."""
    return {
        "identity": {
            "name": "",
            "photo": "",
            "email": "",
            "sub": "",
        },
        "headline": "",
        "about": "",
        "experience": [],
        "education": [],
        "skills": [],
        "projects": [],
        "certifications": [],
        "featured": [],
        "data_status": {
            "name": "missing",
            "photo": "missing",
            "email": "missing",
            "headline": "not_authorized",
            "about": "not_authorized",
            "experience": "not_authorized",
            "education": "not_authorized",
            "skills": "not_authorized",
            "projects": "not_authorized",
            "certifications": "not_authorized",
            "featured": "not_authorized",
        },
    }


def normalize_oidc_userinfo(userinfo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes official LinkedIn OpenID Connect /userinfo payload.
    The standard OIDC profile scope provides name, picture, and email/sub.
    Richer sections (headline, about, experience) are marked 'not_authorized'
    unless provided via profile import.
    """
    profile = create_empty_profile()
    if not userinfo:
        return profile

    name = userinfo.get("name") or f"{userinfo.get('given_name', '')} {userinfo.get('family_name', '')}".strip()
    photo = userinfo.get("picture", "")
    email = userinfo.get("email", "")
    sub = userinfo.get("sub", "")

    profile["identity"]["name"] = name
    profile["identity"]["photo"] = photo
    profile["identity"]["email"] = email
    profile["identity"]["sub"] = sub

    profile["data_status"]["name"] = "available" if name else "missing"
    profile["data_status"]["photo"] = "available" if photo else "missing"
    profile["data_status"]["email"] = "available" if email else "missing"

    return profile


def normalize_user_import(import_data: Dict[str, Any], base_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Merges user-provided profile data (Path B: manual import/entry) into canonical format.
    Explicitly tags fields as 'user_provided' so the application NEVER pretends manual
    data was scraped from LinkedIn.
    """
    profile = base_profile if base_profile else create_empty_profile()
    if not import_data:
        return profile

    # Identity overrides if provided
    if import_data.get("name") and not profile["identity"]["name"]:
        profile["identity"]["name"] = str(import_data["name"]).strip()
        profile["data_status"]["name"] = "user_provided"

    # Headline
    headline = str(import_data.get("headline", "")).strip()
    profile["headline"] = headline
    profile["data_status"]["headline"] = "user_provided" if headline else "missing"

    # About
    about = str(import_data.get("about", "")).strip()
    profile["about"] = about
    profile["data_status"]["about"] = "user_provided" if about else "missing"

    # Skills: accept list or comma-separated string
    raw_skills = import_data.get("skills", [])
    if isinstance(raw_skills, str):
        skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
    elif isinstance(raw_skills, list):
        skills = [str(s).strip() for s in raw_skills if str(s).strip()]
    else:
        skills = []
    profile["skills"] = skills
    profile["data_status"]["skills"] = "user_provided" if skills else "missing"

    # Projects
    raw_projects = import_data.get("projects", [])
    projects = []
    if isinstance(raw_projects, list):
        for p in raw_projects:
            if isinstance(p, dict):
                title = str(p.get("title") or p.get("name", "")).strip()
                desc = str(p.get("description", "")).strip()
                tech = p.get("technologies") or p.get("tech", [])
                if isinstance(tech, str):
                    tech = [t.strip() for t in tech.split(",") if t.strip()]
                if title or desc:
                    projects.append({
                        "title": title,
                        "description": desc,
                        "technologies": tech,
                        "outcomes": str(p.get("outcomes", "")).strip()
                    })
    profile["projects"] = projects
    profile["data_status"]["projects"] = "user_provided" if projects else "missing"

    # Experience
    raw_exp = import_data.get("experience", [])
    experience = []
    if isinstance(raw_exp, list):
        for e in raw_exp:
            if isinstance(e, dict):
                role = str(e.get("role") or e.get("title", "")).strip()
                company = str(e.get("company", "")).strip()
                desc = str(e.get("description", "")).strip()
                if role or company:
                    experience.append({"role": role, "company": company, "description": desc})
    profile["experience"] = experience
    profile["data_status"]["experience"] = "user_provided" if experience else "missing"

    # Education
    raw_edu = import_data.get("education", [])
    education = []
    if isinstance(raw_edu, list):
        for ed in raw_edu:
            if isinstance(ed, dict):
                school = str(ed.get("school") or ed.get("institution", "")).strip()
                degree = str(ed.get("degree", "")).strip()
                field = str(ed.get("field", "")).strip()
                if school or degree:
                    education.append({"school": school, "degree": degree, "field": field})
    profile["education"] = education
    profile["data_status"]["education"] = "user_provided" if education else "missing"

    # Certifications
    raw_certs = import_data.get("certifications", [])
    certs = []
    if isinstance(raw_certs, list):
        for c in raw_certs:
            if isinstance(c, dict):
                name = str(c.get("name", "")).strip()
                issuer = str(c.get("issuer", "")).strip()
                if name:
                    certs.append({"name": name, "issuer": issuer})
            elif isinstance(c, str) and c.strip():
                certs.append({"name": c.strip(), "issuer": ""})
    profile["certifications"] = certs
    profile["data_status"]["certifications"] = "user_provided" if certs else "missing"

    # Featured
    raw_featured = import_data.get("featured", [])
    featured = [str(f).strip() for f in raw_featured if str(f).strip()] if isinstance(raw_featured, list) else []
    profile["featured"] = featured
    profile["data_status"]["featured"] = "user_provided" if featured else "missing"

    return profile


def validate_career_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitizes and validates the user's career intent onboarding object.
    """
    if not isinstance(intent, dict):
        intent = {}

    stage = str(intent.get("stage", "Student")).strip()
    domain = str(intent.get("domain", "Software Development")).strip()
    target_role = str(intent.get("target_role", "Software Engineer")).strip()

    raw_goals = intent.get("goals", ["Internship"])
    if isinstance(raw_goals, list):
        goals = [str(g).strip() for g in raw_goals if str(g).strip()]
    elif isinstance(raw_goals, str):
        goals = [g.strip() for g in raw_goals.split(",") if g.strip()]
    else:
        goals = ["Internship"]

    try:
        timeline = int(intent.get("timeline_months", 6))
    except (ValueError, TypeError):
        timeline = 6

    return {
        "stage": stage,
        "domain": domain,
        "target_role": target_role,
        "goals": goals or ["Internship"],
        "timeline_months": timeline if timeline in (3, 6, 12) else 6,
    }
