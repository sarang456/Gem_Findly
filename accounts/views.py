from django.shortcuts import render, redirect, get_object_or_404
from .forms import UserRegisterForm, UserUpdateForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from core.models import Report
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from core.models import OTPVerification
from core.signals import send_verification_email
import random

User = get_user_model()

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # CRITICAL: User cannot login yet!
            user.save()

            request.session['otp_user_id'] = user.id
            return redirect('verify_otp')

    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            if user is not None:
                login(request, user)
                
                # --- START ADMIN REDIRECT LOGIC ---
                
                if user.is_staff:
                    return redirect('admin_dashboard') # Must match name in urls.py
                else:
                    return redirect('dashboard') # Send regular users to their Workspace
                # --- END ADMIN REDIRECT LOGIC ---
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def profile_view(request, user_id=None):
    User = get_user_model()
    # 1. Determine whose profile we are looking at
    if user_id:
        target_user = get_object_or_404(User, id=user_id)
        is_own_profile = (target_user == request.user)
    else:
        target_user = request.user
        is_own_profile = True

    # 2. Get stats for the TARGET user, not the request.user
    user_reports = Report.objects.filter(user=target_user)
    total_reports = user_reports.count()
    resolved_reports = user_reports.filter(is_resolved=True).count()
    
    trust_percentage = int((resolved_reports / total_reports) * 100) if total_reports > 0 else 100

    return render(request, 'accounts/profile.html', {
        'target_user': target_user, # Use this in the template instead of 'user'
        'is_own_profile': is_own_profile,
        'total_reports': total_reports,
        'resolved_reports': resolved_reports,
        'trust_percentage': trust_percentage,
    })

@login_required
def settings_view(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated!")
            return redirect('profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    return render(request, 'accounts/settings.html', {'form': form})

class MyPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('profile') # Redirect after success

    def form_valid(self, form):
        messages.success(self.request, "Your password was successfully updated!")
        return super().form_valid(form)
    
@login_required
def deactivate_account(request):
    if request.method == 'POST':
        user = request.user
        # 1. Log them out first
        logout(request)
        # 2. Deactivate the account (Soft Delete)
        user.is_active = False
        user.save()
        
        messages.success(request, "Your account has been deactivated. We're sorry to see you go.")
        return redirect('home')
    
    # If they try to GET this page, just send them back to settings
    return redirect('settings')



def verify_otp(request):
    # 1. Get the user from the session (saved during register view)
    user_id = request.session.get('otp_user_id')
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')

    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        entered_otp = request.POST.get('otp_code')
        otp_record = OTPVerification.objects.filter(user=user, otp_code=entered_otp).first()

        # 2. Check if OTP is correct and not expired
        if otp_record:
            # We will add an 'is_expired' check here later
            user.is_active = True
            user.save()
            
            # Cleanup: Delete the OTP so it can't be used again
            otp_record.delete()
            
            # Log them in and send to dashboard
            login(request, user)
            del request.session['otp_user_id'] # Clear session
            messages.success(request, "Email verified! Welcome to Findly.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid OTP code. Please try again.")

    return render(request, 'accounts/verify_otp.html', {'email': user.email})

def resend_otp(request):
    # 1. Identify the user from the session
    user_id = request.session.get('otp_user_id')
    
    if not user_id:
        messages.error(request, "Session expired. Please register again.")
        return redirect('register')

    try:
        user = User.objects.get(id=user_id)
        
        # 2. Trigger the Master Logic from signals.py
        # This generates a new code and sends the email
        send_verification_email(user)
        
        messages.success(request, "A fresh 6-digit code has been sent to your inbox.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('register')

    # 3. Stay on the same verification page
    return redirect('verify_otp')

