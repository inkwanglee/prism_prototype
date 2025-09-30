from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Dataset
from .forms import DatasetForm

@login_required
def dataset_list(request):
    """데이터셋 목록"""
    datasets = Dataset.objects.filter(status='active')
    
    # 필터링
    schema_ref = request.GET.get('schema_ref')
    owner = request.GET.get('owner')
    
    if schema_ref:
        datasets = datasets.filter(schema_ref__icontains=schema_ref)
    if owner:
        datasets = datasets.filter(owner__icontains=owner)
    
    context = {
        'page_title': 'Datasets',
        'datasets': datasets,
        'schema_ref_filter': schema_ref,
        'owner_filter': owner,
    }
    return render(request, 'datasets/list.html', context)

@login_required
def dataset_detail(request, pk):
    """데이터셋 상세"""
    dataset = get_object_or_404(Dataset, pk=pk)
    context = {
        'page_title': f'Dataset: {dataset.key}',
        'dataset': dataset,
    }
    return render(request, 'datasets/detail.html', context)

@login_required
def dataset_create(request):
    """데이터셋 생성"""
    if request.method == 'POST':
        form = DatasetForm(request.POST)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.created_by = request.user
            dataset.save()
            messages.success(request, f'Dataset "{dataset.key}" created successfully.')
            return redirect('datasets:detail', pk=dataset.pk)
    else:
        form = DatasetForm()
    
    context = {
        'page_title': 'Create Dataset',
        'form': form,
    }
    return render(request, 'datasets/form.html', context)