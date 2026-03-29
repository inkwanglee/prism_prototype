from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.apps import apps
from django import forms
import csv
import io


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_APP_LABELS = {'core', 'accounts', 'schemas', 'datasets', 'ingestion', 'qaqc', 'lineage'}


def _get_project_models():
    """Return all concrete Django models belonging to the project's apps."""
    result = []
    for model in apps.get_models():
        if model._meta.app_label in PROJECT_APP_LABELS:
            result.append(model)
    return sorted(result, key=lambda m: (m._meta.app_label, m._meta.model_name))


def _resolve_model(app_label, model_name):
    """Safely resolve a model from app_label + model_name."""
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return None
    if model._meta.app_label not in PROJECT_APP_LABELS:
        return None
    return model


def _build_model_form(model):
    """Dynamically build a ModelForm for any model."""
    excluded = []
    for field in model._meta.get_fields():
        if not hasattr(field, 'column'):
            continue
        if getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
            excluded.append(field.name)
        if field.primary_key and not getattr(field, 'editable', True):
            excluded.append(field.name)

    class DynForm(forms.ModelForm):
        class Meta:
            _model = model
            fields = '__all__'
            exclude = excluded

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for name, f in self.fields.items():
                f.widget.attrs.setdefault('class', 'form-control')
                if isinstance(f.widget, forms.Select):
                    f.widget.attrs['class'] = 'form-select'
                if isinstance(f.widget, forms.CheckboxInput):
                    f.widget.attrs['class'] = 'form-check-input'

    DynForm.Meta.model = model
    return DynForm


def _get_editable_fields(model):
    """Return field objects that are user-editable (for CSV headers etc.)."""
    fields = []
    for field in model._meta.get_fields():
        if not hasattr(field, 'column'):
            continue
        if field.primary_key and not getattr(field, 'editable', True):
            continue
        if getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
            continue
        fields.append(field)
    return fields


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@login_required
def table_list(request):
    """List all database tables from project apps."""
    models = _get_project_models()
    table_info = []
    for model in models:
        try:
            count = model.objects.count()
        except Exception:
            count = '—'
        table_info.append({
            'app_label': model._meta.app_label,
            'model_name': model._meta.model_name,
            'verbose_name': model._meta.verbose_name.title(),
            'verbose_name_plural': model._meta.verbose_name_plural.title(),
            'db_table': model._meta.db_table,
            'row_count': count,
            'field_count': len([f for f in model._meta.get_fields() if hasattr(f, 'column')]),
        })

    q = request.GET.get('q', '').strip()
    if q:
        table_info = [t for t in table_info if q.lower() in t['db_table'].lower()
                      or q.lower() in t['verbose_name'].lower()
                      or q.lower() in t['app_label'].lower()]

    context = {
        'page_title': 'Datasets',
        'tables': table_info,
        'search_q': q,
    }
    return render(request, 'datasets/list.html', context)


@login_required
def table_view(request, app_label, model_name):
    """View all rows of a table."""
    model = _resolve_model(app_label, model_name)
    if model is None:
        messages.error(request, 'Table not found.')
        return redirect('datasets:list')

    fields = [f for f in model._meta.get_fields() if hasattr(f, 'column')]
    queryset = model.objects.all()[:500]

    rows = []
    for obj in queryset:
        row = []
        for field in fields:
            val = getattr(obj, field.attname, '')
            row.append(val)
        rows.append({'pk': obj.pk, 'cells': row})

    context = {
        'page_title': f'{model._meta.verbose_name_plural.title()}',
        'model_meta': model._meta,
        'app_label': app_label,
        'model_name': model_name,
        'fields': fields,
        'rows': rows,
        'total_count': model.objects.count(),
    }
    return render(request, 'datasets/table_view.html', context)


@login_required
def table_add_entry(request, app_label, model_name):
    """Add a single row to a table."""
    model = _resolve_model(app_label, model_name)
    if model is None:
        messages.error(request, 'Table not found.')
        return redirect('datasets:list')

    FormClass = _build_model_form(model)

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Entry added to {model._meta.verbose_name_plural}.')
            return redirect('datasets:table_view', app_label=app_label, model_name=model_name)
    else:
        form = FormClass()

    context = {
        'page_title': f'Add {model._meta.verbose_name.title()}',
        'form': form,
        'app_label': app_label,
        'model_name': model_name,
        'model_verbose': model._meta.verbose_name.title(),
    }
    return render(request, 'datasets/table_add.html', context)


@login_required
def table_add_bulk(request, app_label, model_name):
    """Bulk-add rows via CSV upload."""
    model = _resolve_model(app_label, model_name)
    if model is None:
        messages.error(request, 'Table not found.')
        return redirect('datasets:list')

    editable_fields = _get_editable_fields(model)
    expected_headers = [f.name for f in editable_fields]

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please upload a CSV file.')
        elif not csv_file.name.endswith('.csv'):
            messages.error(request, 'File must be a .csv file.')
        else:
            try:
                decoded = csv_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                created = 0
                errors_count = 0
                for row in reader:
                    try:
                        FormClass = _build_model_form(model)
                        form = FormClass(row)
                        if form.is_valid():
                            form.save()
                            created += 1
                        else:
                            errors_count += 1
                    except Exception:
                        errors_count += 1
                if created:
                    messages.success(request, f'{created} entries added successfully.')
                if errors_count:
                    messages.warning(request, f'{errors_count} rows had errors and were skipped.')
                return redirect('datasets:table_view', app_label=app_label, model_name=model_name)
            except Exception as e:
                messages.error(request, f'Error processing CSV: {e}')

    context = {
        'page_title': f'Bulk Add — {model._meta.verbose_name_plural.title()}',
        'app_label': app_label,
        'model_name': model_name,
        'model_verbose': model._meta.verbose_name_plural.title(),
        'expected_headers': expected_headers,
    }
    return render(request, 'datasets/table_bulk.html', context)


@login_required
def table_delete_entry(request, app_label, model_name, pk):
    """Delete a single row from a table."""
    model = _resolve_model(app_label, model_name)
    if model is None:
        messages.error(request, 'Table not found.')
        return redirect('datasets:list')

    try:
        obj = model.objects.get(pk=pk)
        obj.delete()
        messages.success(request, f'Entry deleted from {model._meta.verbose_name_plural}.')
    except model.DoesNotExist:
        messages.error(request, 'Entry not found.')

    return redirect('datasets:table_view', app_label=app_label, model_name=model_name)
