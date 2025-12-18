"""
Enhanced seed script to populate products: 10+ per market with variety.
Run with: python manage.py shell < seed_products_enhanced.py
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

def create_enhanced_data():
    """Create 10+ products per market with variety"""
    
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
        cat, _ = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={
                "description": f"{cat_data['name']} category",
                "profit_percentage": cat_data["profit"]
            }
        )
        categories[cat_data["name"]] = cat
    
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
    
    dozen_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=count_type,
        name="Dozen",
        defaults={"symbol": "dz", "conversion_factor": Decimal("12")}
    )
    units["dz"] = dozen_unit
    
    litre_unit, _ = MeasurementUnit.objects.get_or_create(
        unit_type=volume_type,
        name="Litre",
        defaults={"symbol": "L", "conversion_factor": Decimal("1"), "is_base_unit": True}
    )
    units["L"] = litre_unit
    
    # 4. Create multiple markets with zones
    print("Creating markets and zones...")
    markets_data = [
        {
            "name": "Dar es Salaam Central Market",
            "location": "Dar es Salaam",
            "zones": [
                {"name": "Fruits Section", "type": "Fruits"},
                {"name": "Vegetables Section", "type": "Vegetables"},
            ]
        },
        {
            "name": "Arusha Market",
            "location": "Arusha",
            "zones": [
                {"name": "Produce Section", "type": "Mixed Produce"},
                {"name": "Dairy Section", "type": "Dairy"},
            ]
        },
        {
            "name": "Mbeya Market",
            "location": "Mbeya",
            "zones": [
                {"name": "Main Bazaar", "type": "Mixed"},
            ]
        },
    ]
    
    markets = {}
    zones_dict = {}
    
    for market_data in markets_data:
        market, _ = Market.objects.get_or_create(
            name=market_data["name"],
            defaults={
                "description": f"Market in {market_data['location']}",
                "location": market_data["location"],
                "is_active": True
            }
        )
        markets[market_data["name"]] = market
        
        for zone_data in market_data["zones"]:
            zone, _ = MarketZone.objects.get_or_create(
                market=market,
                name=zone_data["name"],
                defaults={
                    "description": f"{zone_data['type']} vendors",
                    "zone_type": zone_data["type"],
                    "is_active": True
                }
            )
            zones_dict[f"{market_data['name']}:{zone_data['name']}"] = zone
    
    # 5. Create vendors for each market
    print("Creating vendors...")
    vendors = {}
    for idx, market_name in enumerate(markets.keys(), start=1):
        user, created = User.objects.get_or_create(
            phone_number=f"+255655225{227+idx}",
            defaults={
                "names": f"Vendor {idx} ({market_name.split()[0]})",
                "user_type": "vendor",
                "is_active": True
            }
        )
        if created:
            user.set_password("vendor123")
            user.save()
        
        vendor, _ = Vendor.objects.get_or_create(
            user=user,
            defaults={
                "business_name": f"Vendor {idx} Fresh Supplies",
                "business_type": "Vendor",
                "is_approved": True,
                "is_active": True
            }
        )
        vendors[market_name] = vendor
    
    # 6. Product data: 10+ diverse products
    products_data = [
        # Fruits (5)
        {"name": "Mango", "category": "Fruits", "cost": Decimal("5000"), "unit": "kg", "desc": "Sweet tropical mangoes"},
        {"name": "Banana", "category": "Fruits", "cost": Decimal("3000"), "unit": "kg", "desc": "Ripe yellow bananas"},
        {"name": "Orange", "category": "Fruits", "cost": Decimal("4500"), "unit": "kg", "desc": "Fresh citrus oranges"},
        {"name": "Papaya", "category": "Fruits", "cost": Decimal("4000"), "unit": "kg", "desc": "Golden ripe papayas"},
        {"name": "Pineapple", "category": "Fruits", "cost": Decimal("6000"), "unit": "pcs", "desc": "Fresh juicy pineapples"},
        
        # Vegetables (5)
        {"name": "Tomato", "category": "Vegetables", "cost": Decimal("4000"), "unit": "kg", "desc": "Red ripe tomatoes"},
        {"name": "Onion", "category": "Vegetables", "cost": Decimal("2500"), "unit": "kg", "desc": "Fresh white onions"},
        {"name": "Lettuce", "category": "Vegetables", "cost": Decimal("3500"), "unit": "kg", "desc": "Crisp green lettuce"},
        {"name": "Cabbage", "category": "Vegetables", "cost": Decimal("2000"), "unit": "kg", "desc": "Fresh green cabbage"},
        {"name": "Pepper", "category": "Vegetables", "cost": Decimal("5000"), "unit": "kg", "desc": "Colorful bell peppers"},
        
        # Grains (3)
        {"name": "Rice", "category": "Grains", "cost": Decimal("3000"), "unit": "kg", "desc": "Long grain white rice"},
        {"name": "Maize", "category": "Grains", "cost": Decimal("2500"), "unit": "kg", "desc": "Fresh corn kernels"},
        {"name": "Beans", "category": "Grains", "cost": Decimal("4000"), "unit": "kg", "desc": "Dried kidney beans"},
        
        # Dairy (3)
        {"name": "Milk", "category": "Dairy", "cost": Decimal("3500"), "unit": "L", "desc": "Fresh whole milk"},
        {"name": "Cheese", "category": "Dairy", "cost": Decimal("12000"), "unit": "kg", "desc": "Local cheddar cheese"},
        {"name": "Yogurt", "category": "Dairy", "cost": Decimal("5000"), "unit": "kg", "desc": "Plain yogurt"},
    ]
    
    # 7. Create products and variants for each market
    print("Creating products and variants for each market...")
    product_created_count = 0
    
    for market_name, market in markets.items():
        print(f"\n  Processing market: {market_name}")
        vendor = vendors[market_name]
        
        for zone_key in zones_dict.keys():
            if market_name not in zone_key:
                continue
            
            zone = zones_dict[zone_key]
            
            for prod_data in products_data:
                category = categories[prod_data["category"]]
                unit = units[prod_data["unit"]]
                
                # Create product template
                product, created = ProductTemplate.objects.get_or_create(
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
                
                # Add available unit
                product.available_units.add(unit)
                
                # Create variant for this market
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
                unit_price, created = UnitPrice.objects.get_or_create(
                    product_variant=variant,
                    unit=unit,
                    defaults={
                        "cost_price": prod_data["cost"],
                        "is_active": True
                    }
                )
                
                if created or unit_price.cost_price != prod_data["cost"]:
                    unit_price.cost_price = prod_data["cost"]
                    unit_price.save()
                    product_created_count += 1
    
    print(f"\n✅ Product seeding complete! Created/Updated {product_created_count} product variants")
    print(f"   - Total products: {len(products_data)} per market")
    print(f"   - Total markets: {len(markets)}")
    print(f"   - Total variants created: {product_created_count}")

if __name__ == "__main__":
    create_enhanced_data()
