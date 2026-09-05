"""OTP generation, hashing, and verification utility."""
import os
import hashlib
import hmac
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def hash_token(raw_token):
    """Securely hash a token or OTP using SHA-256."""
    if not raw_token:
        return ""
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def verify_hashed_token(raw_token, stored_hash):
    """Safely verify a raw token against its SHA-256 hash using constant-time comparison."""
    if not raw_token or not stored_hash:
        return False
    computed = hash_token(raw_token)
    return hmac.compare_digest(computed, stored_hash)


def generate_otp(length=6):
    """
    Generate a numeric OTP.

    Args:
        length (int): Length of OTP (default 6).

    Returns:
        str: OTP string.
    """
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


def send_otp_email(email, otp):
    """
    Send OTP via email (SMTP) or fallback to console.

    Args:
        email (str): Recipient email.
        otp (str): OTP code.

    Returns:
        bool: True if sent successfully via SMTP, False otherwise.
    """
    smtp_host = os.environ.get('SMTP_HOST', '').strip()
    raw_port = os.environ.get('SMTP_PORT', '').strip()
    smtp_port = int(raw_port) if raw_port.isdigit() else 587
    smtp_user = os.environ.get('SMTP_USER', '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD', '').strip()

    if smtp_host and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Your OTP for AI Resume Screening Registration'
            msg['From'] = smtp_user
            msg['To'] = email

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>AI Resume Screening System</h2>
                    <p>Your One-Time Password (OTP) for registration is:</p>
                    <h1 style="font-size: 32px; color: #6c5ce7; letter-spacing: 5px;">{otp}</h1>
                    <p>This OTP is valid for 10 minutes. Please do not share it with anyone.</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            # Fallback to console

    # Fallback: print OTP to console (DEMO mode)
    print("\n" + "=" * 50)
    print("[DEMO MODE: OTP Email]")
    print(f"To: {email}")
    print(f"Your OTP is: {otp}")
    print("=" * 50 + "\n")
    return False