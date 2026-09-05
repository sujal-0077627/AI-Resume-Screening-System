"""Database models for AI Resume Screening System."""
import os
import bcrypt
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

# Section headers / meta-lines that must NEVER become "skills"
SECTION_HEADERS = (
    'good to have', 'good-to-have', 'nice to have', 'nice-to-have',
    'must have', 'must-have', 'required skills', 'skills required',
    'key skills', 'core skills', 'skills', 'responsibilities',
    'requirement', 'requirements', 'qualification', 'qualifications',
    'education', 'salary', 'compensation', 'ctc', 'perks', 'benefits',
    'about us', 'about the role', 'about', 'what you will do',
    'who we are', 'preferred', 'bonus', 'experience required', 'role',
)
# Wrapper phrases JDs put around real skills
PREFIXES = (
    'hands-on experience with ', 'hands on experience with ',
    'experience with ', 'experience of ', 'experience in ',
    'working knowledge of ', 'working knowledge in ',
    'basic knowledge of ', 'strong knowledge of ',
    'good knowledge of ', 'knowledge of ', 'knowledge in ',
    'basic understanding of ', 'strong understanding of ',
    'understanding of ', 'familiarity with ', 'familiar with ',
    'proficiency in ', 'proficient in ', 'expertise in ',
    'expertise with ', 'exposure to ', 'ability to work with ',
    'ability to ', 'should have ', 'must have ', 'should know ',
    'must know ', 'strong ', 'solid ', 'good ', 'excellent ',
    'basic ',
)
GENERIC_EDGES = {
    'framework', 'frameworks', 'programming', 'development',
    'skills', 'skill', 'concepts', 'concept', 'tools', 'tool',
    'technologies', 'technology', 'knowledge',
}


class User(models.Model):
    """Custom admin user with bcrypt password hashing and hashed verification tokens."""
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=255, blank=True, help_text="Hashed OTP storage")
    otp_created_at = models.DateTimeField(null=True, blank=True, help_text="When the OTP was created")
    reset_token = models.CharField(max_length=255, blank=True, help_text="Hashed password reset token")
    reset_token_created = models.DateTimeField(null=True, blank=True, help_text="When the reset token was created")
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        """Hash password using bcrypt."""
        self.password_hash = bcrypt.hashpw(
            raw_password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, raw_password):
        """Verify password against bcrypt hash."""
        try:
            return bcrypt.checkpw(
                raw_password.encode('utf-8'),
                self.password_hash.encode('utf-8')
            )
        except (ValueError, AttributeError):
            return False

    def set_otp(self, raw_otp):
        """Securely store SHA-256 hashed OTP."""
        from .utils.otp import hash_token
        self.otp_secret = hash_token(raw_otp)
        self.otp_created_at = timezone.now()

    def verify_otp(self, raw_otp):
        """Verify raw OTP against stored hash (also supports legacy plaintext)."""
        from .utils.otp import verify_hashed_token
        if not self.otp_secret or not raw_otp:
            return False
        # If legacy plaintext matched directly or hash matches
        return self.otp_secret == raw_otp or verify_hashed_token(raw_otp, self.otp_secret)

    def set_reset_token(self, raw_token):
        """Securely store SHA-256 hashed reset token."""
        from .utils.otp import hash_token
        self.reset_token = hash_token(raw_token)
        self.reset_token_created = timezone.now()

    def verify_reset_token(self, raw_token):
        """Verify raw reset token against stored hash (also supports legacy plaintext)."""
        from .utils.otp import verify_hashed_token
        if not self.reset_token or not raw_token:
            return False
        return self.reset_token == raw_token or verify_hashed_token(raw_token, self.reset_token)

    def __str__(self):
        return self.username


class Job(models.Model):
    """Job posting with title, JD, required skills, and customizable screening criteria."""
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, default="Your Company", blank=True, help_text="Company / Organization name")
    cutoff_score = models.FloatField(default=75.0, help_text="Passing score percentage for shortlisting (e.g. 75.0)")
    experience_required = models.PositiveIntegerField(default=0, help_text="Minimum years of experience required (0 for any)")
    description = models.TextField(
        help_text="Job Description including required skills. "
                  "Add a 'Skills:' section with comma-separated skills, e.g. "
                  "Skills: Python, Django, SQL, Machine Learning"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def skills_list(self):
        """
        Extract required skills from the description.

        Handles multiple formats:
        - 'Skills: Python, Django, SQL' (comma-separated)
        - 'Skills:\\n- Python\\n- Django\\n- SQL' (bullet points)
        - 'Skills:\\nPython\\nDjango\\nSQL' (newline-separated)
        - 'Required Skills: Python, Django' (with prefix)
        - Skills mentioned anywhere in the description (fallback keyword extraction)
        """
        import re

        def clean_part(raw):
            """Turn one raw JD chunk into a clean skill string (or None)."""
            s = re.sub(r'^\s*[-*•·–—>)\d.]+\s*', '', raw.strip())
            s = re.sub(r'\s+', ' ', s).strip(' \t:.;-')
            if not s or len(s) > 45:
                return None
            low = s.lower()
            # Never treat headers / salary / education lines as skills
            if any(low == h or low.startswith(h + ':') or low.startswith(h) and len(low) <= len(h) + 12 for h in SECTION_HEADERS):
                return None
            if re.search(
                r'(\blpa\b|\bsalary\b|\bctc\b|stipend|\bb\.?\s*tech\b'
                r'|\bm\.?\s*tech\b|bachelor|master|\bdegree\b|\bcgpa\b'
                r'|percentage|years?\s+of\s+exp)',
                low,
            ):
                return None
            if not re.search(r'[a-z]', low):
                return None
            # Strip wrappers: "Experience with LLMs" -> "LLMs",
            # "Basic knowledge of Django Framework" -> "Django ..."
            changed = True
            while changed and s:
                changed = False
                for p in PREFIXES:
                    if low.startswith(p) and len(low) > len(p) + 1:
                        s = s[len(p):].strip()
                        low = s.lower()
                        changed = True
            words = s.split()
            while words and words[0].lower() in ('and', '&', 'or'):
                words.pop(0)
            while words and len(words) > 1 and (
                words[-1].lower() in GENERIC_EDGES
                or words[0].lower() in GENERIC_EDGES
            ):
                if words[-1].lower() in GENERIC_EDGES:
                    words.pop()
                else:
                    words.pop(0)
            s = ' '.join(words).strip(' -&,.')
            return s if len(s) >= 2 and len(s) <= 40 else None

        NON_TECH_WORDS = {
            'responsibilities', 'requirements', 'qualifications', 'experience',
            'opportunity', 'benefits', 'salary', 'compensation', 'candidate',
            'company', 'team', 'work', 'working', 'years', 'degree', 'bachelor',
            'master', 'phd', 'graduate', 'undergraduate', 'btech', 'mtech',
            'overview', 'summary', 'location', 'remote', 'hybrid', 'fulltime',
            'parttime', 'contract', 'internship', 'description', 'role', 'title',
            'deadline', 'apply', 'contact', 'email', 'phone', 'india', 'bangalore',
            'mumbai', 'delhi', 'pune', 'hyderabad', 'usa', 'strong', 'good',
            'excellent', 'basic', 'hands-on', 'proficient', 'knowledge', 'understanding',
            'ability', 'skills', 'skill', 'tools', 'tool', 'technologies', 'technology',
            'looking', 'seeking', 'hiring', 'senior', 'junior', 'lead', 'principal',
            'developer', 'engineer', 'architect', 'manager', 'specialist', 'analyst',
            'backend', 'frontend', 'fullstack', 'plus', 'must', 'should', 'have', 'with',
            'from', 'this', 'that', 'they', 'their', 'what', 'when', 'where', 'which',
            'will', 'your', 'please', 'join', 'about', 'welcome', 'ideal', 'building', 'apps',
            'tech stack', 'tech', 'stack'
        }

        # 1. Look for a Skills / Requirements / Qualifications / Tech Stack section
        section_pattern = (
            r'(?:^|\n)\s*(?:[A-Za-z/&\s]+\s+)?'
            r'(?:skills?|requirements?|qualifications?|technologies|tech\s+stack|tools|competencies)'
            r'\s*:?\s*\n+(.*)'
        )
        skill_section = re.search(
            section_pattern,
            self.description,
            re.IGNORECASE | re.DOTALL
        )
        if skill_section:
            # Take everything after the section header up to the next section
            section_text = skill_section.group(1)
            section_text = re.split(
                r'\n\s*(?:responsibilities|about(?:\s+us|\s+the\s+role)?|what\s+you\s+will\s+do'
                r'|salary|compensation|perks|benefits|who\s+we\s+are|contact|how\s+to\s+apply|requirements)\s*:?[\s]*',
                section_text,
                flags=re.IGNORECASE
            )[0]

            # Split by commas, bullet points, newlines, semicolons, pipes, tabs;
            # then also split "X and Y" style chunks into individual skills.
            skills = []
            seen = set()
            for part in re.split(r'[,;\n|•*·–—\t]', section_text):
                for chunk in re.split(r'\s+(?:and|&)\s+', part, flags=re.IGNORECASE):
                    sk = clean_part(chunk)
                    if not sk or sk.lower() in NON_TECH_WORDS:
                        continue
                    if len(sk) == 1 and sk.lower() not in ('c', 'r'):
                        continue
                    key = sk.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    skills.append(sk)
            if skills:
                return skills

        extracted_skills = []
        seen = set()

        def add_skill(s):
            clean = clean_part(s)
            if clean and clean.lower() not in seen and clean.lower() not in NON_TECH_WORDS:
                if len(clean) == 1 and clean.lower() not in ('c', 'r'):
                    return
                seen.add(clean.lower())
                extracted_skills.append(clean)

        # Pattern A: CamelCase, PascalCase, Acronyms, Hyphenated, Dotted, C++, C#
        tech_pattern = re.findall(
            r'\b(?:[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*|[A-Z]{2,6}(?:/[A-Z]{2,6})?|[A-Za-z0-9]+(?:\.[a-z]{2,3}|\+\+|#)|[A-Za-z0-9]+-[A-Za-z0-9]+|[A-Z][a-zA-Z0-9]{2,20})\b',
            self.description
        )
        for match in tech_pattern:
            add_skill(match)

        # Pattern B: Multi-word technical domains
        multi_patterns = [
            r'\b(?:machine\s+learning|deep\s+learning|data\s+science|prompt\s+engineering|cloud\s+computing|natural\s+language\s+processing|computer\s+vision|vector\s+database|big\s+data|microservices|distributed\s+systems|rest\s+api|web\s+scraping|unit\s+testing|ci/cd|generative\s+ai|large\s+language\s+models?)\b',
        ]
        for mp in multi_patterns:
            for match in re.finditer(mp, self.description, re.IGNORECASE):
                add_skill(match.group(0).title())

        # Pattern C: Essential seed language tokens (handles lowercase mentions of python, rust, go, etc.)
        seed_tokens = [
            'python', 'django', 'flask', 'fastapi', 'sql', 'nosql', 'javascript', 'typescript',
            'react', 'angular', 'vue', 'node', 'express', 'java', 'golang', 'go', 'rust',
            'c++', 'c#', 'ruby', 'php', 'html', 'css', 'docker', 'kubernetes', 'aws',
            'azure', 'gcp', 'git', 'linux', 'mongodb', 'postgresql', 'mysql', 'redis',
            'graphql', 'rest', 'tailwind', 'bootstrap', 'pandas', 'numpy', 'scikit-learn',
            'pytorch', 'tensorflow', 'keras', 'spark', 'hadoop', 'kafka', 'airflow'
        ]
        desc_lower = self.description.lower()
        for tok in seed_tokens:
            if re.search(rf'\b{re.escape(tok)}\b', desc_lower):
                add_skill(tok.title() if len(tok) > 3 else tok.upper())

        return extracted_skills

    def __str__(self):
        return self.title


class Candidate(models.Model):
    """Candidate with uploaded resume document (.pdf, .docx, .txt)."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidates')
    name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    experience_years = models.FloatField(default=0.0, help_text="Estimated years of experience")
    github_url = models.URLField(blank=True, help_text="Candidate GitHub profile")
    linkedin_url = models.URLField(blank=True, help_text="Candidate LinkedIn profile")
    portfolio_url = models.URLField(blank=True, help_text="Portfolio / Website")
    notes = models.TextField(blank=True, help_text="Recruiter internal notes & evaluation")
    resume = models.FileField(upload_to='resumes/%Y/%m/')
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Candidate #{self.id}"


class Score(models.Model):
    """Matching score with explainable AI reasons and ATS workflow lifecycle."""
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('screened', 'Screened'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'),
        ('technical', 'Technical Round'),
        ('offered', 'Offered'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name='scores'
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='scores')
    overall_score = models.FloatField(default=0.0)
    tfidf_score = models.FloatField(default=0.0)
    semantic_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=100.0)
    explanation = models.TextField(blank=True, help_text="Explainable AI reasons")
    matched_skills = models.TextField(blank=True)
    missing_skills = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='screened')
    email_content = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-overall_score']

    def __str__(self):
        return f"{self.candidate} - {self.job} - {self.overall_score:.1f}%"



@receiver(post_delete, sender=Candidate)
def auto_delete_file_on_candidate_delete(sender, instance, **kwargs):
    """Deletes physical resume file from disk when Candidate instance is deleted."""
    if instance.resume:
        try:
            if os.path.isfile(instance.resume.path):
                os.remove(instance.resume.path)
        except Exception:
            pass