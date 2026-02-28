import os
from django.shortcuts import redirect
from django.views.generic import FormView, DetailView, ListView
from django.conf import settings
from django.core.files import File

from .models import ValidationReport
from .forms import ValidationForm
from .services.zeplin_service import ZeplinService
from .services.screenshot_service import ScreenshotService
from .services.comparison_service import ComparisonService
from .services.css_validation_service import CSSValidationService

class InputPageView(FormView):
    template_name = 'input.html'
    form_class = ValidationForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the 20 most recent scans
        context['recent_scans'] = ValidationReport.objects.all().order_by('-created_at')[:20]
        return context
    
    def form_valid(self, form):
        token = form.cleaned_data.get('zeplin_token')
        project_id = form.cleaned_data['zeplin_project_id']
        screen_id = form.cleaned_data['zeplin_screen_id']
        live_url = form.cleaned_data['live_url']
        
        report = form.save(commit=False)
        
        try:
            # 1. Zeplin
            z_service = ZeplinService(token=token if token else None)
            zeplin_data = z_service.fetch_screen_data(project_id, screen_id)
            report.raw_json_data = zeplin_data
            
            # Images
            design_url = zeplin_data['screen'].get('image', {}).get('original_url')
            if not design_url:
                 raise ValueError("Could not find original_url for the screen image.")
                 
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            design_img_path = os.path.join(settings.MEDIA_ROOT, f"temp_design_{screen_id}.png")
            z_service.download_design_image(design_url, design_img_path)
            
            # 2. Screenshot & DOM stats & JS Errors
            live_img_path = os.path.join(settings.MEDIA_ROOT, f"temp_live_{screen_id}.png")
            page_data = ScreenshotService.capture_screenshot(live_url, live_img_path)
            report.js_error_count = len(page_data.get('js_errors', []))
            report.dom_node_count = page_data.get('dom_count', 0)
            report.raw_json_data['js_errors'] = page_data.get('js_errors', [])
            
            # 3. Compare Images
            diff_img_path = os.path.join(settings.MEDIA_ROOT, f"temp_diff_{screen_id}.png")
            mismatch_px, mismatch_regions = ComparisonService.compare_images(design_img_path, live_img_path, diff_img_path, threshold=0.1)
            report.pixel_mismatch_count = mismatch_px
            report.mismatch_regions = mismatch_regions
            
            # 4. CSS Validation
            mismatches, element_inventory = CSSValidationService.validate_css(live_url, zeplin_data)
            report.css_mismatch_count = len(mismatches)
            report.zeplin_layer_count = len(zeplin_data.get('layers', []))
            report.raw_json_data['css_mismatches'] = mismatches
            report.raw_json_data['element_inventory'] = element_inventory
            
            # Status
            report.status = "PASS" if mismatch_px < 5000 and report.css_mismatch_count == 0 and report.js_error_count == 0 else "FAIL"
            
            # Save files to model
            with open(design_img_path, 'rb') as f:
                report.design_image.save(f"design_{screen_id}.png", File(f), save=False)
            with open(live_img_path, 'rb') as f:
                report.live_image.save(f"live_{screen_id}.png", File(f), save=False)
            with open(diff_img_path, 'rb') as f:
                report.diff_image.save(f"diff_{screen_id}.png", File(f), save=False)
                
            report.save()
            
            # Cleanup
            try:
                os.remove(design_img_path)
                os.remove(live_img_path)
                os.remove(diff_img_path)
            except Exception:
                pass
            
            return redirect('validator:report', pk=report.pk)
            
        except Exception as e:
            form.add_error(None, f"Validation Failed: {str(e)}")
            return self.form_invalid(form)


class ReportPageView(DetailView):
    model = ValidationReport
    template_name = 'report.html'
    context_object_name = 'report'


class ReportListView(ListView):
    model = ValidationReport
    template_name = 'list.html'
    context_object_name = 'reports'
    paginate_by = 10
    
    def get_queryset(self):
        from django.db.models import Q
        qs = super().get_queryset()
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(zeplin_project_id__icontains=q) |
                Q(zeplin_screen_id__icontains=q) |
                Q(live_url__icontains=q)
            )
            
        date_filter = self.request.GET.get('date_filter')
        if date_filter:
            qs = qs.filter(created_at__date=date_filter)
            
        return qs.order_by('-created_at')


class LocateDefectView(DetailView):
    model = ValidationReport
    template_name = 'locate.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.object
        idx = int(self.kwargs.get('idx', 0))
        
        defects = report.raw_json_data.get('css_mismatches', [])
        defect = defects[idx] if idx < len(defects) else {}
        
        # Parse location string like "(851, 501) — 517x52px"
        x, y, w, h = 0, 0, 200, 50
        location = defect.get('location', '')
        if location:
            import re
            coords = re.findall(r'(\d+)', location)
            if len(coords) >= 4:
                x, y, w, h = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
            elif len(coords) >= 2:
                x, y = int(coords[0]), int(coords[1])
        
        # Severity color mapping
        severity = defect.get('severity', 'medium')
        color_map = {'critical': 'danger', 'high': 'warning', 'medium': 'info'}
        
        context['defect'] = defect
        context['defect_idx'] = idx
        context['defect_x'] = max(x - 2, 0)
        context['defect_y'] = max(y - 2, 0)
        context['defect_w'] = w + 4  # snug fit with small padding
        context['defect_h'] = h + 4
        context['label_y'] = max(y - 24, 0)
        context['severity_color'] = color_map.get(severity, 'info')
        return context


class LocateAllDefectsView(DetailView):
    model = ValidationReport
    template_name = 'locate_all.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.object
        
        defects_with_coords = []
        color_map = {'critical': 'danger', 'high': 'warning', 'medium': 'info'}
        
        import re
        for idx, defect in enumerate(report.raw_json_data.get('css_mismatches', [])):
            x, y, w, h = 0, 0, 0, 0
            location = defect.get('location', '')
            if location:
                coords = re.findall(r'(\d+)', location)
                if len(coords) >= 4:
                    x, y, w, h = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                elif len(coords) >= 2:
                    x, y = int(coords[0]), int(coords[1])
            
            if w > 0 and h > 0:
                severity = defect.get('severity', 'medium')
                defect_copy = defect.copy()
                defect_copy['idx'] = idx
                defect_copy['x'] = max(x - 2, 0)
                defect_copy['y'] = max(y - 2, 0)
                defect_copy['w'] = w + 4
                defect_copy['h'] = h + 4
                defect_copy['label_y'] = max(y - 24, 0)
                defect_copy['color_cls'] = color_map.get(severity, 'info')
                
                # Full details for the popovers section
                defect_copy['problem_description'] = defect.get('description', 'Mismatch detected.')
                defect_copy['selector'] = defect.get('selector', 'Unknown Selector')
                defect_copy['expected_value'] = defect.get('expected', 'N/A')
                defect_copy['actual_value'] = defect.get('actual', 'N/A')
                defect_copy['element'] = defect.get('element', 'Unknown Element')
                defect_copy['property'] = defect.get('property', 'N/A')
                
                defects_with_coords.append(defect_copy)
                
        context['defects_with_coords'] = defects_with_coords
        return context
