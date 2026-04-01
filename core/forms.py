from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model  # Fact: This is the safest way to refer to your User
from .models import Item, Report

User = get_user_model()


# core/forms.py

