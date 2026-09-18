# roast-my-github

## About

**Roast My GitHub** is an AI-powered developer feedback tool that analyzes a public GitHub profile and its repositories.

The application fetches public GitHub data, evaluates the profile using a deterministic rule-based scoring engine, and generates a personalized roast with actionable recommendations using the **Google Gemini API**.

The core workflow is:

**GitHub Username → Fetch → Analyze → Score → Roast → Improve**

## Features

- 🔍 **GitHub Profile & Repository Analysis** — Analyze public GitHub profile and repository data.
- 📊 **GitHub Health Score** — Get a score out of 100 across Documentation, Activity, Presentation, and Profile.
- 🔥 **AI-Powered Roast** — Gemini generates a personalized and constructive roast based on detected weaknesses.
- 💡 **Actionable Recommendations** — Get specific suggestions for improving your GitHub profile and repositories.
- ✨ **AI README Generator** — Generate a structured README starter for repositories with weak or missing documentation.
- 🛡️ **Error & Fallback Handling** — Handles GitHub API errors, rate limits, and AI failures gracefully.
- 🎯 **Demo Mode** — Includes a sample profile for quick demonstrations when live API access is unavailable.

## Tech Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **GitHub Data:** GitHub REST API
- **AI:** Google Gemini API
- **Environment Management:** Python dotenv
