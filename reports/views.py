from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import SmartReportForm, FlagReportForm
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
                        reward_amount=form.cleaned_data.get('reward_amount', 0),
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
        # 1. Catch the data from the URL (?prefill_title=...)
        prefill_title = request.GET.get('prefill_title', '')
        prefill_cat = request.GET.get('prefill_cat', '')
        prefill_loc = request.GET.get('prefill_loc', '')

        # 2. Set the 'initial' dictionary
        initial_data = {}
        if prefill_title:
            initial_data['title'] = f"Regarding: {prefill_title}"
        if prefill_cat:
            initial_data['category'] = prefill_cat
        if prefill_loc:
            initial_data['location_name'] = prefill_loc

        # 3. Pass the initial data to the form
        form = SmartReportForm(initial=initial_data)
    
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

@login_required
def close_case_manual(request, report_id):
    report = get_object_or_404(Report, id=report_id, user=request.user)
    if request.method == 'POST':
        report.is_resolved = True
        report.save()
        messages.success(request, "Congratulations! Your report has been marked as resolved.")
    return redirect('dashboard')

@login_required
def edit_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    
    # BRUTAL SECURITY: Stop people from editing other people's posts
    if report.user != request.user:
        messages.error(request, "You do not have permission to edit this report.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Fill the form with POST data AND the existing image
        form = SmartReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Update the Item details
            item = report.item
            item.title = form.cleaned_data['title']
            item.description = form.cleaned_data['description']
            item.category = form.cleaned_data['category']
            if form.cleaned_data['image']:
                item.image = form.cleaned_data['image']
            item.save()

            # Update the Report details
            report.location_name = form.cleaned_data['location_name']
            report.latitude = form.cleaned_data['latitude']
            report.longitude = form.cleaned_at['longitude']
            report.reward_amount = form.cleaned_data.get('reward_amount', 0)
            report.save()

            messages.success(request, "Report updated successfully!")
            return redirect('item_details', report_id=report.id)
    else:
        # PRE-FILL the form with existing data
        initial_data = {
            'title': report.item.title,
            'description': report.item.description,
            'category': report.item.category,
            'report_type': report.report_type,
            'location_name': report.location_name,
            'latitude': report.latitude,
            'longitude': report.longitude,
            'reward_amount': report.reward_amount,
        }
        form = SmartReportForm(initial=initial_data)

    return render(request, 'reports/report_form.html', {'form': form, 'edit_mode': True})

@login_required
def flag_report(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(Report, id=report_id)
        
        # 1. Flip the switch
        report.is_flagged = True
        
        # 2. Add a reason (You can make this a form later, for now we hardcode it)
        report.flag_reason = f"Reported by user: {request.user.email}"
        report.save()
        
        messages.warning(request, "This listing has been reported to administrators for review.")
        return redirect('item_details', report_id=report.id)
    
    return redirect('dashboard')

@login_required
def report_item_page(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    
    if request.method == "POST":
        form = FlagReportForm(request.POST)
        if form.is_valid():
            # 1. Mark the item as flagged
            report.is_flagged = True
            
            # 2. Combine the choice and description for the Admin to see
            chosen_reason = form.cleaned_data['reason_type']
            extra_details = form.cleaned_data['description']
            report.flag_reason = f"[{chosen_reason.upper()}] {extra_details}"
            
            report.save()
            
            messages.success(request, "Thank you. Our moderators will review this listing shortly.")
            return redirect('item_details', report_id=report.id)
    else:
        form = FlagReportForm()

    return render(request, 'reports/report_reason_page.html', {
        'form': form,
        'report': report
    })

