
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
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