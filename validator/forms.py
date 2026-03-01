from django import forms
from .models import ValidationReport

class ValidationForm(forms.ModelForm):
    zeplin_token = forms.CharField(max_length=255, required=False, help_text="Optional if ZEP_DEFAULT_TOKEN is set in .env")
    
    class Meta:
        model = ValidationReport
        fields = ['zeplin_project_id', 'zeplin_screen_id', 'live_url']
        widgets = {
            'zeplin_project_id': forms.TextInput(attrs={'value': '66c45f1c5c37f6cb69fddb8d'}),
            'zeplin_screen_id': forms.TextInput(attrs={'value': '695f5c885da4446e4fcd18e3'}),
            'live_url': forms.URLInput(attrs={'value': 'https://deb.careers360.org/'}),
        }

class GenerateCodeForm(forms.Form):
    zeplin_project_id = forms.CharField(max_length=100, initial='5c4ea8a26910a6bef537d67f', label="Zeplin Project ID")
    zeplin_screen_id = forms.CharField(max_length=100, initial='695b97d21e9234f736bf5127', label="Zeplin Screen ID")
    zeplin_token = forms.CharField(max_length=255, required=False, help_text="Optional if ZEP_DEFAULT_TOKEN is set in .env")
