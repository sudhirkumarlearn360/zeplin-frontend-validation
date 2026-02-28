from django.contrib import admin
from .models import ValidationReport

@admin.register(ValidationReport)
class ValidationReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'zeplin_project_id', 'zeplin_screen_id', 'live_url', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('zeplin_project_id', 'zeplin_screen_id', 'live_url')
