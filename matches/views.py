from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import Report, Match, Transaction
from django.db.models import Q
from django.contrib import messages
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

# Create your views here.
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

    return render(request, 'matches/dashboard.html', {
        'my_reports': active_reports,      # Still using the same variable name to avoid breaking your HTML
        'my_matches': my_matches,          # Still using the same variable name
        'history_reports': history_reports, # New: Pass this to a "History" section
        'history_matches': history_matches  # New: Pass this to a "History" section
    })


@login_required
def match_detail(request, match_id):
    # Fetch the match or 404 if it doesn't exist
    match = get_object_or_404(Match, id=match_id)
    
    # Security Check: Is this user part of this match?
    if request.user != match.lost_report.user and request.user != match.found_report.user:
        return redirect('dashboard') # Redirect if they try to snoop on others

    return render(request, 'matches/match_detail.html', {'match': match})


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

    return render(request, 'matches/claim_challenge.html', {
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

    return render(request, 'matches/review_claim.html', {'match': match})


@login_required
def start_claim_process(request, report_id):
    # 1. Get the Found Item the user is looking at
    found_report = get_object_or_404(Report, id=report_id)

    # 2. Try to find a LOST report with the SAME CATEGORY
    # This is much smarter than just taking the '.first()' one.
    user_lost_report = Report.objects.filter(
        user=request.user, 
        report_type='lost', 
        item__category=found_report.item.category, # Match by category!
        is_resolved=False
    ).first()

    # 3. SMART REDIRECT: If no matching report exists, pre-fill the form
    if not user_lost_report:
        messages.info(request, "Please confirm your lost item details to start the claim.")
        # We pass the found item's data so they don't have to type it!
        return redirect(
            f"{reverse('create_report')}?prefill_title={found_report.item.title}"
            f"&prefill_cat={found_report.item.category}"
            f"&prefill_loc={found_report.location_name}"
        )
    
    # 4. Create the match
    match, created = Match.objects.get_or_create(
        found_report=found_report,
        lost_report=user_lost_report,
        defaults={
            'status': 'pending',
            'score': 100.0  
        }
    )
    
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
    is_staff = request.user.is_staff
    
    if is_staff:
        # ADMIN: Get every resolved report and completed match in the system
        history_reports = Report.objects.filter(is_resolved=True).order_by('-created_at')
        history_matches = Match.objects.filter(status='completed').select_related(
            'lost_report__item', 
            'found_report__item',
            'lost_report__user'
        ).order_by('-id')
    else:
        # USER: Only their own data
        history_reports = Report.objects.filter(user=request.user, is_resolved=True).order_by('-created_at')
        history_matches = Match.objects.filter(
            Q(lost_report__user=request.user) | Q(found_report__user=request.user)
        ).filter(status='completed').select_related(
            'lost_report__item', 
            'found_report__item',
            'lost_report__user'
        ).order_by('-id')

    return render(request, 'matches/history.html', {
        'history_reports': history_reports,
        'history_matches': history_matches,
        'is_admin': is_staff  # Pass this flag to the template
    })


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


def match_detail_public(request, match_id):
    # This is a placeholder for the AI match detail view
    match = get_object_or_404(Match, id=match_id)
    return render(request, 'core/match_detail.html', {'match': match})

@login_required
def my_reports(request):
    # Fetching all reports by this user
    # We order by 'is_resolved' (False comes first usually) and then date
    reports = Report.objects.filter(user=request.user).order_by('is_resolved', '-created_at')
    
    return render(request, 'matches/my_reports.html', {
        'reports': reports,
        'total_count': reports.count(),
        'active_count': reports.filter(is_resolved=False).count()
    })




# Initialize Razorpay Client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def pay_reward(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    
    # BRUTAL SECURITY: Only the owner (loser) can pay the reward
    if match.lost_report.user != request.user:
        messages.error(request, "Unauthorized payment attempt.")
        return redirect('dashboard')

    amount = int(match.lost_report.reward_amount * 100) # Convert to Paise (Razorpay requirement)
    
    # 1. Create Razorpay Order
    data = {
        "amount": amount,
        "currency": "INR",
        "receipt": f"match_{match.id}",
        "notes": {
            "match_id": match.id,
            "type": "reward_escrow"
        }
    }
    
    try:
        razorpay_order = client.order.create(data=data)
        
        # 2. Create a "Pending" Transaction in our DB
        transaction = Transaction.objects.create(
            user=request.user,
            match=match,
            amount=match.lost_report.reward_amount,
            razorpay_order_id=razorpay_order['id'],
            status='Pending'
        )
        
        return render(request, 'matches/pay_reward.html', {
            'match': match,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': match.lost_report.reward_amount,
            'amount_paise': amount
        })
        
    except Exception as e:
        messages.error(request, f"Payment Gateway Error: {e}")
        return redirect('dashboard')

@csrf_exempt # REMOVE @login_required here
def payment_success_reward(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        # 1. Get the transaction - if this fails, the view stops
        transaction = get_object_or_404(Transaction, razorpay_order_id=order_id)
        
        try:
            # 2. Verify the signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)
            
            # 3. Update Transaction
            transaction.status = 'Success'
            transaction.razorpay_payment_id = payment_id
            transaction.save()

            # 4. Update Match - THE CRITICAL PART
            match = transaction.match
            if match:
                match.status = 'paid' # Ensure this matches your models.py choices exactly
                match.save()
                print(f"SUCCESS: Match {match.id} is now PAID.") # Check your terminal for this!
            
            return redirect('dashboard')

        except Exception as e:
            print(f"PAYMENT VERIFICATION ERROR: {e}")
            transaction.status = 'Failed'
            transaction.save()
            return redirect('dashboard')

    return redirect('dashboard')
        
# matches/views.py

@login_required
def close_case(request, match_id):
    if request.method == 'POST':
        match = get_object_or_404(Match, id=match_id)
        
        # SECURITY: Only the person who LOST the item can release the money
        if match.lost_report.user != request.user:
            messages.error(request, "Unauthorized! Only the owner can confirm receipt.")
            return redirect('dashboard')
            
        # 1. Update Match and Reports to 'Resolved'
        match.status = 'returned'
        match.save()
        
        match.found_report.is_resolved = True
        match.found_report.save()
        match.lost_report.is_resolved = True
        match.lost_report.save()
        
        # 2. Find the successful payment
        transaction = Transaction.objects.filter(match=match, status='Success').first()
        
        if transaction:
            # We don't mark 'is_disbursed' as True yet. 
            # This is the "Signal" to the Admin to pay the Finder.
            messages.success(request, "Success! The case is closed. We have notified the admin to release your reward to the finder.")
        else:
            messages.success(request, "Case closed successfully!")

        return redirect('dashboard')