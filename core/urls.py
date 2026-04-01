from django.urls import path

from . import views

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('flagged-items/', views.flagged_items, name='flagged_items'),
    path('resolve-flag/<int:report_id>/', views.resolve_flag, name='resolve_flag'),
    path('all-reports/', views.all_reports_list, name='all_reports_list'),
    path('export-reports/', views.export_reports_csv, name='export_reports_csv'),
    path('manage-users/toggle/<int:user_id>/', views.toggle_user_active, name='admin_toggle_user'),
    path('analytics/', views.site_analytics, name='site_analytics'),
]