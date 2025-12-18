from datetime import timedelta
from decimal import Decimal, InvalidOperation
from unicodedata import decimal
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.db.models import Sum, Prefetch, Avg, Count, Q
from django.db import models
from django.http import JsonResponse
from django.core.paginator import Paginator

from accounts.models import SecurityQuestion, User, Customer, UserSecurityAnswer, Vendor, Driver, AdminProfile
from location.models import DeliveryZone
from products.models import Category, MeasurementUnitType, ProductAddonMapping, ProductTemplate, ProductVariant, MeasurementUnit, GlobalSetting, UnitPrice
from markets.models import Market, MarketZone
from order.models import Order, OrderItem, ordertatusUpdate

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

from .decorators import admin_required
# ============================================
# HELPER FUNCTION
# ============================================
def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'




def admin_login_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone_number')
        password = request.POST.get('password')
        
        # Authenticate using phone number (assuming your User model uses phone as username)
        user = authenticate(request, username=phone, password=password)
        
        if user is not None:
            if user.is_active and user.user_type == 'admin':
                login(request, user)
                next_url = request.GET.get('next', 'admin_dashboard:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "Access denied. Admin privileges required.")
        else:
            messages.error(request, "Invalid phone number or password.")
    
    return render(request, 'admin_dashboard/auth/login.html')



from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def admin_logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You've been logged out successfully.")
        return redirect('home')  # Redirect to your homepage
    # Show confirmation page on GET
    return render(request, 'admin_dashboard/auth/logout_confirm.html')
# ============================================
# DASHBOARD
# ============================================
@admin_required
@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin Dashboard Overview"""
    # Basic statistics
    total_customers = Customer.objects.count()
    total_vendors = Vendor.objects.count()
    total_drivers = Driver.objects.count()
    total_products = ProductTemplate.objects.count()
    total_order = Order.objects.count()
    
    # Revenue calculations
    revenue_today = Order.objects.filter(
        created_at__date=timezone.now().date(),
        status__in=['completed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_week = Order.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=7),
        status__in=['completed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_month = Order.objects.filter(
        created_at__gte=timezone.now()-timedelta(days=30),
        status__in=['completed', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Pending verifications
    pending_vendors = Vendor.objects.filter(is_verified=False).count()
    pending_drivers = Driver.objects.filter(is_verified=False).count()
    
    # Recent order
    recent_order = Order.objects.select_related('customer').order_by('-created_at')[:10]
    
    # Recent activities (you can create an ActivityLog model later)
    recent_activities = []
    
    stats = {
        'total_customers': total_customers,
        'total_vendors': total_vendors,
        'total_drivers': total_drivers,
        'total_products': total_products,
        'total_order': total_order,
        'pending_vendors': pending_vendors,
        'pending_drivers': pending_drivers,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
    }

    return render(request, 'admin_dashboard/dashboard.html', {
        'stats': stats,
        'recent_order': recent_order,
        'recent_activities': recent_activities,
    })

# ============================================
# USER MANAGEMENT
# ============================================
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from accounts.models import User, Customer, Vendor, Driver, AdminProfile

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    user_type = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    users = User.objects.select_related('customer', 'vendor', 'driver', 'admin_profile').all()
    
    # Apply filters
    if user_type != 'all':
        users = users.filter(user_type=user_type)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'verified':
        users = users.filter(is_verified=True)
    elif status_filter == 'unverified':
        users = users.filter(is_verified=False)
    
    if search_query:
        users = users.filter(
            Q(phone_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(customer__names__icontains=search_query) |
            Q(vendor__names__icontains=search_query) |
            Q(driver__names__icontains=search_query) |
            Q(admin_profile__names__icontains=search_query)
        )
    
    # Apply ordering (newest first)
    users = users.order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(users, 25)  # Show 25 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats (calculate based on ALL users, not filtered)
    total_users = User.objects.count()
    customers_count = Customer.objects.count()
    vendors_count = Vendor.objects.count()
    drivers_count = Driver.objects.count()
    admins_count = AdminProfile.objects.count()
    
    # Get filtered counts for the current filter type
    if user_type != 'all':
        filtered_type_count = User.objects.filter(user_type=user_type).count()
    else:
        filtered_type_count = total_users
    
    context = {
        'page_obj': page_obj,
        'active_tab': user_type,
        'total_users': total_users,
        'customers_count': customers_count,
        'vendors_count': vendors_count,
        'drivers_count': drivers_count,
        'admins_count': admins_count,
        'filtered_type_count': filtered_type_count,
        'filters': {
            'type': user_type,
            'status': status_filter,
            'search': search_query,
        }
    }
    return render(request, 'admin_dashboard/users/manage_users.html', context)

# In admin_dashboard/views.py

@login_required
@user_passes_test(is_admin)
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Get user profile based on user type
    profile = None
    if user.user_type == 'customer':
        profile = getattr(user, 'customer', None)
        recent_orders = Order.objects.filter(customer=user).order_by('-created_at')[:5]
    elif user.user_type == 'vendor':
        profile = getattr(user, 'vendor', None)
        recent_orders = []
    elif user.user_type == 'driver':
        profile = getattr(user, 'driver', None)
        recent_orders = []
    elif user.user_type == 'admin':
        profile = getattr(user, 'admin_profile', None)
        recent_orders = []
    
    context = {
        'user': user,
        'profile': profile,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'admin_dashboard/users/user_detail.html', context)

from accounts.models import User

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        phone_number = user.phone_number
        user.delete()  # This will cascade-delete related profiles (vendor, driver, etc.)
        messages.success(request, f'User "{phone_number}" deleted successfully!')
    return redirect('admin_dashboard:manage-users')


@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        action = "activated" if user.is_active else "deactivated"
        messages.success(request, f'User {user.phone_number} has been {action}.')
    # ✅ FIX: Use namespaced URL
    return redirect('admin_dashboard:user-detail', user_id=user_id)

@login_required
@user_passes_test(is_admin)
def update_security_answers(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        questions = request.POST.getlist('question_id')
        answers = request.POST.getlist('answer')
        for q_id, answer in zip(questions, answers):
            if answer.strip():
                UserSecurityAnswer.objects.update_or_create(
                    user=user,
                    question_id=q_id,
                    defaults={'answer': answer.strip()}
                )
        messages.success(request, 'Security answers updated!')
    return redirect('admin_dashboard:edit-user', user_id=user_id)


@login_required
@user_passes_test(is_admin)
def verify_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.is_verified = True
        user.save()
        messages.success(request, f'User {user.phone_number} has been verified.')
    return redirect('admin_dashboard:user-detail', user_id=user_id)



@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    security_questions = SecurityQuestion.objects.all()
    security_answers = UserSecurityAnswer.objects.filter(user=user)
    
    if request.method == 'POST':
        # Update user fields
        user.phone_number = request.POST.get('phone_number')
        user.email = request.POST.get('email', '')
        user.user_type = request.POST.get('user_type')
        user.is_active = request.POST.get('is_active') == 'on'
        user.is_verified = request.POST.get('is_verified') == 'on'
        user.save()
        
        # Update profile based on user type
        if user.user_type == 'customer' and hasattr(user, 'customer'):
            user.customer.names = request.POST.get('customer_names', '')
            user.customer.address = request.POST.get('customer_address', '')
            user.customer.save()
        elif user.user_type == 'vendor' and hasattr(user, 'vendor'):
            user.vendor.names = request.POST.get('vendor_names', '')
            user.vendor.business_name = request.POST.get('vendor_business_name', '')
            user.vendor.business_license = request.POST.get('vendor_business_license', '')
            user.vendor.save()
        elif user.user_type == 'driver' and hasattr(user, 'driver'):
            user.driver.names = request.POST.get('driver_names', '')
            user.driver.license_number = request.POST.get('driver_license_number', '')
            user.driver.vehicle_type = request.POST.get('driver_vehicle_type', '')
            user.driver.vehicle_plate = request.POST.get('driver_vehicle_plate', '')
            user.driver.save()
        elif user.user_type == 'admin' and hasattr(user, 'admin_profile'):
            user.admin_profile.names = request.POST.get('admin_names', '')
            user.admin_profile.department = request.POST.get('admin_department', '')
            user.admin_profile.position = request.POST.get('admin_position', '')
            user.admin_profile.save()
        
        messages.success(request, f'User {user.phone_number} updated successfully!')
        return redirect('admin_dashboard:user-detail', user_id=user.id)
    
    return render(request, 'admin_dashboard/users/edit_user.html', {
        'user': user,
        'security_questions': security_questions,
        'security_answers': security_answers,
    })

# Update Security Answers
@login_required
@user_passes_test(is_admin)
def update_security_answers(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        questions = request.POST.getlist('question_id')
        answers = request.POST.getlist('answer')
        for q_id, answer in zip(questions, answers):
            if answer.strip():
                UserSecurityAnswer.objects.update_or_create(
                    user=user,
                    question_id=q_id,
                    defaults={'answer': answer.strip()}
                )
        messages.success(request, 'Security answers updated!')
    return redirect('admin_dashboard:edit-user', user_id=user_id)

# Reset Password
@login_required
@user_passes_test(is_admin)
def reset_user_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_pass = request.POST.get('new_password')
        confirm_pass = request.POST.get('confirm_password')
        if new_pass == confirm_pass and len(new_pass) >= 8:
            user.set_password(new_pass)
            user.save()
            messages.success(request, f'Password reset for {user.phone_number}')
        else:
            messages.error(request, 'Passwords must match and be at least 8 characters')
    return redirect('admin_dashboard:edit-user', user_id=user_id)


# ============================================
# VENDOR MANAGEMENT
# ============================================
@login_required
@user_passes_test(is_admin)
def manage_vendors(request):
    """Manage vendors with verification status"""
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    vendors = Vendor.objects.select_related('user').all()
    
    # Apply filters
    if status_filter == 'verified':
        vendors = vendors.filter(is_verified=True)
    elif status_filter == 'pending':
        vendors = vendors.filter(is_verified=False)
    elif status_filter == 'active':
        vendors = vendors.filter(user__is_active=True)
    elif status_filter == 'inactive':
        vendors = vendors.filter(user__is_active=False)
    
    if search_query:
        vendors = vendors.filter(
            Q(names__icontains=search_query) |
            Q(business_name__icontains=search_query) |
            Q(business_license__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )
    
    # Statistics
    total_vendors = vendors.count()
    verified_vendors = vendors.filter(is_verified=True).count()
    pending_vendors = vendors.filter(is_verified=False).count()
    active_vendors = vendors.filter(user__is_active=True).count()
    
    context = {
        'vendors': vendors,
        'total_vendors': total_vendors,
        'verified_vendors': verified_vendors,
        'pending_vendors': pending_vendors,
        'active_vendors': active_vendors,
        'filters': {
            'status': status_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'admin_dashboard/vendors/manage_vendors.html', context)
# Add to admin_dashboard/views.py
import secrets
@login_required
@user_passes_test(is_admin)
def add_vendor(request):
    if request.method == 'POST':
        try:
            # User data
            phone = request.POST.get('phone_number').strip()
            email = request.POST.get('email', '').strip()
            names = request.POST.get('names').strip()
            business_name = request.POST.get('business_name').strip()
            business_license = request.POST.get('business_license', '').strip()
            location = request.POST.get('location', '').strip()

            # Validate unique phone
            if User.objects.filter(phone_number=phone).exists():
                messages.error(request, "A user with this phone number already exists.")
                return render(request, 'admin_dashboard/vendors/add_vendor.html', {'data': request.POST})

            # Create User
            user = User.objects.create_user(
                phone_number=phone,
                email=email,
                password = secrets.token_urlsafe(12),
                user_type='vendor',
                is_active=True,
                is_verified=False
            )

            # Create Vendor Profile
            Vendor.objects.create(
                user=user,
                names=names,
                business_name=business_name,
                business_license=business_license,
                location=location
            )

            messages.success(request, f'Vendor "{business_name}" created successfully!')
            return redirect('admin_dashboard:manage-vendors')

        except Exception as e:
            messages.error(request, f'Error creating vendor: {str(e)}')
            return render(request, 'admin_dashboard/vendors/add_vendor.html', {'data': request.POST})

    return render(request, 'admin_dashboard/vendors/add_vendor.html')

# Add to views.py
import csv
from django.http import HttpResponse

@login_required
@user_passes_test(is_admin)
def export_vendors_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vendors.csv"'

    writer = csv.writer(response)
    writer.writerow(['Business Name', 'Owner', 'Phone', 'Email', 'License', 'Verified', 'Active', 'Joined'])

    vendors = Vendor.objects.select_related('user').all()
    for v in vendors:
        writer.writerow([
            v.business_name,
            v.names,
            v.user.phone_number,
            v.user.email or '',
            v.business_license or '',
            'Yes' if v.is_verified else 'No',
            'Yes' if v.user.is_active else 'No',
            v.user.date_joined.strftime('%Y-%m-%d %H:%M')
        ])

    return response


# Add to views.py

@login_required
@user_passes_test(is_admin)
def bulk_vendor_action(request):
    if request.method == 'POST':
        vendor_ids = request.POST.getlist('vendor_ids')
        action = request.POST.get('action')

        if not vendor_ids:
            messages.warning(request, 'No vendors selected.')
            return redirect('admin_dashboard:manage-vendors')

        vendors = Vendor.objects.filter(user_id__in=vendor_ids)

        if action == 'verify':
            vendors.update(is_verified=True, verified_at=timezone.now())
            messages.success(request, f'{vendors.count()} vendors verified.')
        elif action == 'suspend':
            User.objects.filter(id__in=vendor_ids).update(is_active=False)
            messages.success(request, f'{vendors.count()} vendors suspended.')
        elif action == 'activate':
            User.objects.filter(id__in=vendor_ids).update(is_active=True)
            messages.success(request, f'{vendors.count()} vendors activated.')

    return redirect('admin_dashboard:manage-vendors')


@login_required
@user_passes_test(is_admin)
def vendor_detail(request, vendor_id):
    """Vendor detail view"""
    vendor = get_object_or_404(Vendor.objects.select_related('user'), user_id=vendor_id)
    
    # Get vendor products
    products = ProductVariant.objects.filter(vendor=vendor).select_related('product_template')
    
    # Get vendor order
    order = Order.objects.filter(items__product_variant__vendor=vendor).distinct().order_by('-created_at')[:10]
    
    context = {
        'vendor': vendor,
        'products': products,
        'order': order,
    }
    
    return render(request, 'admin_dashboard/vendors/vendor_detail.html', context)
# Replace all redirect() calls with namespaced versions

@login_required
@user_passes_test(is_admin)
def verify_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, user_id=vendor_id)
    if request.method == 'POST':
        vendor.is_verified = True
        vendor.verified_at = timezone.now()
        vendor.save()
        messages.success(request, f'Vendor {vendor.business_name} has been verified.')
    return redirect('admin_dashboard:vendor-detail', vendor_id=vendor_id)

@login_required
@user_passes_test(is_admin)
def suspend_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, user_id=vendor_id)
    if request.method == 'POST':
        vendor.user.is_active = False
        vendor.user.save()
        messages.success(request, f'Vendor {vendor.business_name} has been suspended.')
    return redirect('admin_dashboard:vendor-detail', vendor_id=vendor_id)

@login_required
@user_passes_test(is_admin)
def activate_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, user_id=vendor_id)
    if request.method == 'POST':
        vendor.user.is_active = True
        vendor.user.save()
        messages.success(request, f'Vendor {vendor.business_name} has been activated.')
    return redirect('admin_dashboard:vendor-detail', vendor_id=vendor_id)


# ============================================
# DRIVER MANAGEMENT
# ============================================
from accounts.models import Driver

@login_required
@user_passes_test(is_admin)
def manage_drivers(request):
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    drivers = Driver.objects.select_related('user').all()
    
    # Apply filters
    if status_filter == 'verified':
        drivers = drivers.filter(is_verified=True)
    elif status_filter == 'pending':
        drivers = drivers.filter(is_verified=False)
    elif status_filter == 'active':
        drivers = drivers.filter(user__is_active=True)
    elif status_filter == 'inactive':
        drivers = drivers.filter(user__is_active=False)
    elif status_filter == 'available':
        drivers = drivers.filter(is_available=True)
    elif status_filter == 'unavailable':
        drivers = drivers.filter(is_available=False)
    
    if search_query:
        drivers = drivers.filter(
            Q(names__icontains=search_query) |
            Q(license_number__icontains=search_query) |
            Q(vehicle_plate__icontains=search_query) |
            Q(user__phone_number__icontains=search_query)
        )
    
    total_drivers = drivers.count()
    verified_drivers = drivers.filter(is_verified=True).count()
    pending_drivers = drivers.filter(is_verified=False).count()
    available_drivers = drivers.filter(is_available=True).count()
    
    context = {
        'drivers': drivers,
        'total_drivers': total_drivers,
        'verified_drivers': verified_drivers,
        'pending_drivers': pending_drivers,
        'available_drivers': available_drivers,
        'filters': {
            'status': status_filter,
            'search': search_query,
        }
    }
    return render(request, 'admin_dashboard/drivers/manage_drivers.html', context)

@login_required
@user_passes_test(is_admin)
def add_driver(request):
    if request.method == 'POST':
        try:
            phone = request.POST.get('phone_number')
            email = request.POST.get('email', '')
            names = request.POST.get('names')
            license_number = request.POST.get('license_number')
            vehicle_type = request.POST.get('vehicle_type')
            vehicle_plate = request.POST.get('vehicle_plate')
            is_active = request.POST.get('is_active') == 'on'
            is_available = request.POST.get('is_available') == 'on'
            
            # Create user
            user = User.objects.create_user(
                phone_number=phone,
                email=email,
                user_type='driver',
                is_active=is_active,
                is_verified=False
            )
            user.set_password('driver123')  # Set default password
            user.save()
            
            # Create driver profile
            Driver.objects.create(
                user=user,
                names=names,
                license_number=license_number,
                vehicle_type=vehicle_type,
                vehicle_plate=vehicle_plate,
                is_available=is_available
            )
            messages.success(request, f'Driver "{names}" created successfully!')
            return redirect('admin_dashboard:manage-drivers')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/drivers/add_driver.html')

@login_required
@user_passes_test(is_admin)
def edit_driver(request, driver_id):
    driver = get_object_or_404(Driver, user_id=driver_id)
    if request.method == 'POST':
        try:
            driver.names = request.POST.get('names')
            driver.license_number = request.POST.get('license_number')
            driver.vehicle_type = request.POST.get('vehicle_type')
            driver.vehicle_plate = request.POST.get('vehicle_plate')
            driver.is_available = request.POST.get('is_available') == 'on'
            driver.user.is_active = request.POST.get('is_active') == 'on'
            driver.user.save()
            driver.save()
            messages.success(request, f'Driver "{driver.names}" updated!')
            return redirect('admin_dashboard:driver-detail', driver_id=driver.user.id)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/drivers/edit_driver.html', {'driver': driver})

@login_required
@user_passes_test(is_admin)
def driver_detail(request, driver_id):
    driver = get_object_or_404(Driver.objects.select_related('user'), user_id=driver_id)
    orders = Order.objects.filter(driver=driver.user).order_by('-created_at')[:10]
    return render(request, 'admin_dashboard/drivers/driver_detail.html', {
        'driver': driver,
        'orders': orders
    })

@login_required
@user_passes_test(is_admin)
def verify_driver(request, driver_id):
    driver = get_object_or_404(Driver, user_id=driver_id)
    if request.method == 'POST':
        driver.is_verified = True
        driver.verified_at = timezone.now()
        driver.save()
        messages.success(request, f'Driver {driver.names} has been verified.')
    return redirect('admin_dashboard:driver-detail', driver_id=driver.user.id)

@login_required
@user_passes_test(is_admin)
def toggle_driver_availability(request, driver_id):
    driver = get_object_or_404(Driver, user_id=driver_id)
    if request.method == 'POST':
        driver.is_available = not driver.is_available
        driver.save()
        status = "available" if driver.is_available else "unavailable"
        messages.success(request, f'Driver {driver.names} is now {status}.')
    return redirect('admin_dashboard:driver-detail', driver_id=driver.user.id)

@login_required
@user_passes_test(is_admin)
def delete_driver(request, driver_id):
    driver = get_object_or_404(Driver, user_id=driver_id)
    if request.method == 'POST':
        name = driver.names
        driver.user.delete()  # This will cascade delete driver profile
        messages.success(request, f'Driver "{name}" deleted successfully!')
    return redirect('admin_dashboard:manage-drivers')

# Export Drivers CSV
@login_required
@user_passes_test(is_admin)
def export_drivers_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="drivers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'License', 'Plate', 'Verified', 'Active', 'Available'])
    drivers = Driver.objects.select_related('user').all()
    for d in drivers:
        writer.writerow([
            d.names,
            d.user.phone_number,
            d.license_number,
            d.vehicle_plate,
            'Yes' if d.is_verified else 'No',
            'Yes' if d.user.is_active else 'No',
            'Yes' if d.is_available else 'No'
        ])
    return response

# Bulk Driver Actions
@login_required
@user_passes_test(is_admin)
def bulk_driver_action(request):
    if request.method == 'POST':
        driver_ids = request.POST.getlist('driver_ids')
        action = request.POST.get('action')
        if not driver_ids:
            messages.warning(request, 'No drivers selected.')
            return redirect('admin_dashboard:manage-drivers')
        
        drivers = Driver.objects.filter(user_id__in=driver_ids)
        user_ids = [d.user_id for d in drivers]
        
        if action == 'verify':
            drivers.update(is_verified=True, verified_at=timezone.now())
            messages.success(request, f'{len(drivers)} drivers verified.')
        elif action == 'unverify':
            drivers.update(is_verified=False, verified_at=None)
            messages.success(request, f'{len(drivers)} drivers unverified.')
        elif action == 'activate':
            User.objects.filter(id__in=user_ids).update(is_active=True)
            messages.success(request, f'{len(drivers)} drivers activated.')
        elif action == 'deactivate':
            User.objects.filter(id__in=user_ids).update(is_active=False)
            messages.success(request, f'{len(drivers)} drivers deactivated.')
        elif action == 'set-available':
            drivers.update(is_available=True)
            messages.success(request, f'{len(drivers)} drivers set as available.')
        elif action == 'set-unavailable':
            drivers.update(is_available=False)
            messages.success(request, f'{len(drivers)} drivers set as unavailable.')
    
    return redirect('admin_dashboard:manage-drivers')


# ============================================
# PRODUCT MANAGEMENT
# ============================================
@login_required
@user_passes_test(is_admin)
def manage_products(request):
    """Manage products with filtering"""
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    products = ProductTemplate.objects.select_related('category').prefetch_related('variants').all()
    
    # Apply filters
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'verified':
        products = products.filter(is_verified=True)
    elif status_filter == 'unverified':
        products = products.filter(is_verified=False)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(search_keywords__icontains=search_query)
        )
    
    # Statistics
    total_products = products.count()
    active_products = products.filter(is_active=True).count()
    verified_products = products.filter(is_verified=True).count()
    unverified_products = total_products - verified_products  # ✅ Do this in Python
    
    # Categories for filter
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'categories': categories,
        'total_products': total_products,
        'active_products': active_products,
        'verified_products': verified_products,
        'unverified_products': unverified_products,
        'filters': {
            'category': category_filter,
            'status': status_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'admin_dashboard/products/manage_products.html', context)

# admin_dashboard/views.py
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from products.models import (
    Category, 
    MeasurementUnitType, 
    MeasurementUnit, 
    ProductTemplate
)
from accounts.models import User

# Helper function (assumed to exist)
def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

from products.forms import ProductTemplateForm
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Prefetch
from products.forms import ProductTemplateForm
from products.models import (
    Category, 
    MeasurementUnitType, 
    MeasurementUnit, 
    ProductTemplate
)

# Helper
def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

# ============= ADD PRODUCT =============
@login_required
@user_passes_test(is_admin)
def add_product_template(request):
    if request.method == 'POST':
        form = ProductTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            # Set extra fields that aren't in the form
            product = form.save(commit=False)
            product.created_by = request.user
            product.is_verified = False
            product.save()  # ✅ Saves main_image to Cloudinary
            form.save_m2m()  # ✅ Required for ManyToMany (available_units)
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('admin_dashboard:manage-products')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductTemplateForm()

    # Prepare data for dynamic unit UI in Add form
    unit_types = MeasurementUnitType.objects.filter(is_active=True)
    unit_groups_serializable = []
    for ut in unit_types:
        units = list(ut.units.filter(is_active=True).values('id', 'name', 'symbol'))
        unit_groups_serializable.append({
            'unit_type': {'id': str(ut.id), 'name': ut.name},
            'units': units
        })
    unit_groups_json = json.dumps(unit_groups_serializable, cls=DjangoJSONEncoder)
    selected_unit_ids = form.data.getlist('available_units') if form.is_bound else []

    return render(request, 'admin_dashboard/products/add_product.html', {
        'form': form,
        'unit_groups_json': unit_groups_json,
        'selected_unit_ids': selected_unit_ids,
    })

# ============= EDIT PRODUCT =============
@login_required
@user_passes_test(is_admin)
def edit_product_template(request, product_id):
    product = get_object_or_404(ProductTemplate, id=product_id)

    if request.method == 'POST':
        form = ProductTemplateForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()  # ✅ This handles Cloudinary upload automatically
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('admin_dashboard:product-detail', product_id=product.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductTemplateForm(instance=product)

    # Prepare data for dynamic unit UI in Edit form (SAME AS ADD FORM)
    unit_types = MeasurementUnitType.objects.filter(is_active=True)
    unit_groups_serializable = []
    for ut in unit_types:
        units = list(ut.units.filter(is_active=True).values('id', 'name', 'symbol'))
        unit_groups_serializable.append({
            'unit_type': {'id': str(ut.id), 'name': ut.name},
            'units': units
        })
    unit_groups_json = json.dumps(unit_groups_serializable, cls=DjangoJSONEncoder)
    
    # Get currently selected unit IDs from the product
    selected_unit_ids = list(product.available_units.values_list('id', flat=True))
    selected_unit_ids = [str(unit_id) for unit_id in selected_unit_ids]  # Convert to strings for JSON

    return render(request, 'admin_dashboard/products/edit_product.html', {
        'product': product,
        'form': form,
        'unit_groups_json': unit_groups_json,
        'selected_unit_ids': selected_unit_ids,
    })



@login_required
@user_passes_test(is_admin)
def manage_product_variants(request, product_id):
    product = get_object_or_404(ProductTemplate, id=product_id)
    variants = product.variants.select_related('vendor', 'market_zone').prefetch_related('unit_prices__unit').all()

    # For each variant, build {unit_id: price}
    for variant in variants:
        variant.unit_price_dict = {
            str(up.unit.id): up.selling_price  # ✅ Use 'selling_price'
            for up in variant.unit_prices.all()
        }

    return render(request, 'admin_dashboard/products/manage_variants.html', {
        'product': product,
        'variants': variants,
    })


# admin_dashboard/views.py
from products.models import ProductVariant
# admin_dashboard/views.py
from products.models import ProductAddon
@login_required
@user_passes_test(is_admin)
def add_product_variant(request, product_id):
    product = get_object_or_404(ProductTemplate, id=product_id)
    
    if request.method == 'POST':
        try:
            vendor_id = request.POST.get('vendor')
            market_zone_id = request.POST.get('market_zone')
            custom_profit = request.POST.get('custom_profit_percentage') or None
            quality_grade = request.POST.get('quality_grade') or ''
            is_active = request.POST.get('is_active') == 'on'

            vendor = Vendor.objects.get(user_id=vendor_id)
            market_zone = MarketZone.objects.get(id=market_zone_id)

            # Create variant (NO base_cost_price)
            variant = ProductVariant.objects.create(
                product_template=product,
                vendor=vendor,
                market_zone=market_zone,
                custom_profit_percentage=custom_profit,
                quality_grade=quality_grade,
                is_active=is_active,
                is_approved=True
            )

            # Save unit costs → selling_price auto-calculated
            for unit in product.available_units.all():
                cost_key = f"cost_price_{unit.id}"
                if cost_key in request.POST:
                    cost_price = Decimal(request.POST.get(cost_key))
                    # Auto-calculate selling_price
                    profit_pct = variant.effective_profit_percentage
                    selling_price = cost_price + (cost_price * profit_pct / Decimal('100'))
                    
                    UnitPrice.objects.update_or_create(
                        product_variant=variant,
                        unit=unit,
                        defaults={
                            'cost_price': cost_price,
                            'selling_price': selling_price,
                            'is_active': True
                        }
                    )

            messages.success(request, f'Variant for {vendor.business_name} created!')
            return redirect('admin_dashboard:manage-product-variants', product_id=product.id)

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    # GET
    vendors = Vendor.objects.filter(is_verified=True, user__is_active=True)
    market_zones = MarketZone.objects.filter(is_active=True)
    return render(request, 'admin_dashboard/products/add_variant.html', {
        'product': product,
        'vendors': vendors,
        'market_zones': market_zones,
    })



from decimal import Decimal, InvalidOperation

@login_required
@user_passes_test(is_admin)
def edit_product_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if request.method == 'POST':
        try:
            # Update non-price fields
            variant.custom_profit_percentage = request.POST.get('custom_profit_percentage') or None
            variant.quality_grade = request.POST.get('quality_grade') or ''
            variant.is_active = request.POST.get('is_active') == 'on'
            variant.save()

            # Update unit costs and auto-calculate selling prices
            for unit in variant.product_template.available_units.all():
                cost_key = f"cost_price_{unit.id}"
                if cost_key in request.POST:
                    cost_price_str = request.POST.get(cost_key)
                    if cost_price_str:
                        cost_price = Decimal(str(cost_price_str).strip())
                        # Auto-calculate selling_price
                        profit_pct = variant.effective_profit_percentage
                        selling_price = cost_price + (cost_price * profit_pct / Decimal('100'))
                        
                        UnitPrice.objects.update_or_create(
                            product_variant=variant,
                            unit=unit,
                            defaults={
                                'cost_price': cost_price,
                                'selling_price': selling_price,
                                'is_active': True
                            }
                        )
                    else:
                        # Skip if no cost price provided
                        continue

            messages.success(request, f'Variant updated successfully!')
            return redirect('admin_dashboard:manage-product-variants', product_id=variant.product_template.id)

        except (ValueError, TypeError, InvalidOperation, Exception) as e:
            messages.error(request, f'Error: {str(e)}')

    # GET request
    market_zones = MarketZone.objects.filter(is_active=True)
    addons = ProductAddon.objects.filter(is_active=True)
    
    # Load current unit prices
    unit_prices = {}
    for up in variant.unit_prices.all():
        unit_prices[str(up.unit.id)] = {
            'cost_price': up.cost_price,
            'selling_price': up.selling_price
        }
    selected_addons = [a.id for a in variant.available_addons.all()]

    return render(request, 'admin_dashboard/products/edit_variant.html', {
        'variant': variant,
        'market_zones': market_zones,
        'all_addons': addons,
        'unit_prices': unit_prices,
        'selected_addons': selected_addons,
    })

@login_required
@user_passes_test(is_admin)
def bulk_product_action(request):
    if request.method == 'POST':
        product_ids = request.POST.getlist('product_ids')
        action = request.POST.get('action')

        if not product_ids:
            messages.warning(request, 'No products selected.')
            return redirect('admin_dashboard:manage-products')

        products = ProductTemplate.objects.filter(id__in=product_ids)

        if action == 'verify':
            products.update(is_verified=True)
            messages.success(request, f'{products.count()} products verified.')
        elif action == 'unverify':
            products.update(is_verified=False)
            messages.success(request, f'{products.count()} products unverified.')
        elif action == 'activate':
            products.update(is_active=True)
            messages.success(request, f'{products.count()} products activated.')
        elif action == 'deactivate':
            products.update(is_active=False)
            messages.success(request, f'{products.count()} products deactivated.')

    return redirect('admin_dashboard:manage-products')

import csv
from django.http import HttpResponse

@login_required
@user_passes_test(is_admin)
def export_products_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Category', 'Primary Unit', 'Verified', 'Active', 'Created'])

    products = ProductTemplate.objects.select_related('category', 'primary_unit_type').all()
    for p in products:
        writer.writerow([
            p.name,
            p.category.name,
            p.primary_unit_type.name,
            'Yes' if p.is_verified else 'No',
            'Yes' if p.is_active else 'No',
            p.created_at.strftime('%Y-%m-%d')
        ])

    return response


@login_required
@user_passes_test(is_admin)
def product_detail(request, product_id):
    """Product detail view"""
    product = get_object_or_404(
        ProductTemplate.objects.select_related('category', 'primary_unit_type')
        .prefetch_related('variants__vendor', 'variants__market_zone'),
        id=product_id
    )
    
    context = {
        'product': product,
    }
    
    return render(request, 'admin_dashboard/products/product_detail.html', context)

@login_required
@user_passes_test(is_admin)
def verify_product(request, product_id):
    """Verify product template"""
    product = get_object_or_404(ProductTemplate, id=product_id)
    
    if request.method == 'POST':
        product.is_verified = True
        product.save()
        messages.success(request, f'Product {product.name} has been verified.')
    
    # In verify_product and toggle_product_status
    return redirect('admin_dashboard:product-detail', product_id=product_id)

@login_required
@user_passes_test(is_admin)
def toggle_product_status(request, product_id):
    """Toggle product active status"""
    product = get_object_or_404(ProductTemplate, id=product_id)
    
    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save()
        
        status = "activated" if product.is_active else "deactivated"
        messages.success(request, f'Product {product.name} has been {status}.')
    
    # In verify_product and toggle_product_status
    return redirect('admin_dashboard:product-detail', product_id=product_id)






from products.models import Category

@login_required
@user_passes_test(is_admin)
def manage_categories(request):
    """List all categories with filtering"""
    status_filter = request.GET.get('status', 'all')
    parent_filter = request.GET.get('parent', '')
    
    categories = Category.objects.all()
    
    # Apply filters
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)
    
    if parent_filter:
        if parent_filter == 'top-level':
            categories = categories.filter(parent__isnull=True)
        else:
            categories = categories.filter(parent_id=parent_filter)
    
    # Stats
    total_categories = categories.count()
    active_categories = categories.filter(is_active=True).count()
    top_level_categories = Category.objects.filter(parent__isnull=True).count()
    
    # Parent options for filter
    parent_options = Category.objects.filter(parent__isnull=True)
    
    context = {
        'categories': categories,
        'parent_options': parent_options,
        'total_categories': total_categories,
        'active_categories': active_categories,
        'top_level_categories': top_level_categories,
        'filters': {
            'status': status_filter,
            'parent': parent_filter,
        }
    }
    return render(request, 'admin_dashboard/categories/manage_categories.html', context)

@login_required
@user_passes_test(is_admin)
def add_category(request):
    """Add new category"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            parent_id = request.POST.get('parent') or None
            profit_percentage = request.POST.get('profit_percentage', 10.00)
            
            category = Category(
                name=name,
                description=description,
                profit_percentage=profit_percentage
            )
            
            if parent_id:
                parent = Category.objects.get(id=parent_id)
                category.parent = parent
            
            if 'image' in request.FILES:
                category.image = request.FILES['image']
            
            category.save()
            messages.success(request, f'Category "{name}" created successfully!')
            return redirect('admin_dashboard:manage-categories')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    parent_categories = Category.objects.filter(parent__isnull=True)
    return render(request, 'admin_dashboard/categories/add_category.html', {
        'parent_categories': parent_categories
    })

@login_required
@user_passes_test(is_admin)
def edit_category(request, category_id):
    """Edit existing category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.description = request.POST.get('description', '')
            category.profit_percentage = request.POST.get('profit_percentage', 10.00)
            
            parent_id = request.POST.get('parent') or None
            if parent_id:
                parent = Category.objects.get(id=parent_id)
                category.parent = parent
            else:
                category.parent = None
            
            if 'image' in request.FILES:
                category.image = request.FILES['image']
            
            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('admin_dashboard:manage-categories')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    parent_categories = Category.objects.filter(parent__isnull=True).exclude(id=category_id)
    return render(request, 'admin_dashboard/categories/edit_category.html', {
        'category': category,
        'parent_categories': parent_categories
    })

@login_required
@user_passes_test(is_admin)
def delete_category(request, category_id):
    """Delete category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted successfully!')
    
    return redirect('admin_dashboard:manage-categories')



# ============================================
# ORDER MANAGEMENT
# ============================================
@login_required
@user_passes_test(is_admin)
def manage_order(request):
    """Manage order with filtering"""
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    date_range = request.GET.get('date_range', '')
    search_query = request.GET.get('q', '')
    
    order = Order.objects.select_related('customer').all().order_by('-created_at')
    
    # Apply filters
    if status_filter != 'all':
        order = order.filter(status=status_filter)
    
    if payment_filter != 'all':
        order = order.filter(payment_method=payment_filter)
    
    if search_query:
        order = order.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__phone_number__icontains=search_query) |
            Q(customer__customer__names__icontains=search_query)
        )
    
    # Date range filter
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            order = order.filter(created_at__date=today)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            order = order.filter(created_at__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            order = order.filter(created_at__date__gte=month_ago)
    
    # Statistics
    total_order = order.count()
    pending_order = order.filter(status='pending').count()
    completed_order = order.filter(status='completed').count()
    total_revenue = order.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    context = {
        'order': order,
        'total_order': total_order,
        'pending_order': pending_order,
        'completed_order': completed_order,
        'total_revenue': total_revenue,
        'filters': {
            'status': status_filter,
            'payment': payment_filter,
            'date_range': date_range,
            'search': search_query,
        }
    }
    
    return render(request, 'admin_dashboard/order/manage_order.html', context)

@login_required
@user_passes_test(is_admin)
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(
        Order.objects.select_related('customer', 'driver')
        .prefetch_related('items__product_variant'),
        id=order_id
    )
    
    context = {
        'order': order,
    }
    
    return render(request, 'admin_dashboard/order/order_detail.html', context)

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    """Update order status"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            order.status = new_status
            order.save()
            messages.success(request, f'Order status updated to {new_status}.')

    
    
    return redirect('order-detail', order_id=order_id)

# # admin_dashboard/views.py (Market Management Section)
# admin_dashboard/views.py (Market Management Section)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from datetime import datetime, timedelta

# Import all the models
from markets.models import Market, MarketZone, MarketDay
from location.models import (
    DeliveryFeeConfig, 
    DeliveryZone, 
    DeliveryTimeSlot, 
    CustomerAddress
)


def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def manage_markets(request):
    # Prefetch related data for efficiency
    markets = Market.objects.prefetch_related(
        'zones',
        'delivery_zones',
        'market_days',
        'customer_addresses'
    ).all().order_by('name')

    # Helper: Convert list of MarketDay objects to compact display (e.g., "Mon–Fri")
    def compact_market_days(market_days_qs):
        if not market_days_qs:
            return "No days set"
        # Define weekday order (Monday = 0)
        weekday_order = {
            'monday': 0,
            'tuesday': 1,
            'wednesday': 2,
            'thursday': 3,
            'friday': 4,
            'saturday': 5,
            'sunday': 6,
        }
        days = list(market_days_qs)
        # Sort by weekday
        sorted_days = sorted(days, key=lambda d: weekday_order.get(d.day, 99))
        day_names = [d.get_day_display() for d in sorted_days]
        indices = [weekday_order[d.day] for d in sorted_days]

        # If consecutive weekdays (2+ days), show range
        if len(indices) >= 2 and indices == list(range(indices[0], indices[-1] + 1)):
            return f"{day_names[0]}–{day_names[-1]}"
        else:
            return ", ".join(day_names)

    # Enrich each market with stats
    for market in markets:
        market.active_zones_count = market.zones.filter(is_active=True).count()
        market.active_delivery_zones_count = market.delivery_zones.filter(is_active=True).count()
        market.customer_addresses_count = market.customer_addresses.count()
        market.compact_market_days = compact_market_days(market.market_days.all())  # ✅ Key fix

        # Delivery coverage
        total_zones = market.delivery_zones.count()
        active_zones = market.delivery_zones.filter(is_active=True).count()
        market.delivery_coverage = f"{active_zones}/{total_zones}" if total_zones > 0 else "No zones"

    # Overall statistics
    total_markets = markets.count()
    active_markets = markets.filter(is_active=True).count()
    total_market_zones = MarketZone.objects.count()
    total_delivery_zones = DeliveryZone.objects.count()

    # Delivery fee config status
    try:
        fee_config = DeliveryFeeConfig.objects.get(is_default=True, is_active=True)
        fee_config_status = "Active"
    except DeliveryFeeConfig.DoesNotExist:
        fee_config_status = "Not configured"

    context = {
        'markets': markets,
        'total_markets': total_markets,
        'active_markets': active_markets,
        'total_market_zones': total_market_zones,
        'total_delivery_zones': total_delivery_zones,
        'fee_config_status': fee_config_status,
        'today': timezone.now().date(),
    }
    return render(request, 'admin_dashboard/markets/manage_markets.html', context)


@login_required
@user_passes_test(is_admin)
def add_market(request):
    all_days = MarketDay.objects.all()
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            contact_phone = request.POST.get('contact_phone', '')
            address = request.POST.get('address', '')
            location = request.POST.get('location', '')
            
            # Location coordinates
            latitude = request.POST.get('latitude') or None
            longitude = request.POST.get('longitude') or None
            
            # Opening hours
            opening_time = request.POST.get('opening_time') or None
            closing_time = request.POST.get('closing_time') or None
            
            # Create market
            market = Market.objects.create(
                name=name,
                description=description,
                contact_phone=contact_phone,
                address=address,
                location=location,
                latitude=latitude,
                longitude=longitude,
                opening_time=opening_time,
                closing_time=closing_time,
                is_active=True
            )
            
            # Add market days
            selected_days = request.POST.getlist('market_days')
            if selected_days:
                days = MarketDay.objects.filter(id__in=selected_days)
                market.market_days.set(days)
            
            messages.success(request, f'Market "{name}" added successfully!')
            return redirect('admin_dashboard:manage-markets')
            
        except Exception as e:
            messages.error(request, f'Error adding market: {str(e)}')
    
    context = {
        'all_days': all_days,
    }
    return render(request, 'admin_dashboard/markets/add_market.html', context)


@login_required
@user_passes_test(is_admin)
def edit_market(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    all_days = MarketDay.objects.all()
    selected_days = market.market_days.all()
    
    if request.method == 'POST':
        try:
            market.name = request.POST.get('name')
            market.description = request.POST.get('description', '')
            market.contact_phone = request.POST.get('contact_phone', '')
            market.address = request.POST.get('address', '')
            market.location = request.POST.get('location', '')
            
            # Location coordinates
            latitude = request.POST.get('latitude') or None
            longitude = request.POST.get('longitude') or None
            if latitude and longitude:
                market.latitude = latitude
                market.longitude = longitude
            
            # Opening hours
            opening_time = request.POST.get('opening_time') or None
            closing_time = request.POST.get('closing_time') or None
            market.opening_time = opening_time
            market.closing_time = closing_time
            
            # Status
            market.is_active = request.POST.get('is_active') == 'on'
            
            market.save()
            
            # Update market days
            selected_days = request.POST.getlist('market_days')
            if selected_days:
                days = MarketDay.objects.filter(id__in=selected_days)
                market.market_days.set(days)
            else:
                market.market_days.clear()
            
            messages.success(request, f'Market "{market.name}" updated successfully!')
            return redirect('admin_dashboard:manage-markets')
            
        except Exception as e:
            messages.error(request, f'Error updating market: {str(e)}')
    
    context = {
        'market': market,
        'all_days': all_days,
        'selected_days': selected_days,
    }
    return render(request, 'admin_dashboard/markets/edit_market.html', context)


@login_required
@user_passes_test(is_admin)
def delete_market(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    if request.method == 'POST':
        market_name = market.name
        market.delete()
        messages.success(request, f'Market "{market_name}" deleted successfully!')
        return redirect('admin_dashboard:manage-markets')
    return redirect('admin_dashboard:manage-markets')


@login_required
@user_passes_test(is_admin)
def market_detail(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    
    # Get related data
    zones = market.zones.all()
    delivery_zones = market.delivery_zones.all()
    market_days = market.market_days.all()
    customer_addresses = market.customer_addresses.all()
    
    # Statistics
    stats = {
        'total_zones': zones.count(),
        'active_zones': zones.filter(is_active=True).count(),
        'total_delivery_zones': delivery_zones.count(),
        'active_delivery_zones': delivery_zones.filter(is_active=True).count(),
        'customer_addresses': customer_addresses.count(),
        'verified_addresses': customer_addresses.filter(is_verified=True).count(),
    }
    
    # Zone type distribution
    zone_types = zones.values('zone_type').annotate(count=Count('zone_type'))
    
    # Delivery zone type distribution
    delivery_zone_types = delivery_zones.values('zone_type').annotate(count=Count('zone_type'))
    
    context = {
        'market': market,
        'zones': zones,
        'delivery_zones': delivery_zones,
        'market_days': market_days,
        'customer_addresses': customer_addresses,
        'stats': stats,
        'zone_types': zone_types,
        'delivery_zone_types': delivery_zone_types,
    }
    return render(request, 'admin_dashboard/markets/market_detail.html', context)

# Add these near your other views
@login_required
@user_passes_test(is_admin)
def toggle_market_status(request, market_id):
    """Toggle market active status"""
    market = get_object_or_404(Market, id=market_id)
    if request.method == 'POST':
        try:
            market.is_active = not market.is_active
            market.save()
            
            action = "activated" if market.is_active else "deactivated"
            messages.success(request, f'Market "{market.name}" {action} successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'is_active': market.is_active})
            else:
                return redirect('admin_dashboard:manage-markets')
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error toggling market status: {str(e)}')
                return redirect('admin_dashboard:manage-markets')
    
    return redirect('admin_dashboard:manage-markets')


@login_required
@user_passes_test(is_admin)
def bulk_market_action(request):
    """Handle bulk actions for markets"""
    if request.method == 'POST':
        try:
            market_ids = request.POST.getlist('market_ids')
            action = request.POST.get('action')
            
            if not market_ids:
                messages.warning(request, 'No markets selected.')
                return redirect('admin_dashboard:manage-markets')
            
            markets = Market.objects.filter(id__in=market_ids)
            
            if action == 'activate':
                markets.update(is_active=True)
                messages.success(request, f'{markets.count()} market(s) activated.')
            elif action == 'deactivate':
                markets.update(is_active=False)
                messages.success(request, f'{markets.count()} market(s) deactivated.')
            elif action == 'delete':
                count = markets.count()
                markets.delete()
                messages.success(request, f'{count} market(s) deleted.')
            else:
                messages.error(request, 'Invalid action specified.')
                
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
    
    return redirect('admin_dashboard:manage-markets')


@login_required
@user_passes_test(is_admin)
def toggle_zone_status(request, zone_id):
    """Toggle market zone active status"""
    zone = get_object_or_404(MarketZone, id=zone_id)
    if request.method == 'POST':
        try:
            zone.is_active = not zone.is_active
            zone.save()
            
            action = "activated" if zone.is_active else "deactivated"
            messages.success(request, f'Zone "{zone.name}" {action} successfully!')
            
            return redirect('admin_dashboard:manage-market-zones', market_id=zone.market.id)
                
        except Exception as e:
            messages.error(request, f'Error toggling zone status: {str(e)}')
            return redirect('admin_dashboard:manage-market-zones', market_id=zone.market.id)
    
    return redirect('admin_dashboard:manage-market-zones', market_id=zone.market.id)


@login_required
@user_passes_test(is_admin)
def bulk_zone_action(request, market_id):
    """Handle bulk actions for market zones"""
    market = get_object_or_404(Market, id=market_id)
    
    if request.method == 'POST':
        try:
            zone_ids = request.POST.getlist('zone_ids')
            action = request.POST.get('action')
            
            if not zone_ids:
                messages.warning(request, 'No zones selected.')
                return redirect('admin_dashboard:manage-market-zones', market_id=market_id)
            
            zones = MarketZone.objects.filter(id__in=zone_ids, market=market)
            
            if action == 'activate':
                zones.update(is_active=True)
                messages.success(request, f'{zones.count()} zone(s) activated.')
            elif action == 'deactivate':
                zones.update(is_active=False)
                messages.success(request, f'{zones.count()} zone(s) deactivated.')
            elif action == 'delete':
                count = zones.count()
                zones.delete()
                messages.success(request, f'{count} zone(s) deleted.')
            else:
                messages.error(request, 'Invalid action specified.')
                
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
    
    return redirect('admin_dashboard:manage-market-zones', market_id=market_id)


# Add export functionality if needed
@login_required
@user_passes_test(is_admin)
def export_markets_csv(request):
    """Export markets data to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="markets.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Location', 'Contact Phone', 'Address', 
                     'Status', 'Active Zones', 'Delivery Zones', 'Market Days'])
    
    markets = Market.objects.prefetch_related('zones', 'delivery_zones', 'market_days').all()
    
    for market in markets:
        active_zones = market.zones.filter(is_active=True).count()
        delivery_zones = market.delivery_zones.count()
        market_days = ", ".join([day.get_day_display() for day in market.market_days.all()])
        
        writer.writerow([
            market.name,
            market.location or '',
            market.contact_phone or '',
            market.address or '',
            'Active' if market.is_active else 'Inactive',
            active_zones,
            delivery_zones,
            market_days
        ])
    
    return response

# Add these to your views.py
@login_required
@user_passes_test(is_admin)
def toggle_delivery_zone_status(request, zone_id):
    """Toggle delivery zone active status"""
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    if request.method == 'POST':
        try:
            zone.is_active = not zone.is_active
            zone.save()
            
            action = "activated" if zone.is_active else "deactivated"
            messages.success(request, f'Delivery zone "{zone.name}" {action} successfully!')
            
            return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)
                
        except Exception as e:
            messages.error(request, f'Error toggling delivery zone status: {str(e)}')
            return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)
    
    return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)


@login_required
@user_passes_test(is_admin)
def bulk_delivery_zone_action(request, market_id):
    """Handle bulk actions for delivery zones"""
    market = get_object_or_404(Market, id=market_id)
    
    if request.method == 'POST':
        try:
            zone_ids = request.POST.getlist('zone_ids')
            action = request.POST.get('action')
            
            if not zone_ids:
                messages.warning(request, 'No delivery zones selected.')
                return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)
            
            zones = DeliveryZone.objects.filter(id__in=zone_ids, market=market)
            
            if action == 'activate':
                zones.update(is_active=True)
                messages.success(request, f'{zones.count()} delivery zone(s) activated.')
            elif action == 'deactivate':
                zones.update(is_active=False)
                messages.success(request, f'{zones.count()} delivery zone(s) deactivated.')
            elif action == 'delete':
                count = zones.count()
                zones.delete()
                messages.success(request, f'{count} delivery zone(s) deleted.')
            else:
                messages.error(request, 'Invalid action specified.')
                
        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')
    
    return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)


# Market Zone Management
@login_required
@user_passes_test(is_admin)
def manage_market_zones(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    zones = market.zones.all().order_by('name')
    
    # Statistics
    active_zones = zones.filter(is_active=True)
    inactive_zones = zones.filter(is_active=False)
    
    context = {
        'market': market,
        'zones': zones,
        'active_zones_count': active_zones.count(),
        'inactive_zones_count': inactive_zones.count(),
        'total_zones': zones.count(),
    }
    return render(request, 'admin_dashboard/markets/manage_zones.html', context)


@login_required
@user_passes_test(is_admin)
def add_market_zone(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            zone_type = request.POST.get('zone_type', '')
            
            MarketZone.objects.create(
                market=market,
                name=name,
                description=description,
                zone_type=zone_type,
                is_active=True
            )
            messages.success(request, f'Zone "{name}" added to {market.name}!')
            return redirect('admin_dashboard:manage-market-zones', market_id=market.id)
        except Exception as e:
            messages.error(request, f'Error adding zone: {str(e)}')
    
    return render(request, 'admin_dashboard/markets/add_zone.html', {'market': market})


@login_required
@user_passes_test(is_admin)
def edit_market_zone(request, zone_id):
    zone = get_object_or_404(MarketZone, id=zone_id)
    
    if request.method == 'POST':
        try:
            zone.name = request.POST.get('name')
            zone.description = request.POST.get('description', '')
            zone.zone_type = request.POST.get('zone_type', '')
            zone.is_active = request.POST.get('is_active') == 'on'
            zone.save()
            
            messages.success(request, f'Zone "{zone.name}" updated!')
            return redirect('admin_dashboard:manage-market-zones', market_id=zone.market.id)
        except Exception as e:
            messages.error(request, f'Error updating zone: {str(e)}')
    
    return render(request, 'admin_dashboard/markets/edit_zone.html', {'zone': zone})


@login_required
@user_passes_test(is_admin)
def delete_market_zone(request, zone_id):
    zone = get_object_or_404(MarketZone, id=zone_id)
    market_id = zone.market.id
    
    if request.method == 'POST':
        zone_name = zone.name
        zone.delete()
        messages.success(request, f'Zone "{zone_name}" deleted!')
    
    return redirect('admin_dashboard:manage-market-zones', market_id=market_id)


# Delivery Management Views
@login_required
@user_passes_test(is_admin)
def delivery_dashboard(request):
    """Main delivery management dashboard"""
    
    # Overall statistics
    total_markets = Market.objects.count()
    total_delivery_zones = DeliveryZone.objects.count()
    active_delivery_zones = DeliveryZone.objects.filter(is_active=True).count()
    total_customer_addresses = CustomerAddress.objects.count()
    total_time_slots = DeliveryTimeSlot.objects.count()
    
    # Fee configuration
    try:
        fee_config = DeliveryFeeConfig.objects.get(is_default=True, is_active=True)
        fee_config_name = fee_config.name
        fee_config_active = True
    except DeliveryFeeConfig.DoesNotExist:
        fee_config_name = "Not configured"
        fee_config_active = False
    
    # Recent activity
    recent_zones = DeliveryZone.objects.select_related('market').order_by('-created_at')[:10]
    recent_addresses = CustomerAddress.objects.select_related('customer', 'market', 'delivery_zone') \
        .order_by('-created_at')[:10]
    
    # Market-wise stats
    market_stats = Market.objects.annotate(
        zone_count=Count('delivery_zones'),
        address_count=Count('customer_addresses')
    ).order_by('-zone_count')[:5]
    
    context = {
        'total_markets': total_markets,
        'total_delivery_zones': total_delivery_zones,
        'active_delivery_zones': active_delivery_zones,
        'total_customer_addresses': total_customer_addresses,
        'total_time_slots': total_time_slots,
        'fee_config_name': fee_config_name,
        'fee_config_active': fee_config_active,
        'recent_zones': recent_zones,
        'recent_addresses': recent_addresses,
        'market_stats': market_stats,
    }
    return render(request, 'admin_dashboard/delivery/dashboard.html', context)


# Delivery Zone Management
@login_required
@user_passes_test(is_admin)
def manage_delivery_zones(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    zones = market.delivery_zones.all().order_by('priority', 'name')
    
    # Zone type counts
    zone_type_counts = zones.values('zone_type').annotate(
        count=Count('id'),
        active_count=Count('id', filter=models.Q(is_active=True))
    )
    
    # Statistics
    total_zones = zones.count()
    active_zones = zones.filter(is_active=True).count()
    
    context = {
        'market': market,
        'zones': zones,
        'total_zones': total_zones,
        'active_zones': active_zones,
        'zone_type_counts': zone_type_counts,
        'now': timezone.now(),
    }
    return render(request, 'admin_dashboard/delivery/manage_delivery_zones.html', context)


@login_required
@user_passes_test(is_admin)
def add_delivery_zone(request, market_id):
    market = get_object_or_404(Market, id=market_id)
    
    # Get active fee config for default values
    fee_config = DeliveryFeeConfig.get_active_config()
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            zone_type = request.POST.get('zone_type', 'standard')
            priority = int(request.POST.get('priority', 1))
            
            # Create zone
            zone = DeliveryZone.objects.create(
                market=market,
                name=name,
                description=description,
                zone_type=zone_type,
                priority=priority,
                is_active=True
            )
            
            # Handle zone-specific pricing
            if zone_type == 'fixed':
                fixed_price = Decimal(request.POST.get('fixed_price', '0'))
                zone.fixed_price = fixed_price
            elif zone_type == 'surcharge':
                surcharge_percent = Decimal(request.POST.get('surcharge_percent', '0'))
                zone.surcharge_percent = surcharge_percent
            
            # Coordinates for boundary and center point
            boundary_coords = request.POST.get('boundary_coords')
            center_lat = request.POST.get('center_latitude')
            center_lng = request.POST.get('center_longitude')
            
            if center_lat and center_lng:
                from django.contrib.gis.geos import Point
                zone.center_point = Point(float(center_lng), float(center_lat), srid=4326)
            
            # TODO: Handle polygon boundary if implemented
            # if boundary_coords:
            #     zone.boundary = parse_polygon(boundary_coords)
            
            zone.save()
            
            messages.success(request, f'Delivery zone "{name}" created successfully!')
            return redirect('admin_dashboard:manage-delivery-zones', market_id=market.id)
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error creating zone: {str(e)}')
    
    context = {
        'market': market,
        'fee_config': fee_config,
        'zone_type_choices': DeliveryZone.ZONE_TYPE_CHOICES,
    }
    return render(request, 'admin_dashboard/delivery/add_delivery_zone.html', context)


@login_required
@user_passes_test(is_admin)
def all_delivery_zones(request):
    """View all delivery zones across all markets"""
    zones = DeliveryZone.objects.select_related('market').all().order_by('market__name', 'name')
    
    # Group by market
    zones_by_market = {}
    for zone in zones:
        market_name = zone.market.name
        if market_name not in zones_by_market:
            zones_by_market[market_name] = []
        zones_by_market[market_name].append(zone)
    
    context = {
        'zones': zones,
        'zones_by_market': zones_by_market,
        'total_zones': zones.count(),
        'active_zones': zones.filter(is_active=True).count(),
    }
    return render(request, 'admin_dashboard/delivery/all_zones.html', context)

@login_required
@user_passes_test(is_admin)
def export_delivery_zones_csv(request, market_id):
    """Export delivery zones data to CSV"""
    market = get_object_or_404(Market, id=market_id)
    zones = DeliveryZone.objects.filter(market=market).order_by('priority', 'name')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="delivery_zones_{market.name}_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Zone Name', 'Description', 'Zone Type', 'Pricing', 'Priority', 
                     'Status', 'Center Latitude', 'Center Longitude', 'Created At', 'Updated At'])
    
    for zone in zones:
        # Determine pricing based on zone type
        if zone.zone_type == 'fixed':
            pricing = f"Tsh {zone.fixed_price}"
        elif zone.zone_type == 'surcharge':
            pricing = f"{zone.surcharge_percent}% surcharge"
        else:
            pricing = f"Tsh {zone.base_fee} + distance"
        
        # Get coordinates
        lat = zone.center_point.y if zone.center_point else ''
        lng = zone.center_point.x if zone.center_point else ''
        
        writer.writerow([
            zone.name,
            zone.description or '',
            zone.get_zone_type_display(),
            pricing,
            zone.priority,
            'Active' if zone.is_active else 'Inactive',
            lat,
            lng,
            zone.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            zone.updated_at.strftime('%Y-%m-%d %H:%M:%S') if zone.updated_at else ''
        ])
    
    return response



@login_required
@user_passes_test(is_admin)
@require_POST
def bulk_delivery_zone_action(request, market_id):
    """Handle bulk actions for delivery zones via AJAX"""
    market = get_object_or_404(Market, id=market_id)
    
    try:
        data = json.loads(request.body) if request.body else {}
        zone_ids = data.get('zone_ids', [])
        action = data.get('action', '')
        
        if not zone_ids:
            return JsonResponse({'success': False, 'error': 'No zones selected.'})
        
        zones = DeliveryZone.objects.filter(id__in=zone_ids, market=market)
        
        if action == 'activate':
            zones.update(is_active=True)
            message = f'{zones.count()} zone(s) activated.'
        elif action == 'deactivate':
            zones.update(is_active=False)
            message = f'{zones.count()} zone(s) deactivated.'
        elif action == 'make_standard':
            zones.update(zone_type='standard', fixed_price=None, surcharge_percent=None)
            message = f'{zones.count()} zone(s) changed to standard pricing.'
        elif action == 'make_fixed':
            # Get default fixed price from request or use 0
            fixed_price = data.get('fixed_price', 0)
            zones.update(zone_type='fixed', fixed_price=fixed_price, surcharge_percent=None)
            message = f'{zones.count()} zone(s) changed to fixed pricing.'
        elif action == 'delete':
            count = zones.count()
            zones.delete()
            message = f'{count} zone(s) deleted.'
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action specified.'})
        
        return JsonResponse({'success': True, 'message': message})
        
    except json.JSONDecodeError:
        # Fallback for form submission
        zone_ids = request.POST.getlist('zone_ids')
        action = request.POST.get('action', '')
        
        if not zone_ids:
            messages.warning(request, 'No zones selected.')
            return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)
        
        zones = DeliveryZone.objects.filter(id__in=zone_ids, market=market)
        
        if action == 'activate':
            zones.update(is_active=True)
            messages.success(request, f'{zones.count()} zone(s) activated.')
        elif action == 'deactivate':
            zones.update(is_active=False)
            messages.success(request, f'{zones.count()} zone(s) deactivated.')
        elif action == 'make_standard':
            zones.update(zone_type='standard', fixed_price=None, surcharge_percent=None)
            messages.success(request, f'{zones.count()} zone(s) changed to standard pricing.')
        elif action == 'make_fixed':
            fixed_price = request.POST.get('fixed_price', 0)
            zones.update(zone_type='fixed', fixed_price=fixed_price, surcharge_percent=None)
            messages.success(request, f'{zones.count()} zone(s) changed to fixed pricing.')
        elif action == 'delete':
            count = zones.count()
            zones.delete()
            messages.success(request, f'{count} zone(s) deleted.')
        else:
            messages.error(request, 'Invalid action specified.')
        
        return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


@login_required
@user_passes_test(is_admin)
def toggle_delivery_zone_status(request, zone_id):
    """Toggle delivery zone active status - supports both AJAX and regular"""
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    
    if request.method == 'POST':
        try:
            zone.is_active = not zone.is_active
            zone.save()
            
            action = "activated" if zone.is_active else "deactivated"
            message = f'Delivery zone "{zone.name}" {action} successfully!'
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': message,
                    'is_active': zone.is_active,
                    'zone_id': str(zone.id)
                })
            else:
                messages.success(request, message)
                return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)
                
        except Exception as e:
            error_msg = f'Error toggling zone status: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            else:
                messages.error(request, error_msg)
                return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)
    
    # If GET request, redirect to manage page
    return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)


@login_required
@user_passes_test(is_admin)
@require_POST
def quick_toggle_zone_status(request, zone_id):
    """Quick AJAX-only endpoint for toggling zone status"""
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    
    try:
        zone.is_active = not zone.is_active
        zone.save()
        
        return JsonResponse({
            'success': True,
            'is_active': zone.is_active,
            'new_status': 'Active' if zone.is_active else 'Inactive',
            'zone_id': str(zone.id)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


@login_required
@user_passes_test(is_admin)
def bulk_update_delivery_zones(request, market_id):
    """Handle multiple bulk operations for delivery zones"""
    market = get_object_or_404(Market, id=market_id)
    
    if request.method == 'POST':
        zone_ids = request.POST.getlist('zone_ids')
        action = request.POST.get('action')
        
        if not zone_ids:
            messages.warning(request, 'No zones selected.')
            return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)
        
        zones = DeliveryZone.objects.filter(id__in=zone_ids, market=market)
        
        try:
            if action == 'update_priority':
                new_priority = request.POST.get('priority', 1)
                zones.update(priority=new_priority)
                messages.success(request, f'Priority updated for {zones.count()} zone(s).')
                
            elif action == 'update_fixed_price':
                fixed_price = request.POST.get('fixed_price', 0)
                zones.filter(zone_type='fixed').update(fixed_price=fixed_price)
                messages.success(request, f'Fixed price updated for {zones.filter(zone_type="fixed").count()} zone(s).')
                
            elif action == 'update_surcharge':
                surcharge_percent = request.POST.get('surcharge_percent', 0)
                zones.filter(zone_type='surcharge').update(surcharge_percent=surcharge_percent)
                messages.success(request, f'Surcharge updated for {zones.filter(zone_type="surcharge").count()} zone(s).')
                
            elif action == 'update_base_fee':
                base_fee = request.POST.get('base_fee', 0)
                zones.filter(zone_type='standard').update(base_fee=base_fee)
                messages.success(request, f'Base fee updated for {zones.filter(zone_type="standard").count()} zone(s).')
                
            else:
                messages.error(request, 'Invalid update action.')
                
        except (InvalidOperation, ValueError) as e:
            messages.error(request, f'Invalid value provided: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error updating zones: {str(e)}')
    
    return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)




@login_required
@user_passes_test(is_admin)
def get_zone_details_ajax(request, zone_id):
    """Get zone details for AJAX requests"""
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    
    data = {
        'id': str(zone.id),
        'name': zone.name,
        'description': zone.description,
        'zone_type': zone.zone_type,
        'zone_type_display': zone.get_zone_type_display(),
        'is_active': zone.is_active,
        'priority': zone.priority,
        'base_fee': str(zone.base_fee) if zone.base_fee else None,
        'fixed_price': str(zone.fixed_price) if zone.fixed_price else None,
        'surcharge_percent': str(zone.surcharge_percent) if zone.surcharge_percent else None,
        'center_latitude': zone.center_point.y if zone.center_point else None,
        'center_longitude': zone.center_point.x if zone.center_point else None,
        'market_id': str(zone.market.id),
        'market_name': zone.market.name,
        'created_at': zone.created_at.isoformat() if zone.created_at else None,
        'updated_at': zone.updated_at.isoformat() if zone.updated_at else None,
    }
    
    return JsonResponse({'success': True, 'zone': data})



@login_required
@user_passes_test(is_admin)
def edit_delivery_zone(request, zone_id):
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    
    if request.method == 'POST':
        try:
            zone.name = request.POST.get('name')
            zone.description = request.POST.get('description', '')
            zone.zone_type = request.POST.get('zone_type', 'standard')
            zone.priority = int(request.POST.get('priority', 1))
            zone.is_active = request.POST.get('is_active') == 'on'
            
            # Handle zone-specific pricing
            if zone.zone_type == 'fixed':
                fixed_price = Decimal(request.POST.get('fixed_price', '0'))
                zone.fixed_price = fixed_price
            elif zone.zone_type == 'surcharge':
                surcharge_percent = Decimal(request.POST.get('surcharge_percent', '0'))
                zone.surcharge_percent = surcharge_percent
            
            # Coordinates
            center_lat = request.POST.get('center_latitude')
            center_lng = request.POST.get('center_longitude')
            if center_lat and center_lng:
                from django.contrib.gis.geos import Point
                zone.center_point = Point(float(center_lng), float(center_lat), srid=4326)
            
            zone.save()
            
            messages.success(request, f'Delivery zone "{zone.name}" updated!')
            return redirect('admin_dashboard:manage-delivery-zones', market_id=zone.market.id)
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error updating zone: {str(e)}')
    
    context = {
        'zone': zone,
        'zone_type_choices': DeliveryZone.ZONE_TYPE_CHOICES,
    }
    return render(request, 'admin_dashboard/delivery/edit_delivery_zone.html', context)


@login_required
@user_passes_test(is_admin)
def delete_delivery_zone(request, zone_id):
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    market_id = zone.market.id
    
    if request.method == 'POST':
        zone_name = zone.name
        zone.delete()
        messages.success(request, f'Delivery zone "{zone_name}" deleted!')
    
    return redirect('admin_dashboard:manage-delivery-zones', market_id=market_id)


@login_required
@user_passes_test(is_admin)
def delivery_zone_detail(request, zone_id):
    zone = get_object_or_404(DeliveryZone, id=zone_id)
    
    # Get addresses in this zone
    addresses = zone.customer_addresses.all()
    
    # Statistics
    stats = {
        'total_addresses': addresses.count(),
        'verified_addresses': addresses.filter(is_verified=True).count(),
        'default_addresses': addresses.filter(is_default=True).count(),
    }
    
    # Sample fee calculation
    sample_fee = None
    if zone.center_point:
        sample_fee = zone.calculate_delivery_fee(zone.center_point)
    
    context = {
        'zone': zone,
        'addresses': addresses,
        'stats': stats,
        'sample_fee': sample_fee,
    }
    return render(request, 'admin_dashboard/delivery/zone_detail.html', context)


# Delivery Fee Configuration
@login_required
@user_passes_test(is_admin)
def manage_delivery_fee_configs(request):
    configs = DeliveryFeeConfig.objects.all().order_by('-is_default', 'name')
    
    # Get active config
    active_config = DeliveryFeeConfig.get_active_config()
    
    context = {
        'configs': configs,
        'active_config': active_config,
        'total_configs': configs.count(),
        'active_configs': configs.filter(is_active=True).count(),
    }
    return render(request, 'admin_dashboard/delivery/manage_fee_configs.html', context)


@login_required
@user_passes_test(is_admin)
def add_delivery_fee_config(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            calculation_method = request.POST.get('calculation_method', 'haversine')
            base_fee = Decimal(request.POST.get('base_fee', '1000'))
            per_km_rate = Decimal(request.POST.get('per_km_rate', '500'))
            free_delivery_threshold = Decimal(request.POST.get('free_delivery_threshold', '50000'))
            max_delivery_distance = Decimal(request.POST.get('max_delivery_distance', '50'))
            surcharge_percent = Decimal(request.POST.get('surcharge_percent', '0'))
            delivery_time_estimate_per_km = int(request.POST.get('delivery_time_estimate_per_km', '3'))
            min_delivery_time = int(request.POST.get('min_delivery_time', '30'))
            is_active = request.POST.get('is_active') == 'on'
            is_default = request.POST.get('is_default') == 'on'
            
            config = DeliveryFeeConfig.objects.create(
                name=name,
                calculation_method=calculation_method,
                base_fee=base_fee,
                per_km_rate=per_km_rate,
                free_delivery_threshold=free_delivery_threshold,
                max_delivery_distance=max_delivery_distance,
                surcharge_percent=surcharge_percent,
                delivery_time_estimate_per_km=delivery_time_estimate_per_km,
                min_delivery_time=min_delivery_time,
                is_active=is_active,
                is_default=is_default,
            )
            
            messages.success(request, f'Delivery fee configuration "{name}" created!')
            return redirect('admin_dashboard:manage-delivery-fee-configs')
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error creating configuration: {str(e)}')
    
    context = {
        'calculation_methods': DeliveryFeeConfig.CALCULATION_CHOICES,
    }
    return render(request, 'admin_dashboard/delivery/add_fee_config.html', context)


@login_required
@user_passes_test(is_admin)
def edit_delivery_fee_config(request, config_id):
    config = get_object_or_404(DeliveryFeeConfig, id=config_id)
    
    if request.method == 'POST':
        try:
            config.name = request.POST.get('name')
            config.calculation_method = request.POST.get('calculation_method', 'haversine')
            config.base_fee = Decimal(request.POST.get('base_fee', '1000'))
            config.per_km_rate = Decimal(request.POST.get('per_km_rate', '500'))
            config.free_delivery_threshold = Decimal(request.POST.get('free_delivery_threshold', '50000'))
            config.max_delivery_distance = Decimal(request.POST.get('max_delivery_distance', '50'))
            config.surcharge_percent = Decimal(request.POST.get('surcharge_percent', '0'))
            config.delivery_time_estimate_per_km = int(request.POST.get('delivery_time_estimate_per_km', '3'))
            config.min_delivery_time = int(request.POST.get('min_delivery_time', '30'))
            config.is_active = request.POST.get('is_active') == 'on'
            config.is_default = request.POST.get('is_default') == 'on'
            
            config.save()
            
            messages.success(request, f'Delivery fee configuration "{config.name}" updated!')
            return redirect('admin_dashboard:manage-delivery-fee-configs')
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error updating configuration: {str(e)}')
    
    context = {
        'config': config,
        'calculation_methods': DeliveryFeeConfig.CALCULATION_CHOICES,
    }
    return render(request, 'admin_dashboard/delivery/edit_fee_config.html', context)


@login_required
@user_passes_test(is_admin)
def delete_delivery_fee_config(request, config_id):
    config = get_object_or_404(DeliveryFeeConfig, id=config_id)
    
    if request.method == 'POST':
        config_name = config.name
        config.delete()
        messages.success(request, f'Delivery fee configuration "{config_name}" deleted!')
    
    return redirect('admin_dashboard:manage-delivery-fee-configs')


# Delivery Time Slots
@login_required
@user_passes_test(is_admin)
def manage_delivery_time_slots(request):
    slots = DeliveryTimeSlot.objects.all().order_by('delivery_start_time')
    
    context = {
        'slots': slots,
        'total_slots': slots.count(),
        'active_slots': slots.filter(is_active=True).count(),
    }
    return render(request, 'admin_dashboard/delivery/manage_time_slots.html', context)


@login_required
@user_passes_test(is_admin)
def add_delivery_time_slot(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            cut_off_time = request.POST.get('cut_off_time')
            delivery_start_time = request.POST.get('delivery_start_time')
            delivery_end_time = request.POST.get('delivery_end_time')
            max_orders = int(request.POST.get('max_orders', '50'))
            delivery_fee_multiplier = Decimal(request.POST.get('delivery_fee_multiplier', '1.0'))
            is_active = request.POST.get('is_active') == 'on'
            
            DeliveryTimeSlot.objects.create(
                name=name,
                cut_off_time=cut_off_time,
                delivery_start_time=delivery_start_time,
                delivery_end_time=delivery_end_time,
                max_orders=max_orders,
                delivery_fee_multiplier=delivery_fee_multiplier,
                is_active=is_active,
            )
            
            messages.success(request, f'Delivery time slot "{name}" created!')
            return redirect('admin_dashboard:manage-delivery-time-slots')
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error creating time slot: {str(e)}')
    
    return render(request, 'admin_dashboard/delivery/add_time_slot.html')


@login_required
@user_passes_test(is_admin)
def edit_delivery_time_slot(request, slot_id):
    slot = get_object_or_404(DeliveryTimeSlot, id=slot_id)
    
    if request.method == 'POST':
        try:
            slot.name = request.POST.get('name')
            slot.cut_off_time = request.POST.get('cut_off_time')
            slot.delivery_start_time = request.POST.get('delivery_start_time')
            slot.delivery_end_time = request.POST.get('delivery_end_time')
            slot.max_orders = int(request.POST.get('max_orders', '50'))
            slot.delivery_fee_multiplier = Decimal(request.POST.get('delivery_fee_multiplier', '1.0'))
            slot.is_active = request.POST.get('is_active') == 'on'
            
            slot.save()
            
            messages.success(request, f'Delivery time slot "{slot.name}" updated!')
            return redirect('admin_dashboard:manage-delivery-time-slots')
            
        except (InvalidOperation, ValueError, Exception) as e:
            messages.error(request, f'Error updating time slot: {str(e)}')
    
    return render(request, 'admin_dashboard/delivery/edit_time_slot.html', {'slot': slot})


@login_required
@user_passes_test(is_admin)
def delete_delivery_time_slot(request, slot_id):
    slot = get_object_or_404(DeliveryTimeSlot, id=slot_id)
    
    if request.method == 'POST':
        slot_name = slot.name
        slot.delete()
        messages.success(request, f'Delivery time slot "{slot_name}" deleted!')
    
    return redirect('admin_dashboard:manage-delivery-time-slots')


# Customer Address Management
@login_required
@user_passes_test(is_admin)
def manage_customer_addresses(request):
    addresses = CustomerAddress.objects.select_related(
        'customer', 'market', 'delivery_zone'
    ).order_by('-created_at')
    
    # Filtering
    market_id = request.GET.get('market')
    if market_id:
        addresses = addresses.filter(market_id=market_id)
    
    zone_id = request.GET.get('zone')
    if zone_id:
        addresses = addresses.filter(delivery_zone_id=zone_id)
    
    is_verified = request.GET.get('verified')
    if is_verified:
        addresses = addresses.filter(is_verified=(is_verified == 'true'))
    
    # Statistics
    total_addresses = addresses.count()
    verified_addresses = addresses.filter(is_verified=True).count()
    default_addresses = addresses.filter(is_default=True).count()
    
    # Markets for filter dropdown
    markets = Market.objects.all()
    delivery_zones = DeliveryZone.objects.filter(is_active=True)
    
    context = {
        'addresses': addresses,
        'total_addresses': total_addresses,
        'verified_addresses': verified_addresses,
        'default_addresses': default_addresses,
        'markets': markets,
        'delivery_zones': delivery_zones,
    }
    return render(request, 'admin_dashboard/customers/manage_addresses.html', context)


@login_required
@user_passes_test(is_admin)
def customer_address_detail(request, address_id):
    address = get_object_or_404(CustomerAddress, id=address_id)
    
    # Calculate delivery fee and time
    delivery_fee = None
    delivery_time = None
    if address.delivery_zone and address.location_point:
        delivery_fee = address.delivery_zone.calculate_delivery_fee(address.location_point)
        delivery_time = address.estimated_delivery_time
    
    context = {
        'address': address,
        'delivery_fee': delivery_fee,
        'delivery_time': delivery_time,
    }
    return render(request, 'admin_dashboard/customers/address_detail.html', context)


@login_required
@user_passes_test(is_admin)
@require_POST
def toggle_address_verification(request, address_id):
    address = get_object_or_404(CustomerAddress, id=address_id)
    address.is_verified = not address.is_verified
    address.save()
    
    action = "verified" if address.is_verified else "unverified"
    messages.success(request, f'Address {action} successfully!')
    return redirect('admin_dashboard:customer-address-detail', address_id=address_id)


@login_required
@user_passes_test(is_admin)
@require_POST
def recalculate_address_zone(request, address_id):
    address = get_object_or_404(CustomerAddress, id=address_id)
    address.update_zone_and_fee()
    
    messages.success(request, 'Zone and delivery fee recalculated!')
    return redirect('admin_dashboard:customer-address-detail', address_id=address_id)


# AJAX Views for Map and Calculations
@login_required
@user_passes_test(is_admin)
def calculate_delivery_fee_ajax(request):
    """AJAX endpoint for delivery fee calculation"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            market_id = data.get('market_id')
            latitude = Decimal(str(data.get('latitude')))
            longitude = Decimal(str(data.get('longitude')))
            order_amount = Decimal(str(data.get('order_amount', 0)))
            
            market = Market.objects.get(id=market_id)
            
            # Find appropriate delivery zone
            from django.contrib.gis.geos import Point
            point = Point(float(longitude), float(latitude), srid=4326)
            
            zones = DeliveryZone.objects.filter(
                market=market,
                is_active=True,
                boundary__contains=point
            ).order_by('priority')
            
            if not zones.exists():
                # Find nearest zone
                zones = DeliveryZone.objects.filter(
                    market=market,
                    is_active=True,
                    center_point__isnull=False
                )
                
                if zones.exists():
                    nearest_zone = None
                    min_distance = float('inf')
                    
                    for zone in zones:
                        distance = zone._calculate_distance(point, zone.center_point)
                        if distance < min_distance:
                            min_distance = distance
                            nearest_zone = zone
                    
                    zone = nearest_zone
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'No delivery zones available for this market'
                    })
            else:
                zone = zones.first()
            
            # Calculate fee
            delivery_fee = zone.calculate_delivery_fee(point, order_amount)
            
            if delivery_fee is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Delivery not available to this location'
                })
            
            # Get delivery time estimate
            delivery_time = zone.estimated_delivery_time
            
            return JsonResponse({
                'success': True,
                'zone_id': str(zone.id),
                'zone_name': zone.name,
                'zone_type': zone.zone_type,
                'delivery_fee': float(delivery_fee),
                'delivery_time': delivery_time,
                'distance': float(zone.distance_from_market) if zone.distance_from_market else None,
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_admin)
def get_market_zones_ajax(request, market_id):
    """Get delivery zones for a market"""
    zones = DeliveryZone.objects.filter(
        market_id=market_id,
        is_active=True
    ).values('id', 'name', 'zone_type', 'priority')
    
    return JsonResponse(list(zones), safe=False)


# Reports and Analytics
@login_required
@user_passes_test(is_admin)
def delivery_analytics(request):
    """Delivery analytics dashboard"""
    
    # Date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Zone distribution
    zone_distribution = DeliveryZone.objects.values('zone_type').annotate(
        count=Count('id'),
        active_count=Count('id', filter=models.Q(is_active=True))
    )
    
    # Market coverage
    market_coverage = Market.objects.annotate(
        zone_count=Count('delivery_zones'),
        active_zone_count=Count('delivery_zones', filter=models.Q(delivery_zones__is_active=True))
    ).order_by('-active_zone_count')
    
    # Customer address growth
    address_growth = []
    for i in range(30):
        date = start_date + timedelta(days=i)
        count = CustomerAddress.objects.filter(
            created_at__date__lte=date
        ).count()
        address_growth.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'zone_distribution': zone_distribution,
        'market_coverage': market_coverage,
        'address_growth': address_growth,
    }
    return render(request, 'admin_dashboard/analytics/delivery_analytics.html', context)


# Market Day Management
@login_required
@user_passes_test(is_admin)
def manage_market_days(request):
    days = MarketDay.objects.all().order_by('id')
    
    # Statistics
    market_counts = []
    for day in days:
        market_count = day.markets.count()
        market_counts.append(market_count)
    
    context = {
        'days': days,
        'market_counts': zip(days, market_counts),
    }
    return render(request, 'admin_dashboard/markets/manage_market_days.html', context)


@login_required
@user_passes_test(is_admin)
def add_market_day(request):
    if request.method == 'POST':
        try:
            day = request.POST.get('day')
            if not day:
                raise ValueError("Day is required")
            
            # Check if day already exists
            if MarketDay.objects.filter(day=day).exists():
                messages.error(request, f'Day "{day}" already exists!')
            else:
                MarketDay.objects.create(day=day)
                messages.success(request, f'Market day "{day}" added successfully!')
            
            return redirect('admin_dashboard:manage-market-days')
            
        except Exception as e:
            messages.error(request, f'Error adding market day: {str(e)}')
    
    return render(request, 'admin_dashboard/markets/add_market_day.html')


@login_required
@user_passes_test(is_admin)
def delete_market_day(request, day_id):
    day = get_object_or_404(MarketDay, id=day_id)
    
    if request.method == 'POST':
        day_name = str(day)
        day.delete()
        messages.success(request, f'Market day "{day_name}" deleted!')
    
    return redirect('admin_dashboard:manage-market-days')


# ============================================
# SETTINGS & SYSTEM MANAGEMENT
# ============================================
@login_required
@user_passes_test(is_admin)
def system_settings(request):
    """System settings management"""
    settings = GlobalSetting.objects.all()
    
    if request.method == 'POST':
        # Handle settings update
        for setting in settings:
            new_value = request.POST.get(f'setting_{setting.id}')
            if new_value is not None:
                setting.value = new_value
                setting.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('system-settings')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin_dashboard/settings/system_settings.html', context)

















@login_required
@user_passes_test(is_admin)
def manage_unit_types(request):
    unit_types = MeasurementUnitType.objects.all()
    active_types_count = unit_types.filter(is_active=True).count()  # ← ADD THIS
    return render(request, 'admin_dashboard/units/manage_unit_types.html', {
        'unit_types': unit_types,
        'active_types_count': active_types_count,  # ← PASS TO TEMPLATE
    })

@login_required
@user_passes_test(is_admin)
def add_unit_type(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            base_unit_name = request.POST.get('base_unit_name')
            
            MeasurementUnitType.objects.create(
                name=name,
                description=description,
                base_unit_name=base_unit_name
            )
            messages.success(request, f'Unit type "{name}" created!')
            return redirect('admin_dashboard:manage-unit-types')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/units/add_unit_type.html')

@login_required
@user_passes_test(is_admin)
def edit_unit_type(request, type_id):
    unit_type = get_object_or_404(MeasurementUnitType, id=type_id)
    if request.method == 'POST':
        try:
            unit_type.name = request.POST.get('name')
            unit_type.description = request.POST.get('description', '')
            unit_type.base_unit_name = request.POST.get('base_unit_name')
            unit_type.save()
            messages.success(request, f'Unit type updated!')
            return redirect('admin_dashboard:manage-unit-types')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/units/edit_unit_type.html', {
        'unit_type': unit_type
    })

@login_required
@user_passes_test(is_admin)
def delete_unit_type(request, type_id):
    unit_type = get_object_or_404(MeasurementUnitType, id=type_id)
    if request.method == 'POST':
        name = unit_type.name
        unit_type.delete()
        messages.success(request, f'Unit type "{name}" deleted!')
    return redirect('admin_dashboard:manage-unit-types')

@login_required
@user_passes_test(is_admin)
def manage_units(request):
    units = MeasurementUnit.objects.select_related('unit_type').all()
    unit_types = MeasurementUnitType.objects.all()
    
    type_filter = request.GET.get('unit_type')
    if type_filter:
        units = units.filter(unit_type_id=type_filter)
    
    active_units_count = units.filter(is_active=True).count()
    
    return render(request, 'admin_dashboard/units/manage_units.html', {
        'units': units,
        'unit_types': unit_types,
        'active_units_count': active_units_count,
        'filters': {'unit_type': type_filter}
    })

@login_required
@user_passes_test(is_admin)
def add_unit(request):
    unit_types = MeasurementUnitType.objects.all()
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            symbol = request.POST.get('symbol')
            unit_type_id = request.POST.get('unit_type')
            conversion_factor = Decimal(request.POST.get('conversion_factor'))
            is_base_unit = request.POST.get('is_base_unit') == 'on'
            
            MeasurementUnit.objects.create(
                name=name,
                symbol=symbol,
                unit_type_id=unit_type_id,
                conversion_factor=conversion_factor,
                is_base_unit=is_base_unit
            )
            messages.success(request, f'Unit "{name}" created!')
            return redirect('admin_dashboard:measurement-units')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/units/add_unit.html', {
        'unit_types': unit_types
    })

@login_required
@user_passes_test(is_admin)
def edit_unit(request, unit_id):
    unit = get_object_or_404(MeasurementUnit, id=unit_id)
    unit_types = MeasurementUnitType.objects.all()
    if request.method == 'POST':
        try:
            unit.name = request.POST.get('name')
            unit.symbol = request.POST.get('symbol')
            unit.unit_type_id = request.POST.get('unit_type')
            unit.conversion_factor = Decimal(request.POST.get('conversion_factor'))
            unit.is_base_unit = request.POST.get('is_base_unit') == 'on'
            unit.save()
            messages.success(request, f'Unit updated!')
            return redirect('admin_dashboard:measurement-units')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'admin_dashboard/units/edit_unit.html', {
        'unit': unit,
        'unit_types': unit_types
    })

@login_required
@user_passes_test(is_admin)
def delete_unit(request, unit_id):
    unit = get_object_or_404(MeasurementUnit, id=unit_id)
    if request.method == 'POST':
        name = unit.name
        unit.delete()
        messages.success(request, f'Unit "{name}" deleted!')
    return redirect('admin_dashboard:measurement-units')






from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from accounts.models import User, Customer, Vendor, Driver, AdminProfile, SecurityQuestion, UserSecurityAnswer
from accounts.serializers import (
    CustomerRegistrationSerializer, VendorRegistrationSerializer,
    LoginSerializer, CustomerProfileSerializer, VendorProfileSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetVerifySerializer, SecurityQuestionSerializer,
    UserSerializer, DriverProfileSerializer, AdminProfileSerializer,
    ProfilePictureSerializer
)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def security_questions(request):
    """Get all active security questions"""
    questions = SecurityQuestion.objects.filter(is_active=True)
    serializer = SecurityQuestionSerializer(questions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def customer_register(request):
    with transaction.atomic():
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            
            refresh = RefreshToken.for_user(customer.user)
            
            return Response({
                'message': 'Customer registered successfully',
                'customer': CustomerProfileSerializer(customer).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def vendor_register(request):
    with transaction.atomic():
        serializer = VendorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            vendor = serializer.save()
            
            refresh = RefreshToken.for_user(vendor.user)
            
            return Response({
                'message': 'Vendor registered successfully. Awaiting verification.',
                'vendor': VendorProfileSerializer(vendor).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        
        profile_data = {}
        if user.user_type == 'customer':
            profile_data = CustomerProfileSerializer(user.customer).data
        elif user.user_type == 'vendor':
            profile_data = VendorProfileSerializer(user.vendor).data
        elif user.user_type == 'driver':
            profile_data = DriverProfileSerializer(user.driver).data
        elif user.user_type == 'admin':
            profile_data = AdminProfileSerializer(user.admin_profile).data
        
        return Response({
            'message': 'Login successful',
            'user_type': user.user_type,
            'profile': profile_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            security_answers = UserSecurityAnswer.objects.filter(user=user).select_related('question')
            
            questions = []
            for answer in security_answers:
                questions.append({
                    'question_id': answer.question.id,
                    'question': answer.question.question
                })
            
            return Response({
                'message': 'Security questions retrieved',
                'questions': questions
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'User with this phone number does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_verify(request):
    serializer = PasswordResetVerifySerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        answers = serializer.validated_data['answers']
        new_password = serializer.validated_data['new_password']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            security_answers = UserSecurityAnswer.objects.filter(user=user).select_related('question')
            
            # Verify answers
            correct_answers = 0
            for answer_data in answers:
                question_id = answer_data.get('question_id')
                user_answer = answer_data.get('answer', '').lower().strip()
                
                try:
                    stored_answer = security_answers.get(question_id=question_id)
                    if stored_answer.answer == user_answer:
                        correct_answers += 1
                except ObjectDoesNotExist:
                    pass
            
            # Require at least 2 correct answers
            if correct_answers >= 2:
                user.set_password(new_password)
                user.save()
                
                return Response({
                    'message': 'Password reset successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Incorrect answers to security questions'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            return Response({
                'error': 'User with this phone number does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def customer_profile(request):
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = CustomerProfileSerializer(customer)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Handle user data separately from customer data
        user_data = {}
        customer_data = {}
        
        for key, value in request.data.items():
            if key in ['email']:
                user_data[key] = value
            else:
                customer_data[key] = value
        
        # Update user data if provided
        if user_data:
            user_serializer = UserSerializer(request.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update customer data
        serializer = CustomerProfileSerializer(customer, data=customer_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def vendor_profile(request):
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = VendorProfileSerializer(vendor)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Handle user data separately from vendor data
        user_data = {}
        vendor_data = {}
        
        for key, value in request.data.items():
            if key in ['email']:
                user_data[key] = value
            else:
                vendor_data[key] = value
        
        # Update user data if provided
        if user_data:
            user_serializer = UserSerializer(request.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update vendor data
        serializer = VendorProfileSerializer(vendor, data=vendor_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def driver_profile(request):
    """Driver profile management"""
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Driver profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = DriverProfileSerializer(driver)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Handle user data separately from driver data
        user_data = {}
        driver_data = {}
        
        for key, value in request.data.items():
            if key in ['email']:
                user_data[key] = value
            else:
                driver_data[key] = value
        
        # Update user data if provided
        if user_data:
            user_serializer = UserSerializer(request.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update driver data
        serializer = DriverProfileSerializer(driver, data=driver_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['POST', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def profile_picture_upload(request):
    """Upload or delete profile picture"""
    user = request.user
    
    if request.method == 'POST':
        serializer = ProfilePictureSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            # Delete old profile picture if exists
            if user.profile_picture:
                user.delete_profile_picture()
            
            serializer.save()
            return Response({
                'message': 'Profile picture uploaded successfully',
                'profile_picture_url': user.get_profile_picture_url()
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if user.profile_picture:
            user.delete_profile_picture()
            return Response({
                'message': 'Profile picture deleted successfully',
                'profile_picture_url': user.get_profile_picture_url()
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'No profile picture to delete'
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def vendor_document_upload(request):
    """Upload vendor documents"""
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor profile not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    license_document = request.FILES.get('license_document')
    id_document = request.FILES.get('id_document')
    
    if license_document:
        # Delete old license document if exists
        if vendor.license_document:
            vendor.license_document.delete()
        vendor.license_document = license_document
    
    if id_document:
        # Delete old ID document if exists
        if vendor.id_document:
            vendor.id_document.delete()
        vendor.id_document = id_document
    
    if license_document or id_document:
        vendor.save()
        return Response({
            'message': 'Documents uploaded successfully',
            'vendor': VendorProfileSerializer(vendor).data
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'error': 'No documents provided'
        }, status=status.HTTP_400_BAD_REQUEST)

# Admin Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_dashboard(request):
    """Admin dashboard statistics"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    stats = {
        'total_customers': Customer.objects.count(),
        'total_vendors': Vendor.objects.count(),
        'total_drivers': Driver.objects.count(),
        'total_users': User.objects.count(),
        'pending_vendor_verifications': Vendor.objects.filter(is_verified=False).count(),
        'pending_driver_verifications': Driver.objects.filter(is_verified=False).count(),
        'recent_signups': User.objects.filter(date_joined__gte=timezone.now()-timezone.timedelta(days=7)).count(),
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_users_list(request):
    """List all users for admin"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_type = request.GET.get('type', 'all')
    
    if user_type == 'customer':
        users = Customer.objects.all()
        serializer = CustomerProfileSerializer(users, many=True)
    elif user_type == 'vendor':
        users = Vendor.objects.all()
        serializer = VendorProfileSerializer(users, many=True)
    elif user_type == 'driver':
        users = Driver.objects.all()
        serializer = DriverProfileSerializer(users, many=True)
    elif user_type == 'admin':
        users = AdminProfile.objects.all()
        serializer = AdminProfileSerializer(users, many=True)
    else:
        # Return all users count
        return Response({
            'customers': Customer.objects.count(),
            'vendors': Vendor.objects.count(),
            'drivers': Driver.objects.count(),
            'admins': AdminProfile.objects.count(),
            'total': User.objects.count()
        })
    
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_verify_vendor(request, vendor_id):
    """Verify a vendor account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        vendor = Vendor.objects.get(user_id=vendor_id)
        vendor.is_verified = True
        vendor.verified_at = timezone.now()
        vendor.save()
        
        return Response({
            'message': 'Vendor verified successfully',
            'vendor': VendorProfileSerializer(vendor).data
        })
        
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_verify_driver(request, driver_id):
    """Verify a driver account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        driver = Driver.objects.get(user_id=driver_id)
        driver.is_verified = True
        driver.verified_at = timezone.now()
        driver.save()
        
        return Response({
            'message': 'Driver verified successfully',
            'driver': DriverProfileSerializer(driver).data
        })
        
    except Driver.DoesNotExist:
        return Response(
            {'error': 'Driver not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_deactivate_user(request, user_id):
    """Deactivate a user account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        
        return Response({
            'message': 'User deactivated successfully',
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_activate_user(request, user_id):
    """Activate a user account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        
        return Response({
            'message': 'User activated successfully',
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """Get current user information"""
    user = request.user
    profile_data = {}
    
    if user.user_type == 'customer':
        profile_data = CustomerProfileSerializer(user.customer).data
    elif user.user_type == 'vendor':
        profile_data = VendorProfileSerializer(user.vendor).data
    elif user.user_type == 'driver':
        profile_data = DriverProfileSerializer(user.driver).data
    elif user.user_type == 'admin':
        profile_data = AdminProfileSerializer(user.admin_profile).data
    
    return Response({
        'user': UserSerializer(user).data,
        'profile': profile_data
    })



# Add these to your existing views in accounts/views.py

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_get_current_user(request):
    """Get current user information for admin"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
    profile_data = {}
    
    if user.user_type == 'customer':
        profile_data = CustomerProfileSerializer(user.customer).data
    elif user.user_type == 'vendor':
        profile_data = VendorProfileSerializer(user.vendor).data
    elif user.user_type == 'driver':
        profile_data = DriverProfileSerializer(user.driver).data
    elif user.user_type == 'admin':
        profile_data = AdminProfileSerializer(user.admin_profile).data
    
    return Response({
        'user': UserSerializer(user).data,
        'profile': profile_data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_deactivate_user(request, user_id):
    """Deactivate a user account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        
        return Response({
            'message': 'User deactivated successfully',
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_activate_user(request, user_id):
    """Activate a user account"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        
        return Response({
            'message': 'User activated successfully',
            'user': UserSerializer(user).data
        })
        
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    


# Add to accounts/views.py

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_pending_verifications(request):
    """Get all pending vendor verifications"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    pending_vendors = Vendor.objects.filter(
        is_verified=False,
        user__is_active=True
    ).select_related('user')
    
    serializer = VendorProfileSerializer(pending_vendors, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_verified_vendors(request):
    """Get all verified vendors"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    verified_vendors = Vendor.objects.filter(
        is_verified=True,
        user__is_active=True
    ).select_related('user')
    
    serializer = VendorProfileSerializer(verified_vendors, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_vendor_detail(request, vendor_id):
    """Get vendor details by ID"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        vendor = Vendor.objects.select_related('user').get(user_id=vendor_id)
        serializer = VendorProfileSerializer(vendor)
        return Response(serializer.data)
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def admin_update_vendor(request, vendor_id):
    """Update vendor information"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        vendor = Vendor.objects.select_related('user').get(user_id=vendor_id)
        
        # Handle user data and vendor data separately
        user_data = {}
        vendor_data = {}
        
        for key, value in request.data.items():
            if key in ['email']:
                user_data[key] = value
            else:
                vendor_data[key] = value
        
        # Update user data if provided
        if user_data:
            user_serializer = UserSerializer(
                vendor.user, 
                data=user_data, 
                partial=True
            )
            if user_serializer.is_valid():
                user_serializer.save()
            else:
                return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update vendor data
        serializer = VendorProfileSerializer(
            vendor, 
            data=vendor_data, 
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def admin_reject_vendor(request, vendor_id):
    """Reject a vendor application"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        vendor = Vendor.objects.get(user_id=vendor_id)
        # You might want to add a rejection reason field to your model
        # For now, we'll just delete the vendor account
        vendor.user.delete()
        
        return Response({
            'message': 'Vendor application rejected and account deleted'
        })
        
    except Vendor.DoesNotExist:
        return Response(
            {'error': 'Vendor not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def admin_analytics(request):
    """Get analytics data for admin dashboard"""
    if request.user.user_type != 'admin':
        return Response(
            {'error': 'Access denied. Admin privileges required.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    time_range = request.GET.get('time_range', '7d')
    end_date = timezone.now()
    
    if time_range == '7d':
        start_date = end_date - timezone.timedelta(days=7)
    elif time_range == '30d':
        start_date = end_date - timezone.timedelta(days=30)
    elif time_range == '90d':
        start_date = end_date - timezone.timedelta(days=90)
    elif time_range == '1y':
        start_date = end_date - timezone.timedelta(days=365)
    else:
        start_date = end_date - timezone.timedelta(days=7)
    
    analytics_data = {
        'total_users': User.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_vendors': Vendor.objects.count(),
        'total_drivers': Driver.objects.count(),
        'pending_verifications': Vendor.objects.filter(is_verified=False).count(),
        'new_users_this_week': User.objects.filter(
            date_joined__gte=start_date
        ).count(),
        'new_vendors_this_week': Vendor.objects.filter(
            user__date_joined__gte=start_date
        ).count(),
        'verified_vendors_count': Vendor.objects.filter(is_verified=True).count(),
        'active_vendors_count': Vendor.objects.filter(
            is_verified=True, 
            user__is_active=True
        ).count(),
    }
    
    return Response(analytics_data)




# main app views.py (e.g., in your root app or core app)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home_view(request):
    return render(request, 'admin_dashboard/home.html')



















# ============================================
# ENHANCED ORDER MANAGEMENT
# ============================================

@login_required
@user_passes_test(is_admin)
def manage_orders(request):
    """Enhanced order management with advanced filtering"""
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    date_range = request.GET.get('date_range', '')
    search_query = request.GET.get('q', '')
    market_filter = request.GET.get('market', '')
    
    orders = Order.objects.select_related(
        'customer', 'driver', 'delivery_address', 'delivery_time_slot'
    ).prefetch_related('items').order_by('-created_at')
    
    # Apply filters
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    if payment_filter != 'all':
        orders = orders.filter(payment_method=payment_filter)
    
    if market_filter:
        orders = orders.filter(delivery_address__market_id=market_filter)
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__phone_number__icontains=search_query) |
            Q(customer__customer__names__icontains=search_query) |
            Q(driver__driver__names__icontains=search_query)
        )
    
    # Date range filter
    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            orders = orders.filter(created_at__date=today)
        elif date_range == 'yesterday':
            yesterday = today - timedelta(days=1)
            orders = orders.filter(created_at__date=yesterday)
        elif date_range == 'week':
            week_ago = today - timedelta(days=7)
            orders = orders.filter(created_at__date__gte=week_ago)
        elif date_range == 'month':
            month_ago = today - timedelta(days=30)
            orders = orders.filter(created_at__date__gte=month_ago)
    
    # Pagination
    paginator = Paginator(orders, 50)  # Show 50 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics for dashboard cards
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    confirmed_orders = orders.filter(status='confirmed').count()
    preparing_orders = orders.filter(status='preparing').count()
    ready_orders = orders.filter(status='ready').count()
    assigned_orders = orders.filter(status='assigned').count()
    picked_up_orders = orders.filter(status='picked_up').count()
    on_the_way_orders = orders.filter(status='on_the_way').count()
    delivered_orders = orders.filter(status='delivered').count()
    cancelled_orders = orders.filter(status='cancelled').count()
    
    # Revenue calculations
    revenue_today = Order.objects.filter(
        created_at__date=timezone.now().date(),
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    revenue_month = Order.objects.filter(
        created_at__month=timezone.now().month,
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Markets for filter dropdown
    markets = Market.objects.all()
    
    context = {
        'page_obj': page_obj,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'confirmed_orders': confirmed_orders,
        'preparing_orders': preparing_orders,
        'ready_orders': ready_orders,
        'assigned_orders': assigned_orders,
        'picked_up_orders': picked_up_orders,
        'on_the_way_orders': on_the_way_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'revenue_today': revenue_today,
        'revenue_month': revenue_month,
        'markets': markets,
        'filters': {
            'status': status_filter,
            'payment': payment_filter,
            'date_range': date_range,
            'search': search_query,
            'market': market_filter,
        },
        'order_statuses': Order.ORDER_STATUS,
        'payment_methods': Order.PAYMENT_METHODS,
    }
    
    return render(request, 'admin_dashboard/orders/manage_orders.html', context)

@login_required
@user_passes_test(is_admin)
def order_detail(request, order_id):
    """Enhanced order detail view"""
    order = get_object_or_404(
        Order.objects.select_related(
            'customer', 'driver', 'delivery_address', 
            'delivery_time_slot'
        ).prefetch_related(
            'items__product_variant__product_template',
            'items__selected_addons',
            'status_updates__updated_by'
        ),
        id=order_id
    )
    
    # Status timeline
    # Status timeline
    status_timeline = [
        ('Order Created', order.created_at),
        ('Confirmed', order.confirmed_at),
        ('Assigned to Driver', order.assigned_at),
        ('Picked Up', order.picked_up_at),
        ('Delivered', order.delivered_at),
    ]

    # Check for cancellation
    if order.cancelled_at:
        status_timeline.append(('Cancelled', order.cancelled_at))
        
    # Status updates history
    status_updates = order.status_updates.all().order_by('-created_at')
    
    # Calculate preparation time
    # Calculate preparation time (from confirmed to picked_up)
    preparation_time = None
    if order.confirmed_at and order.picked_up_at:
        preparation_time = order.picked_up_at - order.confirmed_at

    # Calculate delivery time
    delivery_time = None
    if order.picked_up_at and order.delivered_at:
        delivery_time = order.delivered_at - order.picked_up_at

    # Calculate total order time
    total_order_time = None
    if order.created_at and order.delivered_at:
        total_order_time = order.delivered_at - order.created_at
    
    # Available drivers for assignment
    available_drivers = Driver.objects.filter(
        is_available=True,
        is_verified=True,
        user__is_active=True
    ).select_related('user')
    
    context = {
        'order': order,
        'status_timeline': status_timeline,
        'status_updates': status_updates,
        'preparation_time': preparation_time,
        'delivery_time': delivery_time,
        'available_drivers': available_drivers,
        'order_statuses': Order.ORDER_STATUS,
    }
    
    return render(request, 'admin_dashboard/orders/order_detail.html', context)

@login_required
@user_passes_test(is_admin)
def update_order_status(request, order_id):
    """Update order status with detailed logging"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        
        if new_status and new_status != order.status:
            old_status = order.status
            
            # Update timestamps based on status
            now = timezone.now()
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = now
            elif new_status == 'assigned' and not order.assigned_at:
                order.assigned_at = now
            elif new_status == 'picked_up' and not order.picked_up_at:
                order.picked_up_at = now
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = now
            elif new_status == 'ready' and not order.ready_at:
                order.ready_at = now
                # Auto-mark as paid for cash on delivery
                if order.payment_method == 'cash_on_delivery':
                    order.is_paid = True
            elif new_status == 'cancelled' and not order.cancelled_at:
                order.cancelled_at = now
                order.cancellation_reason = note
            
            order.status = new_status
            order.save()
            
            # Create status update record
            # Create status update
            ordertatusUpdate.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                updated_by=request.user,
                note=note
            )
            
            messages.success(request, f'Order status updated to {new_status}')
    
    return redirect('admin_dashboard:order-detail', order_id=order_id)

@login_required
@user_passes_test(is_admin)
def assign_driver(request, order_id):
    """Assign driver to order"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        
        if driver_id:
            try:
                driver_user = User.objects.get(id=driver_id, user_type='driver')
                order.driver = driver_user
                order.assigned_at = timezone.now()
                order.status = 'assigned'
                order.save()
                
                # Create status update
                ordertatusUpdate.objects.create(
                    order=order,
                    old_status=order.status,
                    new_status='assigned',
                    updated_by=request.user,
                    note=f'Assigned to driver: {driver_user.driver.names}'
                )
                
                messages.success(request, f'Driver assigned successfully!')
            except User.DoesNotExist:
                messages.error(request, 'Driver not found')
        else:
            # Unassign driver
            order.driver = None
            order.assigned_at = None
            order.status = 'ready'
            order.save()
            
            # Create status update
            ordertatusUpdate.objects.create(
                order=order,
                old_status='assigned',
                new_status='ready',
                updated_by=request.user,
                note='Driver unassigned'
            )
            
            messages.success(request, 'Driver unassigned')
    
    return redirect('admin_dashboard:order-detail', order_id=order_id)


@login_required
@user_passes_test(is_admin)
def bulk_assign_driver(request):
    """Bulk assign driver to multiple orders"""
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        driver_id = request.POST.get('driver_id')
        
        if not order_ids:
            messages.error(request, 'No orders selected.')
            return redirect('admin_dashboard:ready-for-pickup')
        
        orders = Order.objects.filter(id__in=order_ids, status='ready')
        
        if driver_id == 'auto':
            # Auto assign - assign to the first available driver
            available_driver = Driver.objects.filter(
                is_available=True,
                is_verified=True,
                user__is_active=True
            ).first()
            
            if available_driver:
                driver_id = available_driver.user.id
            else:
                messages.error(request, 'No available drivers found.')
                return redirect('admin_dashboard:ready-for-pickup')
        
        try:
            driver_user = User.objects.get(id=driver_id, user_type='driver')
            assigned_count = 0
            
            for order in orders:
                order.driver = driver_user
                order.assigned_at = timezone.now()
                order.status = 'assigned'
                order.save()
                
                # Create status update
                OrderStatusUpdate.objects.create(
                    order=order,
                    old_status='ready',
                    new_status='assigned',
                    updated_by=request.user,
                    note=f'Bulk assigned to driver: {driver_user.driver.names}'
                )
                assigned_count += 1
            
            messages.success(request, f'Successfully assigned {assigned_count} order(s) to {driver_user.driver.names}')
            
        except User.DoesNotExist:
            messages.error(request, 'Driver not found')
        except Exception as e:
            messages.error(request, f'Error assigning driver: {str(e)}')
    
    return redirect('admin_dashboard:ready-for-pickup')


    
@login_required
@user_passes_test(is_admin)
def cancel_order(request, order_id):
    """Cancel order (admin)"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        cancellation_reason = request.POST.get('cancellation_reason', '')
        
        if cancellation_reason:
            order.status = 'cancelled'
            order.cancellation_reason = cancellation_reason
            order.cancelled_at = timezone.now()
            order.save()
            
            # Create status update
            ordertatusUpdate.objects.create(
                order=order,
                old_status=order.status,
                new_status='cancelled',
                updated_by=request.user,
                note=f'Cancelled: {cancellation_reason}'
            )
            
            messages.success(request, 'Order cancelled successfully')
        else:
            messages.error(request, 'Please provide a cancellation reason')
    
    return redirect('admin_dashboard:order-detail', order_id=order_id)

@login_required
@user_passes_test(is_admin)
def update_payment_status(request, order_id):
    """Update payment status"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        is_paid = request.POST.get('is_paid') == 'true'
        payment_reference = request.POST.get('payment_reference', '')
        
        order.is_paid = is_paid
        if payment_reference:
            order.payment_reference = payment_reference
        order.save()
        
        messages.success(request, f'Payment status updated to {"Paid" if is_paid else "Unpaid"}')
    
    return redirect('admin_dashboard:order-detail', order_id=order_id)

@login_required
@user_passes_test(is_admin)
def bulk_order_action(request):
    """Handle bulk actions for orders"""
    if request.method == 'POST':
        order_ids = request.POST.getlist('order_ids')
        action = request.POST.get('action')
        
        if not order_ids:
            messages.warning(request, 'No orders selected.')
            return redirect('admin_dashboard:manage-orders')
        
        orders = Order.objects.filter(id__in=order_ids)
        
        if action == 'confirm':
            orders.update(status='confirmed', confirmed_at=timezone.now())
            messages.success(request, f'{orders.count()} order(s) confirmed.')
        elif action == 'mark_ready':
            orders.update(status='ready')
            messages.success(request, f'{orders.count()} order(s) marked as ready.')
        elif action == 'cancel':
            orders.update(status='cancelled', cancelled_at=timezone.now())
            messages.success(request, f'{orders.count()} order(s) cancelled.')
        elif action == 'mark_paid':
            orders.update(is_paid=True)
            messages.success(request, f'{orders.count()} order(s) marked as paid.')
        elif action == 'mark_unpaid':
            orders.update(is_paid=False)
            messages.success(request, f'{orders.count()} order(s) marked as unpaid.')
        else:
            messages.error(request, 'Invalid action specified.')
    
    return redirect('admin_dashboard:manage-orders')

@login_required
@user_passes_test(is_admin)
def orders_by_status(request, status):
    """View orders by specific status"""
    orders = Order.objects.filter(status=status).select_related(
        'customer', 'driver'
    ).order_by('-created_at')
    
    status_display = dict(Order.ORDER_STATUS).get(status, status)
    
    context = {
        'orders': orders,
        'status': status,
        'status_display': status_display,
        'total_orders': orders.count(),
    }
    
    return render(request, 'admin_dashboard/orders/orders_by_status.html', context)


@login_required
@user_passes_test(is_admin)
def todays_orders(request):
    """View today's orders"""
    today = timezone.now().date()
    orders = Order.objects.filter(
        created_at__date=today
    ).select_related('customer', 'driver').order_by('-created_at')
    
    # Calculate statistics
    total_orders = orders.count()
    total_revenue = sum(order.total_amount for order in orders if order.status == 'delivered')
    delivered_count = orders.filter(status='delivered').count()
    active_count = orders.exclude(status__in=['delivered', 'cancelled', 'failed']).count()
    
    # Group by status
    orders_by_status = {}
    for status_code, status_name in Order.ORDER_STATUS:
        filtered = orders.filter(status=status_code)
        if filtered.exists():
            orders_by_status[status_name] = filtered
    
    context = {
        'orders': orders,
        'today': today,
        'orders_by_status': orders_by_status,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'delivered_count': delivered_count,
        'active_count': active_count,
        'order_statuses': Order.ORDER_STATUS,
    }
    
    return render(request, 'admin_dashboard/orders/todays_orders.html', context)

@login_required
@user_passes_test(is_admin)
def pending_preparation(request):
    """View orders pending preparation (for kitchen/vendor view)"""
    orders = Order.objects.filter(
        status__in=['confirmed', 'preparing']
    ).select_related('customer').prefetch_related(
        'items__product_variant__product_template'
    ).order_by('confirmed_at', 'created_at')
    
    # Group items by vendor for easy kitchen preparation
    vendor_items = {}
    for order in orders:
        for item in order.items.all():
            vendor = item.product_variant.vendor
            if vendor not in vendor_items:
                vendor_items[vendor] = []
            vendor_items[vendor].append({
                'order': order,
                'item': item,
                'preparation_time': 15  # Default preparation time in minutes
            })
    
    context = {
        'orders': orders,
        'vendor_items': vendor_items,
    }
    
    return render(request, 'admin_dashboard/orders/pending_preparation.html', context)

@login_required
@user_passes_test(is_admin)
def ready_for_pickup(request):
    """View orders ready for pickup (driver assignment view)"""
    orders = Order.objects.filter(
        status='ready'
    ).select_related('customer', 'delivery_address').order_by('created_at')
    
    # Group by delivery zone/area
    orders_by_area = {}
    for order in orders:
        area = order.delivery_address.delivery_zone.name if order.delivery_address.delivery_zone else 'Unknown'
        if area not in orders_by_area:
            orders_by_area[area] = []
        orders_by_area[area].append(order)
    
    # Available drivers
    available_drivers = Driver.objects.filter(
        is_available=True,
        is_verified=True,
        user__is_active=True
    ).select_related('user')
    
    context = {
        'orders': orders,
        'orders_by_area': orders_by_area,
        'available_drivers': available_drivers,
    }
    
    return render(request, 'admin_dashboard/orders/ready_for_pickup.html', context)

@login_required
@user_passes_test(is_admin)
def order_timeline(request, order_id):
    """View detailed timeline of order"""
    order = get_object_or_404(Order, id=order_id)
    status_updates = order.status_updates.all().order_by('created_at')
    
    # Create timeline events
    timeline_events = []
    
    # Order created
    timeline_events.append({
        'time': order.created_at,
        'event': 'Order Created',
        'description': f'Order #{order.order_number} created by {order.customer.customer.names}',
        'icon': 'fas fa-shopping-cart',
        'color': 'primary',
        'updated_by': order.customer,  # Add this
        'note': 'Order placed successfully'
    })
    
    # Payment event
    if order.is_paid:
        timeline_events.append({
            'time': order.created_at,  # Adjust if you track payment time
            'event': 'Payment Received',
            'description': f'Payment via {order.get_payment_method_display()}',
            'icon': 'fas fa-credit-card',
            'color': 'success',
            'updated_by': order.customer,  # Add this
            'note': 'Payment completed successfully'
        })
    
    # Confirmation
    if order.confirmed_at:
        # Find who confirmed it
        confirmed_by = None
        for update in status_updates:
            if update.new_status == 'confirmed':
                confirmed_by = update.updated_by
                break
        
        timeline_events.append({
            'time': order.confirmed_at,
            'event': 'Order Confirmed',
            'description': 'Order confirmed and sent for preparation',
            'icon': 'fas fa-check-circle',
            'color': 'info',
            'updated_by': confirmed_by,  # This might be None, template handles it
            'note': 'Order confirmed by system' if not confirmed_by else f'Confirmed by {confirmed_by.get_full_name()}'
        })
    
    # Driver assignment
    if order.assigned_at:
        assigned_by = None
        for update in status_updates:
            if update.new_status == 'assigned':
                assigned_by = update.updated_by
                break
        
        timeline_events.append({
            'time': order.assigned_at,
            'event': 'Driver Assigned',
            'description': f'Assigned to {order.driver.driver.names if order.driver else "Driver"}',
            'icon': 'fas fa-user',
            'color': 'info',
            'updated_by': assigned_by,
            'note': f'Driver assigned: {order.driver.driver.names if order.driver else "Pending"}'
        })
    
    # Pickup
    if order.picked_up_at:
        picked_up_by = None
        for update in status_updates:
            if update.new_status == 'picked_up':
                picked_up_by = update.updated_by
                break
        
        timeline_events.append({
            'time': order.picked_up_at,
            'event': 'Picked Up',
            'description': 'Driver picked up the order',
            'icon': 'fas fa-motorcycle',
            'color': 'warning',
            'updated_by': picked_up_by,
            'note': 'Order picked up for delivery'
        })
    
    # Delivery
    if order.delivered_at:
        delivered_by = None
        for update in status_updates:
            if update.new_status == 'delivered':
                delivered_by = update.updated_by
                break
        
        timeline_events.append({
            'time': order.delivered_at,
            'event': 'Delivered',
            'description': 'Order delivered to customer',
            'icon': 'fas fa-home',
            'color': 'success',
            'updated_by': delivered_by,
            'note': 'Order delivered successfully'
        })
    
    # Cancellation
    if order.cancelled_at:
        cancelled_by = None
        for update in status_updates:
            if update.new_status == 'cancelled':
                cancelled_by = update.updated_by
                break
        
        timeline_events.append({
            'time': order.cancelled_at,
            'event': 'Cancelled',
            'description': f'Order cancelled: {order.cancellation_reason[:50]}...' if order.cancellation_reason else 'Order cancelled',
            'icon': 'fas fa-times-circle',
            'color': 'danger',
            'updated_by': cancelled_by,
            'note': order.cancellation_reason or 'Order cancelled'
        })
    
    # Add status updates
    for update in status_updates:
        timeline_events.append({
            'time': update.created_at,
            'event': f'Status Update: {update.get_new_status_display()}',
            'description': update.note if update.note else f'Changed from {update.get_old_status_display()} to {update.get_new_status_display()}',
            'icon': 'fas fa-sync',
            'color': 'secondary',
            'updated_by': update.updated_by,
            'note': update.note
        })
    
    # Sort timeline by time
    timeline_events.sort(key=lambda x: x['time'])
    
    context = {
        'order': order,
        'timeline_events': timeline_events,
        'status_updates': status_updates,
    }
    
    return render(request, 'admin_dashboard/orders/order_timeline.html', context)


@login_required
@user_passes_test(is_admin)
def export_orders_csv(request):
    """Export orders to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Order Number', 'Customer', 'Phone', 'Delivery Address',
        'Items Total', 'Delivery Fee', 'Total Amount', 'Payment Method',
        'Payment Status', 'Order Status', 'Driver', 'Created Date'
    ])
    
    orders = Order.objects.select_related(
        'customer', 'driver', 'delivery_address'
    ).all().order_by('-created_at')
    
    for order in orders:
        customer_name = order.customer.customer.names if order.customer.customer else 'N/A'
        driver_name = order.driver.driver.names if order.driver and order.driver.driver else 'Not Assigned'
        
        writer.writerow([
            order.order_number,
            customer_name,
            order.customer.phone_number,
            order.delivery_address.street_address,
            float(order.items_total),
            float(order.delivery_fee),
            float(order.total_amount),
            order.get_payment_method_display(),
            'Paid' if order.is_paid else 'Unpaid',
            order.get_status_display(),
            driver_name,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

@login_required
@user_passes_test(is_admin)
def order_analytics(request):
    """Order analytics dashboard"""
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Overall statistics
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Daily statistics
    daily_stats = []
    for i in range(7):
        date = today - timedelta(days=i)
        day_orders = Order.objects.filter(created_at__date=date)
        day_revenue = day_orders.filter(status='delivered').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        daily_stats.append({
            'date': date,
            'orders_count': day_orders.count(),
            'revenue': day_revenue,
            'avg_order_value': day_revenue / day_orders.count() if day_orders.count() > 0 else 0
        })
    
    # Status distribution
    status_distribution = []
    for status_code, status_name in Order.ORDER_STATUS:
        count = Order.objects.filter(status=status_code).count()
        if count > 0:
            status_distribution.append({
                'status': status_name,
                'count': count,
                'percentage': (count / total_orders * 100) if total_orders > 0 else 0
            })
    
    # Top customers
    top_customers = Customer.objects.annotate(
        order_count=Count('user__order'),
        total_spent=Sum('user__order__total_amount', filter=Q(user__order__status='delivered'))
    ).order_by('-total_spent')[:10]
    
    # Delivery performance
    delivered_orders = Order.objects.filter(status='delivered', delivered_at__isnull=False)
    avg_delivery_time = delivered_orders.annotate(
        delivery_time=F('delivered_at') - F('picked_up_at')
    ).aggregate(avg=models.Avg('delivery_time'))['avg']
    
    context = {
        'today': today,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'daily_stats': daily_stats,
        'status_distribution': status_distribution,
        'top_customers': top_customers,
        'avg_delivery_time': avg_delivery_time,
        'delivered_orders_count': delivered_orders.count(),
    }
    
    return render(request, 'admin_dashboard/orders/analytics.html', context)

@login_required
@user_passes_test(is_admin)
def print_order_invoice(request, order_id):
    """Print order invoice"""
    order = get_object_or_404(
        Order.objects.select_related(
            'customer', 'delivery_address', 'delivery_time_slot'
        ).prefetch_related('items'),
        id=order_id
    )
    
    return render(request, 'admin_dashboard/orders/print_invoice.html', {
        'order': order,
        'now': timezone.now()
    })