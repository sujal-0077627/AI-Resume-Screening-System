"""Explainable AI - generate human-readable reasons for match scores."""


def _score_label(score):
    """Categorize a score into a label."""
    if score >= 80:
        return "Excellent"
    elif score >= 65:
        return "Good"
    elif score >= 45:
        return "Moderate"
    else:
        return "Weak"


def generate_explanation(job, resume_text, match_result, candidate_exp=0.0):
    """
    Generate a detailed, human-readable explanation for a match score.

    Args:
        job: Job model instance.
        resume_text (str): Extracted resume text.
        match_result (dict): Result from compute_match().
        candidate_exp (float): Candidate's estimated years of experience.

    Returns:
        str: Multi-line explanation.
    """
    overall = match_result['overall_score']
    tfidf = match_result['tfidf_score']
    semantic = match_result['semantic_score']
    skill = match_result['skill_score']
    exp_score = match_result.get('experience_score', 100.0)
    matched = match_result['matched_skills']
    missing = match_result['missing_skills']
    cutoff = getattr(job, 'cutoff_score', 75.0)

    lines = []
    lines.append(
        f"Overall match score is {overall:.1f}% ({_score_label(overall)} fit "
        f"for the '{job.title}' position). Job shortlist threshold is {cutoff:.0f}%."
    )

    # Semantic explanation
    lines.append(
        f"• Semantic Alignment: {semantic:.1f}% — Measures deep conceptual alignment between "
        f"the resume's context and the job description using Sentence-Transformers."
    )

    # TF-IDF explanation
    lines.append(
        f"• Technical Terms (TF-IDF): {tfidf:.1f}% — Evaluates n-gram keyword density and "
        f"domain-specific terminology overlap."
    )

    # Skill explanation
    if matched:
        lines.append(
            f"• Skills Match: {skill:.1f}% ({len(matched)} matched: {', '.join(matched)})."
        )
    else:
        lines.append(
            f"• Skills Match: {skill:.1f}% (No explicit required skills found in resume)."
        )

    # Missing skills
    if missing:
        lines.append(f"• Missing Skills: {', '.join(missing)}.")
    else:
        lines.append("• Missing Skills: None — all required skills are present in the resume.")

    # Experience alignment
    req_exp = getattr(job, 'experience_required', 0)
    if req_exp > 0:
        lines.append(
            f"• Experience Match: {exp_score:.1f}% (Candidate: {candidate_exp:.1f} yrs vs Required: {req_exp} yrs)."
        )

    # Verdict
    if overall >= cutoff:
        lines.append(
            f"Verdict: Shortlisted. Candidate meets/exceeds the {cutoff:.0f}% threshold and is recommended for the next stage."
        )
    elif overall >= (cutoff - 15):
        lines.append(
            f"Verdict: Under Review / Borderline. Candidate scored close to the {cutoff:.0f}% cutoff. Recruiter manual review suggested."
        )
    else:
        lines.append(
            f"Verdict: Screened. Candidate score ({overall:.1f}%) is below the {cutoff:.0f}% threshold."
        )

    return "\n".join(lines)


def generate_short_reason(match_result):
    """Generate a short one-line reason for display in lists."""
    overall = match_result['overall_score']
    matched = match_result['matched_skills']
    missing = match_result['missing_skills']

    if overall >= 75:
        reason = f"Strong fit ({overall:.0f}%). "
    elif overall >= 50:
        reason = f"Moderate fit ({overall:.0f}%). "
    else:
        reason = f"Weak fit ({overall:.0f}%). "

    if matched:
        reason += f"Matched: {', '.join(matched[:3])}"
        if len(matched) > 3:
            reason += f" +{len(matched) - 3} more"
    if missing:
        reason += f". Missing: {', '.join(missing[:3])}"

    return reason