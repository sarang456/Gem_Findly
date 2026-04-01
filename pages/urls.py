from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('help-support/', views.help_support, name='help_support'),
]