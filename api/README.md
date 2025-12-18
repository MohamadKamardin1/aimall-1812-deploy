# API App - Flutter Mobile Application Backend

## Overview

The `api` app provides a complete REST API for the Flutter mobile application, enabling customers to:

1. **Register & Authenticate** - Phone-based registration with security questions for password recovery
2. **Browse Products** - Browse product templates, variants, prices, and options from different vendors
3. **Select Markets** - View all markets on a map and select which market to order from
4. **Manage Carts** - Separate shopping carts per market
5. **Manage Addresses** - Save delivery addresses with coordinates
6. **Place Orders** - Create orders with full geo-location, product details, vendor info, and pricing
7. **Track Orders** - Monitor order status in real-time
8. **Driver Delivery** - Driver endpoints for accepting and managing deliveries

## Architecture

### Key Design Decisions

#### 1. Per-Market Carts
Each customer can have one cart per market. This allows them to:
- Shop from multiple markets simultaneously
- Maintain separate items and pricing for each market
- Calculate delivery fees based on their selected address relative to each market

```
Customer
  ├── Cart (Market A)
  │   └── Items (products from Market A vendors)
  ├── Cart (Market B)
  │   └── Items (products from Market B vendors)
  └── Cart (Market C)
      └── Items (products from Market C vendors)
```

#### 2. Order Information Completeness
When creating an order, the backend captures:
- **Product Details**: Template ID, name, image, category
- **Variant Details**: Which vendor, which market zone, quality grade
- **Pricing**: Unit price, addons total, quantities, totals
- **Location**: Customer coordinates (latitude/longitude), delivery address
- **Delivery**: Calculated delivery fee from zone, estimated time
- **Vendor Info**: Vendor name, phone, business details

This ensures the driver and customer have all information needed for delivery.

#### 3. Geo-Location in Orders
Orders store:
```python
- delivery_address (CustomerAddress with lat/lng)
- customer_latitude, customer_longitude (from map selection)
- delivery_zone (auto-detected from coordinates)
- delivery_fee (calculated from zone and distance)
```

#### 4. Multi-Vendor Order Items
A single order can contain items from multiple vendors:
```python
Order
  ├── OrderItem (Vendor A - Product X)
  ├── OrderItem (Vendor A - Product Y)
  ├── OrderItem (Vendor B - Product Z)
  └── (All share same delivery address & fee)
```

## API Structure

### Authentication Endpoints
- `POST /auth/register/` - Customer registration with security questions
- `POST /auth/login/` - Phone number + password login
- `POST /auth/forgot-password/` - Get security questions
- `POST /auth/reset-password/` - Verify answers and reset password
- `GET /auth/profile/` - Get customer profile
- `PATCH /auth/profile/` - Update profile

### Product Catalog
- `GET /markets/` - List all markets (for map display)
- `GET /products/` - List all products with pagination
- `GET /products/{id}/` - Product details with variants
- `GET /products/?by_market?market_id=...` - Products in specific market
- `GET /products/?search?q=...` - Search products
- `GET /products/{id}/variants/` - All variants of a product
- `GET /measurement-units/` - List measurement units

### Cart Management
- `GET /cart/list/` - All user's carts
- `GET /cart/get/?market_id=...` - Get specific market cart
- `POST /cart/add/` - Add item to cart
- `POST /cart/update/` - Update item quantity
- `DELETE /cart/remove/?item_id=...` - Remove item
- `POST /cart/set-address/` - Set delivery address
- `DELETE /cart/clear/?market_id=...` - Clear cart

### Addresses
- `GET /addresses/` - List customer addresses
- `POST /addresses/` - Create new address
- `GET /addresses/{id}/` - Get address details
- `PUT /addresses/{id}/` - Update address
- `DELETE /addresses/{id}/` - Delete address

### Orders
- `GET /orders/` - List customer's orders
- `GET /orders/{id}/` - Order details
- `POST /orders/create_order/` - Create order from cart
- `POST /orders/{id}/cancel_order/` - Cancel order

### Driver Endpoints
- `GET /driver/orders/?my_orders` - Get driver's assigned orders
- `GET /driver/orders/?available_orders` - Available orders to pick
- `GET /driver/orders/{id}/` - Order details for driver
- `POST /driver/orders/{id}/accept_order/` - Accept order
- `POST /driver/orders/{id}/update_status/` - Update delivery status

## Serializers

### Authentication
- `CustomerLoginSerializer` - Login validation
- `CustomerRegistrationSerializer` - Registration with security answers
- `ForgotPasswordRequestSerializer` - Password reset request
- `ForgotPasswordVerifySerializer` - Security answer verification
- `CustomerProfileSerializer` - Profile data
- `SecurityQuestionSerializer` - Security questions list

### Products
- `ProductTemplateListSerializer` - Product listing
- `ProductTemplateDetailSerializer` - Detailed product with variants
- `ProductVariantDetailSerializer` - Variant with prices and addons
- `MeasurementUnitSerializer` - Measurement units
- `ProductAddonSerializer` - Optional addons
- `MarketListSerializer` - Markets for map

### Cart
- `CartSerializer` - Cart with items and totals
- `CartItemSerializer` - Individual cart items
- `CartItemCreateSerializer` - Create/update cart items
- `CustomerAddressSerializer` - Delivery addresses

### Orders
- `OrderDetailSerializer` - Complete order information
- `OrderListSerializer` - Order summary listing
- `OrderCreateSerializer` - Order creation input
- `OrderItemDetailSerializer` - Item in order with vendor details

### Driver
- `DriverOrderListSerializer` - Driver's order list
- `DriverOrderDetailSerializer` - Driver's order details

## Security Features

### Authentication
- Phone number + password login
- JWT tokens (access + refresh)
- Password validation (min 6 chars)
- Security questions for password recovery

### Permissions
- `AllowAny` - Auth endpoints, product catalog, markets
- `IsAuthenticated` - Cart, addresses, orders, profile
- Custom driver check - Driver endpoints

### Validation
- Phone number format: `+255xxxxxxxxx`
- Decimal fields for prices and quantities
- Coordinates validation for addresses
- Zone detection from coordinates

## Data Validation & Constraints

### Product Variants
- Unique per (template, vendor, market_zone)
- Auto-calculate selling price from cost + profit %
- Only approved variants are listed

### Orders
- Auto-generate order number: `ORD{YYYYMMDD}{sequence}`
- Calculate delivery fee from zone
- Copy cart items to order items
- Clear cart after order creation

### Addresses
- Store both street address and coordinates
- Auto-detect delivery zone from coordinates
- Auto-calculate delivery fee estimate
- Support is_default flag

### Cart Items
- Unique per (cart, product_variant, measurement_unit)
- Calculate total price from unit price × quantity + addons
- Support multiple addons per item

## Integration Points

### With Existing Apps

**accounts** - Used for:
- Phone-based authentication
- Customer profile via `user.customer`
- Vendor profile for order items
- Driver profile for order delivery
- Security questions/answers

**products** - Used for:
- ProductTemplate (what product is it?)
- ProductVariant (vendor's version)
- MeasurementUnit (how much?)
- UnitPrice (selling price)
- ProductAddon (optional add-ons)

**order** - Used for:
- Order model (with extended fields for location)
- OrderItem (what was ordered?)
- Cart/CartItem (shopping cart)

**location** - Used for:
- CustomerAddress (delivery location with coordinates)
- DeliveryZone (calculate delivery fees)
- DeliveryFeeConfig (fee calculation rules)

**markets** - Used for:
- Market (which market?)
- MarketZone (vendor locations within market)

## Adding to Settings

The api app has been added to `AIMall/settings.py`:

```python
INSTALLED_APPS = [
    ...
    'api',
]
```

And URLs registered in `AIMall/urls.py`:

```python
path('api/v1/', include('api.urls')),  # Mobile API endpoints
```

## Migration Notes

No migrations needed for the api app as it uses existing models from:
- accounts (User, Customer, Vendor, Driver, SecurityQuestion)
- products (ProductTemplate, ProductVariant, UnitPrice, etc.)
- order (Order, OrderItem, Cart, CartItem)
- location (CustomerAddress, DeliveryZone)
- markets (Market, MarketZone)

## Testing

### Register Customer
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+255712345678",
    "password": "password123",
    "password_confirm": "password123",
    "names": "John Doe",
    "email": "john@example.com",
    "security_answers": [
      {"question_id": "q_uuid", "answer": "answer1"},
      {"question_id": "q_uuid", "answer": "answer2"}
    ]
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+255712345678",
    "password": "password123"
  }'
```

### Browse Products
```bash
curl http://localhost:8000/api/v1/products/ \
  -H "Accept: application/json"
```

### Get Markets (Map)
```bash
curl http://localhost:8000/api/v1/markets/ \
  -H "Accept: application/json"
```

### Create Address (with token)
```bash
curl -X POST http://localhost:8000/api/v1/addresses/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "House 123, Area",
    "latitude": "-6.1599",
    "longitude": "39.1925",
    "is_default": true
  }'
```

### Add to Cart
```bash
curl -X POST http://localhost:8000/api/v1/cart/add/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "market_uuid",
    "product_variant_id": "variant_uuid",
    "unit_id": "unit_uuid",
    "quantity": 2.5,
    "special_instructions": "Peel the mango"
  }'
```

## Future Enhancements

1. **Payment Integration** - Mobile money (M-Pesa), card payments
2. **Real-time Tracking** - WebSocket for live driver location
3. **Ratings & Reviews** - Customer feedback on vendors
4. **Favorites** - Wishlist of products
5. **Promotions** - Coupons and discount codes
6. **Notifications** - Order status push notifications
7. **Analytics** - Track popular products, vendors
8. **Recommendation Engine** - AI-based product suggestions

## Performance Considerations

### Prefetch Related
All views use `.prefetch_related()` and `.select_related()` to reduce queries:
- `Order.objects.prefetch_related('items')`
- `Cart.objects.prefetch_related('items')`

### Indexed Fields
Location model has indexes on:
- `(customer, market, is_default)` - Fast address lookup
- `(latitude, longitude)` - Fast geo queries

### Caching Opportunities
- Market locations (changes rarely)
- Products (refreshed on vendor updates)
- Measurement units (static)

## File Structure

```
api/
├── __init__.py
├── apps.py                   # App configuration
├── serializers.py            # All serializers (500+ lines)
├── views.py                  # All viewsets (700+ lines)
├── urls.py                   # URL routing
├── API_DOCUMENTATION.md      # Comprehensive endpoint docs
└── README.md                 # This file
```

## Contact & Support

For API issues, check:
1. Request body matches serializer requirements
2. JWT token is valid and not expired
3. User has correct permissions (authenticated, driver-only for driver endpoints)
4. Coordinates are in decimal format (not degrees/minutes/seconds)
5. Phone numbers include +255 prefix
