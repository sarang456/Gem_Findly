from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('listings/', views.listings, name='listings'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('flagged-items/', views.flagged_items, name='flagged_items'),
    path('report/new/', views.create_report, name='create_report'),
    path('report-item/<int:report_id>/', views.report_item, name='report_item'),
    path('match/public/<int:match_id>/', views.match_detail_public, name='match_detail_public'),
    path('resolve-flag/<int:report_id>/', views.resolve_flag, name='resolve_flag'),
    path('match/claim/<int:match_id>/', views.claim_match, name='claim_match'),
    path('match/<int:match_id>/challenge/', views.claim_challenge, name='claim_challenge'),
    path('match/<int:match_id>/review/', views.review_claim, name='review_claim'),
    path('match/resolve/<int:match_id>/', views.resolve_match, name='resolve_match'),
    path('item/<int:report_id>/', views.item_details, name='item_details'),
    path('start-claim/<int:report_id>/', views.start_claim_process, name='start_claim'),
    path('match/close/<int:match_id>/', views.close_case, name='close_case'),
    path('history/', views.history, name='history'),
    
    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('match/<int:match_id>/', views.match_detail, name='match_detail'),
]