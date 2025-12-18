# API App - Quick Start Guide

## Installation & Setup

### 1. Prerequisites
- Django 5.2
- Python 3.8+
- PostgreSQL with PostGIS (or SQLite for development)

### 2. Dependencies (already in requirements.txt)
```
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
django-cors-headers==4.3.1
cloudinary==1.44.1
geopy==2.4.1
```

### 3. Add to Installed Apps
✅ Already done in `AIMall/settings.py`

```python
INSTALLED_APPS = [
    ...
    'api',
]
```

### 4. Register URLs
✅ Already done in `AIMall/urls.py`

```python
path('api/v1/', include('api.urls')),  # Mobile API endpoints
```

## Quick Test

### 1. Start Server
```bash
python manage.py runserver
```

### 2. Register Customer
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+255712345678",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "names": "John Doe",
    "email": "john@example.com",
    "security_answers": [
      {"question_id": "question-uuid", "answer": "answer1"},
      {"question_id": "question-uuid", "answer": "answer2"}
    ]
  }'
```

### 3. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+255712345678",
    "password": "testpass123"
  }'
```

Response:
```json
{
  "message": "Login successful",
  "customer_id": "uuid",
  "phone_number": "+255712345678",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 4. Use Access Token
```bash
# Set token variable
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Get profile
curl http://localhost:8000/api/v1/auth/profile/ \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Browse Products (no auth needed)
```bash
curl http://localhost:8000/api/v1/products/
```

### 6. Get Markets (no auth needed)
```bash
curl http://localhost:8000/api/v1/markets/
```

## Running Tests

```bash
# Run all API tests
python manage.py test api

# Run specific test
python manage.py test api.tests.CustomerAuthTestCase

# Run with verbosity
python manage.py test api -v 2

# Run specific test method
python manage.py test api.tests.CustomerAuthTestCase.test_customer_registration
```

## Common Issues

### 1. "No such table: accounts_user"
**Solution:** Run migrations
```bash
python manage.py migrate
```

### 2. "OrderedDict() argument after ** must be a mapping"
**Solution:** Check Django REST Framework version
```bash
pip install --upgrade djangorestframework
```

### 3. "No security questions found"
**Solution:** Create security questions first
```bash
python manage.py shell
from accounts.models import SecurityQuestion
SecurityQuestion.objects.create(question="What is your first pet's name?")
SecurityQuestion.objects.create(question="What city were you born?")
```

### 4. "User with this phone number already exists"
**Solution:** Use a different phone number or delete the user:
```bash
python manage.py shell
from accounts.models import User
User.objects.filter(phone_number='+255712345678').delete()
```

## Development Workflow

### Creating a New Endpoint

1. **Add serializer in `api/serializers.py`**
```python
class MyDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ('id', 'name', 'description')
```

2. **Add view in `api/views.py`**
```python
class MyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        data = MyModel.objects.all()
        serializer = MyDataSerializer(data, many=True)
        return Response(serializer.data)
```

3. **Register in `api/urls.py`**
```python
router.register(r'mydata', MyViewSet, basename='mydata')
```

4. **Add tests in `api/tests.py`**
```python
class MyDataTestCase(TestCase):
    def test_list_mydata(self):
        response = self.client.get('/api/v1/mydata/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

### Following Patterns

- Use `@action` decorator for custom endpoint behavior
- Always include permission classes (`IsAuthenticated`, `AllowAny`)
- Return `Response()` with proper status codes
- Validate input with serializers
- Use `select_related()` and `prefetch_related()` for efficiency
- Document response structure in docstrings

## Performance Tips

### 1. Database Queries
```python
# ❌ Bad: N+1 queries
orders = Order.objects.all()
for order in orders:
    print(order.customer.name)  # Query for each order!

# ✅ Good: Single query
orders = Order.objects.select_related('customer')
```

### 2. Filtering
```python
# ❌ Bad: Loads all objects
products = ProductTemplate.objects.all()
filtered = [p for p in products if p.is_active]

# ✅ Good: Filter in database
products = ProductTemplate.objects.filter(is_active=True)
```

### 3. Pagination
```python
# ✅ Good: Use built-in pagination
response = self.paginate_queryset(queryset)
```

## Deployment Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Update `ALLOWED_HOSTS` with domain
- [ ] Configure CORS for Flutter app domain
- [ ] Set up Cloudinary variables
- [ ] Configure PostgreSQL with PostGIS
- [ ] Run migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Create superuser for admin
- [ ] Set up SSL/HTTPS
- [ ] Configure email for password recovery
- [ ] Test all payment integrations
- [ ] Set up monitoring and logging

## Documentation Links

- [API Endpoints Reference](./API_DOCUMENTATION.md)
- [Architecture & Design](./README.md)
- [Implementation Summary](../API_IMPLEMENTATION_SUMMARY.md)
- [Django REST Framework Docs](https://www.django-rest-framework.org/)
- [JWT Authentication](https://django-rest-framework-simplejwt.readthedocs.io/)

## Support

For issues:
1. Check API_DOCUMENTATION.md for endpoint details
2. Review README.md for architecture
3. Look at test cases for usage examples
4. Check Django REST Framework documentation
5. Review error messages carefully

## Success Indicators

Your API is working when:
- ✅ Can register new customer
- ✅ Can login with phone + password
- ✅ Can view products without authentication
- ✅ Can add items to cart (authenticated)
- ✅ Can create orders with delivery address
- ✅ Driver can view and accept orders
