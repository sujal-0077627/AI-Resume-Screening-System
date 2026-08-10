import os
import csv
import zipfile
import random
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password, check_password

from .models import Job, Candidate, Score, User
from .utils import (
    extract_text_from_pdf, 
    extract_email, 
    extract_phone, 
    extract_experience, 
    extract_name_nlp,
    calculate_match_score,
    send_candidate_status_email,
    export_candidates_csv as util_export_csv,
    export_candidates_excel as util_export_excel,
)

OTP_EXPIRY_SECONDS = 60  # OTP valid for 1 minute

# =========================================================
# 1. HOME & AUTHENTICATION VIEWS
# =========================================================
def home_view(request):
    """Welcome/Home page shown after successful login"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    try:
        user = User.objects.get(id=request.session['user_id'])
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/?mode=login')
    return render(request, 'pages/home.html', {'user': user})

def auth_view(request):
    """Handles both rendering the Auth page AND processing Login/Register POST"""
    mode = request.POST.get('mode') or request.GET.get('mode', 'login')

    if request.method == 'POST':

        # ---------------- REGISTER ----------------
        if mode == 'register':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            entered_otp = request.POST.get('otp')

            if not (username and email and password):
                messages.error(request, "Username, Email and Password are all required.")
                return redirect('/?mode=register')

            session_otp = request.session.get('otp')
            session_email = request.session.get('auth_email')
            otp_created_at = request.session.get('otp_created_at')

            if not entered_otp:
                messages.error(request, "Please click 'Send OTP' and enter the code sent to your email.")
                return redirect('/?mode=register')

            if not otp_created_at or (time.time() - otp_created_at) > OTP_EXPIRY_SECONDS:
                request.session.pop('otp', None)
                request.session.pop('auth_email', None)
                request.session.pop('otp_created_at', None)
                messages.error(request, "OTP expired. Please request a new OTP.")
                return redirect('/?mode=register')

            if not session_otp or session_email != email or entered_otp != session_otp:
                messages.error(request, "Invalid or expired OTP. Please request a new OTP and try again.")
                return redirect('/?mode=register')

            if User.objects.filter(username=username).exists():
                messages.error(request, "This username is already registered.")
                return redirect('/?mode=register')

            if User.objects.filter(email=email).exists():
                messages.error(request, "This email is already registered. Please login.")
                return redirect('/?mode=login')

            # OTP verified — clear it so it can't be reused
            request.session.pop('otp', None)
            request.session.pop('auth_email', None)
            request.session.pop('otp_created_at', None)

            user = User.objects.create(
                username=username,
                email=email,
                password_hash=make_password(password)
            )
            request.session['user_id'] = user.id
            messages.success(request, "Registration successful! Welcome.")
            return redirect('home')

        # ---------------- LOGIN ----------------
        elif mode == 'login':
            email = request.POST.get('email')
            password = request.POST.get('password')

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account found with this email.")
                return redirect('/?mode=login')

            if check_password(password, user.password_hash):
                request.session['user_id'] = user.id
                messages.success(request, "Login successful!")
                return redirect('home')
            else:
                messages.error(request, "Incorrect email or password.")
                return redirect('/?mode=login')

    return render(request, 'pages/auth.html', {'mode': mode})

def send_otp_view(request):
    """Generates an OTP for registration and emails it to the user. Called via AJAX (fetch), returns JSON."""
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'success': False, 'message': 'Please enter a valid email.'})

        otp = str(random.randint(100000, 999999))
        request.session['auth_email'] = email
        request.session['otp'] = otp
        request.session['otp_created_at'] = time.time()
        print(f"\n[DEBUG OTP] Generated OTP for {email}: {otp}\n")

        try:
            from django.core.mail import send_mail
            send_mail(
                "Your OTP Code — AI Resume Screener",
                f"Your OTP code is: {otp}\n\nEnter this on the registration page to verify your email.",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': f'OTP sent to {email}.'})
        except Exception as e:
            print(f"[OTP Email] Failed to send: {e}")
            # Still let them proceed using the terminal-printed OTP (e.g. if internet/email fails)
            return JsonResponse({'success': True, 'message': f'OTP generated (email could not be sent — check server terminal for the code).'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})

def verify_otp_view(request):
    """Verifies OTP and creates/logs in user"""
    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        session_otp = request.session.get('otp')
        email = request.session.get('auth_email')

        if user_otp and user_otp == session_otp and email:
            user, _ = User.objects.get_or_create(email=email)
            request.session['user_id'] = user.id
            request.session.pop('otp', None)
            request.session.pop('auth_email', None)
            messages.success(request, "Successfully Logged In!")
            return redirect('home')
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect('/?mode=verify')

    return redirect('/?mode=login')

def forgot_password_view(request):
    """Handles Password Reset Request"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            otp = str(random.randint(100000, 999999))
            request.session['auth_email'] = email
            request.session['otp'] = otp
            print(f"\n[DEBUG FORGOT PASSWORD] Generated OTP for {email}: {otp}\n")
            messages.success(request, f"Password reset OTP sent to {email}. (Demo OTP: {otp})")
            return redirect('/?mode=verify')
        messages.error(request, "Please enter a valid email.")
    return render(request, 'pages/auth.html', {'mode': 'forgot_password'})

def reset_password_view(request):
    """Alias for forgot password"""
    return forgot_password_view(request)

def logout_view(request):
    request.session.flush()
    messages.info(request, "Logged out successfully.")
    return redirect('/?mode=login')


# =========================================================
# 2. JOB MANAGEMENT VIEWS
# =========================================================
def create_job_view(request):
    """Create a new job posting"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        if title and description:
            job = Job.objects.create(title=title, description=description)
            messages.success(request, f"Job '{title}' created!")
            return redirect('candidate_upload', job_id=job.id)
        else:
            messages.error(request, "Title and Description are both required.")

    return render(request, 'pages/job_upload.html')

def job_list_view(request):
    """List all posted jobs"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    jobs = Job.objects.all().order_by('-created_at')
    return render(request, 'pages/job_list.html', {'jobs': jobs})

def job_detail_view(request, job_id):
    """Details for a specific job"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    job = get_object_or_404(Job, id=job_id)
    return render(request, 'pages/job_detail.html', {'job': job})

def delete_job_view(request, job_id):
    """Delete a job position"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    job = get_object_or_404(Job, id=job_id)
    job.delete()
    messages.success(request, "Job deleted successfully.")
    return redirect('bulk_upload')

def job_upload_view(request):
    """Alias for create_job_view"""
    return create_job_view(request)


# =========================================================
# 3. BULK UPLOAD VIEW (Multi-PDF & ZIP Support)
# =========================================================
def bulk_upload_resumes_view(request):
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        uploaded_files = request.FILES.getlist('resumes')

        if not job_id or not uploaded_files:
            messages.error(request, "Please select a job position and upload files.")
            return redirect('bulk_upload')

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            messages.error(request, "Selected job not found.")
            return redirect('bulk_upload')

        pdf_files = []
        for file in uploaded_files:
            # ZIP File Processing
            if file.name.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file, 'r') as z:
                        for filename in z.namelist():
                            if filename.lower().endswith('.pdf') and not filename.startswith('__MACOSX') and not os.path.basename(filename) == '':
                                clean_name = os.path.basename(filename)
                                pdf_files.append((clean_name, ContentFile(z.read(filename), name=clean_name)))
                except Exception as e:
                    messages.error(request, f"ZIP Extract error: {str(e)}")
                    return redirect('bulk_upload')

            # Direct PDF Processing
            elif file.name.lower().endswith('.pdf'):
                pdf_files.append((os.path.basename(file.name), file))

        if not pdf_files:
            messages.error(request, "No valid PDF file found in the upload.")
            return redirect('bulk_upload')

        count = 0
        for filename, pdf_file in pdf_files:
            candidate_name = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
            candidate = Candidate.objects.create(name=candidate_name, applied_job=job, resume_path=pdf_file)

            full_path = os.path.join(settings.MEDIA_ROOT, candidate.resume_path.name)
            resume_text = extract_text_from_pdf(full_path)

            if resume_text:
                nlp_name = extract_name_nlp(resume_text)
                if nlp_name:
                    candidate.name = nlp_name
                candidate.email = extract_email(resume_text) or f"noemail_{candidate.id}@ats.local"
                candidate.phone = extract_phone(resume_text) or ""
                candidate.experience_years, candidate.experience_level = extract_experience(resume_text)
                candidate.save()

                score, matched, missing = calculate_match_score(resume_text, job.description)
                Score.objects.create(
                    candidate=candidate,
                    job=job,
                    matching_score=score,
                    matched_skills=', '.join(matched),
                    missing_skills=', '.join(missing),
                    explanation=f"Matched {len(matched)} skills ({score}%)."
                )
                send_candidate_status_email(candidate, job, score, ', '.join(matched), ', '.join(missing))
                count += 1

        messages.success(request, f"Successfully processed {count} resumes!")
        return redirect('candidate_list', job_id=job.id)

    jobs = Job.objects.all().order_by('-created_at')
    return render(request, 'pages/bulk_upload.html', {'jobs': jobs})

def candidate_upload_view(request, job_id):
    """Upload one or more resumes (PDF or ZIP) to a job, and show the ranked candidates table."""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    job = get_object_or_404(Job, id=job_id)

    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('resumes')

        if not uploaded_files:
            messages.error(request, "Please select at least one resume (PDF or ZIP).")
            return redirect('candidate_upload', job_id=job.id)

        pdf_files = []
        for file in uploaded_files:
            if file.name.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file, 'r') as z:
                        for filename in z.namelist():
                            if filename.lower().endswith('.pdf') and not filename.startswith('__MACOSX') and not os.path.basename(filename) == '':
                                clean_name = os.path.basename(filename)
                                pdf_files.append((clean_name, ContentFile(z.read(filename), name=clean_name)))
                except Exception as e:
                    messages.error(request, f"ZIP extract error: {str(e)}")
                    return redirect('candidate_upload', job_id=job.id)
            elif file.name.lower().endswith('.pdf'):
                pdf_files.append((os.path.basename(file.name), file))

        if not pdf_files:
            messages.error(request, "No valid PDF files found in the upload.")
            return redirect('candidate_upload', job_id=job.id)

        count = 0
        for filename, pdf_file in pdf_files:
            candidate_name = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
            candidate = Candidate.objects.create(name=candidate_name, applied_job=job, resume_path=pdf_file)

            full_path = os.path.join(settings.MEDIA_ROOT, candidate.resume_path.name)
            resume_text = extract_text_from_pdf(full_path)

            if resume_text:
                nlp_name = extract_name_nlp(resume_text)
                if nlp_name:
                    candidate.name = nlp_name
                candidate.email = extract_email(resume_text) or f"noemail_{candidate.id}@ats.local"
                candidate.phone = extract_phone(resume_text) or ""
                candidate.experience_years, candidate.experience_level = extract_experience(resume_text)
                candidate.save()

                score, matched, missing = calculate_match_score(resume_text, job.description)
                Score.objects.create(
                    candidate=candidate,
                    job=job,
                    matching_score=score,
                    matched_skills=', '.join(matched),
                    missing_skills=', '.join(missing),
                    explanation=f"Matched {len(matched)} skills ({score}%)."
                )
                send_candidate_status_email(candidate, job, score, ', '.join(matched), ', '.join(missing))
                count += 1

        messages.success(request, f"Successfully processed {count} resume(s)!")
        return redirect('candidate_upload', job_id=job.id)

    candidates = Candidate.objects.filter(applied_job=job).prefetch_related('score_set').order_by('-score__matching_score')

    candidate_scores = []
    for idx, c in enumerate(candidates, start=1):
        score = c.score_set.first()
        candidate_scores.append({
            'rank': idx,
            'candidate': c,
            'score': score,
            'matched_list': score.matched_skills.split(', ') if score and score.matched_skills else [],
            'missing_list': score.missing_skills.split(', ') if score and score.missing_skills else [],
        })

    return render(request, 'pages/candidate_upload.html', {'job': job, 'candidate_scores': candidate_scores})

def upload_resumes_view(request):
    """Alias for bulk_upload_resumes_view"""
    return bulk_upload_resumes_view(request)


# =========================================================
# 4. CANDIDATE MANAGEMENT & RANKING VIEWS
# =========================================================
def candidate_list_view(request, job_id=None):
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    jobs = Job.objects.all().order_by('-created_at')
    selected_job = None
    candidates = []

    if job_id:
        selected_job = get_object_or_404(Job, id=job_id)
        candidates = Candidate.objects.filter(applied_job=selected_job).prefetch_related('score_set').order_by('-score__matching_score')
    elif jobs.exists():
        selected_job = jobs.first()
        candidates = Candidate.objects.filter(applied_job=selected_job).prefetch_related('score_set').order_by('-score__matching_score')

    context = {
        'jobs': jobs,
        'selected_job': selected_job,
        'candidates': candidates,
    }
    return render(request, 'pages/candidate_list.html', context)

def candidate_detail_view(request, candidate_id):
    """Detailed view for a single candidate"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    candidate = get_object_or_404(Candidate.objects.select_related('applied_job'), id=candidate_id)
    score = candidate.score_set.first()
    return render(request, 'pages/candidate_detail.html', {'candidate': candidate, 'score': score})

def delete_candidate_view(request, candidate_id):
    """Delete candidate record"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')
    candidate = get_object_or_404(Candidate, id=candidate_id)
    job_id = candidate.applied_job.id if candidate.applied_job else None
    candidate.delete()
    messages.success(request, "Candidate deleted successfully.")
    if job_id:
        return redirect('candidate_list', job_id=job_id)
    return redirect('bulk_upload')


# =========================================================
# 5. EXPORT UTILITIES (CSV & EXCEL)
# =========================================================
# =========================================================
# 5. EXPORT UTILITIES (CSV & EXCEL)
# =========================================================
def export_csv_view(request, job_id):
    """Exports full candidate details (with Status, AI Explanation, etc.) as CSV"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    job = get_object_or_404(Job, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job).select_related('applied_job').prefetch_related('score_set').order_by('-score__matching_score')
    return util_export_csv(candidates)

def export_excel_view(request, job_id):
    """Exports full candidate details (with Status, AI Explanation, etc.) as a properly formatted .xlsx"""
    if 'user_id' not in request.session:
        return redirect('/?mode=login')

    job = get_object_or_404(Job, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job).select_related('applied_job').prefetch_related('score_set').order_by('-score__matching_score')
    return util_export_excel(candidates)