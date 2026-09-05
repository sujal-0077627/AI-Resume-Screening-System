"""GenAI-powered automatic email generation and sending for selected/rejected candidates."""
import os
import json
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


def _call_genai_api(prompt, system_prompt):
    """
    Call a GenAI API (OpenAI or Google Gemini) if configured via env vars.
    Falls back to template generation if no API key is set.

    Supported providers:
    - OpenAI: GENAI_PROVIDER=openai (default)
    - Google Gemini: GENAI_PROVIDER=gemini
    """
    api_key = os.environ.get('GENAI_API_KEY', '')
    provider = os.environ.get('GENAI_PROVIDER', 'openai').lower()

    if not api_key:
        return None

    try:
        if provider == 'gemini':
            return _call_gemini_api(prompt, system_prompt, api_key)
        else:
            return _call_openai_api(prompt, system_prompt, api_key)
    except Exception:
        return None


def _call_openai_api(prompt, system_prompt, api_key):
    """Call OpenAI-compatible API."""
    api_url = os.environ.get('GENAI_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.environ.get('GENAI_MODEL', 'gpt-3.5-turbo')

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        return data['choices'][0]['message']['content'].strip()


def _call_gemini_api(prompt, system_prompt, api_key):
    """Call Google Gemini API."""
    model = os.environ.get('GENAI_MODEL', 'gemini-1.5-flash')
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        # Extract text from Gemini response
        candidates = data.get('candidates', [])
        if candidates:
            parts = candidates[0].get('content', {}).get('parts', [])
            if parts:
                return parts[0].get('text', '').strip()
    return None


def _template_email(candidate_name, job_title, company_name, status, score=None, explanation=None):
    """Generate a professional email using templates for various recruitment stages."""
    company_name = company_name or "Our Organization"
    reason_section = ""
    if score is not None:
        reason_section += f"\nYour AI match score for this position was {score:.1f}%.\n"
    if explanation:
        reason_section += f"\n{explanation}\n"

    status_lower = status.lower()

    if status_lower in ('selected', 'shortlisted'):
        subject = f"Congratulations! You're Shortlisted for {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

Congratulations! We are pleased to inform you that your profile has been shortlisted for the position of {job_title} at {company_name}.

Your qualifications and experience stood out during our AI-powered screening process.

MATCH DETAILS & FEEDBACK:
{reason_section}
Our hiring team will be in touch shortly regarding the next interview round and scheduling details.

Best regards,
HR Team
{company_name}"""

    elif status_lower in ('interview', 'technical'):
        subject = f"Interview Invitation: {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

Thank you for your application for the {job_title} role at {company_name}.

We would like to invite you for the next interview round. Our talent team will coordinate the meeting link and schedule shortly.

MATCH OVERVIEW:
{reason_section}
Please let us know your general availability over the coming days.

Best regards,
HR Recruitment Team
{company_name}"""

    elif status_lower in ('offered', 'hired'):
        subject = f"Offer of Employment - {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

We are thrilled to extend an official offer of employment for the position of {job_title} with {company_name}!

We were thoroughly impressed by your background, domain skills, and technical aptitude throughout our evaluation process.

Our HR team will reach out with the formal offer letter, compensation breakdown, and onboarding roadmap.

Welcome to the team!

Warm regards,
Human Resources
{company_name}"""

    else:  # Rejected / other
        subject = f"Update regarding your application for {job_title} - {company_name}"
        body = f"""Dear {candidate_name},

Thank you for your interest in {company_name} and for taking the time to apply for the position of {job_title}.

After careful review and screening of your application against our current role requirements, we have decided to pursue other candidates whose profiles more closely align with our immediate needs.

SCREENING FEEDBACK:
{reason_section}
We sincerely appreciate the effort you put into your application and encourage you to explore future opportunities with {company_name}.

We wish you every success in your ongoing career endeavors.

Best regards,
Talent Acquisition Team
{company_name}"""

    return {"subject": subject, "body": body}



def send_email(to_email, subject, body, from_email=None, from_name=None):
    """
    Send an actual email via SMTP.

    Args:
        to_email (str): Recipient email address.
        subject (str): Email subject.
        body (str): Email body text.
        from_email (str, optional): Sender email. Defaults to SMTP_USER.
        from_name (str, optional): Sender name. Defaults to 'HR Team'.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    # Check if SMTP is configured
    if not (smtp_host and smtp_user and smtp_password):
        return {
            'success': False,
            'message': 'SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD env vars. '
                       'Email content was saved but not sent.'
        }

    if not to_email:
        return {'success': False, 'message': 'No recipient email address.'}

    try:
        # Build email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((from_name or 'HR Team', from_email or smtp_user))
        msg['To'] = to_email

        # Plain text body
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)

        # HTML body
        html_body = body.replace('\n', '<br>')
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
                <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="background: linear-gradient(135deg, #6c5ce7, #a29bfe); padding: 20px; text-align: center;">
                        <h2 style="color: #ffffff; margin: 0;">AI Resume Screening</h2>
                    </div>
                    <div style="padding: 25px;">
                        <p style="color: #333; font-size: 15px; line-height: 1.6;">{html_body}</p>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #888;">
                        This is an automated email from AI Resume Screening System.
                    </div>
                </div>
            </body>
        </html>
        """
        html_part = MIMEText(html, 'html')
        msg.attach(html_part)

        # Send via SMTP
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return {'success': True, 'message': f'Email sent successfully to {to_email}!'}

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'message': 'SMTP authentication failed. Check SMTP_USER/SMTP_PASSWORD.'}
    except smtplib.SMTPException as e:
        return {'success': False, 'message': f'SMTP error: {e}'}
    except Exception as e:
        return {'success': False, 'message': f'Failed to send email: {e}'}


def generate_email(candidate_name, job_title, company_name, status, score=None, explanation=None):
    """
    Generate an email for a candidate with reasons.

    Args:
        candidate_name (str): Candidate's name.
        job_title (str): Job title.
        company_name (str): Company name.
        status (str): 'selected' or 'rejected'.
        score (float, optional): Match score.
        explanation (str, optional): Explainable AI reasons.

    Returns:
        dict: {'subject': str, 'body': str}
    """
    system_prompt = (
        "You are a professional HR assistant. Write a polite, professional "
        "recruitment email. Include clear reasons why the candidate was "
        "selected or rejected based on their AI match score. Keep it warm."
    )
    prompt = (
        f"Write a {'selection' if status == 'selected' else 'rejection'} email "
        f"to {candidate_name} for the position of {job_title} at {company_name}. "
        f"Their AI match score was {score:.1f}%. "
        f"Explain why: {explanation}" if score is not None and explanation else
        f"Write a {'selection' if status == 'selected' else 'rejection'} email "
        f"to {candidate_name} for the position of {job_title} at {company_name}."
    )

    # Try GenAI API first
    generated = _call_genai_api(prompt, system_prompt)
    if generated:
        # Parse subject/body from generated text
        lines = generated.strip().split('\n')
        subject = lines[0].replace('Subject:', '').strip() if lines else job_title
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else generated
        return {"subject": subject, "body": body}

    # Fallback to template
    return _template_email(candidate_name, job_title, company_name, status, score, explanation)


def send_password_reset_email(to_email, reset_url):
    """
    Send a password reset link email.

    Returns:
        bool: True if the email was sent successfully, False otherwise
              (e.g. SMTP not configured - in demo mode the caller should print
              the reset URL to the server console).
    """
    subject = "AI Resume Screening - Password Reset Request"
    body = (
        "Hello,\n\n"
        "You (or someone using your account) requested a password reset.\n\n"
        "Click the link below to set a new password. This link is valid for "
        "30 minutes:\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, simply ignore this email and no changes "
        "will be made.\n\n"
        "Thank you,\nAI Resume Screening Team"
    )

    result = send_email(
        to_email=to_email,
        subject=subject,
        body=body,
        from_name="AI Resume Screening",
    )
    if result.get('success'):
        return True
    # SMTP not configured or send failed - let caller fall back to demo mode
    print(f"[DEMO MODE] Password reset for {to_email}. Use reset link: {reset_url}")
    return False
