from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Schema, SchemaVersion
from .forms import SchemaForm, SchemaVersionForm
import jsonschema

@login_required
def schema_list(request):
    """스키마 목록"""
    schemas = Schema.objects.all().prefetch_related('versions')
    context = {
        'page_title': 'Schema Registry',
        'schemas': schemas,
    }
    return render(request, 'schemas/list.html', context)

@login_required
def schema_detail(request, pk):
    """스키마 상세"""
    schema = get_object_or_404(Schema, pk=pk)
    versions = schema.versions.all()
    context = {
        'page_title': f'Schema: {schema.key}',
        'schema': schema,
        'versions': versions,
    }
    return render(request, 'schemas/detail.html', context)

@login_required
def schema_create(request):
    """스키마 생성"""
    if request.method == 'POST':
        form = SchemaForm(request.POST)
        if form.is_valid():
            schema = form.save(commit=False)
            schema.created_by = request.user
            schema.save()
            messages.success(request, f'Schema "{schema.key}" created successfully.')
            return redirect('schemas:detail', pk=schema.pk)
    else:
        form = SchemaForm()
    
    context = {
        'page_title': 'Create Schema',
        'form': form,
    }
    return render(request, 'schemas/form.html', context)

@login_required
def version_create(request, schema_pk):
    """스키마 버전 생성"""
    schema = get_object_or_404(Schema, pk=schema_pk)
    
    if request.method == 'POST':
        form = SchemaVersionForm(request.POST)
        if form.is_valid():
            version = form.save(commit=False)
            version.schema = schema
            version.created_by = request.user
            
            # JSON Schema 유효성 검사
            try:
                # 스키마 자체가 유효한 JSON Schema인지 확인
                jsonschema.Draft202012Validator.check_schema(version.json_schema)
                version.save()
                messages.success(request, f'Version {version.version} created successfully.')
                return redirect('schemas:detail', pk=schema.pk)
            except jsonschema.SchemaError as e:
                messages.error(request, f'Invalid JSON Schema: {str(e)}')
    else:
        form = SchemaVersionForm()
    
    context = {
        'page_title': f'Add Version to {schema.key}',
        'schema': schema,
        'form': form,
    }
    return render(request, 'schemas/version_form.html', context)

@login_required
def version_approve(request, pk):
    """스키마 버전 승인"""
    version = get_object_or_404(SchemaVersion, pk=pk)
    
    if request.method == 'POST':
        version.status = 'approved'
        version.approved_by = request.user
        version.approved_at = timezone.now()
        version.save()
        messages.success(request, f'Version {version.version} approved.')
        return redirect('schemas:detail', pk=version.schema.pk)
    
    return redirect('schemas:detail', pk=version.schema.pk)