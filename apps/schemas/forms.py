# =============================================================================
# Forms for the legacy schema registry (Schema / SchemaVersion).
# =============================================================================
# These forms power the "Add Schema" and "Add Version" pages. The
# Schema.json editor on the main Schemas page uses a plain <textarea>
# and a hand-written view, not these crispy-forms helpers.
# =============================================================================

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field
from .models import Schema, SchemaVersion
import json


class SchemaForm(forms.ModelForm):
    # Form for creating a new legacy Schema record (key/owner/description).
    class Meta:
        model = Schema
        fields = ['key', 'owner', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # crispy-forms helper renders the form with Bootstrap markup
        # and a submit button so the template can just `{% crispy form %}`.
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Create Schema', css_class='btn btn-primary'))


class SchemaVersionForm(forms.ModelForm):
    # Form for adding a new version to an existing Schema.
    #
    # The JSON Schema definition is captured via a `json_schema_text`
    # CharField so the user can paste raw JSON. `clean_json_schema_text`
    # parses it into a Python dict before the model's JSONField stores it.
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

        # When editing an existing version, pretty-print the stored JSON
        # back into the textarea so it's readable.
        if self.instance and self.instance.pk:
            self.fields['json_schema_text'].initial = json.dumps(
                self.instance.json_schema,
                indent=2
            )

    def clean_json_schema_text(self):
        # Parse the textarea contents into a Python dict so the model
        # field (JSONField) can store it. Surface JSON errors as form
        # validation errors rather than 500s.
        text = self.cleaned_data['json_schema_text']
        try:
            schema = json.loads(text)
            return schema
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f'Invalid JSON: {str(e)}')

    def save(self, commit=True):
        # Move the parsed JSON onto the model's json_schema field before
        # saving. We use commit=False to set the value first and only
        # save when the caller wants it persisted.
        instance = super().save(commit=False)
        instance.json_schema = self.cleaned_data['json_schema_text']
        if commit:
            instance.save()
        return instance
