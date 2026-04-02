import os
import random
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from .models import OTPVerification

User = get_user_model()

def send_verification_email(user):
    """
    The Master Logic: 
    Used by both the Signal (New Register) and the View (Resend OTP).
    """
    # 1. Generate & Save/Update OTP
    otp_code = str(random.randint(100000, 999999))
    OTPVerification.objects.update_or_create(
        user=user, 
        defaults={'otp_code': otp_code}
    )
    
    # 2. Setup Content
    subject = f"Verify your Findly Account: {otp_code} 🚀"
    html_content = render_to_string('emails/welcome_email.html', {
        'user': user,
        'otp_code': otp_code
    })
    
    # 3. Create Email
    email_obj = EmailMessage(
        subject,
        html_content,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    email_obj.content_subtype = "html" 

    # 4. Attach PDF
    pdf_path = os.path.join(settings.BASE_DIR, 'static', 'documents', 'findly_terms.pdf')
    if os.path.exists(pdf_path):
        try:
            email_obj.attach_file(pdf_path)
        except Exception as e:
            print(f"Attachment Error: {e}")

    # 5. Send
    try:
        email_obj.send(fail_silently=False)
        print(f"Successfully sent OTP {otp_code} to {user.email}")
    except Exception as e:
        print(f"SMTP Error: {e}")

@receiver(post_save, sender=User)
def handle_new_user_onboarding(sender, instance, created, **kwargs):
    if created:
        # Just call the helper function!
        send_verification_email(instance)