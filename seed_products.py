"""
Seed script to populate product templates, variants, units, and prices.
Run with: python manage.py shell < seed_products.py
or: python manage.py shell && exec(open('seed_products.py').read())
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

from decimal import Decimal
from products.models import (
    Category, MeasurementUnitType, MeasurementUnit, ProductTemplate, 
    ProductVariant, UnitPrice, ProductAddon, ProductAddonMapping
)
from accounts.models import Vendor, User
from markets.models import Market, MarketZone

def create_demo_data():
    """Create demo product data for testing"""
    
    # 1. Create categories
    print("Creating categories...")
    fruit_cat, _ = Category.objects.get_or_create(
        name="Fruits",
        defaults={
            "description": "Fresh tropical fruits",
            "profit_percentage": Decimal("15.00")
        }
    )
    
    veg_cat, _ = Category.objects.get_or_create(
        name="Vegetables",
        defaults={
            "description": "Fresh vegetables and greens",
            "profit_percentage": Decimal("12.00")
        }
    )
    
    # 2. Create measurement unit types
    print("Creating measurement unit types...")
    weight_type, _ = MeasurementUnitType.objects.get_or_create(
        name="Weight", 
        defaults={"base_unit_name": "gram"}
    )
    
    count_type, _ = MeasurementUnitType.objects.get_or_create(
        name="Count", 
        defaults={"base_unit_name": "piece"}
    )
    
    # 3. Create measurement units
    print("Creating measurement units...")
    kg_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=weight_type,
        name="Kilogram",
        defaults={"symbol": "kg", "conversion_factor": Decimal("1000"), "is_base_unit": False}
    )
    
    piece_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=count_type,
        name="Piece",
        defaults={"symbol": "pcs", "conversion_factor": Decimal("1"), "is_base_unit": True}
    )
    
    # 4. Create or get market and zone
    print("Creating market and zone...")
    market, _ = Market.objects.get_or_create(
        name="Dar es Salaam Central Market",
        defaults={
            "description": "Main market in Dar es Salaam",
            "location": "Dar es Salaam",
            "is_active": True
        }
    )
    
    zone, _ = MarketZone.objects.get_or_create(
        market=market,
        name="Fruits Section",
        defaults={
            "description": "Tropical fruits vendors",
            "zone_type": "Fruits",
            "is_active": True
        }
    )
    
    # 5. Create or get vendor user
    print("Creating vendor user...")
    vendor_user, created = User.objects.get_or_create(
        phone_number="+255655225227",
        defaults={
            "names": "Hassan Mango Vendor",
            "user_type": "vendor",
            "is_active": True
        }
    )
    if created:
        vendor_user.set_password("vendor123")
        vendor_user.save()
    
    # 6. Create or get vendor
    print("Creating vendor...")
    vendor, _ = Vendor.objects.get_or_create(
        user=vendor_user,
        defaults={
            "business_name": "Hassan's Fresh Mangoes",
            "business_type": "Vendor",
            "is_approved": True,
            "is_active": True
        }
    )
    
    # 7. Create product templates and variants
    products_data = [
        {
            "name": "Fresh Mango",
            "description": "Sweet and juicy tropical mangoes, perfect for daily consumption",
            "category": fruit_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("5000"), "unit": kg_unit}]
        },
        {
            "name": "Banana",
            "description": "Ripe yellow bananas, rich in potassium",
            "category": fruit_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("3000"), "unit": kg_unit}]
        },
        {
            "name": "Tomato",
            "description": "Red, ripe tomatoes for cooking or salads",
            "category": veg_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("4000"), "unit": kg_unit}]
        },
        {
            "name": "Onion",
            "description": "Fresh onions, essential for any kitchen",
            "category": veg_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("2500"), "unit": kg_unit}]
        },
        {
            "name": "Lettuce",
            "description": "Fresh green lettuce for salads",
            "category": veg_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("3500"), "unit": kg_unit}]
        },
        {
            "name": "Apple",
            "description": "Imported red apples, crisp and sweet",
            "category": fruit_cat,
            "unit_type": weight_type,
            "variants": [{"cost": Decimal("12000"), "unit": kg_unit}]
        },
    ]
    
    print("Creating products...")
    for prod_data in products_data:
        product, created = ProductTemplate.objects.get_or_create(
            name=prod_data["name"],
            category=prod_data["category"],
            defaults={
                "description": prod_data["description"],
                "primary_unit_type": prod_data["unit_type"],
                "is_active": True,
                "is_verified": True,
                "search_keywords": prod_data["name"].lower()
            }
        )
        
        # Add available units
        product.available_units.add(prod_data["variants"][0]["unit"])
        
        # Create variant
        variant, created = ProductVariant.objects.get_or_create(
            product_template=product,
            vendor=vendor,
            market_zone=zone,
            defaults={
                "quality_grade": "standard",
                "is_active": True,
                "is_approved": True
            }
        )
        
        # Create unit price
        for variant_data in prod_data["variants"]:
            unit_price, created = UnitPrice.objects.get_or_create(
                product_variant=variant,
                unit=variant_data["unit"],
                defaults={
                    "cost_price": variant_data["cost"],
                    "is_active": True
                }
            )
            if created or unit_price.cost_price != variant_data["cost"]:
                unit_price.cost_price = variant_data["cost"]
                unit_price.save()  # Auto-calculates selling_price
        
        print(f"  ✓ {product.name} (cost: {variant_data['cost']} TZS/kg, selling: {UnitPrice.objects.filter(product_variant=variant).first().selling_price} TZS/kg)")
    
    print("\n✅ Product seeding complete!")

if __name__ == "__main__":
    create_demo_data()
