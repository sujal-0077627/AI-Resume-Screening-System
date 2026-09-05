"""Extract contact details (email, phone, links, experience, name) from resume text."""
import re
from datetime import datetime


def extract_email(text):
    """Extract email addresses from text using regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    seen = set()
    result = []
    for e in emails:
        clean = e.strip('.,;:()[]{}')
        if clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)
    return result[0] if result else ""


def extract_phone(text):
    """Extract phone numbers from text using regex."""
    phone_patterns = [
        r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\+?\d{1,3}[-.\s]?\d{10}\b',
        r'\b[6-9]\d{9}\b',  # Indian 10-digit mobile
        r'\b\d{5}[-.\s]\d{5}\b',
    ]
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            digits = re.sub(r'\D', '', m)
            if 10 <= len(digits) <= 13:
                return m.strip()
    return ""


def extract_links(text):
    """Extract LinkedIn, GitHub, and Portfolio URLs from resume text."""
    links = {
        'linkedin_url': '',
        'github_url': '',
        'portfolio_url': ''
    }

    # LinkedIn
    linkedin_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?', text, re.IGNORECASE)
    if linkedin_match:
        url = linkedin_match.group(0)
        links['linkedin_url'] = url if url.startswith('http') else f"https://{url}"

    # GitHub
    github_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?', text, re.IGNORECASE)
    if github_match:
        url = github_match.group(0)
        # Avoid matching generic github.com or github.com/topics
        if not re.search(r'github\.com/(topics|pricing|features|about|explore)', url, re.IGNORECASE):
            links['github_url'] = url if url.startswith('http') else f"https://{url}"

    # Portfolio / Personal Website
    portfolio_match = re.search(
        r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.(?:vercel\.app|netlify\.app|github\.io|me|dev|io|tech|info|site|org|com))(?:/[^\s]*)?',
        text,
        re.IGNORECASE
    )
    if portfolio_match:
        matched_url = portfolio_match.group(0).strip('.,;:()[]{}')
        if 'linkedin.com' not in matched_url and 'github.com' not in matched_url and not re.search(r'\.(pdf|png|jpg)$', matched_url):
            links['portfolio_url'] = matched_url if matched_url.startswith('http') else f"https://{matched_url}"

    return links


def extract_experience(text):
    """
    Extract estimated years of experience from resume text.
    Returns float (e.g. 3.5 years).
    """
    # 1. Direct mentions like "5+ years of experience", "3 years experience"
    exp_pattern = r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:total\s*)?(?:experience|exp|work)'
    matches = re.findall(exp_pattern, text, re.IGNORECASE)
    if matches:
        try:
            val = float(matches[0])
            if 0.5 <= val <= 40:
                return round(val, 1)
        except ValueError:
            pass

    # 2. Pattern: "Experience: 4 Years"
    exp_pattern_alt = r'(?:experience|exp)\s*:\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)'
    matches_alt = re.findall(exp_pattern_alt, text, re.IGNORECASE)
    if matches_alt:
        try:
            val = float(matches_alt[0])
            if 0.5 <= val <= 40:
                return round(val, 1)
        except ValueError:
            pass

    # 3. Calculate year ranges (e.g. "2019 - 2023", "2020 - Present")
    year_range_pattern = r'\b(20[0-2]\d|199\d)\s*(?:-|–|to)\s*(20[0-2]\d|present|current|till\s*date)\b'
    range_matches = re.findall(year_range_pattern, text, re.IGNORECASE)
    if range_matches:
        current_year = datetime.now().year
        total_months = 0
        for start_str, end_str in range_matches:
            try:
                start_y = int(start_str)
                end_y = current_year if end_str.lower() in ('present', 'current', 'till date') else int(end_str)
                diff = end_y - start_y
                if 0 <= diff <= 30:
                    total_months += diff * 12
            except ValueError:
                continue
        if total_months > 0:
            years = total_months / 12.0
            # Cap at realistic ceiling to avoid overcounting overlapping dates
            return round(min(years, 35.0), 1)

    return 0.0


def extract_name(text):
    """
    Intelligently extract the candidate's name from the top of the resume.
    Skips headings, objective statements, addresses, contacts, and generic words.
    """
    first_lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not first_lines:
        return "Candidate"

    generic_words = {
        'resume', 'curriculum vitae', 'cv', 'contact', 'info', 'profile', 'summary',
        'personal', 'details', 'objective', 'about me', 'work experience', 'education',
        'skills', 'projects', 'page', 'portfolio', 'contact information', 'experience'
    }

    for line in first_lines[:8]:
        cleaned = re.sub(r'[^a-zA-Z\s.-]', '', line).strip()
        low = cleaned.lower()

        # Skip if too short or too long
        if len(cleaned) < 3 or len(cleaned) > 50:
            continue
        # Skip if matches generic section headers
        if low in generic_words or any(low.startswith(w + ' ') or low.startswith(w + ':') for w in generic_words):
            continue
        # Skip if contains email, phone, url, digits, or bullet markers
        if '@' in line or re.search(r'\d{3,}', line) or 'http' in line or 'linkedin' in line or 'github' in line:
            continue

        words = cleaned.split()
        # A name usually has 1 to 4 words, each starting with capital or standard name chars
        if 1 <= len(words) <= 4:
            # Check that it contains real alphabetic letters
            if all(len(w) >= 2 for w in words):
                return " ".join(w.capitalize() for w in words)[:200]

    # Fallback to first clean alphabetic line
    fallback = first_lines[0]
    cleaned_fb = re.sub(r'[^a-zA-Z\s]', '', fallback).strip()
    return cleaned_fb[:50] if len(cleaned_fb) >= 3 else "Candidate"


def extract_contact_details(text):
    """Extract all candidate details: email, phone, links, experience, and name."""
    links = extract_links(text)
    return {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'experience_years': extract_experience(text),
        'github_url': links['github_url'],
        'linkedin_url': links['linkedin_url'],
        'portfolio_url': links['portfolio_url'],
    }