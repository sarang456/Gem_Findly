from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model

# 1. Custom User Manager & Model (Refined)
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email: raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

    # ADD THIS SPECIFIC METHOD:
    def get_by_natural_key(self, email):
        return self.get(email=email)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=(('admin', 'Admin'), ('user', 'User')), default='user')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=10, choices=(('male', 'Male'), ('female', 'Female'), ('other', 'Other')), blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

# 2. The Item (The "Physical" Object)
class Item(models.Model):
    category = models.CharField(max_length=100) # e.g. Electronics, Pets
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    
    # AI Metadata - This makes the "AI" feature real
    ai_tags = models.JSONField(default=dict, blank=True) 
    qr_code_id = models.UUIDField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.title

# 3. The Report (The "Event")
class Report(models.Model):
    TYPE_CHOICES = (('lost', 'Lost'), ('found', 'Found'))
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # Location Strategy: Coordinates for real distance math
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(max_length=255) # Human readable name
    requires_photo_proof = models.BooleanField(default=False)
    question_1 = models.CharField(max_length=255, blank=True, null=True, default="Can you describe a unique feature of this item?")
    question_2 = models.CharField(max_length=255, blank=True, null=True)
    
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True, null=True)

    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.report_type.upper()}: {self.item.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # TRIGGER THE BRAIN
            # Local import to prevent Circular Import Errors
            try:
                from .utils import run_matching_engine, analyze_image
                
                # 1. First, let AI tag the image if it exists
                if self.item.image:
                    tags = analyze_image(self.item.image)
                    self.item.ai_tags = tags
                    self.item.save()
                
                # 2. Run the matching engine
                run_matching_engine(self)
                print(f"DEBUG: Matching engine triggered for Report {self.id}")
            except Exception as e:
                print(f"DEBUG: Error triggering engine: {e}")
    
class Match(models.Model):
    lost_report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='lost_matches')
    found_report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='found_matches')
    score = models.FloatField()
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('confirmed', 'Identity Verified'), # Owner confirmed the finder's answers
        ('paid', 'Reward Secured in Escrow'), # NEW: Payment successful
        ('returned', 'Item Handover Complete'), # Case closed
        ('rejected', 'Match Rejected'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    answer_1 = models.TextField(blank=True, null=True)
    answer_2 = models.TextField(blank=True, null=True)
    proof_image = models.ImageField(upload_to='claim_proofs/', blank=True, null=True)

    # NEW DATABASE FIELDS (Actual columns)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def score_display(self):
        if self.score is None:
            return 0
        
        # Standardize: Always treat score as a decimal (0.0 to 1.0)
        # Even if the score is 1.0, 1.0 * 100 = 100%.
        # Use min() to ensure we never show 101% by accident.
        display_value = int(self.score * 100)
        return min(display_value, 100)
    
# core/models.py

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, help_text="Bootstrap icon name (e.g., bi-laptop)")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class OTPVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # OTP is only valid for 5 minutes
        return timezone.now() > self.created_at + datetime.timedelta(minutes=5)

    def __str__(self):
        return f"OTP for {self.user.email}: {self.otp_code}"
    

class Donation(models.Model):
    # Link to the student/user who is donating
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    
    # Financial details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Razorpay specific tracking IDs
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=150, blank=True, null=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20, 
        choices=[('Pending', 'Pending'), ('Success', 'Success'), ('Failed', 'Failed')],
        default='Pending'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - ₹{self.amount} ({self.status})"
    


# Update your Donation/Transaction Model
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey('Match', on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending') 
    is_disbursed = models.BooleanField(default=False)
    
    # ADD THIS LINE HERE:
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"TXN {self.id} - {self.user.email} - ₹{self.amount}"