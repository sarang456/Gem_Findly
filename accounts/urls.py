
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
]