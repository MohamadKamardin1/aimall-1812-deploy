from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from accounts.models import User, Vendor

class VendorRegistrationForm(forms.ModelForm):
    # User fields
    phone_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+255712345678'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    # Vendor fields
    names = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    business_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    business_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    business_license = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    zanzibar_id = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Vendor
        fields = [
            'names', 'business_name', 'business_address',
            'business_license', 'zanzibar_id',
            'license_document', 'id_document'
        ]
        widgets = {
            'license_document': forms.FileInput(attrs={'class': 'form-control'}),
            'id_document': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError("A user with this phone number already exists.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")
        
        return cleaned_data

    def save(self, commit=True):
        # Create User first
        user = User.objects.create_user(
            phone_number=self.cleaned_data['phone_number'],
            password=self.cleaned_data['password'],
            user_type='vendor',
            is_active=True,
            is_verified=False
        )

        # Create Vendor profile
        vendor = Vendor(
            user=user,
            names=self.cleaned_data['names'],
            business_name=self.cleaned_data['business_name'],
            business_address=self.cleaned_data['business_address'],
            business_license=self.cleaned_data['business_license'],
            zanzibar_id=self.cleaned_data['zanzibar_id'],
            is_verified=False
        )

        if self.cleaned_data.get('license_document'):
            vendor.license_document = self.cleaned_data['license_document']
        if self.cleaned_data.get('id_document'):
            vendor.id_document = self.cleaned_data['id_document']

        if commit:
            vendor.save()
        return vendor


class VendorLoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '+255712345678'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '••••••••'
        })
    )

    def clean(self):
        phone = self.cleaned_data.get('phone_number')
        password = self.cleaned_data.get('password')

        if phone and password:
            user = authenticate(phone_number=phone, password=password)
            if not user:
                raise ValidationError("Invalid phone number or password.")
            if user.user_type != 'vendor':
                raise ValidationError("This account is not a vendor account.")
            if not user.is_active:
                raise ValidationError("This account is deactivated.")
            self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
    # vendor_dashboard/forms.py
from django import forms
from markets.models import MarketZone
from products.models import ProductVariant
# vendor_dashboard/forms.py
from django import forms
from products.models import ProductVariant
from markets.models import MarketZone  # assuming this exists

class ProductVariantForm(forms.ModelForm):
    market_zone = forms.ModelChoiceField(
        queryset=MarketZone.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    custom_profit_percentage = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 15.50'})
    )

    class Meta:
        model = ProductVariant
        fields = [
            'market_zone',
            'custom_profit_percentage',
            'quality_grade',   # ✅ Must be included
            'is_active'
        ]
        widgets = {
            'quality_grade': forms.Select(attrs={'class': 'form-select'}),  # ✅ Explicit widget
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# vendor_dashboard/forms.py

class UnitPriceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        units = kwargs.pop('units', None)
        super().__init__(*args, **kwargs)
        if units:
            for unit in units:
                self.fields[f'cost_price_{unit.id}'] = forms.DecimalField(
                    max_digits=10,
                    decimal_places=2,
                    min_value=0,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'placeholder': f'e.g., 5000.00 Tsh/{unit.symbol}',
                        'step': '0.01'
                    })
                )
