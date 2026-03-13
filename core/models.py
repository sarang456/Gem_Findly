from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings

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

    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.report_type.upper()}: {self.item.title}"
    
class Match(models.Model):
    lost_report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='lost_matches')
    found_report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='found_matches')
    score = models.FloatField()
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # AI just created this
        ('claimed', 'Claimed'),      # Owner said "This is mine"
        ('confirmed', 'Confirmed'),  # Finder said "I believe you"
        ('returned', 'Returned'),    # Item is physically back with owner
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