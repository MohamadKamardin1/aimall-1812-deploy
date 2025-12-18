import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import (
    DeleteView,
    DetailView,
    FormView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
)

from accounts.models import Vendor
from products.models import (
    ProductAddon,
    ProductAddonMapping,
    ProductTemplate,
    ProductVariant,
    UnitPrice,
)
from .forms import UnitPriceForm, VendorLoginForm, VendorRegistrationForm
from .mixins import VendorLoginRequiredMixin

logger = logging.getLogger(__name__)


# ======================
# AUTH VIEWS
# ======================

class VendorRegisterView(FormView):
    template_name = 'vendor_dashboard/register.html'
    form_class = VendorRegistrationForm
    success_url = reverse_lazy('vendor_dashboard:dashboard')

    def form_valid(self, form):
        vendor = form.save()
        login(self.request, vendor.user)
        messages.success(self.request, f"Welcome, {vendor.names}! Your vendor account has been created.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)


class VendorLoginView(FormView):
    template_name = 'vendor_dashboard/login.html'
    form_class = VendorLoginForm

    def get_success_url(self):
        next_url = self.request.GET.get('next') or self.request.POST.get('next')
        if next_url:
            url_is_safe = url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            )
            if url_is_safe:
                return next_url
        return reverse_lazy('vendor_dashboard:dashboard')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.vendor.names}!")
        return super().form_valid(form)


class VendorLogoutView(VendorLoginRequiredMixin, RedirectView):
    url = reverse_lazy('vendor_dashboard:login')

    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        return super().get(request, *args, **kwargs)


# ======================
# DASHBOARD & PROFILE
# ======================
# vendor_dashboard/views.py
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.db.models import F


# vendor_dashboard/views.py
from django.views.generic import TemplateView
from django.db.models import Count, Avg
from .mixins import VendorLoginRequiredMixin
from products.models import ProductVariant

class VendorDashboardView(VendorLoginRequiredMixin, TemplateView):
    template_name = 'vendor_dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor

        # Fetch variants with related data (for property access)
        variants = ProductVariant.objects.filter(
            vendor=vendor
        ).select_related('product_template__category')

        total = variants.count()
        active = variants.filter(is_active=True, is_approved=True).count()
        pending = variants.filter(is_approved=False).count()

        # Recent activity
        recent = list(variants.order_by('-updated_at')[:5])

        # Top products (just latest 5)
        top_products = list(variants.order_by('-updated_at')[:5])

        # Market zone distribution
        market_stats = variants.values(
            'market_zone__name'
        ).annotate(count=Count('id')).order_by('-count')

        # ✅ Calculate average profit in Python
        profit_values = []
        for v in variants:
            profit_values.append(float(v.effective_profit_percentage))
        
        if profit_values:
            avg_profit = sum(profit_values) / len(profit_values)
        else:
            avg_profit = 0.0

        context.update({
            'total_products': total,
            'active_products': active,
            'pending_approval': pending,
            'recent_activity': recent,
            'top_products': top_products,
            'market_stats': market_stats,
            'avg_profit_margin': round(avg_profit, 1),
            'vendor': vendor,
        })
        return context

class VendorProfileEditView(VendorLoginRequiredMixin, UpdateView):
    model = Vendor
    fields = [
        'names', 'business_name', 'business_address', 'business_description',
        'license_document', 'id_document'
    ]
    template_name = 'vendor_dashboard/profile_edit.html'
    success_url = reverse_lazy('vendor_dashboard:profile_edit')

    def get_object(self, queryset=None):
        return self.request.user.vendor

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)


# ======================
# PRODUCT TEMPLATES (BROWSE)
# ======================

class ProductTemplateListView(VendorLoginRequiredMixin, ListView):
    model = ProductTemplate
    template_name = 'vendor_dashboard/product_templates.html'
    context_object_name = 'templates'
    paginate_by = 12

    def get_queryset(self):
        return ProductTemplate.objects.filter(
            is_active=True,
            is_verified=True
        ).select_related('category', 'primary_unit_type').prefetch_related('available_units')


# ======================
# CREATE PRODUCT VARIANT
# ======================
from .forms import ProductVariantForm, UnitPriceForm  # Ensure both are imported

class CreateProductVariantView(VendorLoginRequiredMixin, FormView):
    template_name = 'vendor_dashboard/product_variant_create.html'
    form_class = ProductVariantForm
    success_url = reverse_lazy('vendor_dashboard:product_list')

    def dispatch(self, request, *args, **kwargs):
        self.template = get_object_or_404(ProductTemplate, pk=self.kwargs['template_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template'] = self.template
        units = self.template.available_units.filter(is_active=True)
        context['units'] = units

        if self.request.method == 'POST':
            price_form = UnitPriceForm(self.request.POST, units=units)
        else:
            price_form = UnitPriceForm(units=units)

        # Only cost fields are needed (selling price is auto-calculated)
        pricing_fields = []
        for unit in units:
            cost_field = price_form[f'cost_price_{unit.id}']
            pricing_fields.append({
                'unit': unit,
                'cost_field': cost_field,
            })
        context['pricing_fields'] = pricing_fields
        context['price_form'] = price_form
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        units = self.template.available_units.filter(is_active=True)
        price_form = UnitPriceForm(request.POST, units=units)
        if form.is_valid() and price_form.is_valid():
            return self.form_valid(form, price_form)
        else:
            return self.form_invalid(form, price_form)

    def form_valid(self, form, price_form):
        vendor = self.request.user.vendor
        market_zone = form.cleaned_data['market_zone']

        if ProductVariant.objects.filter(
            product_template=self.template,
            vendor=vendor,
            market_zone=market_zone
        ).exists():
            messages.error(self.request, "You already have a product for this template and market zone.")
            return self.render_to_response(self.get_context_data(form=form))

        with transaction.atomic():
            variant = form.save(commit=False)
            variant.product_template = self.template
            variant.vendor = vendor
            variant.is_approved = False
            variant.save()

            # ✅ ONLY save cost_price — selling_price is auto-calculated in UnitPrice.save()
            for unit in self.template.available_units.filter(is_active=True):
                cost_key = f'cost_price_{unit.id}'
                cost_price = price_form.cleaned_data[cost_key]
                UnitPrice.objects.update_or_create(
                    product_variant=variant,
                    unit=unit,
                    defaults={'cost_price': cost_price}  # selling_price handled automatically
                )

        messages.success(self.request, "Product variant created successfully! Awaiting admin approval.")
        return redirect(self.success_url)

    def form_invalid(self, form, price_form):
        return self.render_to_response(self.get_context_data(form=form, price_form=price_form))


from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

class VendorProductEditView(VendorLoginRequiredMixin, FormView):
    template_name = 'vendor_dashboard/product_variant_edit.html'
    form_class = ProductVariantForm

    def dispatch(self, request, *args, **kwargs):
        self.variant = get_object_or_404(
            ProductVariant,
            pk=self.kwargs['pk'],
            vendor=request.user.vendor  # 🔒 Privacy: only own variants
        )
        self.template = self.variant.product_template
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.variant
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['template'] = self.template
        context['variant'] = self.variant
        units = self.template.available_units.filter(is_active=True)
        context['units'] = units

        # ✅ store dict separately
        unit_prices_dict = {price.unit_id: price for price in self.variant.unit_prices.all()}
        context['unit_prices_dict'] = unit_prices_dict

        if self.request.method == 'POST':
            price_form = UnitPriceForm(self.request.POST, units=units)
        else:
            initial = {}
            for price in self.variant.unit_prices.all():
                initial[f'cost_price_{price.unit.id}'] = price.cost_price
            price_form = UnitPriceForm(units=units, initial=initial)

        pricing_fields = []
        for unit in units:
            cost_field = price_form[f'cost_price_{unit.id}']
            pricing_fields.append({
                'unit': unit,
                'cost_field': cost_field,
            })

        context['pricing_fields'] = pricing_fields
        context['price_form'] = price_form

        return context

        # In VendorProductEditView.get_context_data
        

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        units = self.template.available_units.filter(is_active=True)
        price_form = UnitPriceForm(request.POST, units=units)
        if form.is_valid() and price_form.is_valid():
            return self.form_valid(form, price_form)
        else:
            return self.form_invalid(form, price_form)

    def form_valid(self, form, price_form):
        # Save variant (market_zone, profit, quality, active)
        variant = form.save()

        # Update cost prices (selling_price auto-calculated in UnitPrice.save())
        for unit in self.template.available_units.filter(is_active=True):
            cost_price = price_form.cleaned_data[f'cost_price_{unit.id}']
            UnitPrice.objects.update_or_create(
                product_variant=variant,
                unit=unit,
                defaults={'cost_price': cost_price}
            )

        messages.success(self.request, "Product variant updated successfully.")
        return redirect('vendor_dashboard:product_detail', pk=variant.pk)
    

# ======================
# PRODUCT MANAGEMENT (LIST, VIEW, EDIT, DELETE, ADDONS)
# ======================

class VendorProductListView(VendorLoginRequiredMixin, ListView):
    model = ProductVariant
    template_name = 'vendor_dashboard/product_list.html'
    context_object_name = 'variants'
    paginate_by = 10

    def get_queryset(self):
        return ProductVariant.objects.filter(vendor=self.request.user.vendor).select_related(
            'product_template', 'market_zone'
        ).prefetch_related('unit_prices__unit')


# vendor_dashboard/views.py
from django.views.generic import DetailView
from .mixins import VendorLoginRequiredMixin
from products.models import ProductVariant

class VendorProductDetailView(VendorLoginRequiredMixin, DetailView):
    model = ProductVariant
    template_name = 'vendor_dashboard/product_detail.html'
    context_object_name = 'variant'

    def get_queryset(self):
        return ProductVariant.objects.filter(vendor=self.request.user.vendor)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        variant = self.object
        
        # Annotate each UnitPrice with margin
        annotated_prices = []
        for price in variant.unit_prices.all():
            margin = price.selling_price - price.cost_price
            annotated_prices.append({
                'price': price,
                'margin': margin,
            })
        
        context['annotated_prices'] = annotated_prices
        return context

# class VendorProductEditView(VendorLoginRequiredMixin, FormView):
#     template_name = 'vendor_dashboard/product_variant_edit.html'
#     form_class = ProductVariantForm

#     def dispatch(self, request, *args, **kwargs):
#         self.variant = get_object_or_404(
#             ProductVariant,
#             pk=self.kwargs['pk'],
#             vendor=request.user.vendor
#         )
#         self.template = self.variant.product_template
#         return super().dispatch(request, *args, **kwargs)

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['instance'] = self.variant
#         return kwargs

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['template'] = self.template
#         context['variant'] = self.variant
#         units = self.template.available_units.filter(is_active=True)
#         context['units'] = units

#         if self.request.method == 'POST':
#             price_form = UnitPriceForm(self.request.POST, units=units)
#         else:
#             initial = {}
#             for price in self.variant.unit_prices.all():
#                 initial[f'cost_price_{price.unit.id}'] = price.cost_price
#                 initial[f'selling_price_{price.unit.id}'] = price.selling_price
#             price_form = UnitPriceForm(units=units, initial=initial)

#         pricing_fields = []
#         for unit in units:
#             cost_field = price_form[f'cost_price_{unit.id}']
#             sell_field = price_form[f'selling_price_{unit.id}']
#             pricing_fields.append({'unit': unit, 'cost_field': cost_field, 'sell_field': sell_field})
#         context['pricing_fields'] = pricing_fields
#         context['price_form'] = price_form
#         return context

#     def post(self, request, *args, **kwargs):
#         form = self.get_form()
#         units = self.template.available_units.filter(is_active=True)
#         price_form = UnitPriceForm(request.POST, units=units)
#         if form.is_valid() and price_form.is_valid():
#             return self.form_valid(form, price_form)
#         else:
#             return self.form_invalid(form, price_form)

#     def form_valid(self, form, price_form):
#         variant = form.save()
#         for unit in self.template.available_units.filter(is_active=True):
#             cost_price = price_form.cleaned_data[f'cost_price_{unit.id}']
#             selling_price = price_form.cleaned_data[f'selling_price_{unit.id}']

#             if selling_price <= 0:
#                 profit_pct = variant.effective_profit_percentage
#                 multiplier = Decimal('1.00') + (profit_pct / Decimal('100.00'))
#                 selling_price = (cost_price * multiplier).quantize(Decimal('0.01'))

#             UnitPrice.objects.update_or_create(
#                 product_variant=variant,
#                 unit=unit,
#                 defaults={'cost_price': cost_price, 'selling_price': selling_price}
#             )

#         messages.success(self.request, "Product variant updated successfully.")
#         return redirect('vendor_dashboard:product_detail', pk=variant.pk)

#     def get_success_url(self):
#         return reverse_lazy('vendor_dashboard:product_detail', kwargs={'pk': self.variant.pk})


class VendorProductDeleteView(VendorLoginRequiredMixin, DeleteView):
    model = ProductVariant
    success_url = reverse_lazy('vendor_dashboard:product_list')

    def get_queryset(self):
        return ProductVariant.objects.filter(vendor=self.request.user.vendor)

    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Product variant deleted successfully.")
        return super().delete(request, *args, **kwargs)

# vendor_dashboard/views.py
from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib import messages
from .mixins import VendorLoginRequiredMixin
from products.models import ProductAddon, ProductAddonMapping

class VendorProductAddonsView(VendorLoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        self.variant = get_object_or_404(
            ProductVariant,
            pk=self.kwargs['pk'],
            vendor=request.user.vendor
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = {
            'variant': self.variant,
            'all_addons': ProductAddon.objects.filter(is_active=True),
            'assigned_addon_ids': list(
                self.variant.available_addons.values_list('addon_id', flat=True)
            )
        }
        return render(request, 'vendor_dashboard/product_addons.html', context)

    def post(self, request, *args, **kwargs):
        selected_ids = request.POST.getlist('addons')
        
        # Clear existing
        self.variant.available_addons.all().delete()

        # Add selected
        for addon_id in selected_ids:
            ProductAddonMapping.objects.create(
                product_variant=self.variant,
                addon_id=addon_id
            )

        messages.success(request, "Addons updated successfully.")
        return redirect('vendor_dashboard:product_detail', pk=self.variant.pk)