---
title: AI Resume Screening System
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 🤖 AI Resume Screening System

A complete AI-powered resume screening system built with Django that automatically extracts text from PDF resumes, matches candidates to jobs using TF-IDF + Sentence-Transformers, provides explainable AI scores, generates emails, and exports reports.

## ✨ Features

- 🔐 **Admin Login** - Secure bcrypt password hashing
- 💼 **Job Posting** - Title + combined JD & required skills
- 📄 **Resume Upload** - PDF parsing with pdfplumber
- 📧 **Contact Extraction** - Email & phone via Regex
- 🧠 **AI Matching** - TF-IDF + Cosine Similarity + Sentence-Transformers
- 💡 **Explainable AI** - Detailed reasons for every match score
- ✉️ **GenAI Emails** - Automatic Selected/Rejected email generation
- 📊 **Reports** - Export to Excel/CSV with Pandas
- 🌙 **Dark/Light Mode** - Modern responsive UI with animations
- 🐳 **Docker Support** - Run anywhere

## 🚀 Quick Start

### Option 1: Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
python manage.py makemigrations core
python manage.py migrate

# 3. Create admin user (default: admin/admin123)
python manage.py create_admin

# 4. Start server
python manage.py runserver
```

Visit `http://localhost:8000` and login with:
- **Username:** `admin`
- **Password:** `admin123`

### Option 2: Docker + PostgreSQL (Recommended for deployment)

```bash
# 1. Docker Desktop install hone ke baad (WSL2 enabled + reboot karke):
docker compose up --build
```

Kya hota hai:
- `db` service — **PostgreSQL 16** container mein start hota hai
- `web` service — Django app chalata hai, aur **saara data PostgreSQL** mein store hota hai
- Data ek **named volume (`postgres_data`) mein persist** rehta hai, container restart par bhi safe
- Admin user banane ke liye (container chalte waqt, dusre terminal mein):
```bash
docker compose exec web python manage.py create_admin
```

Visit `http://localhost:8000`

> **Note:** `docker-compose.yml` mein `web` ki `DATABASE_URL` apne aap `db` (postgres) service par point karti hai — isliye app ab **SQLite ki bajaye PostgreSQL** mein data store karta hai.

### 🔄 Existing SQLite data ko PostgreSQL mein migrate karna

Pehle se `db.sqlite3` mein data hai (users/jobs/candidates), aur chahte ho ki wo PostgreSQL mein chale:

```bash
# 1. PostgreSQL DB me pehle port 5432 chal rahi hai (compose up se)
# 2. SQLite se data export karo:
python manage.py dumpdata core --indent 2 --output backup.json
# 3. Railway/cloud postgres se bhi windows par 'psql' chalane ke liye
#    (bina sqlite): Dump file ko PostgreSQL database par load karo:
python manage.py loaddata backup.json
```

> Agar yahan `-` ya caveat aaye to: dono DBs pe model-name same hai (`core.User`, etc.), isliye `dumpdata`/`loaddata` cleanly migrate karta hai. Fir aage ka data seedha PostgreSQL mein jaayega.

## 🎯 How It Works

1. **Post a Job** - Add job title and a combined description that includes a `Skills:` section (e.g. `Skills: Python, Django, SQL`)
2. **Upload Resume** - Upload a candidate's PDF resume
3. **AI Screening** - The system:
   - Extracts text from the PDF using pdfplumber
   - Finds email & phone using Regex
   - Computes TF-IDF + Cosine similarity
   - Computes semantic similarity using Sentence-Transformers
   - Matches required skills
   - Generates an explainable score with reasons
4. **Review Results** - See match scores, matched/missing skills, and explanations
5. **Generate Emails** - One-click selection/rejection emails
6. **Export Reports** - Download all data as Excel or CSV

## 📁 Project Structure

```
ai_resume_screening/
├── core/
│   ├── management/commands/
│   │   └── create_admin.py      # Create admin user
│   ├── static/
│   │   ├── css/style.css        # Theme + animations
│   │   └── js/main.js           # Dark/light toggle
│   ├── templates/               # HTML templates
│   ├── utils/
│   │   ├── pdf_extractor.py     # PDF text extraction
│   │   ├── contact_extractor.py # Email/phone regex
│   │   ├── matcher.py           # TF-IDF + Semantic matching
│   │   ├── explainer.py         # Explainable AI reasons
│   │   ├── email_generator.py   # GenAI email generation
│   │   └── reports.py           # Excel/CSV export
│   ├── models.py                # 4 tables: User, Job, Candidate, Score
│   ├── views.py                 # All views
│   └── urls.py                  # URL routing
├── screening/                   # Django project config
├── Dockerfile                   # Docker image
├── docker-compose.yml           # Docker orchestration
└── requirements.txt             # Python dependencies
```

## 🗄️ Database Schema

| Table | Fields |
|-------|--------|
| **User** | username, email, password_hash (bcrypt), full_name, is_active |
| **Job** | title, description (includes JD + Skills section) |
| **Candidate** | job (FK), name, email, phone, resume, extracted_text |
| **Score** | candidate (FK), job (FK), overall_score, tfidf_score, semantic_score, explanation, matched_skills, missing_skills, status, email_content |

## 🔧 GenAI Email Configuration (Optional)

Set these environment variables to use a real GenAI API for email generation:

```bash
export GENAI_API_KEY="your-api-key"
export GENAI_API_URL="https://api.openai.com/v1/chat/completions"
export GENAI_MODEL="gpt-3.5-turbo"
```

Without an API key, the system uses professional email templates automatically.

## 📧 SMTP Email Sending (Send Actual Emails)

To actually **send** selection/rejection emails to candidates, configure SMTP:

### Gmail Example:
```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"  # Use Gmail App Password, not regular password
```

### How to get Gmail App Password:
1. Go to Google Account → Security
2. Enable **2-Step Verification**
3. Go to **App Passwords**
4. Generate a new app password for "Mail"
5. Use that 16-character password as `SMTP_PASSWORD`

### Without SMTP:
- Email content is still **generated and saved** in the database
- UI shows "Not Sent" badge
- A warning message tells you to configure SMTP

### With SMTP:
- Email is **actually sent** to the candidate's email
- UI shows "Email Sent" badge with green checkmark
- Professional HTML email with company branding

## 🛠️ Tech Stack

- **Backend:** Django 5, Python 3.11
- **AI/ML:** scikit-learn (TF-IDF), Sentence-Transformers
- **PDF:** pdfplumber
- **Data:** Pandas, openpyxl
- **Security:** bcrypt
- **Frontend:** Bootstrap 5, Font Awesome, Custom CSS/JS
- **Database:** PostgreSQL 16 (via Docker Compose); SQLite act as local/dev fallback
- **Deployment:** Docker, docker-compose