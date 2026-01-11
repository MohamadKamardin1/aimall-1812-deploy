# admin_dashboard_api/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import csv
from django.http import HttpResponse
import json

# Import models
from django.contrib.auth.models import Group, Permission
from accounts.models import User, Customer, Vendor, Driver, AdminProfile, SecurityQuestion, UserSecurityAnswer
from products.models import Category, ProductTemplate, ProductVariant, MeasurementUnitType, MeasurementUnit
from order.models import Order, OrderItem, OrderStatusUpdate
from markets.models import Market, MarketDay, MarketZone
from location.models import DeliveryZone, DeliveryFeeConfig, DeliveryTimeSlot, CustomerAddress

# Import serializers
from .serializers import *

class IsAdminAPIUser(permissions.BasePermission):
    """Custom permission for API admin users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'

class APIPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

# ============================================
# AUTHENTICATION API
# ============================================

class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')
        
        if not phone or not password:
            return Response({
                'success': False,
                'error': 'Phone and password are required'
            }, status=400)
        
        user = authenticate(username=phone, password=password)
        
        if user and user.is_active and user.user_type == 'admin':
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Get admin profile info
            admin_name = user.phone_number
            if hasattr(user, 'admin_profile'):
                admin_name = user.admin_profile.names
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'phone': user.phone_number,
                    'email': user.email or '',
                    'user_type': user.user_type,
                    'name': admin_name,
                    'is_active': user.is_active,
                    'is_verified': user.is_verified
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        
        return Response({
            'success': False,
            'error': 'Invalid credentials or admin access required'
        }, status=401)

class AdminLogoutView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def post(self, request):
        logout(request)
        return Response({
            'success': True,
            'message': 'Logged out successfully'
        })

class AdminMeView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        user = request.user
        
        # Get admin profile info
        admin_name = user.phone_number
        if hasattr(user, 'admin_profile'):
            admin_name = user.admin_profile.names
            
        return Response({
            'id': str(user.id),
            'phone': user.phone_number,
            'email': user.email or '',
            'username': admin_name, # Frontend expects username
            'user_type': user.user_type,
            'name': admin_name,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'role': 'Admin' # Frontend might expect role
        })

# ============================================
# DASHBOARD API
# ============================================

class DashboardStatsView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            
            # Base querysets
            orders = Order.objects.all()
            today_orders = orders.filter(created_at__date=today)
            
            # Calculate counts
            total_orders = orders.count()
            orders_today = today_orders.count()
            
            # Status based counts
            # In Transit: confirmed, preparing, ready, assigned, picked_up, on_the_way
            in_transit = orders.filter(
                status__in=['confirmed', 'preparing', 'ready', 'assigned', 'picked_up', 'on_the_way']
            ).count()
            
            # Out for Delivery: specifically 'on_the_way'
            out_for_delivery = orders.filter(status='on_the_way').count()
            
            # Delivered
            delivered = orders.filter(status='delivered').count()
            delivered_today = today_orders.filter(status='delivered').count()
            
            # Other entities
            total_customers = Customer.objects.count()
            total_sales_orders = total_orders
            total_invoices = 0 
            
            # Status Counts for Pie Chart
            status_counts = list(orders.values('status').annotate(count=Count('status')))
            
            # Payment Method breakdown
            payment_method_counts = list(orders.values('payment_method').annotate(count=Count('payment_method')))
            
            # Regional distribution based on CustomerAddress.region
            # We filter address region for 'zanzibar' (case insensitive)
            orders_zanzibar = orders.filter(
                delivery_address__region__icontains='zanzibar'
            ).count()
            orders_tanzania = total_orders - orders_zanzibar

            # Daily Stats for Line Chart (Volume)
            daily_stats = []
            for i in range(7):
                date = today - timedelta(days=i)
                count = orders.filter(created_at__date=date).count()
                daily_stats.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': count
                })
            daily_stats.reverse()
            
            # Map recent orders
            recent_orders_qs = orders.select_related('customer').order_by('-created_at')[:5]
            recent_orders = []
            for order in recent_orders_qs:
                customer_name = order.customer.phone_number
                if hasattr(order.customer, 'customer'):
                    customer_name = order.customer.customer.names
                    
                recent_orders.append({
                    'id': str(order.id),
                    'tracking_id': order.order_number,
                    'customer_name': customer_name,
                    'status': order.status,
                    'status_display': order.get_status_display()
                })
            
            stats = {
                'total_orders': total_orders,
                'orders_today': orders_today,
                'delivered_today': delivered_today,
                'in_transit': in_transit,
                'out_for_delivery': out_for_delivery,
                'delivered': delivered,
                'total_customers': total_customers,
                'total_sales_orders': total_sales_orders,
                'total_invoices': total_invoices,
                'status_counts': status_counts,
                'payment_method_counts': payment_method_counts,
                'recent_orders': recent_orders,
                'orders_zanzibar': orders_zanzibar,
                'orders_tanzania': orders_tanzania,
                'daily_stats': daily_stats
            }
            
            return Response({
                'success': True,
                'data': stats
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class DashboardOverviewView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            # Get date range from query params
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Daily stats
            daily_stats = []
            for i in range(days):
                date = end_date - timedelta(days=i)
                
                # Orders for the day
                day_orders = Order.objects.filter(created_at__date=date)
                day_order_count = day_orders.count()
                
                # Revenue for the day
                day_revenue = day_orders.filter(
                    status__in=['completed', 'delivered']
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                
                # New users for the day
                new_users = User.objects.filter(date_joined__date=date).count()
                
                daily_stats.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'orders': day_order_count,
                    'revenue': float(day_revenue),
                    'new_users': new_users
                })
            
            # Order status distribution
            status_distribution = []
            for status_code, status_name in Order.ORDER_STATUS:
                count = Order.objects.filter(status=status_code).count()
                if count > 0:
                    status_distribution.append({
                        'status': status_name,
                        'count': count
                    })
            
            # Top products
            top_products = ProductTemplate.objects.annotate(
                order_count=Count('variants__order_items__order', distinct=True)
            ).filter(order_count__gt=0).order_by('-order_count')[:10]
            
            overview = {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'days': days
                },
                'daily_stats': list(reversed(daily_stats)),
                'status_distribution': status_distribution,
                'top_products': ProductTemplateSerializer(top_products, many=True).data
            }
            
            return Response({
                'success': True,
                'data': overview
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

# ============================================
# USER MANAGEMENT API
# ============================================

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserListSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['phone_number', 'email', 'customer__names', 'vendor__names', 'driver__names']
    ordering_fields = ['date_joined', 'last_login']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user type
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        # Filter by status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == 'true'))
        
        # Filter by verification
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=(is_verified.lower() == 'true'))
        
        # Date range filter
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date_joined__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_joined__date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle user active status"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        return Response({
            'success': True,
            'message': f'User {"activated" if user.is_active else "deactivated"}',
            'is_active': user.is_active
        })
    
    @action(detail=True, methods=['post'])
    def toggle_verified(self, request, pk=None):
        """Toggle user verification status"""
        user = self.get_object()
        user.is_verified = not user.is_verified
        user.save()
        
        return Response({
            'success': True,
            'message': f'User {"verified" if user.is_verified else "unverified"}',
            'is_verified': user.is_verified
        })
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get user details with profile"""
        user = self.get_object()
        serializer = UserDetailSerializer(user)
        return Response({
            'success': True,
            'data': serializer.data
        })

# ============================================
# VENDOR MANAGEMENT API
# ============================================

class VendorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Vendor.objects.select_related('user').all().order_by('-created_at')
    serializer_class = VendorListSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['names', 'business_name', 'business_license', 'user__phone_number']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by verification status
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=(is_verified.lower() == 'true'))
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(user__is_active=(is_active.lower() == 'true'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        vendor = self.get_object()
        vendor.is_verified = True
        vendor.verified_at = timezone.now()
        vendor.save()
        
        return Response({
            'success': True,
            'message': 'Vendor verified successfully'
        })
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        vendor = self.get_object()
        vendor.user.is_active = False
        vendor.user.save()
        
        return Response({
            'success': True,
            'message': 'Vendor suspended successfully'
        })
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        vendor = self.get_object()
        vendor.user.is_active = True
        vendor.user.save()
        
        return Response({
            'success': True,
            'message': 'Vendor activated successfully'
        })

# ============================================
# ORDER MANAGEMENT API
# ============================================

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderListSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['order_number', 'customer__phone_number']

    def get_serializer_class(self):
        if self.action in ['retrieve', 'details']:
            return OrderDetailSerializer
        return OrderListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        order = self.get_object()
        serializer = OrderDetailSerializer(order)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        
        if not new_status:
            return Response({
                'success': False,
                'error': 'Status is required'
            }, status=400)
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Create status update
        OrderStatusUpdate.objects.create(
            order=order,
            old_status=old_status,
            new_status=new_status,
            updated_by=request.user,
            note=note
        )
        
        return Response({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'status': new_status
        })
    
    @action(detail=True, methods=['post'])
    def assign_driver(self, request, pk=None):
        order = self.get_object()
        driver_id = request.data.get('driver_id')
        
        if not driver_id:
            return Response({
                'success': False,
                'error': 'Driver ID is required'
            }, status=400)
        
        try:
            driver = Driver.objects.get(user_id=driver_id)
            order.driver = driver.user
            order.save()
            
            return Response({
                'success': True,
                'message': f'Driver {driver.names} assigned to order'
            })
        except Driver.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Driver not found'
            }, status=404)

# ============================================
# REPORTS & ANALYTICS API
# ============================================

class SalesReportView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            # Get date range from query params
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not start_date or not end_date:
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=30)
            
            # Get orders in date range
            orders = Order.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            # Calculate statistics
            total_orders = orders.count()
            completed_orders = orders.filter(status__in=['completed', 'delivered']).count()
            total_revenue = orders.filter(status__in=['completed', 'delivered']).aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            avg_order_value = total_revenue / completed_orders if completed_orders > 0 else Decimal('0')
            
            # Daily breakdown
            daily_data = []
            current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            while current_date <= end_date_obj:
                day_orders = orders.filter(created_at__date=current_date)
                day_revenue = day_orders.filter(
                    status__in=['completed', 'delivered']
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                
                daily_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'orders': day_orders.count(),
                    'revenue': float(day_revenue),
                    'completed': day_orders.filter(status__in=['completed', 'delivered']).count()
                })
                
                current_date += timedelta(days=1)
            
            return Response({
                'success': True,
                'data': {
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'summary': {
                        'total_orders': total_orders,
                        'completed_orders': completed_orders,
                        'total_revenue': float(total_revenue),
                        'avg_order_value': float(avg_order_value)
                    },
                    'daily_data': daily_data
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class UserAnalyticsView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            # User type distribution
            user_types = ['customer', 'vendor', 'driver', 'admin']
            type_distribution = []
            
            for user_type in user_types:
                count = User.objects.filter(user_type=user_type).count()
                type_distribution.append({
                    'type': user_type.title(),
                    'count': count
                })
            
            # User growth (last 30 days)
            today = timezone.now().date()
            month_ago = today - timedelta(days=30)
            
            user_growth = []
            for i in range(30):
                date = today - timedelta(days=i)
                new_users = User.objects.filter(date_joined__date=date).count()
                user_growth.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'new_users': new_users
                })
            
            # User status
            active_users = User.objects.filter(is_active=True).count()
            verified_users = User.objects.filter(is_verified=True).count()
            
            # Top customers by order count
            top_customers = Customer.objects.annotate(
                order_count=Count('user__order')
            ).filter(order_count__gt=0).order_by('-order_count')[:10]
            
            analytics = {
                'type_distribution': type_distribution,
                'user_growth': list(reversed(user_growth)),
                'status': {
                    'total': User.objects.count(),
                    'active': active_users,
                    'verified': verified_users
                },
                'top_customers': [
                    {
                        'name': customer.names,
                        'phone': customer.user.phone_number,
                        'orders': customer.order_count
                    }
                    for customer in top_customers
                ]
            }
            
            return Response({
                'success': True,
                'data': analytics
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class OrderAnalyticsView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            # Status distribution
            status_distribution = []
            for status_code, status_name in Order.ORDER_STATUS:
                count = Order.objects.filter(status=status_code).count()
                status_distribution.append({
                    'status': status_name,
                    'count': count
                })
            
            # Payment method distribution
            payment_methods = ['cash_on_delivery', 'mobile_money', 'card']
            payment_distribution = []
            for method in payment_methods:
                count = Order.objects.filter(payment_method=method).count()
                payment_distribution.append({
                    'method': method.replace('_', ' ').title(),
                    'count': count
                })
            
            # Top customers by orders
            top_customers = Customer.objects.annotate(
                order_count=Count('user__order')
            ).filter(order_count__gt=0).order_by('-order_count')[:10]
            
            # Weekly order trends (last 4 weeks)
            weekly_trends = []
            today = timezone.now().date()
            for i in range(4):
                week_start = today - timedelta(days=(i * 7) + 7)
                week_end = today - timedelta(days=i * 7)
                
                week_orders = Order.objects.filter(
                    created_at__date__gte=week_start,
                    created_at__date__lt=week_end
                ).count()
                
                weekly_trends.append({
                    'week': f'Week {4-i}',
                    'orders': week_orders
                })
            
            analytics = {
                'status_distribution': status_distribution,
                'payment_distribution': payment_distribution,
                'top_customers': [
                    {
                        'name': customer.names,
                        'phone': customer.user.phone_number,
                        'order_count': customer.order_count
                    }
                    for customer in top_customers
                ],
                'weekly_trends': list(reversed(weekly_trends))
            }
            
            return Response({
                'success': True,
                'data': analytics
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class RevenueAnalyticsView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            # Get date range from query params
            days = int(request.query_params.get('days', 30))
            today = timezone.now().date()
            start_date = today - timedelta(days=days)
            
            # Daily revenue
            daily_revenue = []
            for i in range(days):
                date = today - timedelta(days=i)
                revenue = Order.objects.filter(
                    created_at__date=date,
                    status__in=['completed', 'delivered']
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                
                daily_revenue.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'revenue': float(revenue)
                })
            
            # Revenue by payment method
            payment_revenue = []
            payment_methods = ['cash_on_delivery', 'mobile_money', 'card']
            
            for method in payment_methods:
                revenue = Order.objects.filter(
                    payment_method=method,
                    status__in=['completed', 'delivered']
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                
                payment_revenue.append({
                    'method': method.replace('_', ' ').title(),
                    'revenue': float(revenue)
                })
            
            # Total revenue
            total_revenue = Order.objects.filter(
                status__in=['completed', 'delivered']
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            # Average order value
            total_orders = Order.objects.filter(
                status__in=['completed', 'delivered']
            ).count()
            avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
            
            analytics = {
                'period': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': today.strftime('%Y-%m-%d'),
                    'days': days
                },
                'daily_revenue': list(reversed(daily_revenue)),
                'payment_revenue': payment_revenue,
                'summary': {
                    'total_revenue': float(total_revenue),
                    'total_orders': total_orders,
                    'avg_order_value': float(avg_order_value)
                }
            }
            
            return Response({
                'success': True,
                'data': analytics
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

# ============================================
# EXPORT API
# ============================================

class ExportOrdersCSVView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Order Number', 'Customer Phone', 'Customer Name',
                'Status', 'Payment Method', 'Total Amount',
                'Is Paid', 'Created Date', 'Delivery Date'
            ])
            
            orders = Order.objects.select_related('customer__customer').all().order_by('-created_at')
            
            for order in orders:
                customer_name = 'N/A'
                if hasattr(order.customer, 'customer'):
                    customer_name = order.customer.customer.names
                
                writer.writerow([
                    order.order_number,
                    order.customer.phone_number,
                    customer_name,
                    order.get_status_display(),
                    order.get_payment_method_display(),
                    float(order.total_amount),
                    'Yes' if order.is_paid else 'No',
                    order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    order.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if order.delivered_at else ''
                ])
            
            return response
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class ExportVendorsCSVView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="vendors_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Business Name', 'Owner Name', 'Phone', 'Email',
                'Business License', 'Verified', 'Active', 'Joined Date'
            ])
            
            vendors = Vendor.objects.select_related('user').all()
            
            for vendor in vendors:
                writer.writerow([
                    vendor.business_name,
                    vendor.names,
                    vendor.user.phone_number,
                    vendor.user.email or '',
                    vendor.business_license or '',
                    'Yes' if vendor.is_verified else 'No',
                    'Yes' if vendor.user.is_active else 'No',
                    vendor.user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            return response
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class ExportDriversCSVView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="drivers_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Name', 'Phone', 'License Number', 'Vehicle Type',
                'Vehicle Plate', 'Verified', 'Available', 'Active', 'Joined Date'
            ])
            
            drivers = Driver.objects.select_related('user').all()
            
            for driver in drivers:
                writer.writerow([
                    driver.names,
                    driver.user.phone_number,
                    driver.license_number,
                    driver.vehicle_type,
                    driver.vehicle_plate,
                    'Yes' if driver.is_verified else 'No',
                    'Yes' if driver.is_available else 'No',
                    'Yes' if driver.user.is_active else 'No',
                    driver.user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                ])
            
            return response
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class ExportProductsCSVView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def get(self, request):
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Product Name', 'Category', 'Active', 'Verified',
                'Created Date', 'Last Updated'
            ])
            
            products = ProductTemplate.objects.select_related('category').all()
            
            for product in products:
                writer.writerow([
                    product.name,
                    product.category.name if product.category else 'N/A',
                    'Yes' if product.is_active else 'No',
                    'Yes' if product.is_verified else 'No',
                    product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    product.updated_at.strftime('%Y-%m-%d %H:%M:%S') if product.updated_at else ''
                ])
            
            return response
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

# ============================================
# BULK ACTIONS API
# ============================================

class BulkUserActionView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def post(self, request):
        try:
            user_ids = request.data.get('user_ids', [])
            action = request.data.get('action')
            
            if not user_ids:
                return Response({
                    'success': False,
                    'error': 'No users selected'
                }, status=400)
            
            users = User.objects.filter(id__in=user_ids)
            
            if action == 'activate':
                users.update(is_active=True)
                return Response({
                    'success': True,
                    'message': f'{users.count()} users activated'
                })
            elif action == 'deactivate':
                users.update(is_active=False)
                return Response({
                    'success': True,
                    'message': f'{users.count()} users deactivated'
                })
            elif action == 'verify':
                users.update(is_verified=True)
                return Response({
                    'success': True,
                    'message': f'{users.count()} users verified'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class BulkVendorActionView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def post(self, request):
        try:
            vendor_ids = request.data.get('vendor_ids', [])
            action = request.data.get('action')
            
            if not vendor_ids:
                return Response({
                    'success': False,
                    'error': 'No vendors selected'
                }, status=400)
            
            vendors = Vendor.objects.filter(user_id__in=vendor_ids)
            
            if action == 'verify':
                vendors.update(is_verified=True, verified_at=timezone.now())
                return Response({
                    'success': True,
                    'message': f'{vendors.count()} vendors verified'
                })
            elif action == 'activate':
                User.objects.filter(id__in=vendor_ids).update(is_active=True)
                return Response({
                    'success': True,
                    'message': f'{vendors.count()} vendors activated'
                })
            elif action == 'deactivate':
                User.objects.filter(id__in=vendor_ids).update(is_active=False)
                return Response({
                    'success': True,
                    'message': f'{vendors.count()} vendors deactivated'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class BulkOrderActionView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def post(self, request):
        try:
            order_ids = request.data.get('order_ids', [])
            action = request.data.get('action')
            
            if not order_ids:
                return Response({
                    'success': False,
                    'error': 'No orders selected'
                }, status=400)
            
            orders = Order.objects.filter(id__in=order_ids)
            
            if action == 'mark_as_paid':
                orders.update(is_paid=True)
                return Response({
                    'success': True,
                    'message': f'{orders.count()} orders marked as paid'
                })
            elif action == 'mark_as_unpaid':
                orders.update(is_paid=False)
                return Response({
                    'success': True,
                    'message': f'{orders.count()} orders marked as unpaid'
                })
            elif action == 'cancel':
                orders.update(status='cancelled', cancelled_at=timezone.now())
                return Response({
                    'success': True,
                    'message': f'{orders.count()} orders cancelled'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class BulkProductActionView(APIView):
    permission_classes = [IsAdminAPIUser]
    
    def post(self, request):
        try:
            product_ids = request.data.get('product_ids', [])
            action = request.data.get('action')
            
            if not product_ids:
                return Response({
                    'success': False,
                    'error': 'No products selected'
                }, status=400)
            
            products = ProductTemplate.objects.filter(id__in=product_ids)
            
            if action == 'activate':
                products.update(is_active=True)
                return Response({
                    'success': True,
                    'message': f'{products.count()} products activated'
                })
            elif action == 'deactivate':
                products.update(is_active=False)
                return Response({
                    'success': True,
                    'message': f'{products.count()} products deactivated'
                })
            elif action == 'verify':
                products.update(is_verified=True)
                return Response({
                    'success': True,
                    'message': f'{products.count()} products verified'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Invalid action'
                }, status=400)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

# ============================================
# OTHER VIEWSETS (simplified)
# ============================================

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = ProductTemplate.objects.all().order_by('-created_at')
    serializer_class = ProductTemplateSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

class GlobalSettingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = GlobalSetting.objects.all().order_by('key')
    serializer_class = GlobalSettingSerializer
    pagination_class = APIPagination

class ProductVariantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = ProductVariant.objects.all().order_by('product_template__name')
    serializer_class = ProductVariantSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['product_template__name', 'vendor__business_name']

class UnitPriceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = UnitPrice.objects.all().order_by('product_variant__product_template__name')
    serializer_class = UnitPriceSerializer
    pagination_class = APIPagination

class ProductAddonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = ProductAddon.objects.all().order_by('name')
    serializer_class = ProductAddonSerializer
    pagination_class = APIPagination

class ProductAddonMappingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = ProductAddonMapping.objects.all().order_by('product_variant__product_template__name')
    serializer_class = ProductAddonMappingSerializer
    pagination_class = APIPagination

class ProductImageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = ProductImage.objects.all().order_by('product_template__name')
    serializer_class = ProductImageSerializer
    pagination_class = APIPagination

class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

class MarketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Market.objects.all().order_by('name')
    serializer_class = MarketSerializer
    pagination_class = APIPagination

class DriverViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Driver.objects.select_related('user').all().order_by('-created_at')
    serializer_class = DriverListSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['names', 'license_number', 'vehicle_plate', 'user__phone_number']

class MeasurementUnitTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = MeasurementUnitType.objects.all().order_by('name')
    serializer_class = MeasurementUnitTypeSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'base_unit_name']

class MeasurementUnitViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = MeasurementUnit.objects.select_related('unit_type').all().order_by('name')
    serializer_class = MeasurementUnitSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'symbol', 'unit_type__name']

class DeliveryZoneViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = DeliveryZone.objects.select_related('market').all().order_by('market__name', 'name')
    serializer_class = DeliveryZoneSerializer
    pagination_class = APIPagination

class AdminProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AdminProfileSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['names', 'user__email', 'user__phone_number']
    ordering_fields = ['created_at', 'names']
    
    def get_queryset(self):
        return AdminProfile.objects.all().order_by('-created_at')

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['names', 'user__email', 'user__phone_number', 'address']
    ordering_fields = ['created_at', 'names']
    
    def get_queryset(self):
        return Customer.objects.all().order_by('-created_at')

class SecurityQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = SecurityQuestionSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    
    def get_queryset(self):
        return SecurityQuestion.objects.all().order_by('-created_at')

class UserSecurityAnswerViewSet(viewsets.ModelViewSet):
    serializer_class = UserSecurityAnswerSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__phone_number', 'question__question']
    
    def get_queryset(self):
        return UserSecurityAnswer.objects.all().order_by('-created_at')

class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def get_queryset(self):
        return Group.objects.all().order_by('name')

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminAPIUser]
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'codename']
    queryset = Permission.objects.all().order_by('content_type__app_label', 'codename')

class CustomerAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = CustomerAddress.objects.all().order_by('-created_at')
    serializer_class = CustomerAddressSerializer
    pagination_class = APIPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['customer__phone_number', 'recipient_name', 'street_address', 'label']

class DeliveryFeeConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = DeliveryFeeConfig.objects.all().order_by('-is_default', 'name')
    serializer_class = DeliveryFeeConfigSerializer
    pagination_class = APIPagination

class DeliveryTimeSlotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = DeliveryTimeSlot.objects.all().order_by('delivery_start_time')
    serializer_class = DeliveryTimeSlotSerializer
    pagination_class = APIPagination

class MarketDayViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = MarketDay.objects.all().order_by('id')
    serializer_class = MarketDaySerializer
    pagination_class = APIPagination

class MarketZoneViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = MarketZone.objects.select_related('market').all().order_by('market__name', 'name')
    serializer_class = MarketZoneSerializer
    pagination_class = APIPagination

class OrderItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = OrderItem.objects.all().order_by('-created_at')
    serializer_class = OrderItemSerializer
    pagination_class = APIPagination

class OrderStatusUpdateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = OrderStatusUpdate.objects.all().order_by('-created_at')
    serializer_class = OrderStatusUpdateSerializer
    pagination_class = APIPagination

class CartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = Cart.objects.all().order_by('-created_at')
    serializer_class = CartSerializer
    pagination_class = APIPagination

class CartItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminAPIUser]
    queryset = CartItem.objects.all().order_by('-created_at')
    serializer_class = CartItemSerializer
    pagination_class = APIPagination