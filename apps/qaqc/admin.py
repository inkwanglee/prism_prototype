from django.contrib import admin
from .models import QaqcRun

@admin.register(QaqcRun)
class QaqcRunAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'dataset_key', 'status', 'checks_passed', 'checks_failed', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['batch_id', 'dataset_key']