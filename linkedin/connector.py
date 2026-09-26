# linkedin/connector.py
# LinkedIn Data Ingestion Connector.
# Interacts with LinkedIn OpenID Connect UserInfo endpoint and provides
# demo fallback profiles for testing and live demonstrations.

import requests
from typing import Dict, Any
from . import normalizer


def fetch_member_profile(access_token: str) -> Dict[str, Any]:
    """
    Retrieves authorized OpenID Connect member data from LinkedIn.
    Endpoint: https://api.linkedin.com/v2/userinfo
    """
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.get(userinfo_url, headers=headers, timeout=12)
    if resp.status_code != 200:
        raise RuntimeError(f"LinkedIn UserInfo retrieval failed ({resp.status_code}): {resp.text}")

    raw_userinfo = resp.json()
    return normalizer.normalize_oidc_userinfo(raw_userinfo)


def get_demo_linkedin_profile() -> Dict[str, Any]:
    """
    Returns a realistic sample student LinkedIn profile for demonstration.
    Models a 2nd/3rd-year student aiming for an ML/AI internship who has
    some coding skills (Python, SQL, Web) but lacks clear ML specialization evidence.
    """
    profile = normalizer.create_empty_profile()
    profile["identity"] = {
        "name": "Jordan Patel",
        "photo": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=faces",
        "email": "jordan.patel.demo@example.com",
        "sub": "demo-sub-12345",
    }
    profile["headline"] = "Computer Science Student | Exploring Tech & Coding | Aspiring Developer"
    profile["about"] = (
        "Passionate computer science student who loves solving problems and learning new technologies. "
        "Looking forward to exciting internship opportunities in software and machine learning."
    )
    profile["skills"] = ["Python", "Java", "C++", "HTML/CSS", "JavaScript", "SQL", "Git"]
    profile["projects"] = [
        {
            "title": "Student Task Management App",
            "description": "Built a responsive web dashboard for students to organize assignments with deadline reminders.",
            "technologies": ["JavaScript", "HTML", "CSS", "Node.js"],
            "outcomes": "Adopted by 30+ classmates during midterms.",
        },
        {
            "title": "Basic Sales Data Analyzer",
            "description": "Wrote Python scripts to clean retail sales CSVs and generate statistical summary reports using pandas.",
            "technologies": ["Python", "pandas", "matplotlib"],
            "outcomes": "Analyzed 10k rows of mock transaction data.",
        },
    ]
    profile["education"] = [
        {
            "school": "State Institute of Technology",
            "degree": "Bachelor of Technology",
            "field": "Computer Science & Engineering",
        }
    ]
    profile["experience"] = [
        {
            "role": "Technical Team Member",
            "company": "University Coding Club",
            "description": "Assisted in organizing weekly coding workshops and hackathons for junior students.",
        }
    ]
    profile["certifications"] = [
        {"name": "Python for Everybody Specialization", "issuer": "Coursera"},
        {"name": "Foundations of Data Analysis", "issuer": "Online Academy"},
    ]
    profile["featured"] = []

    # Tag all data as user_provided for transparency
    for k in profile["data_status"]:
        profile["data_status"][k] = "user_provided"

    return profile
