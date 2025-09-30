from django.contrib import admin
from .models import IngestionRun

@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'status', 'total_rows', 'success_rows', 'failed_rows', 'started_at']
    list_filter = ['status', 'source', 'started_at']
    search_fields = ['source']