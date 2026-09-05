"""URL configuration for the core app."""
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),

    # Root / Landing (shows login when logged out, dashboard when logged in)
    path('', views.home_view, name='home'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Jobs
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/delete/', views.job_delete, name='job_delete'),

    # Candidates
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/upload/', views.candidate_upload, name='candidate_upload'),
    path('candidates/compare/', views.candidate_compare, name='candidate_compare'),
    path('candidates/bulk-action/', views.candidate_bulk_action, name='candidate_bulk_action'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:candidate_id>/status/', views.candidate_update_status, name='candidate_update_status'),
    path('candidates/<int:candidate_id>/notes/', views.candidate_update_notes, name='candidate_update_notes'),

    # Email generation
    path('scores/<int:score_id>/email/', views.generate_email_view, name='generate_email'),

    # Reports
    path('reports/', views.reports, name='reports'),
    path('reports/export/excel/', views.export_excel_view, name='export_excel'),
    path('reports/export/csv/', views.export_csv_view, name='export_csv'),
]