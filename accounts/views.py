from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from .models import User, Customer, Vendor, Driver, AdminProfile, SecurityQuestion, UserSecurityAnswer
from .serializers import (
    CustomerRegistrationSerializer, VendorRegistrationSerializer,
    LoginSerializer, CustomerProfileSerializer, VendorProfileSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetVerifySerializer, SecurityQuestionSerializer,
    UserSerializer, DriverProfileSerializer, AdminProfileSerializer,
    ProfilePictureSerializer
)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def security_questions(request):
    """Get all active security questions"""
    questions = SecurityQuestion.objects.filter(is_active=True)
    serializer = SecurityQuestionSerializer(questions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
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
@authentication_classes([])
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

# accounts/views.py
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def user_login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        # ✅ Safely get profile based on user_type
        profile_data = {}
        if user.user_type == 'customer':
            try:
                profile_data = CustomerProfileSerializer(user.customer).data
            except Customer.DoesNotExist:
                return Response(
                    {'error': 'Customer profile missing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif user.user_type == 'vendor':
            try:
                profile_data = VendorProfileSerializer(user.vendor).data
            except Vendor.DoesNotExist:
                return Response(
                    {'error': 'Vendor profile missing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif user.user_type == 'driver':
            try:
                profile_data = DriverProfileSerializer(user.driver).data
            except Driver.DoesNotExist:
                return Response(
                    {'error': 'Driver profile missing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        elif user.user_type == 'admin':
            try:
                profile_data = AdminProfileSerializer(user.admin_profile).data
            except AdminProfile.DoesNotExist:
                return Response(
                    {'error': 'Admin profile missing'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

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
    return render(request, 'home.html')
