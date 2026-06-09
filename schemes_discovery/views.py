from django.shortcuts import render

def dashboard_view(request):
    """Renders the generated frontend UI."""
    return render(request, 'schemes_discovery/dashboard.html')
