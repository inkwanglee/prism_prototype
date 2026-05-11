# =============================================================================
# Lineage views — placeholder snapshot list.
# =============================================================================
# Currently lists the most recent 50 Snapshot rows. The full lineage
# graph UI (upstream / downstream traversal, snapshot diffing) is a
# future-team task.
# =============================================================================

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Snapshot, LineageEdge


@login_required
def lineage_view(request):
    # List the 50 most recent snapshots. Newest first thanks to
    # Snapshot.Meta.ordering = ['-created_at'].
    snapshots = Snapshot.objects.all()[:50]
    context = {
        'page_title': 'Lineage',
        'snapshots': snapshots,
    }
    return render(request, 'lineage/view.html', context)
