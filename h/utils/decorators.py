from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

def manager_required(view_func):
    """
    Decorator: يضمن أن المستخدم مسجّل دخول وله دور MANAGER.
    إذا لم يكن مسجونًا: يعيد توجيه إلى صفحة تسجيل الدخول.
    إذا كان مسجّلًا لكنه ليس MANAGER: يعيد 403.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user or not user.is_authenticated:
            # redirect to UI login page
            return redirect('ui_login')
        if getattr(user, 'role', None) != 'MANAGER':
            return HttpResponseForbidden("غير مصرح لك بالوصول إلى هذه الصفحة.")
        return view_func(request, *args, **kwargs)
    return _wrapped
