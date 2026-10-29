const API_BASE = "";

// State
let jobs = [];
let pendingApps = [];
let pendingPillarActions = [];
let allApps = [];

// DOM Elements
const pendingBadge = document.getElementById("pending-badge");
const pendingList = document.getElementById("pending-list");
const allAppsList = document.getElementById("all-apps-list");
const jobsList = document.getElementById("jobs-list");
const selectJob = document.getElementById("select-job");
const screenForm = document.getElementById("screen-form");
const jobForm = document.getElementById("job-form");
const btnToggleNewJob = document.getElementById("btn-toggle-new-job");
const newJobFormWrapper = document.getElementById("new-job-form-wrapper");

// Modal
const modal = document.getElementById("decision-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");
const modalCandidateName = document.getElementById("modal-candidate-name");
const modalBodyContent = document.getElementById("modal-body-content");

// Init
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadJobs();
  loadPendingApprovals();
  loadAllApplications();
  setupForms();
});

// Tab Switching
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");

      if (targetId === "approvals-tab") loadPendingApprovals();
      if (targetId === "history-tab") loadAllApplications();
      if (targetId === "jobs-tab") loadJobs();
      if (targetId === "analytics-tab") loadAnalytics();
    });
  });

  modalCloseBtn.addEventListener("click", () => modal.classList.add("hidden"));
  modal.querySelector(".modal-overlay").addEventListener("click", () => modal.classList.add("hidden"));

  btnToggleNewJob.addEventListener("click", () => {
    newJobFormWrapper.classList.toggle("hidden");
  });
}

// Fetch & Render Jobs
async function loadJobs() {
  try {
    const res = await fetch(`${API_BASE}/api/hiring/jobs`);
    jobs = await res.json();

    // Populate Select dropdown
    selectJob.innerHTML = '<option value="">Select a job requisition...</option>';
    jobs.forEach((job) => {
      const opt = document.createElement("option");
      opt.value = job.id;
      opt.textContent = `[${job.req_id}] ${job.title} (${job.location || "Remote"})`;
      selectJob.appendChild(opt);
    });

    // Populate Job cards
    if (jobs.length === 0) {
      jobsList.innerHTML = `<div class="loading-state">No job requisitions found. Create one above!</div>`;
      return;
    }

    jobsList.innerHTML = jobs
      .map(
        (j) => `
      <div class="card">
        <div class="cand-meta">REQ ID: ${escapeHtml(j.req_id)}</div>
        <h3 style="margin: 6px 0 10px;">${escapeHtml(j.title)}</h3>
        <p class="cand-meta">📍 ${escapeHtml(j.location || "Not specified")} | 🏢 ${escapeHtml(j.department || "General")}</p>
        <p style="font-size: 13.5px; color: #475569; line-height: 1.5; margin-top: 10px; max-height: 80px; overflow: hidden; text-overflow: ellipsis;">
          ${escapeHtml(j.description)}
        </p>
      </div>
    `
      )
      .join("");
  } catch (err) {
    console.error("Error loading jobs:", err);
  }
}

// Fetch & Render Pending Approvals (All 7 Pillars)
async function loadPendingApprovals() {
  try {
    const [resApps, resActions] = await Promise.all([
      fetch(`${API_BASE}/api/approvals/pending`),
      fetch(`${API_BASE}/api/v1/approvals/pending`)
    ]);

    pendingApps = await resApps.json();
    const allActions = await resActions.json();
    
    // Filter out actions that are already shown as hiring applications to prevent duplicate cards
    pendingPillarActions = allActions.filter((act) => act.module_name !== "HIRING");

    const totalPending = pendingApps.length + pendingPillarActions.length;
    pendingBadge.textContent = totalPending;

    if (totalPending === 0) {
      pendingList.innerHTML = `<div class="loading-state">🎉 All caught up! No candidate or operational actions pending approval.</div>`;
      return;
    }

    const appCards = pendingApps.map((app) => renderApplicationCard(app, true)).join("");
    const pillarCards = pendingPillarActions.map((act) => renderPillarActionCard(act)).join("");

    pendingList.innerHTML = appCards + pillarCards;

    attachReviewListeners();
    attachPillarReviewListeners();
  } catch (err) {
    console.error("Error loading pending approvals:", err);
  }
}

// Render General Pillar Action Card (Onboarding, Payroll, Helpdesk, etc.)
function renderPillarActionCard(act) {
  const payloadStr = typeof act.payload === "object" ? JSON.stringify(act.payload, null, 2) : String(act.payload);
  const title = act.payload.event_title || act.payload.employee_name || act.payload.cycle_period || act.entity_reference_id || act.action_type;

  return `
    <div class="app-card" data-action-id="${act.id}">
      <div>
        <div class="app-card-header">
          <div>
            <div class="cand-title">${escapeHtml(title)}</div>
            <div class="cand-meta">Module: <strong>${escapeHtml(act.module_name)}</strong></div>
            <div class="cand-meta">Action: <code>${escapeHtml(act.action_type)}</code></div>
          </div>
          <span class="status-tag status-PENDING_APPROVAL">Pending Sign-off</span>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; margin: 12px 0; max-height: 110px; overflow-y: auto;">
          <pre style="font-size: 11.5px; color: #334155; font-family: monospace; white-space: pre-wrap;">${escapeHtml(payloadStr)}</pre>
        </div>
      </div>

      <div style="margin-top: 14px;">
        <button class="btn btn-primary btn-pillar-review" data-action-id="${act.id}" style="width: 100%;">
          <span>🔍 Review Payload & Authorize</span>
        </button>
      </div>
    </div>
  `;
}

function attachPillarReviewListeners() {
  document.querySelectorAll(".btn-pillar-review").forEach((btn) => {
    btn.addEventListener("click", () => {
      const actId = parseInt(btn.getAttribute("data-action-id"));
      const act = pendingPillarActions.find((a) => a.id === actId);
      if (act) openPillarReviewModal(act);
    });
  });
}

function openPillarReviewModal(act) {
  modalCandidateName.textContent = `${act.module_name}: ${act.action_type} — HITL Sign-off`;
  const payloadFormatted = typeof act.payload === "object" ? JSON.stringify(act.payload, null, 2) : act.payload;

  modalBodyContent.innerHTML = `
    <div style="margin-bottom: 16px;">
      <p style="font-size: 13.5px; color: #475569;">Module: <strong style="color: #4f46e5;">${act.module_name}</strong> | Reference: <strong>${escapeHtml(act.entity_reference_id || "None")}</strong></p>
    </div>

    <div style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <label for="modal-pillar-payload" style="color: #0f172a; font-weight: 600;">Staged Payload JSON / Text</label>
        <span style="font-size: 11.5px; color: #64748b;">(Editable before authorizing)</span>
      </div>
      <textarea id="modal-pillar-payload" rows="10" style="width: 100%; font-family: monospace; font-size: 12.5px; background: #ffffff; color: #0f172a; border: 1.5px solid #cbd5e1;">${escapeHtml(payloadFormatted)}</textarea>
    </div>

    <div class="form-row">
      <div class="form-group half">
        <label for="modal-pillar-reviewer" style="color: #0f172a; font-weight: 600;">Reviewer Identifier *</label>
        <input type="text" id="modal-pillar-reviewer" value="HR_Department_Lead" required />
      </div>
      <div class="form-group half">
        <label for="modal-pillar-notes" style="color: #0f172a; font-weight: 600;">Decision Notes</label>
        <input type="text" id="modal-pillar-notes" placeholder="e.g. Verified calculations, approved for release." />
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; border-top: 1.5px solid #e2e8f0; padding-top: 16px;">
      <button class="btn btn-reject" id="btn-pillar-modal-reject">
        <span>❌ Reject & Archive</span>
      </button>
      <button class="btn btn-approve" id="btn-pillar-modal-approve">
        <span>✅ Authorize & Commit</span>
      </button>
    </div>
  `;

  modal.classList.remove("hidden");

  document.getElementById("btn-pillar-modal-approve").addEventListener("click", () => submitPillarDecision(act.id, "APPROVE"));
  document.getElementById("btn-pillar-modal-reject").addEventListener("click", () => submitPillarDecision(act.id, "REJECT"));
}

async function submitPillarDecision(actId, decision) {
  const reviewer = document.getElementById("modal-pillar-reviewer").value.trim() || "HR_Reviewer";
  const notes = document.getElementById("modal-pillar-notes").value.trim();
  const rawEdited = document.getElementById("modal-pillar-payload").value;

  let parsedPayload = rawEdited;
  try {
    parsedPayload = JSON.parse(rawEdited);
  } catch (e) {
    // Keep as string if not JSON
  }

  try {
    const res = await fetch(`${API_BASE}/api/v1/approvals/decide/${actId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: decision,
        reviewer_id: reviewer,
        notes: notes,
        edited_payload: parsedPayload
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Decision Failed: ${err.detail || "Server error"}`);
      return;
    }

    if (decision === "APPROVE") {
      await fetch(`${API_BASE}/api/v1/approvals/execute/${actId}`, {
        method: "POST"
      });
    }

    modal.classList.add("hidden");
    await loadPendingApprovals();
    alert(`Success: Action marked as ${decision} and recorded in immutable audit log.`);
  } catch (err) {
    console.error("Pillar decision error:", err);
    alert("Connection error recording decision.");
  }
}

// Fetch & Render All Applications
async function loadAllApplications() {
  try {
    const res = await fetch(`${API_BASE}/api/hiring/applications`);
    allApps = await res.json();

    if (allApps.length === 0) {
      allAppsList.innerHTML = `<div class="loading-state">No applications evaluated yet.</div>`;
      return;
    }

    allAppsList.innerHTML = allApps
      .map((app) => renderApplicationCard(app, false))
      .join("");

    attachAuditListeners();
  } catch (err) {
    console.error("Error loading all applications:", err);
  }
}

// Render Card HTML
function renderApplicationCard(app, isPendingView) {
  const sc = app.scorecard;
  const score = sc ? sc.overall_score : "N/A";
  const rec = sc ? sc.recommendation : "Pending";
  const pendingAction = app.staged_actions.find((a) => a.status === "PENDING_APPROVAL") || app.staged_actions[0];

  return `
    <div class="app-card" data-app-id="${app.id}">
      <div>
        <div class="app-card-header">
          <div>
            <div class="cand-title">${escapeHtml(app.candidate.name)}</div>
            <div class="cand-meta">For: <strong>${escapeHtml(app.job.title)}</strong></div>
            <div class="cand-meta">📍 ${escapeHtml(app.candidate.location || "Unknown")} | 🎓 ${escapeHtml(app.candidate.education || "Unspecified")}</div>
          </div>
          <span class="status-tag status-${app.status}">${app.status.replace("_", " ")}</span>
        </div>

        <div class="score-badge">
          <span class="score-num">${score}</span>
          <span style="font-size: 13.5px; color: #64748b; font-weight: 500;">/100</span>
          <span class="score-rec">${rec}</span>
        </div>

        ${
          sc && sc.strengths && sc.strengths.length > 0
            ? `<div style="font-size: 12.5px; color: #059669; font-weight: 600; margin-bottom: 8px;">✓ ${escapeHtml(sc.strengths[0])}</div>`
            : ""
        }

        ${
          pendingAction
            ? `<div style="font-size: 12.5px; color: #d97706; font-weight: 600; margin-bottom: 12px;">⚠️ Staged: <strong>${pendingAction.action_type}</strong></div>`
            : ""
        }
      </div>

      <div style="display: flex; gap: 8px; margin-top: 14px;">
        ${
          isPendingView
            ? `<button class="btn btn-primary btn-review" data-app-id="${app.id}" style="width: 100%;">
                <span>🔍 Review Scorecard & Decide</span>
               </button>`
            : `<button class="btn btn-secondary btn-audit" data-app-id="${app.id}" style="width: 100%;">
                <span>📜 View Audit Trail (${app.audit_logs.length})</span>
               </button>`
        }
      </div>
    </div>
  `;
}

// Review Button Click Handlers
function attachReviewListeners() {
  document.querySelectorAll(".btn-review").forEach((btn) => {
    btn.addEventListener("click", () => {
      const appId = parseInt(btn.getAttribute("data-app-id"));
      const app = pendingApps.find((a) => a.id === appId);
      if (app) openReviewModal(app);
    });
  });
}

function attachAuditListeners() {
  document.querySelectorAll(".btn-audit").forEach((btn) => {
    btn.addEventListener("click", () => {
      const appId = parseInt(btn.getAttribute("data-app-id"));
      const app = allApps.find((a) => a.id === appId);
      if (app) openAuditModal(app);
    });
  });
}

// Open Review Modal
function openReviewModal(app) {
  modalCandidateName.textContent = `${app.candidate.name} — Review & HITL Decision`;
  const sc = app.scorecard || {};
  const action = app.staged_actions.find((a) => a.status === "PENDING_APPROVAL") || app.staged_actions[0];

  const breakdownHtml = sc.category_scores
    ? Object.entries(sc.category_scores)
        .map(
          ([k, v]) => `
      <div style="display: flex; justify-content: space-between; font-size: 12px; margin: 4px 0;">
        <span style="color: #9ca3af; text-transform: capitalize;">${k.replace("_", " ")}</span>
        <strong>${v}%</strong>
      </div>
    `
        )
        .join("")
    : "";

  modalBodyContent.innerHTML = `
    <div style="display: flex; gap: 16px; margin-bottom: 20px;">
      <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 12px;">
        <h4 style="margin-bottom: 12px; font-size: 14px; font-weight: 700; color: #0f172a;">Scorecard Breakdown (${sc.overall_score}/100)</h4>
        ${breakdownHtml}
      </div>
      <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 18px; border-radius: 12px;">
        <h4 style="margin-bottom: 12px; font-size: 14px; font-weight: 700; color: #0f172a;">Key Strengths & Gaps</h4>
        <ul style="font-size: 12.5px; padding-left: 16px; color: #059669; font-weight: 500; margin-bottom: 8px; line-height: 1.5;">
          ${(sc.strengths || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("")}
        </ul>
        <ul style="font-size: 12.5px; padding-left: 16px; color: #d97706; font-weight: 500; line-height: 1.5;">
          ${(sc.gaps || []).map((g) => `<li>${escapeHtml(g)}</li>`).join("")}
        </ul>
      </div>
    </div>

    ${
      sc.interview_questions && sc.interview_questions.length > 0
        ? `
        <div style="background: #eef2ff; border: 1px solid #c7d2fe; padding: 16px; border-radius: 12px; margin-bottom: 20px;">
          <h4 style="font-size: 13.5px; font-weight: 700; margin-bottom: 10px; color: #4338ca;">💡 Recommended Interview Questions:</h4>
          <ol style="font-size: 13px; color: #1e293b; padding-left: 20px; line-height: 1.6;">
            ${sc.interview_questions.map((q) => `<li>${escapeHtml(q)}</li>`).join("")}
          </ol>
        </div>
      `
        : ""
    }

    <div style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <label for="modal-payload-edit" style="color: #0f172a; font-weight: 600;">Staged Outreach Payload [Status: PENDING_APPROVAL]</label>
        <span style="font-size: 11.5px; color: #64748b;">(Editable before sign-off)</span>
      </div>
      <textarea id="modal-payload-edit" rows="8" style="width: 100%; font-family: monospace; font-size: 13px; background: #ffffff; color: #0f172a; border: 1.5px solid #cbd5e1;">${escapeHtml(
        typeof (action ? action.payload : "") === "object"
          ? JSON.stringify(action.payload, null, 2)
          : (action ? action.payload : "")
      )}</textarea>
    </div>

    <div class="form-row">
      <div class="form-group half">
        <label for="modal-reviewer" style="color: #0f172a; font-weight: 600;">Reviewer Name / Title *</label>
        <input type="text" id="modal-reviewer" value="Talent Acquisition Lead" required />
      </div>
      <div class="form-group half">
        <label for="modal-notes" style="color: #0f172a; font-weight: 600;">Decision Notes</label>
        <input type="text" id="modal-notes" placeholder="e.g. Strong automation background; approved for interview" />
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px; border-top: 1.5px solid #e2e8f0; padding-top: 16px;">
      <button class="btn btn-reject" id="btn-modal-reject">
        <span>❌ Reject Candidate</span>
      </button>
      <button class="btn btn-approve" id="btn-modal-approve">
        <span>✅ Approve & Authorize Dispatch</span>
      </button>
    </div>
  `;

  modal.classList.remove("hidden");

  // Hook decisions
  document.getElementById("btn-modal-approve").addEventListener("click", () => submitDecision(app.id, "APPROVE"));
  document.getElementById("btn-modal-reject").addEventListener("click", () => submitDecision(app.id, "REJECT"));
}

// Open Audit Modal
function openAuditModal(app) {
  modalCandidateName.textContent = `${app.candidate.name} — Immutable Audit Trail`;

  const logsHtml = app.audit_logs
    .map(
      (log) => `
    <li class="audit-item">
      <div class="audit-meta">
        <strong>${escapeHtml(log.actor)}</strong> • ${new Date(log.timestamp).toLocaleString()}
      </div>
      <div class="audit-desc">
        State transition: <code>${escapeHtml(log.from_status)}</code> ➔ <code>${escapeHtml(log.to_status)}</code>
      </div>
      ${log.notes ? `<div style="font-size: 12px; color: #9ca3af; margin-top: 2px;">Notes: "${escapeHtml(log.notes)}"</div>` : ""}
    </li>
  `
    )
    .join("");

  modalBodyContent.innerHTML = `
    <div style="margin-bottom: 20px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 12px;">
      <p style="font-size: 13.5px; color: #475569; margin-bottom: 4px;">Candidate: <strong style="color: #0f172a;">${escapeHtml(app.candidate.name)}</strong> (${app.candidate.email || "No email"})</p>
      <p style="font-size: 13.5px; color: #475569; margin-bottom: 6px;">Requisition: <strong style="color: #0f172a;">${escapeHtml(app.job.title)}</strong> [${app.job.req_id}]</p>
      <p style="font-size: 13.5px; color: #475569;">Current Status: <strong class="status-tag status-${app.status}">${app.status}</strong></p>
    </div>
    <h4 style="margin-bottom: 14px; font-size: 14.5px; font-weight: 700; color: #0f172a;">Audit History Timeline</h4>
    <ul class="audit-list">
      ${logsHtml}
    </ul>
  `;

  modal.classList.remove("hidden");
}

// Submit Decision to Backend
async function submitDecision(appId, decision) {
  const reviewer = document.getElementById("modal-reviewer").value.trim() || "HR Reviewer";
  const notes = document.getElementById("modal-notes").value.trim();
  const editedPayload = document.getElementById("modal-payload-edit").value;

  try {
    // 1. Submit approval/rejection
    const res = await fetch(`${API_BASE}/api/approvals/decide/${appId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision: decision,
        reviewer_name: reviewer,
        notes: notes,
        edited_payload: editedPayload
      })
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Error: ${err.detail || "Failed to submit decision"}`);
      return;
    }

    // 2. If approved, trigger dispatch execution
    if (decision === "APPROVE") {
      await fetch(`${API_BASE}/api/approvals/execute/${appId}`, {
        method: "POST"
      });
    }

    modal.classList.add("hidden");
    await loadPendingApprovals();
    await loadAllApplications();
    alert(`Success: Candidate application marked as ${decision}.`);
  } catch (err) {
    console.error("Error submitting decision:", err);
    alert("Connection error. Could not record decision.");
  }
}

// Setup Forms (Screen & New Job)
function setupForms() {
  // Screen candidate form (Text or File Upload)
  screenForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-screen");
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ Evaluating Resume & Scoring...</span>";

    const fileInput = document.getElementById("cand-file");
    const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
    const jobId = parseInt(selectJob.value);
    const candName = document.getElementById("cand-name").value.trim();
    const candEmail = document.getElementById("cand-email").value.trim();
    const candPhone = "";
    const rawResumeText = document.getElementById("cand-resume").value.trim();

    try {
      let res;
      if (hasFile) {
        const formData = new FormData();
        formData.append("job_id", jobId);
        formData.append("candidate_name", candName);
        if (candEmail) formData.append("candidate_email", candEmail);
        formData.append("file", fileInput.files[0]);

        res = await fetch(`${API_BASE}/api/v1/hiring/upload-resume`, {
          method: "POST",
          body: formData
        });
      } else {
        if (!rawResumeText) {
          alert("Please upload a resume file (.pdf, .docx, .txt) or paste resume text.");
          btn.disabled = false;
          btn.innerHTML = "<span>⚡ Run AI Evaluation & Stage Draft</span>";
          return;
        }

        res = await fetch(`${API_BASE}/api/v1/hiring/screen`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            job_id: jobId,
            candidate_name: candName,
            candidate_email: candEmail,
            candidate_phone: candPhone,
            raw_resume_text: rawResumeText
          })
        });
      }

      if (!res.ok) {
        const err = await res.json();
        alert(`Error: ${err.detail || "Screening failed"}`);
        return;
      }

      screenForm.reset();
      alert("✅ Screening Complete! Result staged under 'Pending Approvals' with status PENDING_APPROVAL.");
      document.querySelector('[data-tab="approvals-tab"]').click();
    } catch (err) {
      console.error("Screening error:", err);
      alert("Network error while screening candidate.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "<span>⚡ Run AI Evaluation & Stage Draft</span>";
    }
  });

  // HRMS Webhook Simulator
  const btnSimulateWebhook = document.getElementById("btn-simulate-webhook");
  if (btnSimulateWebhook) {
    btnSimulateWebhook.addEventListener("click", async () => {
      btnSimulateWebhook.disabled = true;
      btnSimulateWebhook.innerHTML = "<span>⏳ Ingesting Live Webhook Payload...</span>";

      const source = document.getElementById("sim-source").value;
      const candidateKey = document.getElementById("sim-candidate").value;

      const candidates = {
        elena: {
          name: "Elena Rostova",
          email: "elena.rostova@example.com",
          text: `Elena Rostova | Berlin, Germany
Senior Python Automation & Backend Engineer. 5+ years experience building automated ETL pipelines,
Docker microservices, and AI workflow integrations. Designed OCR document parsers reducing manual data entry by 70%.
Skills: Python, FastAPI, Django, PostgreSQL, Pandas, NumPy, Machine Learning, Docker, CI/CD.
Education: MSc Software Systems (TU Berlin). Languages: English Fluent, German B2.`
        },
        marcus: {
          name: "Marcus Weber",
          email: "marcus.weber@example.com",
          text: `Marcus Weber | Brandenburg, Germany
Business Analyst with 2 years experience using Excel, PowerBI, and basic Python scripts for descriptive statistics.
Interested in AI tools and factory operations. English C1, German Native.`
        },
        sophia: {
          name: "Sophia Müller",
          email: "sophia.mueller@example.com",
          text: `Sophia Müller | Frankfurt, Germany
Senior Certified Public Accountant (CPA) with 9 years experience in financial tax audits, QuickBooks, and payroll ledger balancing.
Experienced in corporate accounting compliance.`
        }
      };

      const selected = candidates[candidateKey] || candidates.elena;

      try {
        const res = await fetch(`${API_BASE}/api/v1/integrations/webhook/simulate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_hrms: source,
            external_event_id: `EVT-${Date.now()}`,
            target_req_code: "285983",
            candidate_name: selected.name,
            candidate_email: selected.email,
            raw_resume_text: selected.text
          })
        });

        if (!res.ok) {
          const err = await res.json();
          alert(`Webhook Ingestion Failed: ${err.detail || "Server error"}`);
          return;
        }

        const data = await res.json();
        alert(`⚡ [Live Webhook Ingested]: Received application for ${data.candidate_name} from ${data.source_hrms}! ML Match Score: ${data.score}/100 (${data.recommendation}). Staged in HITL Queue.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Webhook simulation error:", err);
        alert("Failed to connect to webhook ingestion service.");
      } finally {
        btnSimulateWebhook.disabled = false;
        btnSimulateWebhook.innerHTML = "<span>⚡ Trigger Inbound HRMS Webhook</span>";
      }
    });
  }

  // Create job requisition form
  jobForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      req_id: document.getElementById("job-req").value.trim(),
      title: document.getElementById("job-title").value.trim(),
      department: document.getElementById("job-dept").value.trim(),
      location: document.getElementById("job-loc").value.trim(),
      description: document.getElementById("job-desc").value.trim()
    };

    try {
      const res = await fetch(`${API_BASE}/api/hiring/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        alert("Failed to save job requisition.");
        return;
      }

      jobForm.reset();
      newJobFormWrapper.classList.add("hidden");
      await loadJobs();
      alert("Job Requisition created successfully!");
    } catch (err) {
      console.error("Job creation error:", err);
    }
  });

  // Pillar 2: Onboarding Form
  const onbForm = document.getElementById("onboarding-form");
  if (onbForm) {
    onbForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(`${API_BASE}/api/v1/onboarding/generate-checklist`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            employee_name: document.getElementById("onb-name").value.trim(),
            role_title: document.getElementById("onb-role").value.trim(),
            department: document.getElementById("onb-dept").value,
            start_date: new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0],
            salary_offered: parseFloat(document.getElementById("onb-salary").value) || 75000
          })
        });
        const data = await res.json();
        alert(`✅ Onboarding checklist & contract generated for ${data.employee}! Staged for manager review.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Onboarding error:", err);
        alert("Failed to stage onboarding package.");
      }
    });
  }

  // Pillar 3: Helpdesk Form
  const helpForm = document.getElementById("helpdesk-form");
  if (helpForm) {
    helpForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(`${API_BASE}/api/v1/helpdesk/query`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            employee_name: document.getElementById("help-name").value.trim(),
            query_text: document.getElementById("help-query").value.trim(),
            category: "BENEFITS_PTO"
          })
        });
        const data = await res.json();
        alert(`🔍 Policy RAG evaluated query! Response drafted and staged for HR sign-off.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Helpdesk error:", err);
        alert("Failed to submit ticket.");
      }
    });
  }

  // Pillar 4: Attendance Form
  const attForm = document.getElementById("attendance-form");
  if (attForm) {
    attForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rawHours = document.getElementById("att-hours").value.split(",").map((s) => parseFloat(s.trim()) || 8.0);
      try {
        const res = await fetch(`${API_BASE}/api/v1/attendance/audit-timesheet`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            employee_id: "EMP-882",
            employee_name: document.getElementById("att-name").value.trim(),
            week_start: new Date().toISOString().split("T")[0],
            logged_hours: rawHours
          })
        });
        const data = await res.json();
        const flags = data.audit_summary.anomalies_detected.length;
        alert(`⚠️ Attendance audit complete! ${flags} anomalies flagged. Staged in Manager Review Hub.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Attendance audit error:", err);
        alert("Failed to run attendance audit.");
      }
    });
  }

  // Pillar 5: Payroll Form
  const payForm = document.getElementById("payroll-form");
  if (payForm) {
    payForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(`${API_BASE}/api/v1/payroll/pre-audit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            cycle_period: document.getElementById("pay-cycle").value.trim(),
            records: [
              { employee_id: "EMP-001", base_salary: 6500.0, bonus: 500.0, deductions: 1200.0 },
              { employee_id: "EMP-002", base_salary: 5800.0, bonus: 0.0, deductions: 1050.0 },
              { employee_id: "EMP-003", base_salary: 7200.0, bonus: 1000.0, deductions: 1400.0 }
            ]
          })
        });
        const data = await res.json();
        const formattedTotal = Number(data.payroll_summary.total_net_disbursement).toLocaleString('de-DE', {minimumFractionDigits: 2});
        alert(`🔒 Payroll cycle pre-audited! Net disbursement €${formattedTotal} staged awaiting Finance sign-off.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Payroll error:", err);
        alert("Failed to stage payroll pre-audit.");
      }
    });
  }

  // Pillar 6: Event Form
  const evtForm = document.getElementById("event-form");
  if (evtForm) {
    evtForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch(`${API_BASE}/api/v1/events/plan-offsite`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            event_title: document.getElementById("evt-title").value.trim(),
            target_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
            location: "Berlin / Brandenburg Tech Park",
            headcount: parseInt(document.getElementById("evt-headcount").value) || 40,
            budget_per_head: parseFloat(document.getElementById("evt-budget").value) || 150,
            agenda_highlights: ["H2 Strategy Review", "AI Coding Agents Workshop", "Dinner & Networking"]
          })
        });
        const data = await res.json();
        alert(`🎉 Offsite plan & calendar invite created! Staged for organizer review.`);
        document.querySelector('[data-tab="approvals-tab"]').click();
      } catch (err) {
        console.error("Event planning error:", err);
        alert("Failed to stage offsite plan.");
      }
    });
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Fetch & Render Workforce Analytics
async function loadAnalytics() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/summary`);
    const data = await res.json();
    document.getElementById("analytics-narrative").textContent = data.executive_narrative || "No narrative available.";
    if (data.kpis) {
      document.getElementById("kpi-jobs").textContent = data.kpis.total_open_requisitions;
      document.getElementById("kpi-candidates").textContent = data.kpis.total_candidates_screened;
      document.getElementById("kpi-pending").textContent = data.kpis.hitl_pending_reviews;
      document.getElementById("kpi-executed").textContent = data.kpis.hitl_executed_actions;
    }
  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}
