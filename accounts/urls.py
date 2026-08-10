from django.urls import path
from . import views

urlpatterns = [
    path('', views.auth_view, name='auth'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('job-upload/', views.job_upload_view, name='job_upload'),
    path('job/<int:job_id>/candidates/', views.candidate_upload_view, name='candidate_upload'),
    path('bulk-upload/', views.bulk_upload_resumes_view, name='bulk_upload'),
    path('candidate/<int:candidate_id>/', views.candidate_detail_view, name='candidate_detail'),
    path('export-csv/<int:job_id>/', views.export_csv_view, name='export_csv'),
    path('export-excel/<int:job_id>/', views.export_excel_view, name='export_excel'),
]