from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import QaqcRun

@login_required
def qaqc_dashboard(request):
    runs = QaqcRun.objects.all()[:50]
    context = {
        'page_title': 'QAQC Dashboard',
        'runs': runs,
    }
    return render(request, 'qaqc/dashboard.html', context)