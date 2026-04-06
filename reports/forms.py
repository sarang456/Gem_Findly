from django import forms
from core.models import Report, Item

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

    reward_amount = forms.DecimalField(
        required=False,
        initial=0,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'notion-input',
            'placeholder': 'Offer a reward? (Optional ₹)'
        })
    )

# forms.py
class FlagReportForm(forms.Form):
    REASON_CHOICES = [
        ('spam', 'Spam / Fake Listing'),
        ('inappropriate', 'Inappropriate Content / Language'),
        ('wrong_category', 'Wrong Category'),
        ('harassment', 'Harassment / Privacy Violation'),
        ('other', 'Other (Explain below)'),
    ]
    reason_type = forms.ChoiceField(choices=REASON_CHOICES, widget=forms.Select(attrs={'class': 'notion-input'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'class': 'notion-input', 'rows': 4, 'placeholder': 'Tell us more...'}))