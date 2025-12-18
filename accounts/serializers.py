from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.files.images import get_image_dimensions
from .models import User, Customer, Vendor, Driver, AdminProfile, SecurityQuestion, UserSecurityAnswer

class SecurityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityQuestion
        fields = ('id', 'question')

class UserSecurityAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question', read_only=True)
    
    class Meta:
        model = UserSecurityAnswer
        fields = ('id', 'question', 'question_text', 'answer')
        extra_kwargs = {
            'answer': {'write_only': True}
        }

class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'phone_number', 'email', 'user_type', 
            'profile_picture', 'profile_picture_url', 'initials',
            'is_verified', 'date_joined'
        )
        extra_kwargs = {
            'profile_picture': {'write_only': True}
        }
    
    def get_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()
    
    def get_initials(self, obj):
        return obj.get_initials()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
    confirm_password = serializers.CharField(required=True, min_length=6)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        
        validate_password(attrs['new_password'])
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        return value

class PasswordResetVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    answers = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
    new_password = serializers.CharField(min_length=6)
    confirm_password = serializers.CharField(min_length=6)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        
        validate_password(attrs['new_password'])
        return attrs

class ProfilePictureSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('profile_picture', 'profile_picture_url')
    
    def get_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()
    
    def validate_profile_picture(self, value):
        """
        Validate profile picture before uploading to Cloudinary
        """
        if value:
            # Check file size (5MB limit)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image file too large ( > 5MB )")
            
            # Check file extension
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = value.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise serializers.ValidationError("Unsupported file extension.")
            
            # Check image dimensions
            try:
                width, height = get_image_dimensions(value)
                if width < 100 or height < 100:
                    raise serializers.ValidationError("Image dimensions too small. Minimum 100x100 pixels.")
                if width > 2000 or height > 2000:
                    raise serializers.ValidationError("Image dimensions too large. Maximum 2000x2000 pixels.")
            except AttributeError:
                # Can't get dimensions, might not be an image
                raise serializers.ValidationError("Invalid image file.")
        
        return value

# Enhanced registration serializers with security questions
class CustomerRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    phone_number = serializers.CharField(max_length=13, write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, allow_blank=True)
    security_answers = UserSecurityAnswerSerializer(many=True, write_only=True)
    
    class Meta:
        model = Customer
        fields = (
            'user', 'names', 'phone_number', 'email', 'address', 'date_of_birth',
            'password', 'password_confirm', 'security_answers'
        )
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number already exists.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        security_answers = attrs.get('security_answers', [])
        if len(security_answers) < 2:
            raise serializers.ValidationError({"security_answers": "Please provide at least 2 security questions."})
        if len(security_answers) > 4:
            raise serializers.ValidationError({"security_answers": "Maximum 4 security questions allowed."})
        
        # Check for duplicate questions
        question_ids = [answer['question'].id for answer in security_answers]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError({"security_answers": "Duplicate security questions are not allowed."})
        
        return attrs
    
    def create(self, validated_data):
        security_answers_data = validated_data.pop('security_answers')
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        phone_number = validated_data.pop('phone_number')
        email = validated_data.get('email', '')
        
        user = User.objects.create_user(
            phone_number=phone_number,
            email=email,
            user_type='customer',
            password=password
        )
        
        customer = Customer.objects.create(
            user=user,
            names=validated_data['names'],
            address=validated_data.get('address', ''),
            date_of_birth=validated_data.get('date_of_birth')
        )
        
        # Create security answers
        for answer_data in security_answers_data:
            UserSecurityAnswer.objects.create(
                user=user,
                question=answer_data['question'],
                answer=answer_data['answer'].lower().strip()
            )
        
        return customer

class VendorRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    phone_number = serializers.CharField(max_length=13, write_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    security_answers = UserSecurityAnswerSerializer(many=True, write_only=True)
    
    class Meta:
        model = Vendor
        fields = (
            'user', 'names', 'phone_number', 'email', 'business_license',
            'zanzibar_id', 'business_name', 'business_address', 'business_description',
            'license_document', 'id_document',
            'password', 'password_confirm', 'security_answers'
        )
    
    def validate_phone_number(self, value):
        if not value.startswith('+255'):
            raise serializers.ValidationError("Phone number must start with +255")
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number already exists.")
        return value
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        security_answers = attrs.get('security_answers', [])
        if len(security_answers) < 2:
            raise serializers.ValidationError({"security_answers": "Please provide at least 2 security questions."})
        
        return attrs
    
    def create(self, validated_data):
        security_answers_data = validated_data.pop('security_answers')
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        phone_number = validated_data.pop('phone_number')
        email = validated_data.pop('email')
        
        user = User.objects.create_user(
            phone_number=phone_number,
            email=email,
            user_type='vendor',
            password=password
        )
        
        vendor = Vendor.objects.create(
            user=user,
            names=validated_data['names'],
            business_license=validated_data['business_license'],
            zanzibar_id=validated_data['zanzibar_id'],
            business_name=validated_data['business_name'],
            business_address=validated_data['business_address'],
            business_description=validated_data.get('business_description', ''),
            license_document=validated_data.get('license_document'),
            id_document=validated_data.get('id_document')
        )
        
        # Create security answers
        for answer_data in security_answers_data:
            UserSecurityAnswer.objects.create(
                user=user,
                question=answer_data['question'],
                answer=answer_data['answer'].lower().strip()
            )
        
        return vendor

class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True)
    user_type = serializers.CharField(required=False)
    
    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')
        user_type = attrs.get('user_type')
        
        if phone_number and password:
            user = authenticate(phone_number=phone_number, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid phone number or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is disabled.')
            
            if user_type and user.user_type != user_type:
                raise serializers.ValidationError(f'User is not a {user_type}.')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include "phone_number" and "password".')

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Customer
        fields = '__all__'

class VendorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Vendor
        fields = '__all__'

class DriverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Driver
        fields = '__all__'

class AdminProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = AdminProfile
        fields = '__all__'

class DriverRegistrationSerializer(serializers.Serializer):
    """Serializer for driver self-registration"""
    phone_number = serializers.CharField(max_length=13)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)
    names = serializers.CharField(max_length=255)
    license_number = serializers.CharField(max_length=100)
    vehicle_type = serializers.CharField(max_length=100)
    vehicle_plate = serializers.CharField(max_length=20)
    
    def validate_phone_number(self, value):
        # Validate phone number format
        import re
        if not re.match(r'^\+255\d{9}$', value):
            raise serializers.ValidationError(
                "Phone number must be in format: '+255xxxxxxxxx' (12 digits total)"
            )
        
        # Check if phone already exists
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value
    
    def validate_email(self, value):
        # Check if email already exists
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def validate_license_number(self, value):
        # Check if license already exists
        if Driver.objects.filter(license_number=value).exists():
            raise serializers.ValidationError("This license number is already registered.")
        return value
    
    def validate_vehicle_plate(self, value):
        # Check if vehicle plate already exists
        if Driver.objects.filter(vehicle_plate=value).exists():
            raise serializers.ValidationError("This vehicle plate is already registered.")
        return value
    
    def validate(self, data):
        # Validate passwords match
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data
    
    def create(self, validated_data):
        """Create new driver account (pending approval)"""
        # Remove confirm_password as it's not needed for User model
        validated_data.pop('confirm_password')
        
        # Extract driver-specific fields
        driver_fields = {
            'names': validated_data.pop('names'),
            'license_number': validated_data.pop('license_number'),
            'vehicle_type': validated_data.pop('vehicle_type'),
            'vehicle_plate': validated_data.pop('vehicle_plate'),
        }
        
        # Create User
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type='driver'
        )
        
        # Create Driver profile with pending approval
        driver = Driver.objects.create(
            user=user,
            is_approved='pending',
            **driver_fields
        )
        
        return driver