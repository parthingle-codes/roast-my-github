# analyzer.py
# Rule-based GitHub profile scoring engine.
# NO AI is used here — every point is tied to a measurable signal.
# This makes the score fully explainable to judges.

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def days_since(iso_string: str) -> int:
    """Return the number of days between now and an ISO-8601 date string."""
    if not iso_string:
        return 9999
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days


def is_readable_name(name: str) -> bool:
    """
    A repo name is 'readable' if it:
    - is 30 characters or fewer
    - uses only letters, numbers, hyphens, underscores
    - is not a meaningless string like 'asdf' or 'test123' (heuristic)
    """
    if len(name) > 30:
        return False
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
        return False
    # Flag obviously random names: no vowels in the alphabetic part
    alpha = re.sub(r'[^a-zA-Z]', '', name)
    if len(alpha) >= 4 and not re.search(r'[aeiouAEIOU]', alpha):
        return False
    return True


# ---------------------------------------------------------------------------
# SCORING — DOCUMENTATION  (0–25)
# ---------------------------------------------------------------------------

def score_documentation(repos: list) -> dict:
    """
    Measures how well the developer documents their work.

    Signals:
      readme_score  (0–10): % of checked repos that have a README
      desc_score    (0–8):  % of repos that have a non-empty description
      topics_score  (0–7):  % of repos that have at least one topic/tag

    Returns the score and a list of evidence strings for the UI.
    """
    evidence = []

    # --- README ---
    checked = [r for r in repos if r.get("readme_checked")]
    with_readme = [r for r in checked if r.get("has_readme")]
    if checked:
        readme_ratio = len(with_readme) / len(checked)
        readme_score = round(readme_ratio * 10)
        missing = len(checked) - len(with_readme)
        if missing == 0:
            evidence.append(f"✅ All {len(checked)} checked repos have a README")
        else:
            evidence.append(f"⚠️ {missing} of {len(checked)} checked repos are missing a README")
    else:
        readme_score = 0
        evidence.append("⚠️ Could not check for READMEs")

    # --- Description ---
    with_desc = [r for r in repos if r.get("description") and len(r["description"].strip()) > 3]
    desc_ratio = len(with_desc) / len(repos) if repos else 0
    desc_score = round(desc_ratio * 8)
    missing_desc = len(repos) - len(with_desc)
    if missing_desc == 0:
        evidence.append(f"✅ All repos have a description")
    else:
        evidence.append(f"⚠️ {missing_desc} repo(s) have no description")

    # --- Topics ---
    with_topics = [r for r in repos if r.get("topics") and len(r["topics"]) > 0]
    topics_ratio = len(with_topics) / len(repos) if repos else 0
    topics_score = round(topics_ratio * 7)
    if len(with_topics) == 0:
        evidence.append("⚠️ No repos use topics/tags — tags help with discoverability")
    else:
        evidence.append(f"✅ {len(with_topics)} repo(s) use topics/tags")

    total = min(readme_score + desc_score + topics_score, 25)
    return {"score": total, "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# SCORING — ACTIVITY  (0–25)
# ---------------------------------------------------------------------------

def score_activity(profile: dict, repos: list) -> dict:
    """
    Measures how recently and frequently the developer is active.
    Note: updated_at reflects the last repository update (push, PR, issue),
    NOT necessarily the last commit to the default branch.

    Signals:
      updated_30d  (5 pts): any repo updated in the last 30 days
      updated_90d  (3 pts): any repo updated in the last 90 days
      repo_count_5 (4 pts): more than 5 public repos
      repo_count_15(3 pts): more than 15 public repos (bonus)
      avg_stars_1  (4 pts): average repo stars > 0
      avg_stars_5  (3 pts): average repo stars > 5 (bonus)
      recent_count (3 pts): 3+ repos updated in the last 90 days
    """
    evidence = []
    points = 0

    if not repos:
        return {"score": 0, "max": 25, "evidence": ["⚠️ No public repositories found"]}

    # --- Recency ---
    days_since_updates = [days_since(r.get("updated_at", "")) for r in repos]
    min_days = min(days_since_updates)
    recent_90 = sum(1 for d in days_since_updates if d <= 90)

    if min_days <= 30:
        points += 5
        evidence.append(f"✅ At least one repo updated in the last 30 days")
    elif min_days <= 90:
        points += 3
        evidence.append(f"⚠️ Most recent repo update was {min_days} days ago (within 90 days)")
    else:
        evidence.append(f"❌ No repos updated in the last 90 days (most recent: {min_days} days ago)")

    if recent_90 >= 3 and min_days > 30:
        points += 3
        evidence.append(f"✅ {recent_90} repos updated in the last 90 days")
    elif recent_90 >= 3:
        points += 3
        evidence.append(f"✅ {recent_90} repos updated in the last 90 days")
    elif recent_90 > 0:
        evidence.append(f"⚠️ Only {recent_90} repo(s) updated in the last 90 days")
    else:
        evidence.append("❌ No repos updated in the last 90 days")

    # --- Repository count ---
    total_repos = profile.get("public_repos", 0)
    if total_repos > 15:
        points += 4 + 3  # both thresholds
        evidence.append(f"✅ {total_repos} public repos — solid portfolio size")
    elif total_repos > 5:
        points += 4
        evidence.append(f"✅ {total_repos} public repos — decent portfolio size")
    else:
        evidence.append(f"⚠️ Only {total_repos} public repo(s) — build more projects")

    # --- Stars (portfolio visibility signal) ---
    stars = [r.get("stargazers_count", 0) for r in repos]
    avg_stars = sum(stars) / len(stars) if stars else 0
    if avg_stars > 5:
        points += 4 + 3
        evidence.append(f"✅ Average {avg_stars:.1f} stars/repo — others find your work valuable")
    elif avg_stars > 0:
        points += 4
        evidence.append(f"✅ Some repos have stars — your work is getting noticed")
    else:
        evidence.append("⚠️ No stars yet — stars reflect portfolio visibility, not skill level")

    total = min(points, 25)
    return {"score": total, "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# SCORING — PRESENTATION  (0–25)
# ---------------------------------------------------------------------------

def score_presentation(repos: list) -> dict:
    """
    Measures how professional and organized the repositories look.

    Signals:
      readable_names (0–5): % of repos with a readable/professional name
      lang_diversity (0–5): uses more than 2 languages
      desc_quality   (0–4): average description length > 20 chars
      no_forks       (0–3): proportion of original (non-forked) repos
      pinned_worthy  (0–8): does the developer have star-worthy repos
                            (repos a recruiter might want to see pinned)?
    """
    evidence = []
    points = 0

    if not repos:
        return {"score": 0, "max": 25, "evidence": ["⚠️ No public repositories found"]}

    # --- Readable names ---
    readable = [r for r in repos if is_readable_name(r.get("name", ""))]
    unreadable = len(repos) - len(readable)
    readable_ratio = len(readable) / len(repos)
    name_pts = round(readable_ratio * 5)
    points += name_pts
    if unreadable == 0:
        evidence.append("✅ All repo names are clean and professional")
    else:
        bad_names = [r["name"] for r in repos if not is_readable_name(r.get("name", ""))][:3]
        evidence.append(f"⚠️ {unreadable} repo(s) have unclear names: {', '.join(bad_names)}")

    # --- Language diversity ---
    languages = set(r.get("language") for r in repos if r.get("language"))
    if len(languages) > 3:
        points += 5
        evidence.append(f"✅ Uses {len(languages)} languages: {', '.join(list(languages)[:5])}")
    elif len(languages) > 1:
        points += 3
        evidence.append(f"✅ Uses {len(languages)} languages — shows some versatility")
    elif len(languages) == 1:
        points += 1
        evidence.append(f"⚠️ All repos use only {list(languages)[0]} — consider exploring more languages")
    else:
        evidence.append("⚠️ No language detected across repos")

    # --- Description quality ---
    descs = [r.get("description", "") or "" for r in repos]
    long_descs = [d for d in descs if len(d.strip()) > 20]
    if len(long_descs) / max(len(repos), 1) > 0.6:
        points += 4
        evidence.append("✅ Most repos have meaningful descriptions")
    elif len(long_descs) > 0:
        points += 2
        evidence.append(f"⚠️ Only {len(long_descs)} repo(s) have a meaningful description (>20 chars)")
    else:
        evidence.append("❌ No repos have a meaningful description")

    # --- Original vs forked ---
    non_forked = [r for r in repos if not r.get("fork", False)]
    fork_count = len(repos) - len(non_forked)
    if fork_count == 0:
        points += 3
        evidence.append("✅ All repos are original work (no forks cluttering the profile)")
    elif len(non_forked) / max(len(repos), 1) > 0.7:
        points += 2
        evidence.append(f"✅ Mostly original repos ({fork_count} fork(s))")
    else:
        evidence.append(f"⚠️ {fork_count} fork(s) — many forks can dilute your portfolio presentation")

    # --- Star-worthy repos (portfolio visibility) ---
    starred = [r for r in repos if r.get("stargazers_count", 0) > 0]
    top_stars = max((r.get("stargazers_count", 0) for r in repos), default=0)
    if top_stars > 10:
        points += 8
        evidence.append(f"✅ Top repo has {top_stars} stars — strong portfolio signal")
    elif top_stars > 2:
        points += 5
        evidence.append(f"✅ Some repos have stars (top: {top_stars})")
    elif len(starred) > 0:
        points += 3
        evidence.append(f"✅ At least one starred repo — keep building")
    else:
        evidence.append("⚠️ No repos have been starred yet — star count is a portfolio visibility signal, not a measure of skill")

    total = min(points, 25)
    return {"score": total, "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# SCORING — PROFILE  (0–25)
# ---------------------------------------------------------------------------

def score_profile(profile: dict) -> dict:
    """
    Measures how complete and professional the GitHub profile itself is.

    Signals:
      has_avatar    (5 pts): custom profile picture
      has_name      (5 pts): display name set
      has_bio       (4 pts): bio filled in (extra 2 pts if > 50 chars)
      has_location  (3 pts): location visible
      has_blog      (3 pts): blog/website URL set
      account_age   (3 pts): account older than 1 year (tenure signal)
      followers     (2 pts): > 10 followers (portfolio reach signal)
    """
    evidence = []
    points = 0

    # --- Avatar ---
    avatar = profile.get("avatar_url", "")
    # GitHub default avatars contain "gravatar" or identicons
    has_custom_avatar = bool(avatar) and "identicons" not in avatar
    if has_custom_avatar:
        points += 5
        evidence.append("✅ Has a profile picture")
    else:
        evidence.append("⚠️ No custom profile picture — add a photo for a professional first impression")

    # --- Display name ---
    if profile.get("name"):
        points += 5
        evidence.append(f"✅ Display name set: \"{profile['name']}\"")
    else:
        evidence.append("⚠️ No display name — recruiters prefer a real name over a username")

    # --- Bio ---
    bio = profile.get("bio") or ""
    if len(bio.strip()) > 50:
        points += 6  # full + bonus
        evidence.append(f"✅ Bio is descriptive ({len(bio)} chars)")
    elif len(bio.strip()) > 10:
        points += 4
        evidence.append(f"⚠️ Bio exists but is brief — expand it to describe your skills and goals")
    else:
        evidence.append("❌ Bio is empty — this is one of the first things a recruiter reads")

    # --- Location ---
    if profile.get("location"):
        points += 3
        evidence.append(f"✅ Location set: {profile['location']}")
    else:
        evidence.append("⚠️ Location not set — helps recruiters filter for local candidates")

    # --- Blog/Website ---
    if profile.get("blog"):
        points += 3
        evidence.append(f"✅ Website/blog linked: {profile['blog']}")
    else:
        evidence.append("⚠️ No website or blog linked — a portfolio site or LinkedIn URL adds credibility")

    # --- Account age (tenure signal) ---
    created_at = profile.get("created_at", "")
    age_days = days_since(created_at)
    if age_days > 365:
        points += 3
        years = age_days // 365
        evidence.append(f"✅ Account is {years} year(s) old — shows consistent presence on GitHub")
    else:
        months = age_days // 30
        evidence.append(f"⚠️ Account is only {months} month(s) old — keep building your history")

    # --- Followers (portfolio reach signal) ---
    followers = profile.get("followers", 0)
    if followers > 10:
        points += 2  # only a small bonus — followers reflect reach, not skill
        evidence.append(f"✅ {followers} followers — solid community reach (note: follower count reflects portfolio visibility, not programming ability)")
    else:
        evidence.append(f"ℹ️ {followers} follower(s) — engage with the community to grow your reach")

    total = min(points, 25)
    return {"score": total, "max": 25, "evidence": evidence}


# ---------------------------------------------------------------------------
# MAIN ANALYSIS FUNCTION
# ---------------------------------------------------------------------------

def analyze(profile: dict, repos: list) -> dict:
    """
    Orchestrates all four scoring categories and builds the complete
    structured findings object that gets sent to the LLM.
    """
    doc = score_documentation(repos)
    act = score_activity(profile, repos)
    pres = score_presentation(repos)
    prof = score_profile(profile)

    overall = doc["score"] + act["score"] + pres["score"] + prof["score"]

    # --- Build strengths + weaknesses from evidence ---
    strengths = []
    weaknesses = []

    for cat in [doc, act, pres, prof]:
        for e in cat["evidence"]:
            if e.startswith("✅"):
                strengths.append(e[2:].strip())
            elif e.startswith("⚠️") or e.startswith("❌"):
                weaknesses.append(e[2:].strip())

    # --- Identify repos that need a README most ---
    weak_repos = [
        r for r in repos
        if not r.get("has_readme") and r.get("readme_checked")
    ]
    weak_repos_info = [
        {
            "name": r["name"],
            "description": r.get("description") or "",
            "language": r.get("language") or "Unknown",
            "stars": r.get("stargazers_count", 0),
            "topics": r.get("topics", []),
        }
        for r in weak_repos[:5]  # top 5 most improvable repos
    ]

    return {
        "overall": overall,
        "categories": {
            "documentation": doc,
            "activity": act,
            "presentation": pres,
            "profile": prof,
        },
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:6],
        "weak_repos": weak_repos_info,
        "total_repos": profile.get("public_repos", 0),
        "checked_repos": len([r for r in repos if r.get("readme_checked")]),
    }
