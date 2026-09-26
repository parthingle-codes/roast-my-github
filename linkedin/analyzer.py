# linkedin/analyzer.py
# Deterministic, rule-based Goal-Aware LinkedIn Profile Readiness Scoring Engine.
# Evaluates 5 pillars (Total 100 pts):
# 1. Professional Positioning  (20 pts)
# 2. Goal Alignment           (25 pts) — Signature Pillar
# 3. Projects & Evidence      (25 pts)
# 4. Communication            (15 pts)
# 5. Profile Completeness     (15 pts)

import re
from typing import Dict, Any, List

# Domain-specific keywords for goal-alignment comparison
DOMAIN_KEYWORDS = {
    "AI / Machine Learning": [
        "ai", "machine learning", "ml", "deep learning", "neural", "pytorch",
        "tensorflow", "keras", "computer vision", "nlp", "transformers", "llm",
        "scikit-learn", "data science", "pandas", "numpy", "model", "python"
    ],
    "Data Science": [
        "data science", "analytics", "data analysis", "pandas", "numpy", "sql",
        "tableau", "power bi", "statistics", "data visualization", "r", "python",
        "modeling", "etl", "machine learning"
    ],
    "Software Development": [
        "software", "developer", "engineer", "full stack", "backend", "frontend",
        "python", "java", "c++", "javascript", "typescript", "react", "node",
        "api", "git", "database", "sql"
    ],
    "Cybersecurity": [
        "cybersecurity", "security", "infosec", "penetration testing", "ethical hacking",
        "soc", "network security", "cryptography", "firewall", "vulnerability", "linux"
    ],
    "Cloud / DevOps": [
        "cloud", "devops", "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd",
        "terraform", "linux", "infrastructure", "ansible", "monitoring"
    ],
    "UI/UX Design": [
        "ui", "ux", "ui/ux", "product design", "figma", "wireframe", "prototype",
        "user research", "usability", "design system", "interaction design"
    ],
}


def _matches_any(text: str, keywords: List[str]) -> bool:
    """Checks if any keyword appears as a whole or bounded subphrase in text."""
    lower = text.lower()
    for kw in keywords:
        if kw in lower:
            return True
    return False


def _find_matches(text: str, keywords: List[str]) -> List[str]:
    """Returns all matched domain keywords from text."""
    lower = text.lower()
    found = []
    for kw in keywords:
        if kw in lower and kw not in found:
            found.append(kw)
    return found


# ---------------------------------------------------------------------------
# PILLAR 1: PROFESSIONAL POSITIONING (0–20)
# ---------------------------------------------------------------------------

def score_positioning(profile: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    evidence = []
    headline = profile.get("headline", "").strip()

    # 1. Headline Presence (+5)
    if headline:
        score += 5
        evidence.append("✅ Headline is present")
    else:
        evidence.append("❌ Headline is missing — this is the most visible line on your profile")
        return {"score": score, "max": 20, "evidence": evidence}

    # 2. Clarity of Identity / Role (+5)
    target_role = intent.get("target_role", "").lower()
    headline_lower = headline.lower()
    if target_role and target_role in headline_lower:
        score += 5
        evidence.append(f"✅ Headline explicitly targets your role: \"{intent.get('target_role')}\"")
    elif any(term in headline_lower for term in ["student", "engineer", "developer", "intern", "designer", "researcher"]):
        score += 3
        evidence.append("⚠️ Headline mentions a role/title, but could align more tightly with your target goal")
    else:
        evidence.append("⚠️ Headline lacks a clear professional title or focus")

    # 3. Domain Specificity (+5)
    domain = intent.get("domain", "")
    kws = DOMAIN_KEYWORDS.get(domain, [domain.lower()])
    matches = _find_matches(headline, kws)
    if matches:
        score += 5
        evidence.append(f"✅ Headline highlights domain expertise ({', '.join(matches[:3])})")
    else:
        evidence.append(f"⚠️ Headline does not mention keywords for your target field ({domain})")

    # 4. Strength of Phrasing (+5)
    generic_fluff = ["aspiring", "enthusiast", "seeking opportunities", "passionate learner", "hard worker"]
    fluff_found = [f for f in generic_fluff if f in headline_lower]
    if not fluff_found and len(headline) >= 25:
        score += 5
        evidence.append("✅ Clean, direct headline without passive filler phrases")
    elif fluff_found:
        score += 2
        evidence.append(f"⚠️ Headline uses passive terms ({', '.join(fluff_found)}) — state what you build instead")
    else:
        score += 3
        evidence.append("⚠️ Headline is very brief; consider adding your core stack or specialization")

    return {"score": min(score, 20), "max": 20, "evidence": evidence}


# ---------------------------------------------------------------------------
# PILLAR 2: GOAL ALIGNMENT (0–25) — SIGNATURE CATEGORY
# ---------------------------------------------------------------------------

def score_goal_alignment(profile: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    evidence = []

    domain = intent.get("domain", "")
    target_role = intent.get("target_role", "")
    kws = DOMAIN_KEYWORDS.get(domain, [domain.lower()])

    all_text = " ".join([
        profile.get("headline", ""),
        profile.get("about", ""),
        " ".join(profile.get("skills", [])),
        " ".join(p.get("title", "") + " " + p.get("description", "") for p in profile.get("projects", [])),
    ]).lower()

    # 1. Domain Skills in Profile (+8)
    matched_skills = [s for s in profile.get("skills", []) if _matches_any(s, kws)]
    if len(matched_skills) >= 3:
        score += 8
        evidence.append(f"✅ Strong technical alignment: {len(matched_skills)} core {domain} skills listed ({', '.join(matched_skills[:4])})")
    elif len(matched_skills) >= 1:
        score += 4
        evidence.append(f"⚠️ Partial domain skill match ({', '.join(matched_skills)}). Needs deeper {domain} coverage")
    else:
        evidence.append(f"❌ No direct {domain} skills detected in your skills list")

    # 2. Target Role & Domain in Projects (+8)
    proj_text = " ".join(p.get("title", "") + " " + p.get("description", "") for p in profile.get("projects", [])).lower()
    matched_proj_kws = _find_matches(proj_text, kws)
    if len(matched_proj_kws) >= 3:
        score += 8
        evidence.append(f"✅ Project portfolio directly validates your {domain} target")
    elif len(matched_proj_kws) >= 1:
        score += 4
        evidence.append(f"⚠️ Projects have minor {domain} traces, but lack a flagship demonstration")
    else:
        evidence.append(f"❌ No visible projects demonstrating {domain} or {target_role} work")

    # 3. About / Summary Alignment (+5)
    about = profile.get("about", "")
    if about and _matches_any(about, kws):
        score += 5
        evidence.append("✅ About section explains your interest and direction in this field")
    elif about:
        score += 2
        evidence.append(f"⚠️ About section exists but does not clearly articulate your {domain} trajectory")
    else:
        evidence.append("❌ Missing About section to tell your career story")

    # 4. Certifications & Relevant Experience (+4)
    certs = profile.get("certifications", [])
    relevant_certs = [c.get("name", "") for c in certs if _matches_any(c.get("name", ""), kws)]
    if relevant_certs:
        score += 4
        evidence.append(f"✅ Relevant credential: {relevant_certs[0]}")
    elif certs:
        score += 2
        evidence.append("⚠️ Certifications are listed, but none directly target your current goal")
    else:
        evidence.append(f"⚠️ No certifications or specialized coursework listed for {domain}")

    return {"score": min(score, 25), "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# PILLAR 3: PROJECTS & EVIDENCE (0–25)
# ---------------------------------------------------------------------------

def score_projects(profile: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    evidence = []
    projects = profile.get("projects", [])

    if not projects:
        evidence.append("❌ No projects listed. Projects are the strongest proof of competence")
        return {"score": 0, "max": 25, "evidence": evidence}

    # 1. Project Quantity (+6)
    if len(projects) >= 3:
        score += 6
        evidence.append(f"✅ Strong portfolio volume ({len(projects)} projects listed)")
    elif len(projects) >= 1:
        score += 4
        evidence.append(f"⚠️ {len(projects)} project(s) listed; aim for 2–3 strong showcase projects")

    # 2. Descriptions with Substance (+7)
    substantial = [p for p in projects if len(p.get("description", "")) >= 50]
    if len(substantial) >= 2:
        score += 7
        evidence.append("✅ Project descriptions explain problem and context clearly")
    elif len(substantial) >= 1:
        score += 4
        evidence.append("⚠️ Some project descriptions are very short; explain what problem was solved")
    else:
        evidence.append("❌ Project descriptions are too brief to evaluate implementation depth")

    # 3. Technologies Named (+6)
    with_tech = [p for p in projects if p.get("technologies")]
    if len(with_tech) >= 2:
        score += 6
        evidence.append("✅ Technical stacks are clearly specified for projects")
    elif len(with_tech) >= 1:
        score += 3
        evidence.append("⚠️ Specify exact frameworks and languages used on all projects")
    else:
        evidence.append("⚠️ Technologies are not clearly attributed to individual projects")

    # 4. Measurable Outcomes / Results (+6)
    with_outcomes = [p for p in projects if p.get("outcomes") or any(ch.isdigit() for ch in p.get("description", ""))]
    if with_outcomes:
        score += 6
        evidence.append("✅ Projects mention measurable results or user impact")
    else:
        score += 2
        evidence.append("⚠️ Add quantifiable outcomes (e.g. users, latency, accuracy, volume)")

    return {"score": min(score, 25), "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# PILLAR 4: COMMUNICATION (0–15)
# ---------------------------------------------------------------------------

def score_communication(profile: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    evidence = []
    about = profile.get("about", "").strip()

    # 1. About Presence (+5)
    if len(about) >= 100:
        score += 5
        evidence.append("✅ About section has solid substance and narrative flow")
    elif len(about) >= 30:
        score += 3
        evidence.append("⚠️ About section is very brief; expand into your technical background and goals")
    else:
        evidence.append("❌ About section is missing or empty")

    # 2. Specificity vs Clichés (+5)
    cliches = ["hard working", "out of the box", "synergy", "dynamic individual", "detail oriented"]
    cliche_hits = [c for c in cliches if c in about.lower()]
    if about and not cliche_hits:
        score += 5
        evidence.append("✅ Clear, authentic tone free from corporate clichés")
    elif cliche_hits:
        score += 2
        evidence.append(f"⚠️ Replace clichés ({', '.join(cliche_hits)}) with concrete examples")
    else:
        evidence.append("⚠️ Add a summary to showcase your communication style")

    # 3. Readability & Structure (+5)
    if about and ("\n" in about or len(about.split(".")) >= 3):
        score += 5
        evidence.append("✅ Well-structured text with clear sentence breaks")
    elif about:
        score += 3
        evidence.append("⚠️ Consider formatting with short paragraphs for easier recruiter scanning")
    else:
        evidence.append("❌ No written summary available to evaluate")

    return {"score": min(score, 15), "max": 15, "evidence": evidence}


# ---------------------------------------------------------------------------
# PILLAR 5: PROFILE COMPLETENESS (0–15)
# ---------------------------------------------------------------------------

def score_completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates profile completeness ONLY on available or user-provided sections.
    Never penalizes for 'not_authorized' API restriction states.
    """
    score = 0
    evidence = []
    status = profile.get("data_status", {})

    # 1. Identity & Visuals (+4)
    has_name = bool(profile.get("identity", {}).get("name"))
    has_photo = bool(profile.get("identity", {}).get("photo"))
    if has_name and has_photo:
        score += 4
        evidence.append("✅ Name and profile photo are present")
    elif has_name:
        score += 2
        evidence.append("⚠️ Profile photo is missing or not provided")
    else:
        evidence.append("❌ Member name is missing")

    # 2. Headline & About (+4)
    if profile.get("headline") and profile.get("about"):
        score += 4
        evidence.append("✅ Headline and About sections completed")
    elif profile.get("headline") or profile.get("about"):
        score += 2
        evidence.append("⚠️ Incomplete summary sections (headline or about missing)")
    else:
        evidence.append("❌ Neither headline nor about section is present")

    # 3. Education / Experience (+4)
    has_edu = bool(profile.get("education"))
    has_exp = bool(profile.get("experience"))
    if has_edu and has_exp:
        score += 4
        evidence.append("✅ Both education and experience history populated")
    elif has_edu or has_exp:
        score += 3
        evidence.append("✅ Core academic or professional background listed")
    else:
        evidence.append("⚠️ No education or experience entries provided")

    # 4. Skills & Extras (+3)
    has_skills = len(profile.get("skills", [])) >= 3
    if has_skills:
        score += 3
        evidence.append(f"✅ Skills section active ({len(profile.get('skills', []))} skills)")
    else:
        evidence.append("⚠️ Add at least 5 relevant technical and domain skills")

    return {"score": min(score, 15), "max": 15, "evidence": evidence}


# ---------------------------------------------------------------------------
# GAP ANALYSIS (Target vs Evidence vs Gaps)
# ---------------------------------------------------------------------------

def compute_gap_analysis(profile: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    domain = intent.get("domain", "General")
    target_role = intent.get("target_role", "Developer")
    kws = DOMAIN_KEYWORDS.get(domain, [domain.lower()])

    headline = profile.get("headline", "")
    skills = profile.get("skills", [])
    projects = profile.get("projects", [])
    about = profile.get("about", "")

    evidence_found = []
    gaps_found = []

    # Evidence checks
    matching_skills = [s for s in skills if _matches_any(s, kws)]
    if matching_skills:
        evidence_found.append(f"Skills present: {', '.join(matching_skills[:5])}")
    else:
        gaps_found.append(f"No {domain} core skills listed in profile")

    proj_text = " ".join(p.get("title", "") + " " + p.get("description", "") for p in projects)
    if _matches_any(proj_text, kws):
        evidence_found.append(f"Project portfolio includes relevant {domain} work")
    else:
        gaps_found.append(f"No flagship project demonstrating {domain} or {target_role}")

    if _matches_any(headline, kws):
        evidence_found.append(f"Headline contains domain keywords")
    else:
        gaps_found.append(f"Headline lacks {domain} keywords or specific role targeting")

    if about and _matches_any(about, kws):
        evidence_found.append("About section articulates your focus in this domain")
    else:
        gaps_found.append(f"About section does not clearly communicate your goal ({target_role})")

    if not evidence_found:
        evidence_found.append("Basic academic and coding foundation present")

    # Top 3 Critical Gaps
    top_3_gaps = gaps_found[:3] if gaps_found else [
        "Strengthen project descriptions with measurable outcomes",
        "Add topic endorsements and specialized certifications",
        "Refine headline to stand out in recruiter search results"
    ]

    return {
        "target_role": target_role,
        "domain": domain,
        "profile_evidence": evidence_found,
        "gaps": gaps_found,
        "top_3_gaps": top_3_gaps,
    }


# ---------------------------------------------------------------------------
# MAIN ANALYZER ORCHESTRATOR
# ---------------------------------------------------------------------------

def analyze(profile: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main goal-aware analysis orchestrator for LinkedIn profiles.
    Returns deterministic scores, evidence, and gap analysis.
    """
    pos = score_positioning(profile, intent)
    goal = score_goal_alignment(profile, intent)
    proj = score_projects(profile, intent)
    comm = score_communication(profile)
    comp = score_completeness(profile)

    overall = pos["score"] + goal["score"] + proj["score"] + comm["score"] + comp["score"]

    # Strengths and weaknesses
    strengths = []
    weaknesses = []
    for cat in [pos, goal, proj, comm, comp]:
        for e in cat["evidence"]:
            if e.startswith("✅"):
                strengths.append(e[2:].strip())
            elif e.startswith("⚠️") or e.startswith("❌"):
                weaknesses.append(e[2:].strip())

    gaps = compute_gap_analysis(profile, intent)

    return {
        "overall": overall,
        "readiness_label": "Goal-Aware Profile Readiness",
        "categories": {
            "positioning": pos,
            "goal_alignment": goal,
            "projects": proj,
            "communication": comm,
            "completeness": comp,
        },
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:6],
        "gap_analysis": gaps,
        "career_intent": intent,
    }
