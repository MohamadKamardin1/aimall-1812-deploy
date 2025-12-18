from django.urls import path
from . import views

urlpatterns = [
    # Security Questions
    path('security-questions/', views.security_questions, name='security-questions'),
    
    # Authentication
    path('customer/register/', views.customer_register, name='customer-register'),
    path('vendor/register/', views.vendor_register, name='vendor-register'),
    path('login/', views.user_login, name='user-login'),
    
    # Password Management
    path('change-password/', views.change_password, name='change-password'),
    path('password-reset/request/', views.password_reset_request, name='password-reset-request'),
    path('password-reset/verify/', views.password_reset_verify, name='password-reset-verify'),
    
    # Profile Management
    path('profile/customer/', views.customer_profile, name='customer-profile'),
    path('profile/vendor/', views.vendor_profile, name='vendor-profile'),
    path('current-user/', views.admin_get_current_user, name='current-user'),  # ADD THIS
    
    # Media Upload Endpoints
    path('profile/picture/', views.profile_picture_upload, name='profile-picture-upload'),
    path('vendor/documents/upload/', views.vendor_document_upload, name='vendor-document-upload'),
    
    # Admin Routes
    path('admin/dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin/users/', views.admin_users_list, name='admin-users-list'),
    path('admin/users/<uuid:user_id>/deactivate/', views.admin_deactivate_user, name='admin-deactivate-user'),  # ADD THIS
    path('admin/users/<uuid:user_id>/activate/', views.admin_activate_user, name='admin-activate-user'),  # ADD THIS
    path('admin/vendors/<uuid:vendor_id>/verify/', views.admin_verify_vendor, name='admin-verify-vendor'),
    path('admin/drivers/<uuid:driver_id>/verify/', views.admin_verify_driver, name='admin-verify-driver'),  # ADD THIS

    path('admin/analytics/', views.admin_analytics, name='admin-analytics'),
    path('admin/pending-verifications/', views.admin_pending_verifications, name='admin-pending-verifications'),
    path('admin/verified-vendors/', views.admin_verified_vendors, name='admin-verified-vendors'),
    
    # Vendor Management
    path('admin/vendors/<uuid:vendor_id>/', views.admin_vendor_detail, name='admin-vendor-detail'),
    path('admin/vendors/<uuid:vendor_id>/update/', views.admin_update_vendor, name='admin-update-vendor'),
    path('admin/vendors/<uuid:vendor_id>/reject/', views.admin_reject_vendor, name='admin-reject-vendor'),
]