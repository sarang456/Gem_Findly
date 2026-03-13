from django.contrib import admin
from .models import User, Item, Report, Match

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
