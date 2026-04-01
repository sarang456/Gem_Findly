from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


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

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(disabled=True) # Protect the email from easy changes

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-pill bg-light'}),
        }