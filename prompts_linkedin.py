# prompts_linkedin.py
# Prompt templates for Goal-Aware LinkedIn Analysis, Roasting, and Profile Rewriting.

import json
from typing import Dict, Any


def build_linkedin_roast_prompt(analysis: Dict[str, Any], profile: Dict[str, Any], intent: Dict[str, Any]) -> str:
    """
    Builds the prompt sent to Gemini for a Goal-Aware LinkedIn Roast and actionable roadmap.
    Enforces simple, friendly student-level English and roasts the profile's gap against their target.
    """
    name = profile.get("identity", {}).get("name") or "this developer"
    headline = profile.get("headline", "") or "No headline"
    overall = analysis.get("overall", 0)
    cats = analysis.get("categories", {})
    gap_info = analysis.get("gap_analysis", {})

    target_role = intent.get("target_role", "Developer")
    domain = intent.get("domain", "Tech")
    stage = intent.get("stage", "Student")
    timeline = intent.get("timeline_months", 6)

    top_gaps = "\n".join(f"- {g}" for g in gap_info.get("top_3_gaps", []))
    strengths = "\n".join(f"- {s}" for s in analysis.get("strengths", []))
    weaknesses = "\n".join(f"- {w}" for w in analysis.get("weaknesses", []))

    return f"""You are a funny, encouraging tech mentor doing a friendly review of a student/developer's LinkedIn profile.
Your job is to compare where they want to go against what their profile currently shows.

FORMULA:
FACT (The Gap) → FUNNY RELATABLE COMPARISON → "OH, I GET IT" → IMMEDIATE ACTIONABLE FIX

TONE & RULES:
- Like a funny friend who teases them (intensity 7/10) but genuinely wants them to get the role.
- Super simple, everyday English. Relatable college, student, interview, or everyday life situations.
- Roast the PROFILE and the GAP, NEVER the person.
- Do NOT invent facts or experience they do not have.
- Avoid corporate jargon or complicated buzzwords.

=== CAREER INTENT ===
Stage: {stage}
Target Role: {target_role}
Domain: {domain}
Timeline: {timeline} months

=== PROFILE AUDIT DATA ===
Name: {name}
Current Headline: {headline}
Profile Readiness Score: {overall}/100

Category Scores:
- Professional Positioning: {cats.get('positioning', {}).get('score', 0)}/20
- Goal Alignment: {cats.get('goal_alignment', {}).get('score', 0)}/25
- Projects & Evidence: {cats.get('projects', {}).get('score', 0)}/25
- Communication: {cats.get('communication', {}).get('score', 0)}/15
- Profile Completeness: {cats.get('completeness', {}).get('score', 0)}/15

Top 3 Goal Gaps:
{top_gaps}

Strengths:
{strengths}

Weaknesses:
{weaknesses}
=== END DATA ===

Respond ONLY with a valid JSON object in this exact structure (no markdown fences, no extra text):
{{
  "roast_headline": "Short punchy one-liner about the gap between their goal ({target_role}) and their profile (max 12 words).",
  "roast": "2-4 short, funny sentences comparing what their profile shows vs where they want to go. Use everyday comparisons (e.g. group projects, ordering food, exams).",
  "what_it_means": "ONE simple sentence in plain English explaining what recruiters actually see.",
  "fix": "ONE clear action verb sentence they can do today.",
  "top_problems": [
    "Problem 1 directly tied to the goal gap",
    "Problem 2 directly tied to the goal gap",
    "Problem 3 directly tied to the goal gap"
  ],
  "recommendations": [
    "Actionable step 1 to bridge the gap",
    "Actionable step 2 to bridge the gap",
    "Actionable step 3 to bridge the gap"
  ],
  "next_3_actions": [
    "Action 1 (Headline or About fix)",
    "Action 2 (Project framing fix)",
    "Action 3 (Skill/credential addition)"
  ],
  "encouragement": "One genuinely encouraging sentence showing that this gap is totally fixable in time for their {timeline}-month goal."
}}"""


def build_rewrite_prompt(field_type: str, current_text: str, intent: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    Builds the prompt used to rewrite a profile section (headline, about, project) to better align with the goal.
    """
    target_role = intent.get("target_role", "Developer")
    domain = intent.get("domain", "Software")

    field_instructions = {
        "headline": "Rewrite this headline so it clearly highlights the target role, core technical stack, and what they build. Keep it under 180 characters, crisp, and recruiter-friendly.",
        "about": "Rewrite this About/Summary section into 2-3 engaging, conversational paragraphs (approx 100-150 words). Outline their interest, what they build, their key technical competencies, and what they are looking for.",
        "project": "Rewrite this project description with an active problem-action-result structure. Highlight technologies used and measurable outcomes."
    }

    instruction = field_instructions.get(field_type, "Improve this text to better communicate competence and direction.")

    return f"""You are an expert tech resume and LinkedIn advisor helping a candidate optimize their profile for their dream role.

Target Role: {target_role}
Domain: {domain}
Section to Rewrite: {field_type}

Instruction:
{instruction}

Current Text:
"{current_text or 'None provided'}"

Respond ONLY with a valid JSON object:
{{
  "current": "{current_text or 'None'}",
  "improved": "The polished, recruiter-ready rewrite.",
  "why_this_is_better": "2-3 bullet points explaining why this version creates stronger goal alignment and recruiter credibility."
}}"""
