from django.contrib import admin
from .models import User, Job, Candidate, Score


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'is_active', 'created_at')
    search_fields = ('username', 'email')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title',)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'job', 'uploaded_at')
    search_fields = ('name', 'email')


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'overall_score', 'status', 'email_sent')
    list_filter = ('status', 'email_sent')