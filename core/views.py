from django.shortcuts import render, redirect, get_object_or_404
from .models import Report, Match, User
from django.db.models import Count, F, Q
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import csv
from django.http import HttpResponse
from django.db.models.functions import Lower






@staff_member_required
def admin_dashboard(request):
    query = request.GET.get('q', '')
    
    # Base statistics (these stay constant even during search)
    context = {
        'total_reports': Report.objects.count(),
        'pending_reports': Report.objects.filter(is_resolved=False).count(),
        'total_matches': Match.objects.count(),
        'total_users': User.objects.count(),
    }

    # Search Logic
    if query:
        # Search all reports by ID, Title, Location, or Submitting User's Email
        reports = Report.objects.filter(
            Q(id__icontains=query) | 
            Q(item__title__icontains=query) |
            Q(location_name__icontains=query) |
            Q(user__email__icontains=query)
        ).order_by('-created_at')
        
        context['is_searching'] = True
        context['query'] = query
    else:
        # Default: Latest 10 reports
        reports = Report.objects.all().order_by('-created_at')[:10]
        context['is_searching'] = False

    context['all_reports'] = reports
    return render(request, 'core/admin_dashboard.html', context)

User = get_user_model()

@staff_member_required
def manage_users(request):
    users = User.objects.annotate(
        # Counting reports linked to this user
        report_count=Count('reports', distinct=True),
        
        # Counting matches through those reports
        lost_match_count=Count('reports__lost_matches', distinct=True),
        found_match_count=Count('reports__found_matches', distinct=True),
    ).annotate(
        # Coalesce ensures if a count is None, it becomes 0 so the addition works
        match_count=Coalesce(F('lost_match_count'), 0) + Coalesce(F('found_match_count'), 0)
    ).order_by('-date_joined')

    return render(request, 'core/manage_users.html', {'users': users})


@staff_member_required
def flagged_items(request):
    # Fetch reports marked as flagged, newest first
    items = Report.objects.filter(is_flagged=True).order_by('-created_at')
    
    return render(request, 'core/flagged_items.html', {'flagged_items': items})


@staff_member_required
def resolve_flag(request, report_id):
    # A quick action to "unflag" or "delete" an item
    report = get_object_or_404(Report, id=report_id)
    action = request.POST.get('action')
    
    if action == 'delete':
        report.delete()
        messages.warning(request, "Item has been permanently removed.")
    else:
        report.is_flagged = False
        report.save()
        messages.success(request, "Item has been cleared.")
        
    return redirect('flagged_items')

@staff_member_required
def all_reports_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'newest')
    user_id = request.GET.get('user_id') # Capture the ID from the Profile link
    
    reports = Report.objects.all()

    # NEW: Filter by user if the ID is present
    filtered_user = None
    if user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        filtered_user = get_object_or_404(User, id=user_id)
        reports = reports.filter(user=filtered_user)

    # Apply Search
    if query:
        reports = reports.filter(
            Q(id__icontains=query) | 
            Q(item__title__icontains=query) |
            Q(location_name__icontains=query) |
            Q(user__email__icontains=query)
        )

    # Apply Sorting
    reports = reports.order_by('created_at' if sort == 'oldest' else '-created_at')

    return render(request, 'core/all_reports.html', {
        'reports': reports,
        'query': query,
        'sort': sort,
        'total_count': reports.count(),
        'filtered_user': filtered_user,              # Add this
        'is_filtered_by_user': bool(user_id)        # Add this
    })

@staff_member_required
def export_reports_csv(request):
    # 1. Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="findly_reports_export.csv"'

    writer = csv.writer(response)
    # 2. Write the header row
    writer.writerow(['ID', 'User', 'Item Title', 'Type', 'Location', 'Status', 'Date Created'])

    # 3. Write data rows
    reports = Report.objects.all().order_by('-created_at')
    for report in reports:
        status = "Resolved" if report.is_resolved else "Active"
        writer.writerow([
            report.id,
            report.user.email,
            report.item.title,
            report.report_type.upper(),
            report.location_name,
            status,
            report.created_at.strftime("%Y-%m-%d %H:%M")
        ])

    return response

@staff_member_required
def toggle_user_active(request, user_id):
    # Use get_user_model() to be safe with custom models
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    selected_member = get_object_or_404(User, id=user_id)
    
    if selected_member == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('manage_users')

    selected_member.is_active = not selected_member.is_active
    selected_member.save()

    status = "deactivated" if not selected_member.is_active else "reactivated"
    
    # FIX: Use .email or .get_full_name() instead of .username
    identifier = selected_member.email 
    messages.success(request, f"User {identifier} has been {status}.")
    
    return redirect('manage_users')


@staff_member_required
def site_analytics(request):
    User = get_user_model()
    
    # 1. Basic Volume Metrics
    total_reports = Report.objects.count()
    total_users = User.objects.count()
    
    # 2. Status Breakdown (Lost vs Found)
    lost_count = Report.objects.filter(report_type='lost').count()
    found_count = Report.objects.filter(report_type='found').count()
    
    # 3. The "Success" Metric (Resolved vs Active)
    resolved_count = Report.objects.filter(is_resolved=True).count()
    active_count = Report.objects.filter(is_resolved=False).count()
    
    # Calculate Recovery Rate (Safety check for Zero Division)
    recovery_rate = round((resolved_count / total_reports * 100), 1) if total_reports > 0 else 0

    location_data = Report.objects.exclude(location_name__isnull=True) \
    .exclude(location_name="") \
    .values('location_name') \
    .annotate(count=Count('id')) \
    .order_by('-count')[:5]

    recent_activity = Report.objects.select_related('user', 'item').order_by('-created_at')[:5]

    context = {
        'total_reports': total_reports,
        'total_users': total_users,
        'lost_count': lost_count,
        'found_count': found_count,
        'resolved_count': resolved_count,
        'active_count': active_count,
        'recovery_rate': recovery_rate,
        'location_data': location_data,
        'recent_activity': recent_activity,
    }
    
    return render(request, 'core/analytics.html', context)


