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

  // Roast headline
  const headlineEl = document.getElementById("res-roast-headline");
  if (headlineEl) {
    headlineEl.textContent = roastData.roast_headline || "Your GitHub in a nutshell 😂";
  }

  // Roast core narrative
  document.getElementById("res-roast").textContent = roastData.roast || "No roast generated.";

  // What it means & The Fix
  const meaningEl = document.getElementById("res-roast-meaning");
  if (meaningEl) {
    meaningEl.textContent = roastData.what_it_means || "Visitors may not immediately understand your project portfolio.";
  }

  const fixEl = document.getElementById("res-roast-fix");
  if (fixEl) {
    fixEl.textContent = roastData.fix || "Add a quick README to your 3 best repositories.";
  }
  
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

  // Platform Selector Tabs (Phase 1)
  function setPlatform(platform) {
    document.querySelectorAll(".platform-tab").forEach(tab => {
      tab.classList.toggle("active", tab.dataset.platform === platform);
    });
    document.querySelectorAll(".platform-panel").forEach(panel => {
      panel.classList.toggle("active", panel.id === `panel-platform-${platform}`);
    });
  }

  const tabGithub = document.getElementById("tab-platform-github");
  const tabLinkedin = document.getElementById("tab-platform-linkedin");
  if (tabGithub) {
    tabGithub.addEventListener("click", () => setPlatform("github"));
  }
  if (tabLinkedin) {
    tabLinkedin.addEventListener("click", () => setPlatform("linkedin"));
  }

  // ---------------------------------------------------------------------------
  // PHASE 2: LINKEDIN CAREER INTENT ONBOARDING
  // ---------------------------------------------------------------------------
  const DOMAIN_ROLE_SUGGESTIONS = {
    "AI / Machine Learning": ["ML Engineer Intern", "Data Scientist Intern", "AI Research Assistant"],
    "Software Development": ["Full Stack Developer", "Backend Engineer Intern", "Frontend Engineer"],
    "Data Science": ["Data Analyst Intern", "Junior Data Scientist", "BI Specialist"],
    "Cybersecurity": ["Security Analyst Intern", "Junior SOC Analyst", "Penetration Tester"],
    "Cloud / DevOps": ["Cloud Solutions Intern", "DevOps Engineer Intern", "Site Reliability Engineer"],
    "UI/UX": ["UI/UX Designer Intern", "Product Design Intern", "Interaction Designer"],
    "Electronics / Embedded": ["Embedded Systems Intern", "Firmware Engineer", "IoT Developer"],
    "Research": ["Undergraduate Researcher", "Research Fellow", "Graduate Assistant"],
    "Entrepreneurship": ["Technical Co-Founder", "Product Builder", "Founding Engineer"],
    "Other": ["Software Specialist", "Junior Developer", "Technical Intern"]
  };

  const startLiBtn = document.getElementById("btn-start-linkedin");
  if (startLiBtn) {
    startLiBtn.addEventListener("click", () => {
      showScreen("screen-linkedin-intent");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  const backToLandingBtn = document.getElementById("btn-back-to-landing");
  if (backToLandingBtn) {
    backToLandingBtn.addEventListener("click", () => {
      showScreen("screen-landing");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // Helper for single-select pill groups
  function setupPillGroup(groupId, hiddenInputId, onSelect) {
    const group = document.getElementById(groupId);
    if (!group) return;
    const input = document.getElementById(hiddenInputId);
    group.querySelectorAll(".intent-pill").forEach(pill => {
      pill.addEventListener("click", function () {
        group.querySelectorAll(".intent-pill").forEach(p => p.classList.remove("active"));
        this.classList.add("active");
        if (input) input.value = this.dataset.val;
        if (onSelect) onSelect(this.dataset.val);
      });
    });
  }

  setupPillGroup("group-stage", "intent-stage");
  setupPillGroup("group-timeline", "intent-timeline");

  // Domain selection updates target role suggestions
  setupPillGroup("group-domain", "intent-domain", domain => {
    const suggestions = DOMAIN_ROLE_SUGGESTIONS[domain] || DOMAIN_ROLE_SUGGESTIONS["Other"];
    const container = document.getElementById("role-suggestions");
    if (container) {
      container.innerHTML = suggestions.map(s => `<span class="suggestion-tag">${escapeHtml(s)}</span>`).join("");
      bindSuggestionTags();
    }
  });

  // Multi-select goals
  const goalsGroup = document.getElementById("group-goals");
  if (goalsGroup) {
    goalsGroup.querySelectorAll(".multi-pill").forEach(pill => {
      pill.addEventListener("click", function () {
        const currentlyActive = goalsGroup.querySelectorAll(".multi-pill.active");
        if (this.classList.contains("active") && currentlyActive.length === 1) {
          return; // keep at least 1 goal active
        }
        this.classList.toggle("active");
      });
    });
  }

  // Suggestion tags helper
  function bindSuggestionTags() {
    document.querySelectorAll(".suggestion-tag").forEach(tag => {
      tag.addEventListener("click", function () {
        const roleInput = document.getElementById("intent-target-role");
        if (roleInput) {
          roleInput.value = this.textContent.trim();
          roleInput.focus();
        }
      });
    });
  }
  bindSuggestionTags();

  // Validate and Lock In Career Intent Form
  const saveIntentBtn = document.getElementById("btn-save-intent");
  if (saveIntentBtn) {
    saveIntentBtn.addEventListener("click", () => {
      const stageEl = document.getElementById("intent-stage");
      const domainEl = document.getElementById("intent-domain");
      const roleEl = document.getElementById("intent-target-role");
      const timelineEl = document.getElementById("intent-timeline");
      const errorEl = document.getElementById("intent-error");

      const stage = stageEl ? stageEl.value.trim() : "1st year";
      const domain = domainEl ? domainEl.value.trim() : "Software Development";
      const targetRole = roleEl ? roleEl.value.trim() : "";
      const goals = Array.from(document.querySelectorAll("#group-goals .multi-pill.active")).map(p => p.dataset.val);
      const timelineMonths = parseInt(timelineEl ? timelineEl.value : "6", 10) || 6;

      if (!targetRole || targetRole.length < 2) {
        if (errorEl) errorEl.textContent = "❌ Please specify your target role (e.g. ML Engineer Intern).";
        if (roleEl) roleEl.focus();
        return;
      }

      if (goals.length === 0) {
        if (errorEl) errorEl.textContent = "❌ Please select at least one goal (e.g. Internship, Placement).";
        return;
      }

      if (errorEl) errorEl.textContent = "";

      // Canonical Career Intent Object (global state)
      window.currentCareerIntent = {
        stage: stage,
        domain: domain,
        target_role: targetRole,
        goals: goals,
        timeline_months: timelineMonths
      };

      // Populate Confirmed Summary Card
      const sStage = document.getElementById("summary-stage");
      const sDomain = document.getElementById("summary-domain");
      const sRole = document.getElementById("summary-role");
      const sGoals = document.getElementById("summary-goals");
      const sTimeline = document.getElementById("summary-timeline");

      if (sStage) sStage.textContent = stage;
      if (sDomain) sDomain.textContent = domain;
      if (sRole) sRole.textContent = targetRole;
      if (sGoals) sGoals.textContent = goals.join(", ");
      if (sTimeline) sTimeline.textContent = `${timelineMonths} months`;

      const formCard = document.getElementById("intent-form-card");
      const confirmedCard = document.getElementById("intent-confirmed-card");

      if (formCard) formCard.classList.add("hidden");
      if (confirmedCard) {
        confirmedCard.classList.remove("hidden");
        smoothScrollTo("intent-confirmed-card");
      }
    });
  }

  // Edit Career Intent
  const editIntentBtn = document.getElementById("btn-edit-intent");
  if (editIntentBtn) {
    editIntentBtn.addEventListener("click", () => {
      const formCard = document.getElementById("intent-form-card");
      const confirmedCard = document.getElementById("intent-confirmed-card");
      if (confirmedCard) confirmedCard.classList.add("hidden");
      if (formCard) {
        formCard.classList.remove("hidden");
        smoothScrollTo("intent-form-card");
      }
    });
  }

  // ---------------------------------------------------------------------------
  // PHASE 3: LINKEDIN AUTHENTICATION PROOF OF CONCEPT
  // ---------------------------------------------------------------------------

  function renderLinkedinDebugScreen(profile) {
    if (!profile) return;

    // Identity Bar
    const avatarEl = document.getElementById("debug-avatar");
    const nameEl = document.getElementById("debug-name");
    const emailEl = document.getElementById("debug-email");

    if (avatarEl) {
      avatarEl.src = (profile.identity && profile.identity.photo)
        ? profile.identity.photo
        : "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&h=200&fit=crop&crop=faces";
    }
    if (nameEl) nameEl.textContent = (profile.identity && profile.identity.name) || "Anonymous Member";
    if (emailEl) emailEl.textContent = (profile.identity && profile.identity.email) || "No email in current scope";

    // Field Availability Table
    const tbody = document.getElementById("debug-fields-tbody");
    if (tbody) {
      const dataStatus = profile.data_status || {};
      const fieldsConfig = [
        { key: "name", label: "Full Name", val: (profile.identity && profile.identity.name) || "" },
        { key: "photo", label: "Profile Picture", val: (profile.identity && profile.identity.photo) ? "Image URL verified" : "" },
        { key: "email", label: "Email Address", val: (profile.identity && profile.identity.email) || "" },
        { key: "headline", label: "Headline", val: profile.headline || "" },
        { key: "about", label: "About / Summary", val: profile.about ? (profile.about.slice(0, 70) + "...") : "" },
        { key: "experience", label: "Work Experience", val: profile.experience && profile.experience.length ? `${profile.experience.length} entries` : "" },
        { key: "education", label: "Education History", val: profile.education && profile.education.length ? `${profile.education.length} entries` : "" },
        { key: "skills", label: "Skills & Endorsements", val: profile.skills && profile.skills.length ? `${profile.skills.length} skills` : "" },
        { key: "projects", label: "Projects Portfolio", val: profile.projects && profile.projects.length ? `${profile.projects.length} projects` : "" },
        { key: "certifications", label: "Certifications", val: profile.certifications && profile.certifications.length ? `${profile.certifications.length} credentials` : "" },
      ];

      tbody.innerHTML = fieldsConfig.map(f => {
        const status = dataStatus[f.key] || "not_authorized";
        let statusBadge = "";
        let noteText = f.val;

        if (status === "available") {
          statusBadge = '<span class="status-pill status-available">✓ available</span>';
          if (!noteText) noteText = "Retrieved via OpenID Connect";
        } else if (status === "user_provided") {
          statusBadge = '<span class="status-pill status-user-provided">📝 user_provided</span>';
          if (!noteText) noteText = "Supplied via profile import";
        } else if (status === "missing") {
          statusBadge = '<span class="status-pill status-missing">⚠️ missing</span>';
          noteText = "Field is empty on profile";
        } else {
          statusBadge = '<span class="status-pill status-restricted">🔒 not_authorized</span>';
          noteText = "Restricted on LinkedIn API tier";
        }

        return `<tr>
          <td><strong>${escapeHtml(f.label)}</strong></td>
          <td>${statusBadge}</td>
          <td><span style="font-family:var(--font-mono); font-size:0.78rem;">${escapeHtml(noteText)}</span></td>
        </tr>`;
      }).join("");
    }

    // Raw JSON Dump
    const rawJsonEl = document.getElementById("debug-raw-json");
    if (rawJsonEl) {
      rawJsonEl.textContent = JSON.stringify(profile, null, 2);
    }

    // Reveal debug screen
    const debugScreen = document.getElementById("auth-debug-screen");
    if (debugScreen) {
      debugScreen.classList.remove("hidden");
      setTimeout(() => smoothScrollTo("auth-debug-screen"), 100);
    }
  }

  // Connect via LinkedIn OAuth Button
  const oauthConnectBtn = document.getElementById("btn-oauth-connect");
  if (oauthConnectBtn) {
    oauthConnectBtn.addEventListener("click", () => {
      const statusEl = document.getElementById("oauth-status-msg");
      if (statusEl) {
        statusEl.textContent = "Checking LinkedIn OAuth configuration...";
        statusEl.style.color = "var(--text-dim)";
      }
      fetch("/api/linkedin/auth-url")
        .then(r => r.json())
        .then(res => {
          if (res.ok && res.configured && res.auth_url) {
            window.location.href = res.auth_url;
          } else {
            if (statusEl) {
              statusEl.innerHTML = `⚠️ <strong>OAuth Setup Note:</strong> ${escapeHtml(res.error || "LinkedIn OAuth credentials not yet added to .env.")}<br><span style="color:#38bdf8;">👉 Click 'Test Authorized Member Data' below to inspect the complete OpenID Connect payload immediately!</span>`;
              statusEl.style.color = "#fdba74";
            }
          }
        })
        .catch(err => {
          if (statusEl) {
            statusEl.textContent = "Error initiating OAuth: " + err.message;
            statusEl.style.color = "#f87171";
          }
        });
    });
  }

  // Test Authorized Member Data (POC Demo Connect)
  const demoConnectBtn = document.getElementById("btn-demo-connect");
  if (demoConnectBtn) {
    demoConnectBtn.addEventListener("click", () => {
      const statusEl = document.getElementById("oauth-status-msg");
      if (statusEl) {
        statusEl.textContent = "Loading authorized OpenID Connect member data...";
        statusEl.style.color = "var(--text-dim)";
      }
      fetch("/api/linkedin/demo")
        .then(r => r.json())
        .then(res => {
          if (res.ok && res.data && res.data.profile) {
            if (statusEl) {
              statusEl.textContent = "✅ Authorized member data loaded into Proof of Concept debugger.";
              statusEl.style.color = "#3fb950";
            }
            renderLinkedinDebugScreen(res.data.profile);
          }
        })
        .catch(err => {
          if (statusEl) {
            statusEl.textContent = "Error loading sample member: " + err.message;
            statusEl.style.color = "#f87171";
          }
        });
    });
  }

  // Toggle Raw JSON
  const toggleJsonBtn = document.getElementById("btn-toggle-json");
  if (toggleJsonBtn) {
    toggleJsonBtn.addEventListener("click", () => {
      const rawJsonEl = document.getElementById("debug-raw-json");
      if (rawJsonEl) {
        const isHidden = rawJsonEl.classList.toggle("hidden");
        toggleJsonBtn.textContent = isHidden
          ? "{ } View Raw Normalized Profile JSON ▾"
          : "{ } Hide Raw Normalized Profile JSON ▴";
      }
    });
  }

  // Inspect URL parameters for OAuth redirect on page load
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("linkedin_auth") === "success") {
    setPlatform("linkedin");
    showScreen("screen-linkedin-intent");
    const formCard = document.getElementById("intent-form-card");
    const confirmedCard = document.getElementById("intent-confirmed-card");
    if (formCard) formCard.classList.add("hidden");
    if (confirmedCard) confirmedCard.classList.remove("hidden");

    fetch("/api/linkedin/me")
      .then(r => r.json())
      .then(res => {
        if (res.ok && res.profile) {
          const statusEl = document.getElementById("oauth-status-msg");
          if (statusEl) {
            statusEl.textContent = "✅ Official LinkedIn authorization successful! OpenID Connect payload retrieved.";
            statusEl.style.color = "#3fb950";
          }
          renderLinkedinDebugScreen(res.profile);
        }
      });
  } else if (urlParams.get("linkedin_error")) {
    setPlatform("linkedin");
    showScreen("screen-linkedin-intent");
    const errorMsg = urlParams.get("msg") || urlParams.get("linkedin_error");
    const statusEl = document.getElementById("oauth-status-msg");
    if (statusEl) {
      statusEl.textContent = `❌ LinkedIn OAuth Error: ${errorMsg}`;
      statusEl.style.color = "#f87171";
    }
  }

  // ---------------------------------------------------------------------------
  // PHASE 4: PROFILE DATA IMPORT FALLBACK (PATH B)
  // ---------------------------------------------------------------------------
  const toggleImportBtn = document.getElementById("btn-toggle-import-form");
  if (toggleImportBtn) {
    toggleImportBtn.addEventListener("click", () => {
      const formWrap = document.getElementById("import-form-wrapper");
      if (formWrap) {
        const isHidden = formWrap.classList.toggle("hidden");
        toggleImportBtn.textContent = isHidden
          ? "📝 Open / Edit Manual Input Form ▾"
          : "📝 Hide Manual Input Form ▴";
      }
    });
  }

  // Pre-fill button
  const prefillBtn = document.getElementById("btn-prefill-import");
  if (prefillBtn) {
    prefillBtn.addEventListener("click", () => {
      const headlineInput = document.getElementById("import-headline");
      const aboutInput = document.getElementById("import-about");
      const skillsInput = document.getElementById("import-skills");
      const projectsInput = document.getElementById("import-projects");
      const formWrap = document.getElementById("import-form-wrapper");

      if (headlineInput) headlineInput.value = "Computer Science Student | Exploring Tech & Coding | Aspiring Developer";
      if (aboutInput) aboutInput.value = "Passionate computer science student who loves solving problems and learning new technologies. Looking forward to exciting internship opportunities in software and machine learning.";
      if (skillsInput) skillsInput.value = "Python, Java, C++, HTML/CSS, JavaScript, SQL, Git";
      if (projectsInput) projectsInput.value = "Student Task Management App: Built a responsive web dashboard for students to organize assignments (JavaScript, HTML, CSS, Node.js)\nBasic Sales Data Analyzer: Wrote Python scripts to clean retail sales CSVs and generate statistical summary reports (Python, pandas, matplotlib)";

      if (formWrap) formWrap.classList.remove("hidden");
      if (toggleImportBtn) toggleImportBtn.textContent = "📝 Hide Manual Input Form ▴";

      const statusEl = document.getElementById("import-save-status");
      if (statusEl) {
        statusEl.textContent = "✨ Realistic sample fields loaded. Click 'Save User-Provided Profile Data' below.";
        statusEl.style.color = "#38bdf8";
      }
    });
  }

  // Save imported profile data
  const saveImportBtn = document.getElementById("btn-save-import");
  if (saveImportBtn) {
    saveImportBtn.addEventListener("click", () => {
      const headline = document.getElementById("import-headline").value.trim();
      const about = document.getElementById("import-about").value.trim();
      const skills = document.getElementById("import-skills").value.trim();
      const rawProjects = document.getElementById("import-projects").value.trim();
      const statusEl = document.getElementById("import-save-status");

      // Parse projects lines
      const projects = [];
      if (rawProjects) {
        rawProjects.split("\n").forEach(line => {
          const parts = line.split(":");
          if (parts.length >= 2) {
            projects.push({
              title: parts[0].trim(),
              description: parts.slice(1).join(":").trim(),
              technologies: []
            });
          } else if (line.trim()) {
            projects.push({
              title: line.trim(),
              description: "Custom user-provided project description",
              technologies: []
            });
          }
        });
      }

      const importPayload = {
        profile: {
          headline: headline,
          about: about,
          skills: skills,
          projects: projects
        },
        intent: window.currentCareerIntent || {}
      };

      if (statusEl) {
        statusEl.textContent = "Saving and normalizing profile data...";
        statusEl.style.color = "var(--text-dim)";
      }

      fetch("/api/linkedin/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(importPayload)
      })
        .then(r => r.json())
        .then(res => {
          if (res.ok && res.data && res.data.profile) {
            window.currentNormalizedProfile = res.data.profile;
            if (statusEl) {
              statusEl.textContent = "✅ Profile data imported and validated! Audit table updated.";
              statusEl.style.color = "#3fb950";
            }
            renderLinkedinDebugScreen(res.data.profile);
          } else {
            if (statusEl) {
              statusEl.textContent = "❌ Import error: " + (res.error || "Failed to process profile data.");
              statusEl.style.color = "#f87171";
            }
          }
        })
        .catch(err => {
          if (statusEl) {
            statusEl.textContent = "Error saving profile data: " + err.message;
            statusEl.style.color = "#f87171";
          }
        });
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
