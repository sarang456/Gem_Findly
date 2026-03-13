from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model  # Fact: This is the safest way to refer to your User
from .models import Item, Report

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'notion-input', 'placeholder': 'Enter your email'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'notion-input', 'placeholder': 'First Name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'notion-input', 'placeholder': 'Last Name'}))
    gender = forms.ChoiceField(choices=(('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')),widget=forms.Select(attrs={'class': 'notion-input'}))
    # If you have a custom 'role' field in your model
    role = forms.ChoiceField(choices=[('user', 'Standard User'), ('admin', 'Staff')], widget=forms.Select(attrs={'class': 'notion-input'}))

    class Meta(UserCreationForm.Meta):
        model = User
        # Fact: If you haven't deleted 'username' from your model, you MUST include it here.
        fields = ("email", "first_name", "last_name", "gender", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Applying your custom styling to the default UserCreationForm fields
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({'class': 'notion-input', 'placeholder': 'Pick a unique username'})
        for field in self.fields:
            if field not in ['email', 'first_name', 'last_name', 'gender']:
                self.fields[field].widget.attrs.update({'class': 'notion-input', 'placeholder': 'Password'})
# core/forms.py

class SmartReportForm(forms.Form):  # Changed from ModelForm to Form
    # Item Fields
    title = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'notion-input'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'notion-input', 'rows': 3}))
    category = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'notion-input', 'placeholder': 'e.g., Electronics, Keys, Wallet...'}))
    image = forms.ImageField(required=False)

    # Report Fields
    report_type = forms.ChoiceField(choices=[('lost', 'Lost'), ('found', 'Found')], widget=forms.Select(attrs={'class': 'notion-input'}))
    location_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'notion-input'}))
    latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    
    # Security Fields
    question_1 = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Question 1', 'class': 'notion-input'}))
    question_2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Question 2', 'class': 'notion-input'}))
    requires_photo_proof = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))