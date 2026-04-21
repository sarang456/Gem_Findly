from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from .forms import UserRegisterForm, UserUpdateForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from core.models import Report
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from core.models import OTPVerification
from core.signals import send_verification_email
import random
import razorpay
from django.conf import settings
from core.models import Donation
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags



client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
User = get_user_model()

# Create your views here.
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            selected_role = form.cleaned_data.get('role')
            if selected_role == 'admin':
                user.admin_status = 'pending'
                user.role = 'admin'
            else:
                user.admin_status = 'none'
                user.role = 'user'
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




def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()
        
        if user:
            otp = random.randint(100000, 999999)
            request.session['reset_otp'] = otp
            request.session['reset_email'] = email

            # --- WELL-MANNERED EMAIL LOGIC ---
            subject = 'Reset Your Findly Password'
            from_email = settings.EMAIL_HOST_USER
            to = [email]

            # 1. Prepare context for the HTML template
            context = {
                'user_name': user.first_name,
                'otp': otp,
            }

            # 2. Render the HTML content
            # Ensure you create this file in templates/accounts/emails/otp_mail.html
            html_content = render_to_string('emails/otp_email.html', context)
            
            # 3. Create a plain-text version as a fallback
            text_content = strip_tags(html_content) 

            # 4. Construct the email
            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")

            try:
                msg.send(fail_silently=False)
                messages.success(request, f"A secure code has been sent to {email}")
                print("✅ Well-mannered HTML email sent!")
            except Exception as e:
                print(f"❌ SMTP ERROR: {str(e)}")
                messages.warning(request, "Email service busy. Using terminal debug.")

            return redirect('verify_reset_otp')
            
        else:
            messages.error(request, "No account found with that email.")
            
    return render(request, 'accounts/forgot_password.html')


# accounts/views.py
def reset_password(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')

    if request.method == 'POST':
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if new_password == confirm_password:
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                
                # Success! Now clear the session
                del request.session['reset_email']
                
                messages.success(request, "Password updated successfully! Please login.")
                return redirect('login') # THIS MUST BE REACHED
            except User.DoesNotExist:
                messages.error(request, "User no longer exists.")
                return redirect('forgot_password')
        else:
            messages.error(request, "Passwords do not match.")

    return render(request, 'accounts/reset_password.html')



def verify_reset_otp(request):
    # 1. Security Check: Did they even start the forgot password process?
    if 'reset_otp' not in request.session or 'reset_email' not in request.session:
        messages.error(request, "Session expired. Please start over.")
        return redirect('forgot_password')

    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        saved_otp = request.session.get('reset_otp')

        # 2. Compare. Use string conversion to be safe!
        if str(user_otp) == str(saved_otp):
            # Success! Let them through to the reset page
            messages.success(request, "OTP Verified. Set your new password.")
            # Clear ONLY the OTP from session, keep the email for the next view
            del request.session['reset_otp'] 
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'accounts/verify_reset_otp.html')




@login_required
def approve_admin(request, user_id):
    # SECURITY: Only you (the first superuser) should do this
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access!")
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    target_user.is_admin_approved = True
    target_user.is_staff = True  # Allows them into the /admin panel if they need it
    target_user.save()
    
    messages.success(request, f"Access granted for {target_user.email}.")
    return redirect('admin_requests')

@login_required
def reject_admin(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    target_user.role = 'user' # Strip the admin intent
    target_user.is_admin_approved = False # Just to be safe
    target_user.save()
    
    messages.warning(request, f"Request for {target_user.email} was rejected.")
    return redirect('admin_requests')



@login_required
def admin_requests(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
        
    pending_admins = User.objects.filter(admin_status='pending')
    return render(request, 'accounts/admin_requests.html', {'pending_admins': pending_admins})

# accounts/views.py

@login_required
def approve_admin(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    target_user.admin_status = 'approved' # NEW
    target_user.is_admin_approved = True
    target_user.is_staff = True 
    target_user.save()
    
    messages.success(request, f"Approved {target_user.email}")
    return redirect('admin_requests')

@login_required
def reject_admin(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
        
    target_user = get_object_or_404(User, id=user_id)
    target_user.admin_status = 'rejected' # NEW
    target_user.is_admin_approved = False 
    target_user.is_staff = False
    target_user.save()
    
    messages.warning(request, f"Rejected {target_user.email}")
    return redirect('admin_requests')



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



def initiate_donation(request):
    if request.method == "POST":
        amount_in_rupees = int(request.POST.get('amount', 100))
        amount_in_paise = amount_in_rupees * 100 
        client = razorpay.Client(auth=("rzp_test_SYypqSe8o0hG0x", "pu65jh4l769wVWDQw3Xm5yuA"))

        # Create Order
        payment = client.order.create({'amount': amount_in_paise, 'currency': "INR", "payment_capture": "1"})
        
        # Save to DB
        Donation.objects.create(
            user=request.user, 
            amount=amount_in_rupees, 
            razorpay_order_id=payment['id'], 
            status="Pending"
        )
        
        # Pass 'payment' to the template
        return render(request, 'donations/donate_form.html', {
            'payment': payment, 
            'amount_display': amount_in_rupees
        })
    
    return render(request, 'donations/donate_form.html')


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        # Razorpay sends these 3 things automatically in the POST body
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        # Find the donation record we created in initiate_donation
        donation = Donation.objects.filter(razorpay_order_id=order_id).first()
        
        if donation:
            donation.status = 'Success'
            donation.razorpay_payment_id = payment_id
            donation.razorpay_signature = signature
            donation.save()
            return render(request, 'donations/success.html', {'donation': donation})
            
    return render(request, 'donations/error.html', {'error': 'Invalid Request'})


@user_passes_test(lambda u: u.is_staff)
def admin_transaction_manager(request):
    # 1. Get search and filter parameters from the URL
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    # 2. Start with all donations
    donations = Donation.objects.all().order_by('-created_at')

    # 3. Apply Search (Check Email or Order ID)
    if search_query:
        donations = donations.filter(
            Q(user__email__icontains=search_query) | 
            Q(razorpay_order_id__icontains=search_query)
        )

    # 4. Apply Status Filter
    if status_filter:
        donations = donations.filter(status=status_filter)

    # 5. Calculate stats based on the FULL (unfiltered) list for the cards
    all_donations = Donation.objects.all()
    total_revenue = sum(d.amount for d in all_donations if d.status == 'Success')
    pending_count = all_donations.filter(status='Pending').count()

    context = {
        'donations': donations,
        'total_revenue': total_revenue,
        'pending_count': pending_count,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'accounts/admin_transactions.html', context)




@user_passes_test(lambda u: u.is_staff)
def sync_transaction(request, donation_id):
    donation = get_object_or_404(Donation, id=donation_id)
    
    try:
        # Fetch the order details directly from Razorpay
        order_details = client.order.fetch(donation.razorpay_order_id)
        # Fetch all payments associated with this order
        payments = client.order.payments(donation.razorpay_order_id)

        if payments['items']:
            # Get the latest payment for this order
            latest_payment = payments['items'][0]
            
            if latest_payment['status'] == 'captured':
                donation.status = 'Success'
                donation.razorpay_payment_id = latest_payment['id']
                donation.save()
                messages.success(request, f"Sync Successful: Payment {latest_payment['id']} captured.")
            else:
                messages.info(request, f"Sync complete: Payment status is {latest_payment['status']}.")
        else:
            messages.warning(request, "No payments found for this order on Razorpay yet.")

    except Exception as e:
        messages.error(request, f"Razorpay Sync Error: {str(e)}")

    return redirect('admin_transactions')
