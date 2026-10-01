# roast-my-github 🔥

## About

**Roast My GitHub** is an AI-powered developer feedback tool that analyzes a public GitHub profile and its repositories.

Instead of giving generic feedback, the application looks for real issues such as missing README files, weak repository descriptions, inactive projects, naming problems, and profile presentation gaps.

It then uses a **rule-based analysis engine** to calculate a transparent GitHub Health Score and **Google Gemini** to turn the findings into a personalized, hilarious, and friendly roast with practical recommendations.

The goal is simple:

**Make the user laugh → Make them understand the problem → Help them improve.**

### Core Workflow

**GitHub Username → Fetch → Analyze → Score → Roast → Improve**

---

## Features

- 🔍 **GitHub Profile & Repository Analysis** — Analyze public GitHub profile and repository information.

- 📊 **GitHub Health Score** — Get a score out of 100 based on Documentation, Activity, Presentation, and Profile.

- 🧠 **Explainable Scoring** — The score is generated using deterministic rules, with evidence showing why each category received its score.

- 🔥 **AI-Powered Roast** — Google Gemini generates a personalized roast based on the actual weaknesses detected in the profile.

- 😂 **Simple & Friendly Humor** — The roast uses simple English and avoids unnecessary technical jargon. The goal is to make the feedback memorable without insulting the user.

- 💡 **Actionable Recommendations** — Get clear and practical suggestions for improving your GitHub profile and repositories.

- ✨ **AI README Generator** — Generate a structured README starter for repositories with weak or missing documentation.

- 🛡️ **Error & Fallback Handling** — Handles GitHub API errors, rate limits, and AI failures gracefully.

- 🎯 **Demo Mode** — Includes a sample profile for demonstrations when live GitHub data is unavailable.

---

## How It Works

The application separates **analysis** from **AI-generated feedback**.

```text
GitHub Username
       ↓
GitHub REST API
       ↓
Profile + Repository Data
       ↓
Rule-Based Analysis Engine
       ↓
Score + Evidence + Findings
       ↓
Google Gemini
       ↓
Roast + Recommendations
       ↓
Improvement
