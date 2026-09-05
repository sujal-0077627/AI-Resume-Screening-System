import re
import secrets
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from .models import User, Job, Candidate, Score
from .utils.pdf_extractor import extract_text_from_document
from .utils.contact_extractor import extract_contact_details
from .utils.matcher import compute_match
from .utils.explainer import generate_explanation
from .utils.email_generator import generate_email, send_email, send_password_reset_email
from .utils.reports import export_excel, export_csv
from .utils.otp import generate_otp, send_otp_email

# Login brute-force protection settings
LOGIN_MAX_ATTEMPTS = 5        # max failed attempts before lockout
LOGIN_LOCKOUT_MINUTES = 15    # how long the account stays locked


# ---------- Authentication ----------


def login_view(request):
    """Admin login using bcrypt password hashing (verified users only)."""
    if request.method == 'POST':
        login_id = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # --- Brute-force protection: track failed attempts per identifier (Server Cache + Session) ---
        lock_key = f'login_lock_{login_id.lower()}'
        count_key = f'login_count_{login_id.lower()}'
        lock_until = cache.get(lock_key) or request.session.get(lock_key, '')

        if lock_until:
            try:
                from django.utils.dateparse import parse_datetime
                lock_dt = parse_datetime(lock_until)
                if lock_dt and timezone.now() < lock_dt:
                    mins_left = int((lock_dt - timezone.now()).total_seconds() // 60) + 1
                    messages.error(
                        request,
                        "Too many failed attempts. Please try again in " + str(mins_left) + " minute(s)."
                    )
                    return render(request, 'login.html')
                # Lock expired - clear lockout state
                cache.delete(lock_key)
                cache.delete(count_key)
                request.session.pop(lock_key, None)
                request.session.pop(count_key, None)
            except (ValueError, TypeError):
                cache.delete(lock_key)
                cache.delete(count_key)
                request.session.pop(lock_key, None)
                request.session.pop(count_key, None)

        try:
            # Allow login with either username or email
            user = User.objects.filter(username=login_id).first() or User.objects.filter(email=login_id).first()
            if user is None:
                raise User.DoesNotExist
            if not user.is_verified:
                messages.warning(request, "Please verify your email first via OTP.")
                return render(request, 'login.html')
            if user.check_password(password) and user.is_active:
                # Successful login - clear any lockout state
                cache.delete(lock_key)
                cache.delete(count_key)
                request.session.pop(lock_key, None)
                request.session.pop(count_key, None)
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                # Handle "Remember me" checkbox - extend session if checked
                if request.POST.get('remember'):
                    request.session.set_expiry(1209600)  # 2 weeks
                messages.success(request, "Welcome back, " + user.username + "!")
                return redirect('dashboard')
            else:
                # Wrong password - count the attempt
                attempts = (cache.get(count_key) or request.session.get(count_key, 0)) + 1
                cache.set(count_key, attempts, timeout=900)
                request.session[count_key] = attempts
                if attempts >= LOGIN_MAX_ATTEMPTS:
                    lock_expire = (timezone.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).isoformat()
                    cache.set(lock_key, lock_expire, timeout=LOGIN_LOCKOUT_MINUTES * 60)
                    request.session[lock_key] = lock_expire
                    cache.delete(count_key)
                    request.session.pop(count_key, None)
                    messages.error(
                        request,
                        "Too many failed attempts. Account locked for " + str(LOGIN_LOCKOUT_MINUTES) + " minutes."
                    )
                else:
                    messages.error(request, "Invalid email/username or password.")
        except User.DoesNotExist:
            # Count attempts even for unknown users (prevents user enumeration via timing)
            attempts = (cache.get(count_key) or request.session.get(count_key, 0)) + 1
            cache.set(count_key, attempts, timeout=900)
            request.session[count_key] = attempts
            if attempts >= LOGIN_MAX_ATTEMPTS:
                lock_expire = (timezone.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).isoformat()
                cache.set(lock_key, lock_expire, timeout=LOGIN_LOCKOUT_MINUTES * 60)
                request.session[lock_key] = lock_expire
                cache.delete(count_key)
                request.session.pop(count_key, None)
                messages.error(
                    request,
                    "Too many failed attempts. Account locked for " + str(LOGIN_LOCKOUT_MINUTES) + " minutes."
                )
            else:
                messages.error(request, "Invalid email/username or password.")

    return render(request, 'login.html')


def forgot_password_view(request):
    """Allow a user to request a password reset link by entering their email."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email=email).first()

        # Always show the same message whether or not the email exists
        if user:
            # Generate a secure random token valid for 30 minutes
            raw_token = secrets.token_urlsafe(48)
            user.set_reset_token(raw_token)
            user.save()

            # Build reset link
            reset_url = request.build_absolute_uri(
                f"/reset-password/{raw_token}/"
            )

            # Try to send via email; fallback prints to console (demo mode)
            sent = send_password_reset_email(email, reset_url)
            if sent:
                messages.success(
                    request,
                    "Password reset link sent to your email. The link is valid for 30 minutes."
                )
            else:
                messages.info(
                    request,
                    f"Reset link generated. In demo mode, check the server console and use: {reset_url}"
                )
        else:
            messages.success(
                request,
                "If that email exists, a password reset link has been sent."
            )
        return redirect('forgot_password')

    return render(request, 'forgot_password.html')


def reset_password_view(request, token):
    """Allow a user to set a new password using a valid reset token."""
    # Find matching user via secure verification
    target_user = None
    for u in User.objects.exclude(reset_token=''):
        if u.verify_reset_token(token):
            target_user = u
            break

    if not target_user:
        messages.error(request, "Invalid or expired reset link. Please request a new one.")
        return redirect('forgot_password')

    # Check token expiry (30 minutes)
    if target_user.reset_token_created:
        if timezone.now() > target_user.reset_token_created + timedelta(minutes=30):
            target_user.reset_token = ''
            target_user.reset_token_created = None
            target_user.save()
            messages.error(request, "This reset link has expired. Please request a new one.")
            return redirect('forgot_password')
    else:
        messages.error(request, "Invalid reset link. Please request a new one.")
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'reset_password.html', {'token': token})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'reset_password.html', {'token': token})

        # Set new password and clear token
        target_user.set_password(new_password)
        target_user.reset_token = ''
        target_user.reset_token_created = None
        target_user.is_verified = True
        target_user.save()

        messages.success(request, "Password reset successfully! Please login with your new password.")
        return redirect('login')

    return render(request, 'reset_password.html', {'token': token})


def register_view(request):
    """Register a new admin user."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validation
        if not username or not email or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, 'register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'register.html')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return render(request, 'register.html')

        # Create user with bcrypt password
        user = User(username=username, email=email, full_name=username)
        user.set_password(password)

        # Generate OTP and store securely
        otp = generate_otp(6)
        user.set_otp(otp)
        user.save()
        sent = send_otp_email(email, otp)

        # Store in session for verification
        request.session['pending_user_id'] = user.id
        request.session['pending_email'] = email

        smtp_configured = bool(
            os.environ.get('SMTP_HOST') and os.environ.get('SMTP_USER') and os.environ.get('SMTP_PASSWORD')
        )
        if smtp_configured and sent:
            messages.success(request, f"Account created! OTP sent to {email}. Please check your inbox.")
        else:
            messages.info(request, f"Account created! [Verification OTP: {otp}] Please enter it below to verify.")
        return redirect('verify_otp')

    return render(request, 'register.html')


def verify_otp_view(request):
    """Verify OTP for pending registration (with 10-minute expiration & brute force limit)."""
    user_id = request.session.get('pending_user_id')
    if not user_id:
        messages.warning(request, "No pending registration found. Please register first.")
        return redirect('register')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()

        if not otp:
            messages.error(request, "Please enter the OTP.")
            return render(request, 'verify_otp.html', {'email': request.session.get('pending_email')})

        # Check OTP rate-limiting (max 5 invalid attempts)
        attempts_key = f'otp_attempts_{user.id}'
        attempts = cache.get(attempts_key, 0)
        if attempts >= 5:
            messages.error(request, "Too many invalid OTP attempts. Please register again.")
            return render(request, 'verify_otp.html', {'email': request.session.get('pending_email')})

        # Check OTP expiration (10 minutes)
        if user.otp_created_at and timezone.now() > user.otp_created_at + timedelta(minutes=10):
            messages.error(request, "OTP has expired. Please register again to get a new OTP.")
            return render(request, 'verify_otp.html', {'email': request.session.get('pending_email')})

        if user.verify_otp(otp):
            user.is_verified = True
            user.otp_secret = ''
            user.otp_created_at = None
            user.save()
            cache.delete(attempts_key)
            request.session.pop('pending_user_id', None)
            request.session.pop('pending_email', None)
            messages.success(request, "Email verified successfully! Please login.")
            return redirect('login')
        else:
            attempts += 1
            cache.set(attempts_key, attempts, timeout=600)
            messages.error(request, f"Invalid OTP. {5 - attempts} attempt(s) remaining.")
            return render(request, 'verify_otp.html', {'email': request.session.get('pending_email')})

    return render(request, 'verify_otp.html', {'email': request.session.get('pending_email')})


def logout_view(request):
    """Logout the admin user."""
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect('login')


def _require_login(view_func):
    """Decorator to protect views."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def home_view(request):
    """Root: always show login page so user can login/register anytime."""
    return render(request, 'login.html')


# ---------- Dashboard ----------

@_require_login
def dashboard(request):
    """Dashboard with stats and recent activities."""
    total_jobs = Job.objects.count()
    total_candidates = Candidate.objects.count()
    total_scores = Score.objects.count()
    shortlisted = Score.objects.filter(status__in=['shortlisted', 'selected', 'interview', 'offered', 'hired']).count()
    rejected = Score.objects.filter(status='rejected').count()

    # Average score
    scores = Score.objects.all()
    avg_score = 0.0
    if scores:
        avg_score = round(sum(s.overall_score for s in scores) / len(scores), 1)

    recent_scores = scores[:6]

    context = {
        'total_jobs': total_jobs,
        'total_candidates': total_candidates,
        'total_scores': total_scores,
        'selected': shortlisted,
        'shortlisted': shortlisted,
        'rejected': rejected,
        'avg_score': avg_score,
        'recent_scores': recent_scores,
    }
    return render(request, 'dashboard.html', context)


# ---------- Jobs ----------

@_require_login
def job_list(request):
    """List all jobs with candidates count."""
    jobs = Job.objects.all().order_by('-created_at')
    return render(request, 'jobs/job_list.html', {'jobs': jobs})


@_require_login
def job_create(request):
    """Create a new job posting with custom cutoff score and company name."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        company_name = request.POST.get('company_name', 'Your Company').strip() or "Your Company"
        cutoff_score_val = request.POST.get('cutoff_score', '75').strip()
        exp_req_val = request.POST.get('experience_required', '0').strip()

        if not title or not description:
            messages.error(request, "Title and Job Description are required.")
            return render(request, 'jobs/job_form.html')

        try:
            cutoff = float(cutoff_score_val)
        except ValueError:
            cutoff = 75.0

        try:
            exp_req = int(exp_req_val)
        except ValueError:
            exp_req = 0

        job = Job.objects.create(
            title=title,
            description=description,
            company_name=company_name,
            cutoff_score=cutoff,
            experience_required=exp_req,
        )
        messages.success(request, f"Job '{title}' created successfully with {cutoff:.0f}% shortlist cutoff!")
        return redirect('job_list')

    return render(request, 'jobs/job_form.html')


@_require_login
def job_detail(request, job_id):
    """View job details and its candidates/scores."""
    job = get_object_or_404(Job, id=job_id)
    scores = Score.objects.filter(job=job)
    return render(request, 'jobs/job_detail.html', {'job': job, 'scores': scores})


@_require_login
def job_delete(request, job_id):
    """Delete a job posting and its associated candidates/scores."""
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        for candidate in job.candidates.all():
            if candidate.resume:
                try:
                    candidate.resume.delete(save=False)
                except Exception:
                    pass
        job.delete()
        messages.success(request, f"Job '{job.title}' deleted successfully.")
        return redirect('job_list')
    return redirect('job_list')


# ---------- Candidates ----------

def _process_single_resume(job, resume_file):
    """
    Process a single resume: extract text, contacts, compute match, create score.
    Emails are drafted safely into score.email_content, but NOT automatically dispatched.
    """
    try:
        # Save candidate instance
        candidate = Candidate.objects.create(
            job=job,
            resume=resume_file,
        )

        # Extract text (.pdf, .docx, .txt)
        extracted_text = extract_text_from_document(candidate.resume.path)
        candidate.extracted_text = extracted_text

        # Extract contact details, links, experience, and name
        contacts = extract_contact_details(extracted_text)
        candidate.email = contacts.get('email', '')
        candidate.phone = contacts.get('phone', '')
        candidate.experience_years = contacts.get('experience_years', 0.0)
        candidate.github_url = contacts.get('github_url', '')
        candidate.linkedin_url = contacts.get('linkedin_url', '')
        candidate.portfolio_url = contacts.get('portfolio_url', '')
        candidate.name = contacts.get('name', '') or "Candidate"
        candidate.save()

        # Compute match score
        match_result = compute_match(job, extracted_text, candidate_exp=candidate.experience_years)

        # Generate human-readable explanation
        explanation = generate_explanation(job, extracted_text, match_result, candidate_exp=candidate.experience_years)

        # Create score instance
        score = Score.objects.create(
            candidate=candidate,
            job=job,
            overall_score=match_result['overall_score'],
            tfidf_score=match_result['tfidf_score'],
            semantic_score=match_result['semantic_score'],
            experience_score=match_result.get('experience_score', 100.0),
            explanation=explanation,
            matched_skills=', '.join(match_result['matched_skills']),
            missing_skills=', '.join(match_result['missing_skills']),
        )

        # Auto-assign initial status based on job cutoff threshold
        cutoff = getattr(job, 'cutoff_score', 75.0)
        score.status = 'shortlisted' if match_result['overall_score'] >= cutoff else 'screened'
        score.save()

        # Pre-draft email content (safe: email_sent remains False until recruiter sends it)
        if candidate.email:
            company = getattr(job, 'company_name', 'Your Company') or "Your Company"
            email = generate_email(
                candidate_name=candidate.name or "Candidate",
                job_title=job.title,
                company_name=company,
                status=score.status,
                score=score.overall_score,
                explanation=explanation,
            )
            score.email_content = f"Subject: {email['subject']}\n\n{email['body']}"
            score.email_sent = False
            score.save()

        return candidate, score, match_result

    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"An error occurred: {e}"


@_require_login
def candidate_upload(request):
    """Upload one or more resume documents (.pdf, .docx, .txt) and run AI screening."""
    jobs = Job.objects.all()

    if request.method == 'POST':
        job_id = request.POST.get('job')
        resume_files = request.FILES.getlist('resume')

        if not job_id or not resume_files:
            messages.error(request, "Please select a job and upload at least one resume document.")
            return render(request, 'candidates/candidate_upload.html', {'jobs': jobs})

        job = get_object_or_404(Job, id=job_id)

        # Validate file extensions
        valid_extensions = ('.pdf', '.docx', '.doc', '.txt', '.rtf')
        invalid_files = []
        for f in resume_files:
            lower = f.name.lower()
            if not any(lower.endswith(ext) for ext in valid_extensions):
                invalid_files.append(f.name)

        if invalid_files:
            messages.error(
                request,
                f"Supported file formats: PDF, Word (.docx), and Text (.txt). Invalid: {', '.join(invalid_files)}"
            )
            return render(request, 'candidates/candidate_upload.html', {'jobs': jobs})

        processed = 0
        errors = []
        last_candidate_id = None

        for resume_file in resume_files:
            result = _process_single_resume(job, resume_file)

            if isinstance(result, str):
                errors.append(f"{resume_file.name}: {result}")
            else:
                candidate, score, match_result = result
                processed += 1
                last_candidate_id = candidate.id

        # Build notification message
        messages_parts = []
        if processed > 0:
            messages_parts.append(f"✅ {processed} resume(s) successfully screened!")
        if errors:
            messages_parts.append(f"❌ {len(errors)} resume(s) failed:")
            for err in errors:
                messages_parts.append(f"  • {err}")

        messages.info(request, "<br>".join(messages_parts))

        if last_candidate_id:
            return redirect('candidate_detail', candidate_id=last_candidate_id)
        return render(request, 'candidates/candidate_upload.html', {'jobs': jobs})

    return render(request, 'candidates/candidate_upload.html', {'jobs': jobs})


@_require_login
def candidate_list(request):
    """
    List all candidates with search, filtering (by job, status, min score), and ranking.
    """
    candidates = Candidate.objects.all().select_related('job').prefetch_related('scores')
    jobs = Job.objects.all().order_by('title')

    # Query params
    query = request.GET.get('q', '').strip()
    job_filter = request.GET.get('job', '').strip()
    status_filter = request.GET.get('status', '').strip()
    min_score = request.GET.get('min_score', '').strip()

    if job_filter:
        candidates = candidates.filter(job_id=job_filter)

    if query:
        candidates = candidates.filter(
            name__icontains=query
        ) | candidates.filter(
            email__icontains=query
        ) | candidates.filter(
            extracted_text__icontains=query
        )

    # Attach score for sorting and filtering
    candidate_data = []
    for c in candidates:
        score_obj = c.scores.first()
        score_val = score_obj.overall_score if score_obj else 0.0
        status_val = score_obj.status if score_obj else 'applied'

        # Filter by status if requested
        if status_filter and status_filter != 'all' and status_val != status_filter:
            continue

        # Filter by min score if requested
        if min_score:
            try:
                if score_val < float(min_score):
                    continue
            except ValueError:
                pass

        candidate_data.append((score_val, c, score_obj))

    # Sort descending by score
    candidate_data.sort(key=lambda x: (-x[0], x[1].name or ''))
    filtered_candidates = [item[1] for item in candidate_data]

    context = {
        'candidates': filtered_candidates,
        'jobs': jobs,
        'selected_job': job_filter,
        'selected_status': status_filter,
        'search_query': query,
        'min_score': min_score,
        'status_choices': Score.STATUS_CHOICES,
    }
    return render(request, 'candidates/candidate_list.html', context)


@_require_login
def candidate_detail(request, candidate_id):
    """View candidate details, ATS score breakdown, links, and recruiter notes."""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    score = Score.objects.filter(candidate=candidate).first()

    matched_list = []
    missing_list = []
    job_skills_count = 0
    if score:
        matched_list = [s for s in score.matched_skills.split(', ') if s.strip()]
        missing_list = [s for s in score.missing_skills.split(', ') if s.strip()]
        job_skills_count = len(score.job.skills_list())

    return render(request, 'candidates/candidate_detail.html', {
        'candidate': candidate,
        'score': score,
        'matched_list': matched_list,
        'missing_list': missing_list,
        'job_skills_count': job_skills_count,
        'status_choices': Score.STATUS_CHOICES,
    })


@_require_login
def candidate_compare(request):
    """
    Side-by-side comparison matrix of 2 to 4 candidates.
    """
    ids_param = request.GET.get('ids', '')
    ids_list = request.GET.getlist('c')

    if ids_param:
        ids_list = [i.strip() for i in ids_param.split(',') if i.strip().isdigit()]

    if not ids_list:
        messages.warning(request, "Please select candidates from the list to compare.")
        return redirect('candidate_list')

    candidates = Candidate.objects.filter(id__in=ids_list).select_related('job').prefetch_related('scores')
    if not candidates:
        messages.warning(request, "No valid candidates selected for comparison.")
        return redirect('candidate_list')

    comparison_data = []
    for c in candidates:
        score_obj = c.scores.first()
        matched = [s for s in score_obj.matched_skills.split(', ') if s.strip()] if score_obj else []
        missing = [s for s in score_obj.missing_skills.split(', ') if s.strip()] if score_obj else []
        comparison_data.append({
            'candidate': c,
            'score': score_obj,
            'matched_skills': matched,
            'missing_skills': missing,
        })

    return render(request, 'candidates/candidate_compare.html', {
        'comparison_data': comparison_data,
    })


@_require_login
def candidate_update_status(request, candidate_id):
    """Recruiter action to update candidate recruitment status and automatically send email."""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    score = Score.objects.filter(candidate=candidate).first()

    if request.method == 'POST' and score:
        new_status = request.POST.get('status', '').strip()
        valid_statuses = dict(Score.STATUS_CHOICES).keys()
        if new_status in valid_statuses:
            score.status = new_status

            # Generate fresh email tailored to this new status
            company = getattr(score.job, 'company_name', 'Your Company') or "Your Company"
            email = generate_email(
                candidate_name=candidate.name or "Candidate",
                job_title=score.job.title,
                company_name=company,
                status=new_status,
                score=score.overall_score,
                explanation=score.explanation,
            )
            score.email_content = f"Subject: {email['subject']}\n\n{email['body']}"

            # Automatically dispatch email if candidate has an email address
            if candidate.email:
                send_res = send_email(
                    to_email=candidate.email,
                    subject=email['subject'],
                    body=email['body'],
                    from_name=company
                )
                if send_res.get('success'):
                    score.email_sent = True
                    messages.success(
                        request,
                        f"Status updated to '{score.get_status_display()}' & notification email sent successfully to {candidate.email}!"
                    )
                else:
                    messages.warning(
                        request,
                        f"Status updated to '{score.get_status_display()}'. Email delivery note: {send_res.get('message')}"
                    )
            else:
                messages.info(
                    request,
                    f"Status updated to '{score.get_status_display()}'. (Candidate has no email address on file)."
                )

            score.save()
        else:
            messages.error(request, "Invalid status choice.")

    return redirect('candidate_detail', candidate_id=candidate.id)


@_require_login
def candidate_update_notes(request, candidate_id):
    """Recruiter action to save evaluation notes."""
    candidate = get_object_or_404(Candidate, id=candidate_id)

    if request.method == 'POST':
        notes = request.POST.get('notes', '').strip()
        candidate.notes = notes
        candidate.save()
        messages.success(request, "Recruiter evaluation notes saved successfully!")

    return redirect('candidate_detail', candidate_id=candidate.id)


@_require_login
def candidate_bulk_action(request):
    """Perform bulk actions (e.g. bulk status update or bulk email dispatch)."""
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        candidate_ids = request.POST.getlist('candidate_ids')

        if not candidate_ids:
            messages.warning(request, "No candidates were selected.")
            return redirect('candidate_list')

        candidates = Candidate.objects.filter(id__in=candidate_ids)

        if action == 'shortlist':
            for c in candidates:
                for s in c.scores.all():
                    s.status = 'shortlisted'
                    s.save()
            messages.success(request, f"Marked {candidates.count()} candidate(s) as Shortlisted.")

        elif action == 'reject':
            for c in candidates:
                for s in c.scores.all():
                    s.status = 'rejected'
                    s.save()
            messages.success(request, f"Marked {candidates.count()} candidate(s) as Rejected.")

        elif action == 'send_emails':
            sent_count = 0
            for c in candidates:
                s = c.scores.first()
                if s and c.email and s.email_content:
                    lines = s.email_content.split('\n\n', 1)
                    subject = lines[0].replace('Subject:', '').strip() if lines else "Application Update"
                    body = lines[1] if len(lines) > 1 else s.email_content
                    result = send_email(to_email=c.email, subject=subject, body=body)
                    if result['success']:
                        s.email_sent = True
                        s.save()
                        sent_count += 1
            messages.success(request, f"Sent emails to {sent_count} candidate(s).")

        elif action == 'delete':
            count = candidates.count()
            for c in candidates:
                if c.resume:
                    try:
                        c.resume.delete(save=False)
                    except Exception:
                        pass
            candidates.delete()
            messages.success(request, f"Deleted {count} candidate(s).")

    return redirect('candidate_list')


# ---------- Email Generation & Dispatch ----------

@_require_login
def generate_email_view(request, score_id):
    """Generate and send an email for a candidate based on recruiter review."""
    score = get_object_or_404(Score, id=score_id)

    if request.method == 'POST':
        status = request.POST.get('status', score.status)
        score.status = status

        company = getattr(score.job, 'company_name', 'Your Company') or "Your Company"
        # Generate email content
        email = generate_email(
            candidate_name=score.candidate.name or "Candidate",
            job_title=score.job.title,
            company_name=company,
            status=status,
            score=score.overall_score,
            explanation=score.explanation,
        )
        score.email_content = f"Subject: {email['subject']}\n\n{email['body']}"
        score.save()

        # If user explicitly clicked Send Now
        if request.POST.get('send_now') == '1':
            recipient_email = score.candidate.email
            if recipient_email:
                result = send_email(
                    to_email=recipient_email,
                    subject=email['subject'],
                    body=email['body'],
                    from_name="HR Recruitment Team",
                )
                if result['success']:
                    score.email_sent = True
                    score.save()
                    messages.success(request, f"Email sent successfully to {recipient_email}!")
                else:
                    if 'SMTP not configured' in result['message']:
                        messages.warning(
                            request,
                            "Email content saved! Configure SMTP env vars (SMTP_HOST, SMTP_USER, SMTP_PASSWORD) to send live emails."
                        )
                    else:
                        messages.error(request, result['message'])
            else:
                messages.warning(request, "Candidate has no email address.")
        else:
            messages.success(request, "Email draft generated and saved successfully!")

        return redirect('candidate_detail', candidate_id=score.candidate.id)

    return redirect('candidate_detail', candidate_id=score.candidate.id)


# ---------- Reports ----------

@_require_login
def reports(request):
    """Reports page with export options."""
    scores = Score.objects.all().select_related('candidate', 'job')
    return render(request, 'reports.html', {'scores': scores})


@_require_login
def export_excel_view(request):
    """Export all scores to Excel."""
    scores = Score.objects.all().select_related('candidate', 'job')
    return export_excel(scores)


@_require_login
def export_csv_view(request):
    """Export all scores to CSV."""
    scores = Score.objects.all().select_related('candidate', 'job')
    return export_csv(scores)