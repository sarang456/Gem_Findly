from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
    path('match/<int:match_id>/challenge/', views.claim_challenge, name='claim_challenge'),
    path('match/<int:match_id>/review/', views.review_claim, name='review_claim'),
    path('match/close/<int:match_id>/', views.close_case, name='close_case'),
    path('start-claim/<int:report_id>/', views.start_claim_process, name='start_claim'),
    path('history/', views.history, name='history'),
    path('match/claim/<int:match_id>/', views.claim_match, name='claim_match'),
    path('match/resolve/<int:match_id>/', views.resolve_match, name='resolve_match'),
    path('match/public/<int:match_id>/', views.match_detail_public, name='match_detail_public'),
    path('my-reports/', views.my_reports, name='user_reports'),
]