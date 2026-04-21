
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('admin-requests/', views.admin_requests, name='admin_requests'),
    path('admin-requests/approve/<int:user_id>/', views.approve_admin, name='approve_admin'),
    path('admin-requests/reject/<int:user_id>/', views.reject_admin, name='reject_admin'),
    path('profile/', views.profile_view, name='profile'), 
    path('profile/<int:user_id>/', views.profile_view, name='public_profile'),
    path('settings/', views.settings_view, name='settings'),
    path('password/', views.MyPasswordChangeView.as_view(), name='password_change'),
    path('deactivate/', views.deactivate_account, name='deactivate_account'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('donate/', views.initiate_donation, name='donate'),
    path('donate/payment-success/', views.payment_success, name='payment_success'),
    path('admin/transactions/', views.admin_transaction_manager, name='admin_transactions'),
    path('admin/transactions/sync/<int:donation_id>/', views.sync_transaction, name='sync_transaction'),
]