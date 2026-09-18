/* =========================================================
   app.js — Roast My GitHub
   Frontend application logic:
   - Screen management & smooth navigation
   - API orchestration (GitHub, analyzer, Gemini roast, README generator)
   - Visual dashboard animations (HUD gauge, score counter, progress bars)
   - Clean, resilient error and fallback handling
   ========================================================= */

"use strict";

// ---------------------------------------------------------------------------
// SCREEN MANAGEMENT & SMOOTH SCROLLING
// ---------------------------------------------------------------------------

function showScreen(id) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  const target = document.getElementById(id);
  if (target) {
    target.classList.add("active");
  }
}

function smoothScrollTo(elementId) {
  const el = document.getElementById(elementId);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// ---------------------------------------------------------------------------
// STEP PROGRESS (Analyzing screen)
// ---------------------------------------------------------------------------

function setStep(stepId, state) {
  // state: 'pending' | 'active' | 'done' | 'error'
  const el = document.getElementById(stepId);
  if (!el) return;
  el.className = "step " + (state === "done" || state === "active" || state === "error" ? state : "");
  const icon = el.querySelector(".step-icon");
  if (!icon) return;
  if (state === "done")         icon.innerHTML = "✅";
  else if (state === "active")  icon.innerHTML = '<div class="spinner"></div>';
  else if (state === "error")   icon.innerHTML = "❌";
  else                          icon.innerHTML = "○";
}

// ---------------------------------------------------------------------------
// UTILITY HELPERS & COLOR TIERS
// ---------------------------------------------------------------------------

function scoreColor(score, max) {
  const pct = score / max;
  if (pct >= 0.8) return "great";
  if (pct >= 0.6) return "good";
  if (pct >= 0.4) return "ok";
  return "poor";
}

function gradeLabel(score) {
  if (score >= 85) return { text: "Recruiter-ready 🚀",  cls: "badge-great" };
  if (score >= 70) return { text: "Pretty solid 👍",     cls: "badge-good" };
  if (score >= 50) return { text: "Needs work 🛠️",       cls: "badge-ok" };
  return              { text: "Needs serious work 🔥",  cls: "badge-poor" };
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// MICRO-INTERACTIONS: SCORE COUNTER & GAUGE ANIMATION
// ---------------------------------------------------------------------------

function animateScoreCounter(targetScore, colorKey) {
  const scoreEl = document.getElementById("res-score");
  const gaugeBar = document.getElementById("score-gauge-bar");
  
  if (!scoreEl) return;
  
  // Set gauge color
  const colorMap = {
    great: "#3fb950",
    good:  "#58a6ff",
    ok:    "#d29922",
    poor:  "#f85149"
  };
  
  if (gaugeBar) {
    const strokeColor = colorMap[colorKey] || "#f97316";
    gaugeBar.style.stroke = strokeColor;
    
    // Circumference for r=50 is ~314.16
    const circumference = 314.16;
    const targetOffset = circumference - (circumference * targetScore / 100);
    
    // Trigger CSS stroke-dashoffset transition
    setTimeout(() => {
      gaugeBar.style.strokeDashoffset = targetOffset;
    }, 50);
  }

  // Smooth numeric count-up
  const duration = 1100;
  const startTime = performance.now();

  function step(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Cubic ease-out
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = Math.round(targetScore * ease);
    scoreEl.textContent = val;

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      scoreEl.textContent = targetScore;
    }
  }

  requestAnimationFrame(step);
}

// ---------------------------------------------------------------------------
// EVIDENCE TOGGLE
// ---------------------------------------------------------------------------

function toggleEvidence(containerId, btn) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const open = container.classList.toggle("open");
  btn.textContent = open ? "Hide details ▴" : "Show details ▾";
}

// ---------------------------------------------------------------------------
// RENDER RESULTS DASHBOARD
// ---------------------------------------------------------------------------

function renderResults(profile, analysis, roastData) {
  // --- Profile Identity ---
  const avatarEl = document.getElementById("res-avatar");
  if (avatarEl) {
    avatarEl.src = profile.avatar_url || "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png";
  }
  
  document.getElementById("res-username").textContent = profile.login;
  document.getElementById("res-profile-link").href = profile.html_url || `https://github.com/${profile.login}`;
  
  const bioEl = document.getElementById("res-bio");
  bioEl.textContent = profile.bio ? `“${profile.bio}”` : "No public bio set on GitHub.";

  // Profile metadata pills
  const pillsContainer = document.getElementById("profile-pills");
  if (pillsContainer) {
    let pillsHtml = `
      <span class="meta-pill">📦 ${profile.public_repos} repos</span>
      <span class="meta-pill">👥 ${profile.followers} followers</span>
    `;
    if (profile.location) {
      pillsHtml += `<span class="meta-pill">📍 ${escapeHtml(profile.location)}</span>`;
    }
    if (profile.blog) {
      const cleanBlog = profile.blog.replace(/^https?:\/\//, "");
      pillsHtml += `<span class="meta-pill">🔗 ${escapeHtml(cleanBlog.slice(0, 20))}</span>`;
    }
    pillsContainer.innerHTML = pillsHtml;
  }

  // --- Overall Score & Gauge ---
  const score = analysis.overall;
  const colorKey = scoreColor(score, 100);
  const grade = gradeLabel(score);

  const scoreEl = document.getElementById("res-score");
  scoreEl.className = `score-number score-${colorKey}`;

  const gradeEl = document.getElementById("res-grade");
  gradeEl.textContent = grade.text;
  gradeEl.className = `score-grade ${grade.cls}`;

  // Start animated count-up and circular gauge fill
  animateScoreCounter(score, colorKey);

  // --- Category Cards (2x2 Grid) ---
  const cats = [
    { key: "documentation", id: "doc" },
    { key: "activity",      id: "act" },
    { key: "presentation",  id: "pres" },
    { key: "profile",       id: "prof" },
  ];

  cats.forEach(({ key, id }) => {
    const cat = analysis.categories[key];
    const pct = (cat.score / cat.max) * 100;
    const catColor = scoreColor(cat.score, cat.max);

    // Score text
    const scoreValEl = document.getElementById(`score-${id}`);
    scoreValEl.textContent = `${cat.score} / ${cat.max}`;
    scoreValEl.className = `category-score score-${catColor}`;

    // Animated progress bar
    const bar = document.getElementById(`bar-${id}`);
    bar.className = `progress-fill bar-${catColor}`;
    setTimeout(() => {
      bar.style.width = pct + "%";
    }, 100);

    // Evidence list
    const evList = document.getElementById(`ev-${id}-list`);
    evList.innerHTML = cat.evidence
      .map(e => `<li>${escapeHtml(e)}</li>`)
      .join("");
  });

  // --- Key Strengths & Weaknesses ---
  const strengthsList = document.getElementById("strengths-list");
  if (analysis.strengths.length > 0) {
    strengthsList.innerHTML = analysis.strengths
      .map(s => `<li><span class="icon">✅</span> <span>${escapeHtml(s)}</span></li>`)
      .join("");
  } else {
    strengthsList.innerHTML = `<li><span class="icon">—</span> <span>No major standout strengths detected yet</span></li>`;
  }

  const weaknessesList = document.getElementById("weaknesses-list");
  if (analysis.weaknesses.length > 0) {
    weaknessesList.innerHTML = analysis.weaknesses
      .map(w => `<li><span class="icon">⚠️</span> <span>${escapeHtml(w)}</span></li>`)
      .join("");
  } else {
    weaknessesList.innerHTML = `<li><span class="icon">✨</span> <span>No major red flags detected! Excellent portfolio health.</span></li>`;
  }

  // --- AI Roast Section ---
  const fallbackBadge = document.getElementById("fallback-badge");
  if (roastData.fallback) {
    fallbackBadge.classList.remove("hidden");
  } else {
    fallbackBadge.classList.add("hidden");
  }

  document.getElementById("res-roast").textContent = roastData.roast || "No roast generated.";
  
  const encEl = document.getElementById("res-encouragement");
  encEl.textContent = roastData.encouragement || "Keep building — every top portfolio started somewhere.";

  // --- Top Problems Found ---
  const problemsList = document.getElementById("problems-list");
  const problems = roastData.top_problems || [];
  if (problems.length > 0) {
    problemsList.innerHTML = problems
      .map(p => `<li><span class="bullet">•</span> <span>${escapeHtml(p)}</span></li>`)
      .join("");
  } else {
    problemsList.innerHTML = `<li><span class="bullet">•</span> <span>Review the category details above to address specific deductions.</span></li>`;
  }

  // --- Actionable Steps: How to Fix It ---
  const recList = document.getElementById("rec-list");
  const recs = roastData.recommendations || [];
  if (recs.length > 0) {
    recList.innerHTML = recs
      .map((r, i) => {
        const stepNum = String(i + 1).padStart(2, "0");
        return `<li>
          <span class="rec-number">${stepNum}</span>
          <div class="rec-content">
            <span class="rec-text">${escapeHtml(r)}</span>
          </div>
        </li>`;
      })
      .join("");
  } else {
    recList.innerHTML = `<li>
      <span class="rec-number">01</span>
      <div class="rec-content">
        <span class="rec-text">Add detailed README files with setup guides to your primary repositories.</span>
      </div>
    </li>`;
  }

  // --- WOW Feature: Fix My README ---
  const weakRepos = analysis.weak_repos || [];
  const readmeSection = document.getElementById("readme-section");
  const repoSelector = document.getElementById("repo-selector");

  if (weakRepos.length === 0) {
    readmeSection.style.display = "none";
  } else {
    readmeSection.style.display = "block";
    repoSelector.innerHTML = "";
    
    weakRepos.forEach((repo, idx) => {
      const btn = document.createElement("button");
      btn.className = "btn-repo" + (idx === 0 ? " selected" : "");
      btn.textContent = repo.name;
      btn.dataset.repo = JSON.stringify(repo);

      btn.addEventListener("click", function () {
        document.querySelectorAll(".btn-repo").forEach(b => b.classList.remove("selected"));
        this.classList.add("selected");
        document.getElementById("btn-generate-readme").disabled = false;
        document.getElementById("btn-generate-readme").dataset.selectedRepo = this.dataset.repo;
        
        // Reset previous generated output
        document.getElementById("readme-output").classList.remove("visible");
        document.getElementById("readme-content").textContent = "";
      });
      
      repoSelector.appendChild(btn);
    });

    // Pre-select first weak repo so the user can generate immediately
    const firstBtn = repoSelector.querySelector(".btn-repo");
    if (firstBtn) {
      document.getElementById("btn-generate-readme").disabled = false;
      document.getElementById("btn-generate-readme").dataset.selectedRepo = firstBtn.dataset.repo;
    }
  }
}

// ---------------------------------------------------------------------------
// GENERATE README (WOW Feature)
// ---------------------------------------------------------------------------

async function generateReadme(repo) {
  const output = document.getElementById("readme-output");
  const content = document.getElementById("readme-content");
  const btn = document.getElementById("btn-generate-readme");

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Generating README...';
  output.classList.remove("visible");

  try {
    const resp = await fetch("/api/readme", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo }),
    });
    const data = await resp.json();

    if (data.ok && data.readme) {
      content.textContent = data.readme;
      output.classList.add("visible");
      output.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      content.textContent = "❌ Could not generate README: " + (data.error || "Unknown error");
      output.classList.add("visible");
    }
  } catch (err) {
    content.textContent = "❌ Network error. Please try again.";
    output.classList.add("visible");
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="gen-icon">✨</span> Generate Better README';
  }
}

// ---------------------------------------------------------------------------
// MAIN LIVE ANALYSIS FLOW WITH AUTO-SCROLL
// ---------------------------------------------------------------------------

async function runAnalysis(username) {
  document.getElementById("analyzing-username").textContent = "@" + username;
  showScreen("screen-analyzing");

  // Reset steps
  ["step-profile", "step-repos", "step-readme", "step-score", "step-roast"]
    .forEach(id => setStep(id, "pending"));

  let githubData, analysisData, roastData;

  // --- STEP 1: Fetch GitHub Profile & Repos ---
  setStep("step-profile", "active");
  try {
    const resp = await fetch(`/api/github/${encodeURIComponent(username)}`);
    const data = await resp.json();

    if (!data.ok) {
      showError(data.error || "Could not fetch GitHub profile.");
      return;
    }

    githubData = data.data;
    setStep("step-profile", "done");
    setStep("step-repos", "done");
    setStep("step-readme", "done");
  } catch (err) {
    showError("Network error while fetching GitHub data. Please check your connection.");
    return;
  }

  // --- STEP 2: Deterministic Scoring ---
  setStep("step-score", "active");
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(githubData),
    });
    const data = await resp.json();

    if (!data.ok) {
      showError(data.error || "Analysis failed.");
      return;
    }

    analysisData = data.analysis;
    setStep("step-score", "done");
  } catch (err) {
    showError("Network error during profile scoring analysis.");
    return;
  }

  // --- STEP 3: Gemini AI Roast ---
  setStep("step-roast", "active");
  try {
    const resp = await fetch("/api/roast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis: analysisData,
        profile: githubData.profile,
      }),
    });
    roastData = await resp.json();
    setStep("step-roast", "done");
  } catch (err) {
    roastData = {
      fallback: true,
      roast: "A solid developer profile with ambitious projects, but missing documentation leaves recruiters guessing.",
      top_problems: analysisData.weaknesses.slice(0, 3),
      recommendations: [
        "Add README files to your top repositories.",
        "Add meaningful descriptions to every repo.",
        "Highlight your best projects on your profile."
      ],
      encouragement: "Solid foundation across multiple tools! A documentation cleanup will make a big difference."
    };
    setStep("step-roast", "error");
  }

  // Small delay so user sees all green checkmarks
  await new Promise(r => setTimeout(r, 450));

  // --- Render Results ---
  if (githubData.is_demo) {
    document.getElementById("demo-banner").classList.remove("hidden");
  } else {
    document.getElementById("demo-banner").classList.add("hidden");
  }

  renderResults(githubData.profile, analysisData, roastData);
  showScreen("screen-results");

  // REQUIREMENT 1: AUTO-SCROLL TO RESULTS
  // Native smooth scrolling happens strictly after results are completely ready and rendered.
  setTimeout(() => {
    smoothScrollTo("screen-results");
  }, 60);
}

// ---------------------------------------------------------------------------
// DEMO PROFILE FLOW WITH AUTO-SCROLL
// ---------------------------------------------------------------------------

async function runDemoAnalysis() {
  document.getElementById("analyzing-username").textContent = "@alex-developer (Demo)";
  showScreen("screen-analyzing");

  ["step-profile", "step-repos", "step-readme", "step-score", "step-roast"]
    .forEach(id => setStep(id, "pending"));

  let githubData, analysisData, roastData;

  // Step 1: Demo Fetch
  setStep("step-profile", "active");
  await new Promise(r => setTimeout(r, 350));

  try {
    const resp = await fetch("/api/demo");
    const data = await resp.json();
    if (!data.ok) throw new Error("Demo load failed");
    githubData = data.data;
    setStep("step-profile", "done");
    setStep("step-repos", "done");
    setStep("step-readme", "done");
  } catch (err) {
    showError("Could not load demo profile.");
    return;
  }

  // Step 2: Scoring
  setStep("step-score", "active");
  await new Promise(r => setTimeout(r, 350));

  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(githubData),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error("Analysis failed");
    analysisData = data.analysis;
    setStep("step-score", "done");
  } catch (err) {
    showError("Analysis failed on demo profile.");
    return;
  }

  // Step 3: Roast
  setStep("step-roast", "active");
  try {
    const resp = await fetch("/api/roast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        analysis: analysisData,
        profile: githubData.profile,
      }),
    });
    roastData = await resp.json();
    setStep("step-roast", "done");
  } catch (err) {
    roastData = {
      fallback: true,
      roast: "A classic full-stack portfolio with ambitious project titles and unfinished documentation.",
      top_problems: analysisData.weaknesses.slice(0, 3),
      recommendations: [
        "Add README files to your top repositories.",
        "Add meaningful descriptions to every repo.",
        "Highlight your best repositories on your profile."
      ],
      encouragement: "Solid start with diverse technologies! Polish the presentation to stand out."
    };
    setStep("step-roast", "error");
  }

  await new Promise(r => setTimeout(r, 450));

  document.getElementById("demo-banner").classList.remove("hidden");
  renderResults(githubData.profile, analysisData, roastData);
  showScreen("screen-results");

  // REQUIREMENT 1: AUTO-SCROLL TO RESULTS
  setTimeout(() => {
    smoothScrollTo("screen-results");
  }, 60);
}

// ---------------------------------------------------------------------------
// ERROR HANDLING
// ---------------------------------------------------------------------------

function showError(message) {
  showScreen("screen-landing");
  document.getElementById("landing-error").textContent = "❌ " + message;
  const btn = document.getElementById("btn-roast-me");
  if (btn) btn.disabled = false;
}

// ---------------------------------------------------------------------------
// EVENT LISTENERS & INITIALIZATION
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("username-input");
  const btn = document.getElementById("btn-roast-me");
  const demoBtn = document.getElementById("btn-try-demo");

  function triggerRoast() {
    const username = input.value.trim();
    document.getElementById("landing-error").textContent = "";

    if (!username) {
      document.getElementById("landing-error").textContent = "❌ Please enter a GitHub username.";
      input.focus();
      return;
    }

    if (!/^[a-zA-Z0-9\-]{1,39}$/.test(username)) {
      document.getElementById("landing-error").textContent = "❌ Invalid GitHub username format.";
      return;
    }

    btn.disabled = true;
    runAnalysis(username.toLowerCase()).finally(() => {
      btn.disabled = false;
    });
  }

  if (btn) {
    btn.addEventListener("click", triggerRoast);
  }

  if (input) {
    input.addEventListener("keydown", e => {
      if (e.key === "Enter") triggerRoast();
    });
  }

  // Demo Profile Button
  if (demoBtn) {
    demoBtn.addEventListener("click", () => {
      runDemoAnalysis();
    });
  }

  // Generate README Button
  const genReadmeBtn = document.getElementById("btn-generate-readme");
  if (genReadmeBtn) {
    genReadmeBtn.addEventListener("click", function () {
      const repoJson = this.dataset.selectedRepo;
      if (!repoJson) return;
      try {
        const repo = JSON.parse(repoJson);
        generateReadme(repo);
      } catch (e) {
        console.error("Invalid repo JSON:", e);
      }
    });
  }

  // Copy README to Clipboard
  const copyBtn = document.getElementById("btn-copy-readme");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      const content = document.getElementById("readme-content").textContent;
      navigator.clipboard.writeText(content).then(() => {
        const originalHtml = this.innerHTML;
        this.innerHTML = "✅ Copied!";
        setTimeout(() => {
          this.innerHTML = originalHtml;
        }, 2000);
      });
    });
  }

  // Reset Button — Smoothly scroll back to top of landing page
  const resetBtn = document.getElementById("btn-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      document.getElementById("username-input").value = "";
      document.getElementById("landing-error").textContent = "";
      showScreen("screen-landing");
      window.scrollTo({ top: 0, behavior: "smooth" });
      document.getElementById("username-input").focus();
    });
  }
});
