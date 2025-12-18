"""
Seed script to populate 10+ products per market using existing markets.
Run with: python manage.py shell < seed_products_final.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

from decimal import Decimal
from products.models import (
    Category, MeasurementUnitType, MeasurementUnit, ProductTemplate, 
    ProductVariant, UnitPrice, ProductAddon
)
from accounts.models import Vendor, User
from markets.models import Market, MarketZone

def create_final_data():
    """Create 10+ products per market using existing markets"""
    
    # 1. Create categories
    print("Creating categories...")
    categories_data = [
        {"name": "Fruits", "profit": Decimal("15.00")},
        {"name": "Vegetables", "profit": Decimal("12.00")},
        {"name": "Grains", "profit": Decimal("10.00")},
        {"name": "Dairy", "profit": Decimal("18.00")},
    ]
    
    categories = {}
    for cat_data in categories_data:
        cat, created = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={
                "description": f"{cat_data['name']} category",
                "profit_percentage": cat_data["profit"]
            }
        )
        categories[cat_data["name"]] = cat
        if created:
            print(f"  ✓ Created category: {cat.name}")
    
    # 2. Create measurement unit types
    print("\nCreating measurement unit types...")
    weight_type, _ = MeasurementUnitType.objects.get_or_create(
        name="Weight", 
        defaults={"base_unit_name": "gram"}
    )
    
    count_type, _ = MeasurementUnitType.objects.get_or_create(
        name="Count", 
        defaults={"base_unit_name": "piece"}
    )
    
    volume_type, _ = MeasurementUnitType.objects.get_or_create(
        name="Volume",
        defaults={"base_unit_name": "litre"}
    )
    
    # 3. Create measurement units
    print("Creating measurement units...")
    units = {}
    
    kg_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=weight_type,
        name="Kilogram",
        defaults={"symbol": "kg", "conversion_factor": Decimal("1000")}
    )
    units["kg"] = kg_unit
    
    piece_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=count_type,
        name="Piece",
        defaults={"symbol": "pcs", "conversion_factor": Decimal("1"), "is_base_unit": True}
    )
    units["pcs"] = piece_unit
    
    litre_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=volume_type,
        name="Litre",
        defaults={"symbol": "L", "conversion_factor": Decimal("1"), "is_base_unit": True}
    )
    units["L"] = litre_unit
    
    # 4. Get existing markets and create zones for them
    print("\nProcessing existing markets...")
    existing_markets = Market.objects.filter(is_active=True).all()
    
    if not existing_markets.exists():
        print("⚠️ No active markets found!")
        return
    
    market_vendor_map = {}
    
    for idx, market in enumerate(existing_markets, start=1):
        print(f"\n  Market {idx}: {market.name} (ID: {market.id})")
        
        # Ensure market has a zone
        zone, zone_created = MarketZone.objects.get_or_create(
            market=market,
            name="Main Section",
            defaults={
                "description": "Main produce section",
                "zone_type": "General",
                "is_active": True
            }
        )
        if zone_created:
            print(f"    ✓ Created zone: {zone.name}")
        else:
            print(f"    ✓ Using existing zone: {zone.name}")
        
        # Create or get vendor for this market
        vendor_phone = f"+255655225{200+idx}"
        vendor_user, user_created = User.objects.get_or_create(
            phone_number=vendor_phone,
            defaults={
                "names": f"Vendor for {market.name}",
                "user_type": "vendor",
                "is_active": True
            }
        )
        
        if user_created:
            vendor_user.set_password("vendor123")
            vendor_user.save()
            print(f"    ✓ Created vendor user: {vendor_user.names}")
        
        vendor, vendor_created = Vendor.objects.get_or_create(
            user=vendor_user,
            defaults={
                "business_name": f"{market.name} Vendor",
                "business_type": "Produce Vendor",
                "is_approved": True,
                "is_active": True
            }
        )
        
        if vendor_created:
            print(f"    ✓ Created vendor: {vendor.business_name}")
        
        market_vendor_map[market.id] = (zone, vendor)
    
    # 5. Product data: 16 diverse products
    products_data = [
        # Fruits (5)
        {"name": "Mango", "category": "Fruits", "cost": Decimal("5000"), "unit": "kg", "desc": "Sweet tropical mangoes", "image": "assets/images/mango.jpg"},
        {"name": "Banana", "category": "Fruits", "cost": Decimal("3000"), "unit": "kg", "desc": "Ripe yellow bananas", "image": "assets/images/banana.jpg"},
        {"name": "Orange", "category": "Fruits", "cost": Decimal("4500"), "unit": "kg", "desc": "Fresh citrus oranges", "image": "assets/images/orange.jpg"},
        {"name": "Papaya", "category": "Fruits", "cost": Decimal("4000"), "unit": "kg", "desc": "Golden ripe papayas", "image": "assets/images/papaya.jpg"},
        {"name": "Pineapple", "category": "Fruits", "cost": Decimal("6000"), "unit": "pcs", "desc": "Fresh juicy pineapples", "image": "assets/images/pineapple.jpg"},
        
        # Vegetables (5)
        {"name": "Tomato", "category": "Vegetables", "cost": Decimal("4000"), "unit": "kg", "desc": "Red ripe tomatoes", "image": "assets/images/tomato.jpg"},
        {"name": "Onion", "category": "Vegetables", "cost": Decimal("2500"), "unit": "kg", "desc": "Fresh white onions", "image": "assets/images/onion.jpg"},
        {"name": "Lettuce", "category": "Vegetables", "cost": Decimal("3500"), "unit": "kg", "desc": "Crisp green lettuce", "image": "assets/images/lettuce.jpg"},
        {"name": "Cabbage", "category": "Vegetables", "cost": Decimal("2000"), "unit": "kg", "desc": "Fresh green cabbage", "image": "assets/images/cabbage.jpg"},
        {"name": "Pepper", "category": "Vegetables", "cost": Decimal("5000"), "unit": "kg", "desc": "Colorful bell peppers", "image": "assets/images/pepper.jpg"},
        
        # Grains (3)
        {"name": "Rice", "category": "Grains", "cost": Decimal("3000"), "unit": "kg", "desc": "Long grain white rice", "image": "assets/images/rice.jpg"},
        {"name": "Maize", "category": "Grains", "cost": Decimal("2500"), "unit": "kg", "desc": "Fresh corn kernels", "image": "assets/images/maize.jpg"},
        {"name": "Beans", "category": "Grains", "cost": Decimal("4000"), "unit": "kg", "desc": "Dried kidney beans", "image": "assets/images/beans.jpg"},
        
        # Dairy (3)
        {"name": "Milk", "category": "Dairy", "cost": Decimal("3500"), "unit": "L", "desc": "Fresh whole milk", "image": "assets/images/milk.jpg"},
        {"name": "Cheese", "category": "Dairy", "cost": Decimal("12000"), "unit": "kg", "desc": "Local cheddar cheese", "image": "assets/images/cheese.jpg"},
        {"name": "Yogurt", "category": "Dairy", "cost": Decimal("5000"), "unit": "kg", "desc": "Plain yogurt", "image": "assets/images/yogurt.jpg"},
    ]
    
    # 6. Create products and variants for each market
    print("\n\nCreating 16 products for each market...")
    total_variants = 0
    
    for market in existing_markets:
        zone, vendor = market_vendor_map[market.id]
        market_variant_count = 0
        
        for prod_data in products_data:
            category = categories[prod_data["category"]]
            unit = units[prod_data["unit"]]
            
            # Create product template (shared across markets)
            product, prod_created = ProductTemplate.objects.get_or_create(
                name=prod_data["name"],
                category=category,
                defaults={
                    "description": prod_data["desc"],
                    "primary_unit_type": unit.unit_type,
                    "is_active": True,
                    "is_verified": True,
                    "search_keywords": prod_data["name"].lower()
                }
            )
            
            # Ensure unit is available for this product
            product.available_units.add(unit)
            
            # Create variant for this market
            variant, var_created = ProductVariant.objects.get_or_create(
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
            unit_price, price_created = UnitPrice.objects.get_or_create(
                product_variant=variant,
                unit=unit,
                defaults={
                    "cost_price": prod_data["cost"],
                    "is_active": True
                }
            )
            
            if var_created:
                market_variant_count += 1
                total_variants += 1
        
        print(f"  ✓ {market.name}: {market_variant_count} new product variants")
    
    print(f"\n✅ Seeding complete!")
    print(f"   - Products: {len(products_data)} per market")
    print(f"   - Markets processed: {existing_markets.count()}")
    print(f"   - Total new variants: {total_variants}")

if __name__ == "__main__":
    create_final_data()
