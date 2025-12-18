# vendor_dashboard/mixins.py
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

from django.utils.cache import add_never_cache_headers

class VendorLoginRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You need to log in to access the vendor dashboard.")
            return redirect(f"{reverse_lazy('vendor_dashboard:login')}?next={request.get_full_path()}")
        
        if request.user.user_type != 'vendor':
            messages.error(request, "Only vendors can access this dashboard.")
            return redirect('vendor_dashboard:login')
        
        response = super().dispatch(request, *args, **kwargs)
        add_never_cache_headers(response)  # Prevent caching
        return response