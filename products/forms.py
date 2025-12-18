# products/forms.py
from django import forms
from .models import ProductTemplate, MeasurementUnit


class ProductTemplateForm(forms.ModelForm):
    # Override available_units to use CheckboxSelectMultiple
    available_units = forms.ModelMultipleChoiceField(
        queryset=MeasurementUnit.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Available Units"
    )

    class Meta:
        model = ProductTemplate
        fields = [
            'name',
            'category',
            'primary_unit_type',
            'available_units',
            'description',
            'search_keywords',
            'is_active',
            'main_image',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mangoes, Rice'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'primary_unit_type': forms.Select(attrs={'class': 'form-select', 'id': 'primaryUnitType'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief product description...'}),
            'search_keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., mango, sweet, local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'main_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'name': 'Product Name *',
            'category': 'Category *',
            'primary_unit_type': 'Primary Unit Type *',
            'search_keywords': 'Search Keywords',
        }
        help_texts = {
            'search_keywords': 'Comma-separated keywords to improve search',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optimize queries
        from .models import Category, MeasurementUnitType
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['primary_unit_type'].queryset = MeasurementUnitType.objects.filter(is_active=True)
        
        # If editing, pre-check current units
        if self.instance and self.instance.pk:
            self.fields['available_units'].initial = self.instance.available_units.all()