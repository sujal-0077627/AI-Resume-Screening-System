from django.db import models

class User(models.Model):
    username = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True)
    password_hash = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class Job(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Candidate(models.Model):
    EXPERIENCE_LEVELS = [
        ('Fresher', 'Fresher'),
        ('Junior', 'Junior'),
        ('Senior', 'Senior'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    experience_years = models.IntegerField(default=0)
    experience_level = models.CharField(
        max_length=20, choices=EXPERIENCE_LEVELS, default='Fresher'
    )
    resume_path = models.FileField(upload_to='resumes/')
    applied_job = models.ForeignKey(Job, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Score(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    matching_score = models.FloatField(default=0.0)
    matched_skills = models.TextField(blank=True)
    missing_skills = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate.name} - {self.matching_score}%"

class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.otp}"
