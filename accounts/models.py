from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils import timezone
from cloudinary.models import CloudinaryField
import uuid

def user_profile_picture_path(instance, filename):
    """Generate path for profile pictures in Cloudinary"""
    ext = filename.split('.')[-1]
    filename = f"profile_{uuid.uuid4()}.{ext}"
    return f"ai_mall/users/user_{instance.user.id}/profile/{filename}"

def vendor_document_path(instance, filename):
    """Generate path for vendor documents in Cloudinary"""
    ext = filename.split('.')[-1]
    filename = f"document_{uuid.uuid4()}.{ext}"
    return f"ai_mall/vendors/{instance.user.id}/documents/{filename}"

def driver_document_path(instance, filename):
    """Generate path for driver documents in Cloudinary"""
    ext = filename.split('.')[-1]
    filename = f"document_{uuid.uuid4()}.{ext}"
    return f"ai_mall/drivers/{instance.user.id}/documents/{filename}"

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')
        
        return self.create_user(phone_number, password, **extra_fields)

class SecurityQuestion(models.Model):
    question = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'security_questions'
    
    def __str__(self):
        return self.question

class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('driver', 'Driver'),
        ('admin', 'Admin'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_regex = RegexValidator(
        regex=r'^\+255\d{9}$',
        message="Phone number must be in the format: '+255xxxxxxxxx'. 12 digits required."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=13,
        unique=True
    )
    email = models.EmailField(blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    
    # Cloudinary Field for Profile Picture
    profile_picture = CloudinaryField(
        'profile_picture',
        folder='ai_mall/users/profile_pictures/',
        null=True,
        blank=True,
        transformation=[
            {'width': 300, 'height': 300, 'crop': 'fill'},
            {'quality': 'auto:good'},
        ],
        format='webp'  # Convert to webp for better performance
    )
    
    # Security Questions for Password Recovery
    security_questions = models.ManyToManyField(
        SecurityQuestion,
        through='UserSecurityAnswer',
        through_fields=('user', 'question')
    )
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['user_type']
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.phone_number} ({self.user_type})"
    
    def get_initials(self):
        """Get initials for default profile picture"""
        try:
            if self.user_type == 'customer':
                names = self.customer.names.split()
            elif self.user_type == 'vendor':
                names = self.vendor.names.split()
            elif self.user_type == 'driver':
                names = self.driver.names.split()
            elif self.user_type == 'admin':
                names = self.admin_profile.names.split()
            else:
                names = ['A', 'I']  # AI Mall initials
        except:
            names = ['U', 'S']  # User initials as fallback
        
        if len(names) >= 2:
            return f"{names[0][0]}{names[-1][0]}".upper()
        elif len(names) == 1:
            return names[0][:2].upper()
        else:
            return "AI"
    
    def get_profile_picture_url(self):
        """Get profile picture URL or generate initials avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        
        # Generate initials-based avatar URL (using external service)
        initials = self.get_initials()
        return f"https://ui-avatars.com/api/?name={initials}&background=0D8ABC&color=fff&size=300&bold=true&font-size=0.8"
    
    def delete_profile_picture(self):
        """Delete profile picture from Cloudinary"""
        if self.profile_picture:
            self.profile_picture.delete()
            self.profile_picture = None
            self.save()

class UserSecurityAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(SecurityQuestion, on_delete=models.CASCADE)
    answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_security_answers'
        unique_together = ('user', 'question')
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.question.question}"

class Customer(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='customer'
    )
    names = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
    
    def __str__(self):
        return self.names

class Vendor(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='vendor'
    )
    names = models.CharField(max_length=255)
    business_license = models.CharField(max_length=100, unique=True)
    zanzibar_id = models.CharField(max_length=100, unique=True)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField()
    business_description = models.TextField(blank=True)
    
    # Cloudinary Fields for Vendor Documents
    license_document = CloudinaryField(
        'license_document',
        folder='ai_mall/vendors/documents/',
        null=True,
        blank=True
    )
    id_document = CloudinaryField(
        'id_document',
        folder='ai_mall/vendors/documents/',
        null=True,
        blank=True
    )
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendors'
    
    def __str__(self):
        return f"{self.names} - {self.business_name}"

class Driver(models.Model):
    APPROVAL_STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='driver'
    )
    names = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    vehicle_type = models.CharField(max_length=100)
    vehicle_plate = models.CharField(max_length=20, unique=True)
    
    # Cloudinary Fields for Driver Documents
    license_image = CloudinaryField(
        'license_image',
        folder='ai_mall/drivers/documents/',
        null=True,
        blank=True
    )
    vehicle_image = CloudinaryField(
        'vehicle_image',
        folder='ai_mall/drivers/documents/',
        null=True,
        blank=True
    )
    
    # Approval workflow
    is_approved = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
        help_text='Driver account approval status'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_drivers'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'drivers'
    
    def __str__(self):
        return f"{self.names} - {self.vehicle_plate}"

class AdminProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='admin_profile'
    )
    names = models.CharField(max_length=255)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    can_manage_users = models.BooleanField(default=True)
    can_manage_vendors = models.BooleanField(default=True)
    can_manage_order = models.BooleanField(default=True)
    can_manage_content = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'admin_profiles'
    
    def __str__(self):
        return f"{self.names} (Admin)"