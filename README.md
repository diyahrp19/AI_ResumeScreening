# 🧠 AI Resume Screening System

An AI-powered HR Recruitment Platform that parses resumes, compares them against a job
description using NLP and a rule-based expert system, ranks candidates, and generates
downloadable reports — all through a clean, modern Flask web interface.

---

## 📌 Project Overview

Recruiters spend hours manually screening resumes against job requirements. This project
automates that process using genuine AI techniques rather than simple keyword matching:

- **NLP** extracts structured candidate data (contact info, skills, education, experience,
  certifications, projects) from raw PDF/DOCX resumes.
- **Rule-Based Inference** applies explicit IF-THEN rules (skill coverage, experience
  thresholds, education level, certifications, critical-skill gaps) to compute a score.
- **Expert System** turns the rule outcomes into a human-readable explanation — strengths,
  weaknesses, missing skills, and a final recommendation — for every candidate.
- **Candidate Ranking** sorts and filters the pool so the best-fit candidates surface first.
- **Analytics & Reports** visualize the pipeline and export PDF/Excel/CSV summaries.

---

## ✨ Features

- 🏠 **Dashboard** — KPI cards (total resumes, shortlisted, rejected, pending), pipeline
  charts, rejection reasons breakdown, and recent activity feed with auto-refresh.
- 📄 **Resume Screening** — upload PDF/DOCX resumes, fill in the job description, and run
  AI analysis in one workflow.
- 👥 **Candidate Results** — ranked ranking table with click-to-expand detail panels showing
  an itemized score breakdown (✔/✖ per required skill) plus missing skills,
  strengths/weaknesses, and recommendation. Only two outcomes exist: ✅ Shortlisted or ❌ Rejected.
- 📑 **Reports** — one-click PDF / Excel / CSV export with report history tracking.
- 🎨 **Polished HR-platform UI** — dark-navy sidebar with icon navigation, light/dark theme
  toggle, and responsive design.
- 🌗 Light/Dark theme toggle
- 🗄️ SQLite persistence across sessions
- 🔐 User authentication with login/signup

---

## 🧠 AI Concepts Used

| Concept                     | Implementation                                                                                             |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Natural Language Processing | spaCy NER, NLTK tokenization & stop-word removal, regex-based field extraction, TF-IDF + cosine similarity |
| Rule-Based Inference        | `ai/rule_engine.py` — explicit rules with score deltas and explanations                                    |
| Expert System               | `ai/rule_engine.py::build_expert_recommendation` — aggregates rules into a narrative verdict               |
| Candidate Ranking           | `ai/ranking.py` — sorts by weighted composite score                                                        |

---

## 🛠️ Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS (Bootstrap 5), JavaScript (Chart.js)
- **AI & NLP:** spaCy, NLTK, pandas, scikit-learn
- **Resume Parsing:** PyMuPDF (fitz), python-docx
- **Database:** SQLite
- **Reports:** ReportLab, openpyxl

---

## 📂 Folder Structure

```
AI_Resume_Screening/
├── app.py                     # Flask application factory
├── run.py                     # Entry point to run the server
├── config.py                  # Application configuration
├── requirements.txt
├── README.md
├── uploads/                   # Uploaded resume files land here
├── exports/                   # Export staging area
├── logs/                      # Application logs
├── database/
│   ├── database.db             # Created automatically on first run
│   └── models.py               # SQLite schema + CRUD functions
├── ai/                        # All AI/NLP logic — UI-independent, unit-testable
│   ├── knowledge_base.py       # Skill taxonomy, education ranks, section headers
│   ├── parser.py                # PDF/DOCX text extraction, contact/name/experience parsing
│   ├── skill_extractor.py       # NLTK preprocessing + skill/education/cert/project extraction
│   ├── matcher.py               # Weighted scoring + TF-IDF similarity
│   ├── rule_engine.py           # Rule-based inference + expert system explanations
│   ├── ranking.py               # Sorting, dataframe conversion, KPI aggregation
│   └── report_generator.py      # PDF / Excel / CSV report builders
├── routes/                    # Flask blueprints
│   ├── auth_routes.py          # Login, signup, logout
│   ├── main_routes.py          # Dashboard, KPI API
│   ├── screening_routes.py     # Resume upload, job description, analysis
│   ├── candidates_routes.py    # Candidate results, ranking
│   └── reports_routes.py       # Report downloads, settings, clear data
├── auth/
│   └── auth_db.py              # Authentication database helpers
├── templates/                 # Jinja2 HTML templates
│   ├── base.html               # Base layout with sidebar
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── screening.html
│   ├── candidates.html
│   ├── reports.html
│   └── settings.html
├── static/
│   ├── css/style.css           # Custom styles
│   └── js/app.js               # Client-side JavaScript
└── utils/
    └── helpers.py               # Activity logging, formatting helpers
```

---

## 🚀 Installation

1. **Clone or unzip** the project, then move into the folder:

   ```bash
   cd AI_Resume_Screening
   ```

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Download the spaCy English model** (used for name extraction via NER):

   ```bash
   python -m spacy download en_core_web_sm
   ```

   If this step is skipped, the app automatically falls back to a regex-based name
   heuristic — no functionality is lost, just slightly less robust name detection.

   NLTK's `punkt` and `stopwords` corpora are downloaded automatically on first run.

---

## ▶️ How to Run

```bash
python run.py
```

Then open `http://127.0.0.1:5000` in your browser.

**Suggested workflow inside the app:**

1. Create an account or sign in.
2. Go to **Resume Screening**:
   - Upload one or more PDF/DOCX resumes.
   - Fill in and save the job description.
   - Click **Analyze Resumes** to run NLP extraction, rule-based inference,
     and expert-system scoring on every uploaded resume.
3. Review the ranked shortlist in **Candidate Results** — click any candidate row's
   expander for the full score breakdown and recommendation.
4. Export a report from **Reports** (PDF, Excel, or CSV).
5. Check pipeline-wide KPIs and charts anytime on **Dashboard**.

---

## 🔮 Future Enhancements

- Swap TF-IDF similarity for transformer-based embeddings (e.g. Sentence-BERT) for deeper
  semantic matching between resumes and job descriptions.
- Add multi-job-description support with per-job candidate pools.
- OCR support (e.g. Tesseract) for scanned/image-based PDF resumes.
- Bias/fairness auditing dashboard for the scoring rules.
- Email notifications to shortlisted candidates directly from the Reports page.

---

## ⚠️ Notes

- This is an educational/demo system. Match scores and recommendations are generated by
  transparent, rule-based heuristics — they should support, not replace, human hiring
  decisions.
- All data (resumes, scores, job descriptions) is stored locally in `database/database.db`
  and the `uploads/` folder. Use **Clear All Data** in the sidebar to reset the system.
