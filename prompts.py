# prompts.py
# All LLM prompt templates live here.
# Keeping prompts in one file makes them easy to iterate on and explain to judges.


def build_roast_prompt(analysis: dict, profile: dict) -> str:
    """
    Builds the structured prompt sent to Gemini for roast + recommendations.

    Design principles:
    - We send ONLY pre-calculated findings, never raw GitHub JSON.
    - The model is explicitly told NOT to invent GitHub facts.
    - We request structured JSON output for reliable parsing.
    - Tone: witty, honest, constructive — never personal or cruel.
    """

    username = profile.get("login", "this developer")
    overall = analysis["overall"]
    cats = analysis["categories"]
    weaknesses = analysis["weaknesses"]
    strengths = analysis["strengths"]

    weakness_list = "\n".join(f"- {w}" for w in weaknesses) or "- No major weaknesses detected"
    strength_list = "\n".join(f"- {s}" for s in strengths) or "- No major strengths detected"

    return f"""You are a senior developer doing a friendly, honest code-review-style roast of a GitHub profile.

You have been given PRE-CALCULATED analysis data. 
DO NOT invent any GitHub facts, numbers, or repository names that are not in the data below.
Your job is ONLY to interpret these findings and write engaging natural language.

=== ANALYSIS DATA ===
Username: {username}
Overall Score: {overall}/100

Category Scores:
- Documentation: {cats['documentation']['score']}/25
- Activity: {cats['activity']['score']}/25
- Presentation: {cats['presentation']['score']}/25
- Profile: {cats['profile']['score']}/25

Detected Weaknesses:
{weakness_list}

Detected Strengths:
{strength_list}
=== END DATA ===

Respond ONLY with a valid JSON object in this exact format (no markdown, no code fences):
{{
  "roast": "A witty 2-4 sentence roast targeting the specific weaknesses above. Be playful and specific, not generic. Avoid personal attacks. The roast must be clearly based on the weaknesses listed above.",
  "top_problems": [
    "Specific problem 1 based on the weaknesses above (1-2 sentences)",
    "Specific problem 2 based on the weaknesses above (1-2 sentences)",
    "Specific problem 3 based on the weaknesses above (1-2 sentences)"
  ],
  "recommendations": [
    "Actionable fix for problem 1 (be specific — what exactly should they do?)",
    "Actionable fix for problem 2 (be specific — what exactly should they do?)",
    "Actionable fix for problem 3 (be specific — what exactly should they do?)"
  ],
  "encouragement": "One genuinely encouraging sentence acknowledging their strengths or potential."
}}"""


def build_readme_prompt(repo: dict) -> str:
    """
    Builds the prompt used to generate a starter README for a weak repository.

    We send only the repository metadata we have — name, description, language, topics.
    The model generates a realistic skeleton the developer can customize.
    """

    name = repo.get("name", "my-project")
    description = repo.get("description") or "No description provided"
    language = repo.get("language") or "Not specified"
    topics = ", ".join(repo.get("topics", [])) or "None"
    stars = repo.get("stars", 0)

    return f"""You are a technical writer helping a developer create a professional README for their GitHub repository.

Repository details (this is ALL the information you have — do not invent features or installation steps you cannot confirm):
- Name: {name}
- Description: {description}
- Primary Language: {language}
- Topics/Tags: {topics}
- Stars: {stars}

Generate a starter README in Markdown format.
Use placeholders like [Your description here] and [Add installation steps] where you lack specific information.
Keep it realistic — do not invent specific features, commands, or file paths.

The README should include these sections:
# {name}

## About
## Features
## Tech Stack
## Installation
## Usage
## Contributing
## License

Make it clean, professional, and useful as a starting template the developer can fill in."""
