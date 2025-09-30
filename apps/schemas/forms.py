from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field
from .models import Schema, SchemaVersion
import json

class SchemaForm(forms.ModelForm):
    class Meta:
        model = Schema
        fields = ['key', 'owner', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Create Schema', css_class='btn btn-primary'))

class SchemaVersionForm(forms.ModelForm):
    json_schema_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 15, 'class': 'font-monospace'}),
        help_text='JSON Schema in Draft 2020-12 format',
        label='JSON Schema'
    )
    
    class Meta:
        model = SchemaVersion
        fields = ['version', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Create Version', css_class='btn btn-primary'))
        
        # 초기값 설정 (편집 시)
        if self.instance and self.instance.pk:
            self.fields['json_schema_text'].initial = json.dumps(
                self.instance.json_schema, 
                indent=2
            )
    
    def clean_json_schema_text(self):
        text = self.cleaned_data['json_schema_text']
        try:
            schema = json.loads(text)
            return schema
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'Invalid JSON: {str(e)}')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.json_schema = self.cleaned_data['json_schema_text']
        if commit:
            instance.save()
        return instance