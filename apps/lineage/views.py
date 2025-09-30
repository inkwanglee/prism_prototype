from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Snapshot, LineageEdge

@login_required
def lineage_view(request):
    snapshots = Snapshot.objects.all()[:50]
    context = {
        'page_title': 'Lineage',
        'snapshots': snapshots,
    }
    return render(request, 'lineage/view.html', context)