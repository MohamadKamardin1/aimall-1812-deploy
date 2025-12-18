"""
COMPREHENSIVE API DOCUMENTATION FOR FLUTTER MOBILE APP

Base URL: https://your-domain.tz/api/v1/

All endpoints except auth require:
- Header: Authorization: Bearer <access_token>
- Header: Content-Type: application/json

================================================================================
1. AUTHENTICATION ENDPOINTS
================================================================================

POST /auth/register/
- Register new customer
- BODY: {
    "phone_number": "+2557XXXXXXXX",
    "password": "password123",
    "password_confirm": "password123",
    "names": "John Doe",
    "email": "john@example.com",
    "address": "House 123, Area",
    "date_of_birth": "1990-01-01",
    "security_answers": [
      {"question_id": "uuid", "answer": "answer1"},
      {"question_id": "uuid", "answer": "answer2"}
    ]
  }
- RESPONSE: {
    "message": "Registration successful",
    "customer_id": "uuid",
    "phone_number": "+2557XXXXXXXX",
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
  }

POST /auth/login/
- Customer login
- BODY: {"phone_number": "+2557XXXXXXXX", "password": "password123"}
- RESPONSE: Same as register

GET /auth/profile/
- Get customer profile
- RESPONSE: {
    "phone_number": "+2557XXXXXXXX",
    "email": "john@example.com",
    "names": "John Doe",
    "address": "House 123",
    "date_of_birth": "1990-01-01",
    "profile_picture_url": "https://..."
  }

PATCH /auth/profile/
- Update customer profile
- BODY: {profile fields to update}

POST /auth/forgot-password/
- Request password reset (get security questions)
- BODY: {"phone_number": "+2557XXXXXXXX"}
- RESPONSE: {
    "phone_number": "+2557XXXXXXXX",
    "security_questions": [
      {"id": "uuid", "question": "What is your first pet's name?"},
      {"id": "uuid", "question": "What city were you born?"}
    ]
  }

POST /auth/reset-password/
- Reset password by answering security questions
- BODY: {
    "phone_number": "+2557XXXXXXXX",
    "answers": [
      {"question_id": "uuid", "answer": "answer1"},
      {"question_id": "uuid", "answer": "answer2"}
    ],
    "new_password": "newpassword123",
    "confirm_password": "newpassword123"
  }
- RESPONSE: {"message": "Password reset successful..."}

================================================================================
2. MARKET & PRODUCT CATALOG ENDPOINTS
================================================================================

GET /markets/
- List all markets (for map display)
- RESPONSE: [
    {
      "id": "uuid",
      "name": "Darajani Market",
      "location": "Stone Town",
      "latitude": -6.1599,
      "longitude": 39.1925,
      "zone_count": 5
    }
  ]

GET /products/
- List all available products
- QUERY PARAMS:
  - limit: 20 (default)
  - offset: 0 (default)
- RESPONSE: {
    "count": 100,
    "next": "url",
    "previous": null,
    "results": [
      {
        "id": "uuid",
        "name": "Mango",
        "category_name": "Fruits",
        "image_url": "https://...",
        "vendors_count": 5,
        "description": "Fresh mangoes"
      }
    ]
  }

GET /products/{id}/
- Get product details with all variants
- RESPONSE: {
    "id": "uuid",
    "name": "Mango",
    "description": "...",
    "category_name": "Fruits",
    "primary_unit_type": "Weight",
    "image_url": "https://...",
    "additional_images": ["https://...", "https://..."],
    "variants": [
      {
        "id": "uuid",
        "product_name": "Mango",
        "category_name": "Fruits",
        "vendor_name": "Ali's Farm",
        "vendor_id": "uuid",
        "market_zone_name": "Sokoni la Matunda",
        "quality_grade": "premium",
        "unit_prices": [
          {
            "id": "uuid",
            "unit": "uuid",
            "unit_name": "Kilogram",
            "unit_symbol": "kg",
            "cost_price": 2000.00,
            "selling_price": 2500.00
          }
        ],
        "available_addons": [
          {
            "id": "uuid",
            "name": "Peeling",
            "price": 500.00,
            "addon_type": "preparation"
          }
        ],
        "product_image": "https://...",
        "is_active": true
      }
    ]
  }

GET /products/?by_market?market_id={market_uuid}
- Get products available in a specific market
- Returns list of ProductTemplate serializers

GET /products/?search?q=mango
- Search products by name or keywords
- Returns list of matching ProductTemplate serializers

GET /products/{id}/variants/
- Get all variants of a specific product
- Returns array of ProductVariantDetail serializers

GET /measurement-units/
- List all measurement units
- RESPONSE: [
    {
      "id": "uuid",
      "name": "Kilogram",
      "symbol": "kg",
      "unit_type_name": "Weight",
      "unit_type": "uuid"
    }
  ]

================================================================================
3. CART ENDPOINTS (Per-Market Carts)
================================================================================

GET /cart/list/
- Get all user's carts (one per market)
- RESPONSE: [
    {
      "id": "uuid",
      "market": "uuid",
      "market_name": "Darajani Market",
      "items": [...],
      "delivery_address_data": null,
      "subtotal": 5000.00,
      "delivery_fee": 500.00,
      "total": 5500.00
    }
  ]

GET /cart/get/?market_id={market_uuid}
- Get cart for specific market
- RESPONSE: CartSerializer response

POST /cart/add/
- Add item to cart
- BODY: {
    "market_id": "uuid",
    "product_variant_id": "uuid",
    "unit_id": "uuid",
    "quantity": 2.5,
    "selected_addons": ["addon_uuid_1", "addon_uuid_2"],
    "special_instructions": "Peel the mango"
  }
- RESPONSE: {
    "message": "Item added to cart",
    "cart": CartSerializer response
  }

POST /cart/update/
- Update cart item quantity
- BODY: {
    "item_id": "uuid",
    "quantity": 3.0
  }

DELETE /cart/remove/?item_id={uuid}
- Remove item from cart

DELETE /cart/clear/?market_id={uuid}
- Clear all items from a cart

POST /cart/set-address/
- Set delivery address for cart
- BODY: {
    "market_id": "uuid",
    "address_id": "uuid"
  }

================================================================================
4. CUSTOMER ADDRESSES
================================================================================

GET /addresses/
- List all customer delivery addresses
- RESPONSE: [
    {
      "id": "uuid",
      "address": "House 123, Area, District",
      "latitude": -6.1599,
      "longitude": 39.1925,
      "is_default": true
    }
  ]

POST /addresses/
- Create new delivery address
- BODY: {
    "address": "House 123, Area, District",
    "latitude": -6.1599,
    "longitude": 39.1925,
    "is_default": false
  }
- RESPONSE: Address serializer with id

GET /addresses/{id}/
- Get address details

PUT /addresses/{id}/
- Update address

DELETE /addresses/{id}/
- Delete address

================================================================================
5. ORDER MANAGEMENT
================================================================================

GET /orders/
- Get customer's orders (with pagination)
- RESPONSE: [
    {
      "id": "uuid",
      "order_number": "ORD202312010001",
      "total_amount": 5500.00,
      "status": "delivered",
      "payment_method": "cash_on_delivery",
      "order_items_count": 3,
      "created_at": "2023-12-01T10:00:00Z",
      "scheduled_delivery_date": "2023-12-01"
    }
  ]

GET /orders/{id}/
- Get complete order details
- RESPONSE: {
    "id": "uuid",
    "order_number": "ORD202312010001",
    "customer_name": "John Doe",
    "customer_phone": "+2557XXXXXXXX",
    "customer_address": "House 123, Area",
    "customer_location": {
      "latitude": "-6.1599",
      "longitude": "39.1925"
    },
    "market_name": "Darajani Market",
    "delivery_zone_name": "Sokoni la Matunda",
    "items": [
      {
        "id": "uuid",
        "product_template_id": "uuid",
        "product_name": "Mango",
        "product_image": "https://...",
        "vendor_id": "uuid",
        "vendor_name": "Ali's Farm",
        "vendor_phone": "+2557XXXXXXXX",
        "unit_name": "Kilogram",
        "unit_symbol": "kg",
        "quantity": 2.5,
        "unit_price": 2500.00,
        "addons_total": 1000.00,
        "total_price": 7500.00,
        "selected_addons_data": [...],
        "special_instructions": "Peel the mango"
      }
    ],
    "items_total": 7500.00,
    "delivery_fee": 500.00,
    "service_fee": 0.00,
    "discount_amount": 0.00,
    "total_amount": 8000.00,
    "payment_method": "cash_on_delivery",
    "is_paid": false,
    "status": "confirmed",
    "driver_name": "Ali Mohamed",
    "driver_phone": "+2557XXXXXXXX",
    "driver_vehicle": {
      "type": "motorcycle",
      "plate": "T 123 ABC"
    },
    "created_at": "2023-12-01T10:00:00Z",
    "scheduled_delivery_date": "2023-12-01",
    "scheduled_delivery_time": "09:00 - 12:00"
  }

POST /orders/create_order/
- Create order from cart with geo-location
- BODY: {
    "market_id": "uuid",
    "delivery_address_id": "uuid",
    "customer_latitude": -6.1599,
    "customer_longitude": 39.1925,
    "payment_method": "cash_on_delivery"
  }
- RESPONSE: {
    "message": "Order created successfully",
    "order": OrderDetailSerializer response
  }

POST /orders/{id}/cancel_order/
- Cancel order (only pending/confirmed)
- BODY: {"reason": "Change of plans"}
- RESPONSE: {"message": "Order cancelled", "order": {...}}

================================================================================
6. DRIVER ENDPOINTS
================================================================================

GET /driver/orders/?my_orders
- Get driver's assigned orders
- RESPONSE: [
    {
      "id": "uuid",
      "order_number": "ORD202312010001",
      "customer_name": "John Doe",
      "customer_phone": "+2557XXXXXXXX",
      "customer_location": {
        "latitude": "-6.1599",
        "longitude": "39.1925"
      },
      "items_count": 3,
      "total_amount": 8000.00,
      "status": "assigned",
      "scheduled_delivery_date": "2023-12-01",
      "scheduled_delivery_time": "09:00 - 12:00"
    }
  ]

GET /driver/orders/?available_orders
- Get available orders for driver pickup
- Same response structure as my_orders

GET /driver/orders/{id}/
- Get order details for driver
- RESPONSE: DriverOrderDetailSerializer

POST /driver/orders/{id}/accept_order/
- Driver accepts order for delivery
- RESPONSE: {
    "message": "Order accepted",
    "order": DriverOrderDetailSerializer response
  }

POST /driver/orders/{id}/update_status/
- Update order delivery status
- BODY: {
    "status": "picked_up|on_the_way|delivered|failed",
    "reason": "Optional reason (for failed)"
  }
- RESPONSE: {
    "message": "Order status updated to picked_up",
    "order": DriverOrderDetailSerializer response
  }

================================================================================
ERROR RESPONSES
================================================================================

400 Bad Request:
{
  "error": "Description of the error"
}

401 Unauthorized:
{
  "detail": "Authentication credentials were not provided."
}

403 Forbidden:
{
  "error": "Only drivers can access this endpoint"
}

404 Not Found:
{
  "error": "Resource not found"
}

500 Internal Server Error:
{
  "error": "Internal server error"
}

================================================================================
AUTHENTICATION FLOW
================================================================================

1. Register:
   POST /auth/register/ → Get access_token & refresh_token

2. Login:
   POST /auth/login/ → Get access_token & refresh_token

3. Use access_token:
   Header: Authorization: Bearer {access_token}

4. When access_token expires, refresh:
   POST /token/refresh/ (using refresh_token)

5. Forgot Password:
   POST /auth/forgot-password/ → Get security questions
   POST /auth/reset-password/ → Reset password

================================================================================
MAP & LOCATION FLOW
================================================================================

1. Display Markets:
   GET /markets/ → Show all markets on map

2. Browse Products by Market:
   GET /products/?by_market?market_id={market_uuid}

3. User Selects Market & Clicks on Map:
   Customer clicks market marker, then clicks delivery location on map

4. Create Address:
   POST /addresses/
   BODY: {
     "address": "Area name",
     "latitude": -6.1599,
     "longitude": 39.1925,
     "is_default": false
   }

5. Set Cart Delivery Address:
   POST /cart/set-address/
   BODY: {
     "market_id": "uuid",
     "address_id": "uuid"
   }

6. Create Order:
   POST /orders/create_order/
   BODY: {
     "market_id": "uuid",
     "delivery_address_id": "uuid",
     "customer_latitude": -6.1599,
     "customer_longitude": 39.1925,
     "payment_method": "cash_on_delivery"
   }

Order receives:
- Which products customer selected
- Which variants from which vendors
- Which measurement units and addons
- All prices and quantities
- Full customer address, name, phone, coordinates
- Which market the order belongs to
- Delivery fee calculated from zone

================================================================================
"""
