from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import IngestionRun

@login_required
def ingestion_list(request):
    runs = IngestionRun.objects.all()[:50]
    context = {
        'page_title': 'Ingestion Runs',
        'runs': runs,
    }
    return render(request, 'ingestion/list.html', context)