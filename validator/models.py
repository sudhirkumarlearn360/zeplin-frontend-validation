from django.db import models

class ValidationReport(models.Model):
    zeplin_project_id = models.CharField(max_length=255)
    zeplin_screen_id = models.CharField(max_length=255)
    live_url = models.URLField(max_length=2000)
    
    pixel_mismatch_count = models.IntegerField(null=True, blank=True)
    css_mismatch_count = models.IntegerField(null=True, blank=True)
    js_error_count = models.IntegerField(null=True, blank=True)
    dom_node_count = models.IntegerField(null=True, blank=True)
    zeplin_layer_count = models.IntegerField(null=True, blank=True)
    
    status = models.CharField(max_length=50, blank=True, null=True) # PASS / FAIL
    created_at = models.DateTimeField(auto_now_add=True)
    
    design_image = models.ImageField(upload_to='design/', null=True, blank=True)
    live_image = models.ImageField(upload_to='live/', null=True, blank=True)
    diff_image = models.ImageField(upload_to='diff/', null=True, blank=True)
    
    raw_json_data = models.JSONField(null=True, blank=True)
    mismatch_regions = models.JSONField(null=True, blank=True, help_text="Stored geometric location data (x, y, w, h)")

    def __str__(self):
        return f"Report {self.id} | {self.zeplin_screen_id} - {self.status}"
