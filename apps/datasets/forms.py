from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import Dataset

class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['key', 'title', 'description', 'schema_ref', 'owner', 'project_id']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'schema_ref': 'e.g., drillhole.collar@0.1.0',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Create Dataset', css_class='btn btn-primary'))