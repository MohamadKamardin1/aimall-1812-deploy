from django.urls import path
from . import views

app_name = 'vendor_dashboard'

urlpatterns = [
    path('register/', views.VendorRegisterView.as_view(), name='register'),
    path('login/', views.VendorLoginView.as_view(), name='login'),
    path('logout/', views.VendorLogoutView.as_view(), name='logout'),
    path('profile/edit/', views.VendorProfileEditView.as_view(), name='profile_edit'),
    
    # Future: dashboard, profile, products, etc.
    path('', views.VendorDashboardView.as_view(), name='dashboard'),
    path('products/templates/', views.ProductTemplateListView.as_view(), name='product_templates'),
    path(
    'products/templates/<uuid:template_id>/create/',
        views.CreateProductVariantView.as_view(),
        name='create_product_variant'
    ),
    path('products/', views.VendorProductListView.as_view(), name='product_list'),
    path('products/<uuid:pk>/delete/', views.VendorProductDeleteView.as_view(), name='delete_product'),
    path('products/<uuid:pk>/', views.VendorProductDetailView.as_view(), name='product_detail'),
    path('products/<uuid:pk>/edit/', views.VendorProductEditView.as_view(), name='product_edit'),
    path('products/<uuid:pk>/addons/', views.VendorProductAddonsView.as_view(), name='product_addons'),
]