from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import SmartReportForm
from django.db import transaction
from core.utils import analyze_image, find_potential_matches, run_matching_engine
from core.models import Report, Item, Category, Match
from django.contrib import messages

# Create your views here.
@login_required
def create_report(request):
    if request.method == 'POST':
        form = SmartReportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Manually create the Item object
                    item = Item.objects.create(
                        title=form.cleaned_data['title'],
                        description=form.cleaned_data['description'],
                        category=form.cleaned_data['category'].strip().title(),
                        image=form.cleaned_data.get('image')
                    )
                    
                    # Optional: AI Analysis
                    if item.image:
                        item.ai_tags = analyze_image(item.image)
                        item.save()

                    # 2. Manually create the Report object
                    new_report = Report.objects.create(
                        user=request.user,
                        item=item,
                        report_type=form.cleaned_data['report_type'],
                        location_name=form.cleaned_data['location_name'],
                        latitude=form.cleaned_data['latitude'],
                        longitude=form.cleaned_data['longitude'],
                        question_1=form.cleaned_data.get('question_1'),
                        question_2=form.cleaned_data.get('question_2'),
                        requires_photo_proof=form.cleaned_data.get('requires_photo_proof', False)
                    )

                    # 3. Trigger AI Matching
                    run_matching_engine(new_report)

                messages.success(request, "Report created! Checking for matches...")
                return redirect('dashboard')
            
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = SmartReportForm()
    
    return render(request, 'reports/report_form.html', {'form': form})

def listings(request):
    # 1. ALWAYS filter out resolved items (Requirement met)
    reports = Report.objects.filter(is_resolved=False)
    
    # 2. Handle Search Query
    search_query = request.GET.get('q')
    if search_query:
        reports = reports.filter(item__title__icontains=search_query)

    # 3. Handle Location Filter (New Requirement)
    location_query = request.GET.get('location')
    if location_query:
        reports = reports.filter(location_name__icontains=location_query)

    # 4. Handle Type Filter
    report_type = request.GET.get('type') 
    if report_type:
        reports = reports.filter(report_type=report_type)

    # 5. Handle Sorting (Requirement: Newest/Oldest)
    sort = request.GET.get('sort', 'newest') # Default to newest
    if sort == 'oldest':
        reports = reports.order_by('created_at')
    else:
        reports = reports.order_by('-created_at')
        
    context = {
        'reports': reports,
        'categories': Category.objects.all(),
        'current_type': report_type,
        'current_sort': sort,
        'current_location': location_query,
    }
    return render(request, 'reports/listings.html', context)

def item_details(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    
    # Logic: Show info if Admin OR if there's a confirmed match involving the current user
    # We use a filter to see if a match exists where status is confirmed and the user is the loster
    has_confirmed_match = Match.objects.filter(
        found_report=report, 
        lost_report__user=request.user, 
        status='confirmed'
    ).exists()

    context = {
        'report': report,
        'has_confirmed_match': has_confirmed_match,
        'is_owner': report.user == request.user,
    }
    return render(request, 'reports/item_details.html', context)

@login_required
def report_item(request, report_id):
    # We are reporting a 'Report' object
    item_to_report = get_object_or_404(Report, id=report_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason')
        item_to_report.is_flagged = True
        item_to_report.flag_reason = f"Reported by {request.user.get_username()}: {reason}"
        item_to_report.save()
        
        messages.success(request, "Thank you. This item has been sent to administrators for review.")
        return redirect('listings') # Or wherever the user was
        
    return render(request, 'reports/report_confirm.html', {'report': item_to_report})