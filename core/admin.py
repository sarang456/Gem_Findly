from django.contrib import admin
from .models import User, Item, Report, Match, Donation, OTPVerification, Category, Transaction

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'role', 'is_staff', 'is_active')
    search_fields = ('email',)

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'qr_code_id')
    readonly_fields = ('ai_tags',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('get_title', 'user', 'report_type', 'location_name', 'is_resolved')
    list_filter = ('report_type', 'is_resolved', 'created_at')

    def get_title(self, obj):
        return obj.item.title

    get_title.short_description = "Item Title"

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):

    list_display = ('id', 'display_lost', 'display_found', 'score_display','is_confirmed', 'created_at')
    list_filter = ('is_confirmed', 'created_at',)
    readonly_fields = ('score', 'lost_report', 'found_report', 'created_at')

    fieldsets = (
        ('Match Info', {
            'fields': ('score',)
        }),
        ('Reports Involved', {
            'fields': ('lost_report', 'found_report')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def display_lost(self, obj):
        if obj.lost_report and obj.lost_report.item:
            return f"{obj.lost_report.item.title} ({obj.lost_report.user.email})"
        return "Missing Report/Item"
    display_lost.short_description = "Lost Report (Owner)"

    def display_found(self, obj):
        if obj.found_report and obj.found_report.item:
            return f"{obj.found_report.item.title} ({obj.found_report.user.email})"
        return "Missing Report/Item"
    display_found.short_description = "Found Report (Finder)"

    def score_display(self, obj):
        if obj.score is None:
            return "-"
        return f"{int(obj.score * 100)}%"
    score_display.short_description = "Confidence"



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'created_at', 'is_expired_status')
    readonly_fields = ('otp_code', 'user', 'created_at') # Prevent manual tampering
    
    def is_expired_status(self, obj):
        return obj.is_expired()
    is_expired_status.boolean = True
    is_expired_status.short_description = "Expired?"

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at', 'razorpay_order_id')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'created_at')
    
    # Color coding the status in admin
    def save_model(self, request, obj, form, change):
        # Optional: Add logic here if you want to perform actions on save
        super().save_model(request, obj, form, change)

# core/admin.py
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # Filter for Success but NOT yet disbursed
    list_display = ('id', 'get_finder_email', 'amount', 'status', 'is_disbursed', 'created_at')
    list_filter = ('is_disbursed', 'status')
    
    # This helps the admin see WHO to pay
    def get_finder_email(self, obj):
        if obj.match:
            return obj.match.found_report.user.email
        return "No Match"
    get_finder_email.short_description = 'Pay to Finder'

    # Action to mark as paid once you send the UPI
    actions = ['mark_as_paid']

    def mark_as_paid(self, request, queryset):
        queryset.update(is_disbursed=True)
        self.message_user(request, "Marked as paid. Ensure you actually sent the UPI/Bank transfer!")
