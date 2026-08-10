# AI Resume Screening System

An end-to-end Django web application that automates resume screening — from upload to shortlist. It parses resumes, scores them against a job description using NLP and TF-IDF + Cosine Similarity, ranks candidates with an explainable score, and automatically emails each candidate their outcome using Generative AI (Gemini).

---

## Features

- **Secure Authentication** — Registration and login with hashed passwords and email-based OTP verification (1-minute expiry).
- **Job Posting** — Recruiters create a job with a title and description, which becomes the source of truth for matching.
- **Bulk Resume Upload** — Upload a single resume, multiple resumes at once, or a ZIP archive of PDFs.
- **Automatic Resume Parsing** — Extracts name, email, phone number, and years of experience from each PDF using `pdfplumber`, `Regex`, and `spaCy` (NLP).
- **Smart Matching Engine** — Blends two techniques into one score:
  - Skill Keyword Matching (explainable, exact skill overlap)
  - TF-IDF + Cosine Similarity (`scikit-learn`) for broader text similarity
- **Explainable AI** — Every score ships with a Matched Skills / Missing Skills breakdown, not just a number.
- **GenAI-Powered Emails** — Google Gemini automatically writes and sends a personalized shortlist or rejection email based on the candidate's score and skill gaps. Falls back to a fixed template if the AI or network is unavailable.
- **Ranked Candidates Dashboard** — All candidates for a job are ranked by match score.
- **Reports** — Export the candidate list as a formatted CSV or Excel (`.xlsx`) file with `pandas` + `openpyxl`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django |
| Database | SQLite |
| Password Security | Django password hashers (salted hashing) |
| PDF Parsing | pdfplumber |
| Text Extraction | Regex, spaCy (NLP) |
| Matching Engine | scikit-learn (TF-IDF Vectorizer + Cosine Similarity) |
| Generative AI | Google Gemini (`google-generativeai`) |
| Reports | pandas, openpyxl |
| Email | Gmail SMTP |

---

## Project Structure

```
AI_Resume_Screening_System/
├── accounts/
│   ├── views.py           # All view logic (auth, jobs, candidates, exports)
│   ├── models.py          # User, Job, Candidate, Score, EmailOTP
│   ├── urls.py             # App URL routes
│   ├── utils.py            # PDF parsing, matching engine, GenAI email, reports
│   ├── forms.py
│   └── templates/pages/    # HTML templates
├── resume_screener/
│   ├── settings.py         # Project settings (DB, email, API keys)
│   └── urls.py
├── media/resumes/          # Uploaded resume PDFs
├── db.sqlite3               # SQLite database
└── manage.py
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `User` | Registered recruiters — username, email, hashed password |
| `Job` | Posted roles — title & description used for matching |
| `Candidate` | Parsed resume data — name, email, phone, experience |
| `Score` | Match score, matched/missing skills, AI explanation |
| `EmailOTP` | One-time codes issued during registration |

---

## Setup & Installation

**1. Clone the repository and set up a virtual environment**
```bash
git clone <repo-url>
cd AI_Resume_Screening_System
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

**2. Install dependencies**
```bash
pip install django pdfplumber spacy scikit-learn pandas openpyxl google-generativeai
python -m spacy download en_core_web_sm
```

**3. Configure `resume_screener/settings.py`**
```python
# Gmail SMTP (use a Gmail App Password, not your normal password)
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-16-character-app-password'
EMAIL_TIMEOUT = 10

# Gemini API key (free from https://aistudio.google.com/apikey)
GEMINI_API_KEY = 'your-gemini-api-key'
```

**4. Run migrations and start the server**
```bash
python manage.py migrate
python manage.py runserver
```

**5. Open the app**
```
http://127.0.0.1:8000/
```

---

## How the Matching Score Works

For every resume uploaded against a job:

1. **Skill Keyword Match** — Skills are extracted from both the resume and job description; the overlap is measured directly.
2. **TF-IDF + Cosine Similarity** — Both texts are converted into weighted term vectors, and the angle between them is measured.
3. **Final Score** — `50% Skill Match + 50% TF-IDF Similarity`, so the score stays explainable while still capturing context beyond exact keywords.

If the match score is **80% or higher**, the candidate is automatically shortlisted and emailed; below 80%, a constructive rejection email is sent explaining the missing skills — both written by Gemini.

---

## Reliability

The system is designed to degrade gracefully:
- If the Gemini API or Gmail SMTP is slow/unavailable, requests time out safely (15s / 10s) and a fixed template email is used instead — nothing hangs or crashes.
- If a resume's email can't be reliably extracted, the notification email is skipped rather than failing the whole upload.

---

## Future Scope

- **Sentence-Transformers** for deep semantic matching (e.g. recognizing "ML Engineer" ≈ "Machine Learning Specialist").
- **OCR** support for scanned or image-based resumes (e.g. Canva exports).
- **Docker** packaging for one-command deployment on any machine.

---

## Author
Sujal Pawar
