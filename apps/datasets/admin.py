from django.contrib import admin
from .models import Dataset, Collar, Survey

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['key', 'title', 'owner', 'status', 'created_at']
    search_fields = ['key', 'title', 'owner']
    list_filter = ['status', 'created_at']

@admin.register(Collar)
class CollarAdmin(admin.ModelAdmin):
    list_display = ['hole_id', 'project_id', 'x', 'y', 'z', 'crs_epsg']
    search_fields = ['hole_id', 'project_id']
    list_filter = ['project_id']

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['collar', 'depth_m', 'dip_deg', 'azimuth_deg']
    search_fields = ['collar__hole_id']