from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'notion-input', 'placeholder': 'Enter your email'
    }))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'notion-input', 'placeholder': 'First Name'
    }))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'notion-input', 'placeholder': 'Last Name'
    }))
    
    GENDER_CHOICES = (('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other'))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, widget=forms.Select(attrs={'class': 'notion-input'}))
    
    ROLE_CHOICES = [('user', 'Standard User'), ('admin', 'Staff')]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'notion-input'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name", "gender", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'notion-input'})
            if 'password' in field_name:
                field.widget.attrs.update({'placeholder': 'Enter Password'})


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(disabled=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control rounded-pill'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-pill bg-light'}),
        }