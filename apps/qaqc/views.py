# =============================================================================
# QAQC views — placeholder dashboard.
# =============================================================================
# Currently lists the most recent 50 QaqcRun rows. Adding real validation
# logic (per-batch pass/fail badges, sparkline charts, blocking promotion
# when QAQC fails) is a future-team task.
# =============================================================================

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import QaqcRun


@login_required
def qaqc_dashboard(request):
    # List the 50 most recent QAQC runs. Newest first thanks to
    # QaqcRun.Meta.ordering = ['-created_at'].
    runs = QaqcRun.objects.all()[:50]
    context = {
        'page_title': 'QAQC Dashboard',
        'runs': runs,
    }
    return render(request, 'qaqc/dashboard.html', context)
