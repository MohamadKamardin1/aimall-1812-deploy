from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    User, Customer, Vendor, Driver, AdminProfile,
    SecurityQuestion, UserSecurityAnswer
)


class UserSecurityAnswerInline(admin.TabularInline):
    """Inline admin for user security answers"""
    model = UserSecurityAnswer
    extra = 0
    readonly_fields = ['created_at']
    fields = ['question', 'answer', 'created_at']


class CustomerInline(admin.StackedInline):
    """Inline admin for customer profile"""
    model = Customer
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    fields = ['names', 'address', 'date_of_birth', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


class VendorInline(admin.StackedInline):
    """Inline admin for vendor profile"""
    model = Vendor
    can_delete = False
    verbose_name_plural = 'Vendor Profile'
    fields = [
        'names', 'business_name', 'business_license', 'zanzibar_id',
        'business_address', 'business_description',
        'license_document_preview', 'id_document_preview',
        'is_verified', 'verified_at', 'created_at', 'updated_at'
    ]
    readonly_fields = [
        'license_document_preview', 'id_document_preview',
        'created_at', 'updated_at', 'verified_at'
    ]

    def license_document_preview(self, obj):
        if obj.license_document:
            return format_html(
                '<a href="{}" target="_blank">View License Document</a>',
                obj.license_document.url
            )
        return "No document uploaded"
    license_document_preview.short_description = "License Document"

    def id_document_preview(self, obj):
        if obj.id_document:
            return format_html(
                '<a href="{}" target="_blank">View ID Document</a>',
                obj.id_document.url
            )
        return "No document uploaded"
    id_document_preview.short_description = "ID Document"


class DriverInline(admin.StackedInline):
    """Inline admin for driver profile"""
    model = Driver
    can_delete = False
    verbose_name_plural = 'Driver Profile'
    fk_name = 'user'  # Specify which ForeignKey is the parent
    fields = [
        'names', 'license_number', 'vehicle_type', 'vehicle_plate',
        'license_image_preview', 'vehicle_image_preview',
        'is_approved', 'approved_at', 'approved_by', 'rejection_reason',
        'is_available', 'is_verified', 'verified_at',
        'created_at', 'updated_at'
    ]
    readonly_fields = [
        'license_image_preview', 'vehicle_image_preview',
        'created_at', 'updated_at', 'verified_at', 'approved_at'
    ]

    def license_image_preview(self, obj):
        if obj.license_image:
            return format_html(
                '<a href="{}" target="_blank">View License</a>',
                obj.license_image.url
            )
        return "No image uploaded"
    license_image_preview.short_description = "License Image"

    def vehicle_image_preview(self, obj):
        if obj.vehicle_image:
            return format_html(
                '<a href="{}" target="_blank">View Vehicle</a>',
                obj.vehicle_image.url
            )
        return "No image uploaded"
    vehicle_image_preview.short_description = "Vehicle Image"


class AdminProfileInline(admin.StackedInline):
    """Inline admin for admin profile"""
    model = AdminProfile
    can_delete = False
    verbose_name_plural = 'Admin Profile'
    fields = [
        'names', 'department', 'position',
        'can_manage_users', 'can_manage_vendors',
        'can_manage_order', 'can_manage_content',
        'created_at', 'updated_at'
    ]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin with enhanced features"""
    list_display = [
        'phone_number', 'email', 'user_type', 'is_active',
        'is_verified', 'date_joined', 'last_login', 'profile_picture_preview'
    ]
    list_filter = [
        'user_type', 'is_active', 'is_staff', 'is_superuser',
        'is_verified', 'date_joined'
    ]
    search_fields = ['phone_number', 'email', 'customer__names', 'vendor__names', 'driver__names']
    ordering = ['-date_joined']
    readonly_fields = [
        'date_joined', 'last_login', 'profile_picture_preview',
        'security_questions_list', 'user_profile_link'
    ]
    fieldsets = (
        ('Authentication', {
            'fields': ('phone_number', 'password', 'user_type')
        }),
        ('Personal Info', {
            'fields': ('email', 'profile_picture', 'profile_picture_preview')
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'is_verified', 'groups', 'user_permissions'
            )
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login')
        }),
        ('Security', {
            'fields': ('security_questions_list',)
        }),
        ('Profile Links', {
            'fields': ('user_profile_link',)
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'user_type', 'password1', 'password2'),
        }),
    )
    inlines = [UserSecurityAnswerInline]

    def get_inline_instances(self, request, obj=None):
        """Show appropriate inline based on user type"""
        if not obj:
            return []
        
        inlines = []
        if obj.user_type == 'customer':
            inlines.append(CustomerInline(self.model, self.admin_site))
        elif obj.user_type == 'vendor':
            inlines.append(VendorInline(self.model, self.admin_site))
        elif obj.user_type == 'driver':
            inlines.append(DriverInline(self.model, self.admin_site))
        elif obj.user_type == 'admin':
            inlines.append(AdminProfileInline(self.model, self.admin_site))
        
        return inlines

    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.profile_picture.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; border-radius: 50%; background: #0D8ABC; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold;">{}</div>',
            obj.get_initials()
        )
    profile_picture_preview.short_description = 'Profile Picture'

    def security_questions_list(self, obj):
        questions = obj.usersecurityanswer_set.all()
        if questions:
            return format_html(
                '<br>'.join([f"• {answer.question.question}" for answer in questions])
            )
        return "No security questions set"
    security_questions_list.short_description = 'Security Questions'

    def user_profile_link(self, obj):
        """Link to the specific user profile"""
        if obj.user_type == 'customer' and hasattr(obj, 'customer'):
            return format_html(
                '<a href="{}">View Customer Profile</a>',
                reverse('admin:accounts_customer_change', args=[obj.customer.pk])
            )
        elif obj.user_type == 'vendor' and hasattr(obj, 'vendor'):
            return format_html(
                '<a href="{}">View Vendor Profile</a>',
                reverse('admin:accounts_vendor_change', args=[obj.vendor.pk])
            )
        elif obj.user_type == 'driver' and hasattr(obj, 'driver'):
            return format_html(
                '<a href="{}">View Driver Profile</a>',
                reverse('admin:accounts_driver_change', args=[obj.driver.pk])
            )
        elif obj.user_type == 'admin' and hasattr(obj, 'admin_profile'):
            return format_html(
                '<a href="{}">View Admin Profile</a>',
                reverse('admin:accounts_adminprofile_change', args=[obj.admin_profile.pk])
            )
        return "No profile available"
    user_profile_link.short_description = 'Profile Management'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'vendor', 'driver', 'admin_profile'
        )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Customer Admin with enhanced features"""
    list_display = [
        'names', 'user_phone', 'user_email', 'date_of_birth',
        'created_at', 'profile_picture_preview'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['names', 'user__phone_number', 'user__email']
    readonly_fields = [
        'user_link', 'created_at', 'updated_at', 'profile_picture_preview'
    ]
    fieldsets = (
        ('User Information', {
            'fields': ('user_link', 'profile_picture_preview')
        }),
        ('Personal Information', {
            'fields': ('names', 'address', 'date_of_birth')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Phone Number'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            obj.user.phone_number
        )
    user_link.short_description = 'User Account'

    def profile_picture_preview(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            UserAdmin.profile_picture_preview(self, obj.user)
        )
    profile_picture_preview.short_description = 'Profile Picture'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """Vendor Admin with verification features"""
    list_display = [
        'business_name', 'names', 'user_phone', 'is_verified',
        'verified_at', 'created_at', 'verification_status'
    ]
    list_filter = ['is_verified', 'created_at', 'verified_at']
    search_fields = [
        'names', 'business_name', 'business_license',
        'zanzibar_id', 'user__phone_number'
    ]
    readonly_fields = [
        'user_link', 'created_at', 'updated_at', 'verified_at',
        'license_document_link', 'id_document_link'
    ]
    list_editable = ['is_verified']
    actions = ['verify_vendors', 'unverify_vendors']

    fieldsets = (
        ('User Information', {
            'fields': ('user_link',)
        }),
        ('Business Information', {
            'fields': (
                'names', 'business_name', 'business_license',
                'zanzibar_id', 'business_address', 'business_description'
            )
        }),
        ('Documents', {
            'fields': (
                'license_document', 'license_document_link',
                'id_document', 'id_document_link'
            )
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Phone Number'

    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            obj.user.phone_number
        )
    user_link.short_description = 'User Account'

    def license_document_link(self, obj):
        if obj.license_document:
            return format_html(
                '<a href="{}" target="_blank">View License Document</a>',
                obj.license_document.url
            )
        return "No document uploaded"
    license_document_link.short_description = "Current License Document"

    def id_document_link(self, obj):
        if obj.id_document:
            return format_html(
                '<a href="{}" target="_blank">View ID Document</a>',
                obj.id_document.url
            )
        return "No document uploaded"
    id_document_link.short_description = "Current ID Document"

    def verification_status(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">⏳ Pending</span>'
        )
    verification_status.short_description = 'Status'

    def verify_vendors(self, request, queryset):
        updated = queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f'{updated} vendors verified successfully.')
    verify_vendors.short_description = "Verify selected vendors"

    def unverify_vendors(self, request, queryset):
        updated = queryset.update(is_verified=False, verified_at=None)
        self.message_user(request, f'{updated} vendors unverified.')
    unverify_vendors.short_description = "Unverify selected vendors"

    def save_model(self, request, obj, form, change):
        if 'is_verified' in form.changed_data and obj.is_verified:
            obj.verified_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    """Driver Admin with verification and approval features"""
    list_display = [
        'names', 'vehicle_plate', 'vehicle_type', 'user_phone',
        'approval_status_display', 'is_verified', 'is_available',
        'approved_at', 'created_at'
    ]
    list_filter = [
        'is_approved', 'is_verified', 'is_available',
        'vehicle_type', 'created_at'
    ]
    search_fields = [
        'names', 'license_number', 'vehicle_plate',
        'vehicle_type', 'user__phone_number'
    ]
    readonly_fields = [
        'user_link', 'created_at', 'updated_at', 'verified_at',
        'approved_at', 'license_image_link', 'vehicle_image_link',
        'approval_timeline'
    ]
    list_editable = ['is_verified', 'is_available']
    actions = [
        'approve_drivers', 'reject_drivers_action',
        'verify_drivers', 'unverify_drivers',
        'make_available', 'make_unavailable'
    ]

    fieldsets = (
        ('User Information', {
            'fields': ('user_link',)
        }),
        ('Personal Information', {
            'fields': ('names',)
        }),
        ('Vehicle Information', {
            'fields': ('license_number', 'vehicle_type', 'vehicle_plate')
        }),
        ('Documents', {
            'fields': (
                'license_image', 'license_image_link',
                'vehicle_image', 'vehicle_image_link'
            )
        }),
        ('Approval Status', {
            'fields': (
                'is_approved', 'rejection_reason',
                'approval_timeline'
            ),
            'classes': ('collapse',),
        }),
        ('Driver Status', {
            'fields': ('is_available', 'is_verified', 'verified_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Phone Number'
    
    def user_email(self, obj):
        return obj.user.email or '-'
    user_email.short_description = 'Email'

    def user_link(self, obj):
        return format_html(
            '<a href="{}">{} ({})</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            obj.user.phone_number,
            obj.user.email or 'No email'
        )
    user_link.short_description = 'User Account'

    def license_image_link(self, obj):
        if obj.license_image:
            return format_html(
                '<a href="{}" target="_blank">View License</a>',
                obj.license_image.url
            )
        return "No image uploaded"
    license_image_link.short_description = "Current License Image"

    def vehicle_image_link(self, obj):
        if obj.vehicle_image:
            return format_html(
                '<a href="{}" target="_blank">View Vehicle</a>',
                obj.vehicle_image.url
            )
        return "No image uploaded"
    vehicle_image_link.short_description = "Current Vehicle Image"

    def approval_status_display(self, obj):
        """Display approval status with color coding"""
        colors = {
            'approved': 'green',
            'pending': 'orange',
            'rejected': 'red'
        }
        labels = {
            'approved': '✓ Approved',
            'pending': '⏳ Pending',
            'rejected': '✗ Rejected'
        }
        color = colors.get(obj.is_approved, 'gray')
        label = labels.get(obj.is_approved, obj.get_is_approved_display())
        
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 5px 10px; '
            'background: {}; border-radius: 3px;">{}</span>',
            color,
            'rgba(0,0,0,0.05)',
            label
        )
    approval_status_display.short_description = 'Approval Status'

    def approval_timeline(self, obj):
        """Show approval timeline"""
        timeline = f'<strong>Created:</strong> {obj.created_at.strftime("%Y-%m-%d %H:%M")}<br>'
        
        if obj.approved_at:
            timeline += f'<strong>Approved:</strong> {obj.approved_at.strftime("%Y-%m-%d %H:%M")}<br>'
            if obj.approved_by:
                timeline += f'<strong>Approved by:</strong> {obj.approved_by.phone_number}<br>'
        
        if obj.rejection_reason:
            timeline += f'<strong>Rejection Reason:</strong> {obj.rejection_reason}<br>'
        
        return format_html(timeline) if timeline else "No approval yet"
    approval_timeline.short_description = 'Approval Timeline'

    def verification_status(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">⏳ Pending</span>'
        )
    verification_status.short_description = 'Verification Status'

    def approve_drivers(self, request, queryset):
        """Bulk approve drivers"""
        updated = queryset.update(
            is_approved='approved',
            approved_at=timezone.now(),
            approved_by=request.user
        )
        self.message_user(request, f'{updated} drivers approved successfully.')
    approve_drivers.short_description = "✓ Approve selected drivers"

    def reject_drivers_action(self, request, queryset):
        """Bulk reject drivers - requires reason"""
        # This is a simple rejection without reason
        # For better UX, implement a form-based action
        updated = queryset.update(
            is_approved='rejected',
            approved_at=timezone.now(),
            approved_by=request.user,
            rejection_reason='Rejected by admin'
        )
        self.message_user(request, f'{updated} drivers rejected.')
    reject_drivers_action.short_description = "✗ Reject selected drivers"

    def verify_drivers(self, request, queryset):
        updated = queryset.update(is_verified=True, verified_at=timezone.now())
        self.message_user(request, f'{updated} drivers verified successfully.')
    verify_drivers.short_description = "Mark as verified"

    def unverify_drivers(self, request, queryset):
        updated = queryset.update(is_verified=False, verified_at=None)
        self.message_user(request, f'{updated} drivers unverified.')
    unverify_drivers.short_description = "Mark as unverified"

    def make_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} drivers marked as available.')
    make_available.short_description = "Mark as available"

    def make_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} drivers marked as unavailable.')
    make_unavailable.short_description = "Mark as unavailable"

    def save_model(self, request, obj, form, change):
        """Auto-set approved_by when status changes to approved"""
        if 'is_approved' in form.changed_data:
            if obj.is_approved == 'approved' and not obj.approved_by:
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """Admin Profile Admin"""
    list_display = [
        'names', 'department', 'position', 'user_phone',
        'permissions_summary', 'created_at'
    ]
    list_filter = ['department', 'created_at']
    search_fields = ['names', 'department', 'position', 'user__phone_number']
    readonly_fields = ['user_link', 'created_at', 'updated_at']

    fieldsets = (
        ('User Information', {
            'fields': ('user_link',)
        }),
        ('Profile Information', {
            'fields': ('names', 'department', 'position')
        }),
        ('Permissions', {
            'fields': (
                'can_manage_users', 'can_manage_vendors',
                'can_manage_order', 'can_manage_content'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Phone Number'

    def user_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            obj.user.phone_number
        )
    user_link.short_description = 'User Account'

    def permissions_summary(self, obj):
        permissions = []
        if obj.can_manage_users:
            permissions.append("Users")
        if obj.can_manage_vendors:
            permissions.append("Vendors")
        if obj.can_manage_order:
            permissions.append("order")
        if obj.can_manage_content:
            permissions.append("Content")
        
        if permissions:
            return ", ".join(permissions)
        return "No permissions"
    permissions_summary.short_description = 'Permissions'


@admin.register(SecurityQuestion)
class SecurityQuestionAdmin(admin.ModelAdmin):
    """Security Question Admin"""
    list_display = ['question', 'is_active', 'created_at', 'users_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['question']
    list_editable = ['is_active']
    actions = ['activate_questions', 'deactivate_questions']

    def users_count(self, obj):
        return obj.usersecurityanswer_set.count()
    users_count.short_description = 'Users Using'

    def activate_questions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} security questions activated.')
    activate_questions.short_description = "Activate selected questions"

    def deactivate_questions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} security questions deactivated.')
    deactivate_questions.short_description = "Deactivate selected questions"


@admin.register(UserSecurityAnswer)
class UserSecurityAnswerAdmin(admin.ModelAdmin):
    """User Security Answer Admin"""
    list_display = ['user_phone', 'question', 'answer_preview', 'created_at']
    list_filter = ['question', 'created_at']
    search_fields = ['user__phone_number', 'question__question', 'answer']
    readonly_fields = ['created_at']

    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'User Phone'

    def answer_preview(self, obj):
        return obj.answer[:50] + '...' if len(obj.answer) > 50 else obj.answer
    answer_preview.short_description = 'Answer'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'question')


# Admin site customization
admin.site.site_header = "AI Mall Zanzibar Administration"
admin.site.site_title = "AI Mall Admin"
admin.site.index_title = "Welcome to AI Mall Administration Portal"