from django.shortcuts import render, redirect
from core.models import Report
from django.contrib import messages

# Create your views here.
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
    return render(request, 'pages/index.html', {'recent_found': all_recent})

def help_support(request):
    # We can categorize the FAQs here later if we want to pull from a database
    return render(request, 'pages/help.html')