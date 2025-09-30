from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.decorators import login_required

def home(request):
    """홈 페이지"""
    context = {
        'page_title': 'PRISM Dashboard',
    }
    return render(request, 'core/home.html', context)

def health(request):
    """헬스 체크 엔드포인트"""
    try:
        # DB 연결 확인
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

@login_required
def settings_view(request):
    """설정 페이지"""
    context = {
        'page_title': 'Settings',
        'user_roles': getattr(request.user, 'prism_roles', []),
        'project_ids': getattr(request.user, 'project_ids', []),
    }
    return render(request, 'core/settings.html', context)