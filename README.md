# 🤖 Michelle HR — Enterprise AI HR Agent

Michelle is an All-in-One AI HR Agent built with a strict **Human-in-the-Loop (HITL) Draft-Review-Commit state machine** and immutable audit trail.

---

## 🌟 Architecture & Features

### 1. Web App First, Desktop Application Ready
- **Backend:** FastAPI + SQLAlchemy + SQLite / PostgreSQL.
- **Frontend:** Responsive Web Dashboard with tabs for Pending Approvals, Resume Screening, Job Requisitions, and Audit Logs.
- **Desktop Ready:** Can be packaged directly with [Tauri](https://tauri.app/) or [Electron](https://www.electronjs.org/) by wrapping the FastAPI server + frontend assets into a single desktop binary `.exe`.

### 2. HITL State Machine
```
Candidate Resume + JD
         │
         ▼
[DRAFT] ➔ [PARSED] ➔ [SCORED] ➔ [PENDING_APPROVAL]
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
                 [HUMAN APPROVE]                [HUMAN REJECT]
                         │                             │
                         ▼                             ▼
                 [EXECUTE DISPATCH]             [ARCHIVE & LOG]
                         │
                         ▼
                    [COMMITTED]
```

### 3. Core Database Tables
- `jobs`: Job requisitions (req ID, title, department, requirements, description).
- `candidates`: Candidate profiles, contacts, education, raw resume.
- `applications`: Application lifecycle status (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `COMMITTED`).
- `scorecards`: AI evaluation metrics (overall score 0-100, category weights, strengths, gaps, interview questions).
- `staged_actions`: Drafted emails/letters staged as `PENDING_APPROVAL` with editable payloads.
- `audit_logs`: Immutable, append-only log recording actor, transition, timestamp, and review notes.

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Tests
```bash
python -m pytest tests/test_hitl_workflow.py
```

### 3. Run the Web Application
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 🖥️ Turning into a Desktop App (Next Step)
To bundle Michelle HR as a native Windows desktop app:
1. **Option A (Tauri - Recommended):** Lightweight Rust-based shell (~15MB installer) running webview against localhost.
2. **Option B (PyInstaller + Webview):** Single executable bundling Python runtime + local UI window via `pywebview`.
