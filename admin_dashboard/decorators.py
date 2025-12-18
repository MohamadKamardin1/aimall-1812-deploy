# admin_dashboard/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse_lazy
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from django.contrib.auth.decorators import login_required
        actual_decorator = login_required(
            login_url=reverse_lazy('admin_dashboard:login')
        )
        wrapped_view = actual_decorator(view_func)
        return user_passes_test(
            lambda u: u.is_authenticated and u.user_type == 'admin',
            login_url=reverse_lazy('admin_dashboard:login')
        )(wrapped_view)(request, *args, **kwargs)
    return wrapper