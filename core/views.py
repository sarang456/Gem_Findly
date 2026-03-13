from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import SmartReportForm
from .models import Report, Match, User, Category, Item
from .utils import analyze_image, find_potential_matches, run_matching_engine
from django.db.models import Count, Q, F
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, get_user_model
from .forms import UserRegisterForm
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.db import models




def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Automatically log them in after signing up
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'core/register.html', {'form': form})

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
    
    return render(request, 'core/login.html', {'form': form})



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
    
    return render(request, 'core/report_form.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_staff:
        return redirect('admin_dashboard')

    # 1. Separate Reports: Active vs Resolved
    # This cleans the "messy" dashboard instantly
    active_reports = Report.objects.filter(user=request.user, is_resolved=False).order_by('-created_at')
    history_reports = Report.objects.filter(user=request.user, is_resolved=True).order_by('-created_at')

   # 2. Separate Matches: Active vs Returned
    # Only pull matches where BOTH reports are still live
    all_user_matches = Match.objects.filter(
        Q(lost_report__user=request.user) | Q(found_report__user=request.user)
    ).filter(
        # THIS IS THE CRITICAL ADDITION:
        lost_report__is_resolved=False, 
        found_report__is_resolved=False
    ).select_related('lost_report__item', 'found_report__item')

    # This will now only show matches for items that are ACTUALLY still lost/found
    my_matches = Match.objects.filter(
        Q(lost_report__user=request.user) | Q(found_report__user=request.user),
        lost_report__is_resolved=False,
        found_report__is_resolved=False
    ).exclude(status='completed').order_by('-score')

    # History Matches: Only show the ones specifically marked as finished
    history_matches = Match.objects.filter(
        Q(lost_report__user=request.user) | Q(found_report__user=request.user),
        status='completed'
    ).order_by('-score')

    return render(request, 'core/dashboard.html', {
        'my_reports': active_reports,      # Still using the same variable name to avoid breaking your HTML
        'my_matches': my_matches,          # Still using the same variable name
        'history_reports': history_reports, # New: Pass this to a "History" section
        'history_matches': history_matches  # New: Pass this to a "History" section
    })

def home(request):

    query = request.GET.get('q')
    
    if query:
        # Check if any ACTIVE items match the query
        results_exist = Report.objects.filter(
            item__title__icontains=query, 
            is_resolved=False
        ).exists()
        
        if results_exist:
            # If found, go to listings with the search term
            return redirect(f'/listings/?q={query}')
        else:
            # If NOT found, stay on home and show a message
            messages.info(request, f"No active reports found for '{query}'. Try a different keyword.")
            return redirect('home')
    # TEMPORARY: Remove all filters to see what is actually in your DB
    all_recent = Report.objects.all().order_by('-created_at')[:4]
    # Print to your terminal/console so you can see the truth behind the scenes
    return render(request, 'index.html', {'recent_found': all_recent})

@login_required
def match_detail(request, match_id):
    # Fetch the match or 404 if it doesn't exist
    match = get_object_or_404(Match, id=match_id)
    
    # Security Check: Is this user part of this match?
    if request.user != match.lost_report.user and request.user != match.found_report.user:
        return redirect('dashboard') # Redirect if they try to snoop on others

    return render(request, 'core/match_detail.html', {'match': match})

@login_required
def resolve_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    
    if request.user == match.lost_report.user or request.user == match.found_report.user:
        # 1. Update the Match Status (The most important part)
        match.status = 'returned'
        match.save()
        
        # 2. Update the Reports (To hide them from main dashboard)
        match.lost_report.is_resolved = True
        match.lost_report.save()
        
        match.found_report.is_resolved = True
        match.found_report.save()
        
        messages.success(request, "Item successfully returned and moved to history!")
    else:
        messages.error(request, "You do not have permission to resolve this match.")
        
    return redirect('dashboard')

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
    return render(request, 'listings.html', context)

@staff_member_required
def admin_dashboard(request):
    context = {
        'total_reports': Report.objects.count(),
        'pending_reports': Report.objects.filter(is_resolved=False).count(),
        'total_matches': Match.objects.count(),
        'total_users': User.objects.count(),
        'all_reports': Report.objects.all().order_by('-created_at')[:10], # Latest 10
    }
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
        
    return render(request, 'core/report_confirm.html', {'report': item_to_report})


#11-03
def match_detail_public(request, match_id):
    # This is a placeholder for the AI match detail view
    match = get_object_or_404(Match, id=match_id)
    return render(request, 'core/match_detail.html', {'match': match})

def claim_match(request, match_id):
    # 1. Fetch the match safely
    match = get_object_or_404(Match, id=match_id)
    
    # 2. Brutal Security Check: Is this actually the user's lost item?
    if match.lost_report.user != request.user:
        messages.error(request, "You don't have permission to claim this item.")
        return redirect('dashboard')
    
    # 3. Logic: Mark as confirmed
    match.status = 'claimed'
    match.save()
    
    # 4. Feedback
    messages.success(request, f"Claim submitted for {match.found_report.item.title}! The finder has been notified.")
    return redirect('dashboard')



def claim_challenge(request, match_id):
    # select_related avoids multiple hits to the DB
    match = get_object_or_404(Match.objects.select_related('lost_report', 'found_report', 'found_report__item'), id=match_id)
    
    # Permission check
    if match.lost_report.user != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
    
    if match.status != 'pending':
        messages.info(request, "This claim is already being processed.")
        return redirect('dashboard')

    if request.method == "POST":
        match.answer_1 = request.POST.get('answer_1')
        match.answer_2 = request.POST.get('answer_2')
        
        # Always check for files when using enctype="multipart/form-data"
        if request.FILES.get('proof_image'):
            match.proof_image = request.FILES['proof_image']
        
        match.status = 'claimed'
        match.save()
        
        messages.success(request, "Claim submitted! Waiting for finder's verification.")
        return redirect('dashboard')

    return render(request, 'core/claim_challenge.html', {
        'match': match, 
        'item': match.found_report  # This provides item.question_1 and item.item.title
    })

def review_claim(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    
    # 1. SECURITY: Only the Finder can judge the claim
    if match.found_report.user != request.user:
        messages.error(request, "Nice try, but you can't review your own item!")
        return redirect('dashboard')

    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'accept':
            match.status = 'confirmed'
            match.is_confirmed = True
            match.save()
            messages.success(request, "Match Confirmed! The owner can now see your contact details.")
        
        elif action == 'reject':
            # 2. BRUTAL TRUTH: If you reject, we must wipe the thief's answers
            match.status = 'pending'
            match.answer_1 = ""
            match.answer_2 = ""
            match.proof_image = None # Delete the fake proof
            match.save()
            messages.warning(request, "Claim rejected. The item is back on the market.")
            
        return redirect('dashboard')

    return render(request, 'core/review_claim.html', {'match': match})


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
    return render(request, 'core/item_details.html', context)

def start_claim_process(request, report_id):
    # 1. Get the item
    found_report = get_object_or_404(Report, id=report_id)
    
    # 2. Find or Create a match for THIS user
    # We must include something that identifies the 'Claimer'
    # Check if your Match model has a 'user' or 'claimer' field
    match, created = Match.objects.get_or_create(
        found_report=found_report,
        lost_report__user=request.user, # Only works if they have a lost report
        defaults={'status': 'pending'}
    )
    
    # BRUTAL TRUTH: If the user doesn't have a lost report, 
    # the line above will fail.
    
    return redirect('claim_challenge', match_id=match.id)

def close_case(request, match_id):
    if request.method == 'POST':
        # 1. Get the match
        match = get_object_or_404(Match, id=match_id)
        
        # 2. Security Check (Only the Finder should close the case)
        if match.found_report.user != request.user:
            messages.error(request, "Unauthorized.")
            return redirect('dashboard')
            
        # 3. THE FIX: Explicitly flip the switches
        match.status = 'completed'
        
        # We must update the FOUND report
        match.found_report.is_resolved = True
        match.found_report.save() # CRITICAL: This saves the Report table
        
        # We must update the LOST report (if it exists)
        if match.lost_report:
            match.lost_report.is_resolved = True
            match.lost_report.save() # CRITICAL: This saves the other Report
            
        match.save() # This saves the Match table status
        
        messages.success(request, "Database updated! Case is now resolved.")
    
    return redirect('dashboard')
    

@login_required
def history(request):
    # 1. Get reports the user resolved (Manual close or Match close)
    history_reports = Report.objects.filter(
        user=request.user, 
        is_resolved=True
    ).order_by('-created_at')

    # 2. Get matches that reached the 'completed' status
    history_matches = Match.objects.filter(
        Q(lost_report__user=request.user) | Q(found_report__user=request.user)
    ).filter(status='completed').select_related(
        'lost_report__item', 
        'found_report__item'
    ).order_by('-id')

    return render(request, 'core/history.html', {
        'history_reports': history_reports,
        'history_matches': history_matches
    })