#!/bin/bash
# Test script for new delivery API endpoints

API_URL="http://localhost:8000/api/v1"
CUSTOMER_LAT="-6.19"
CUSTOMER_LNG="39.24"
ORDER_TOTAL="50000"

echo "=========================================="
echo "Testing Delivery API Endpoints"
echo "=========================================="

# Test 1: Find Nearest Market
echo -e "\n📍 TEST 1: Find Nearest Market"
echo "Endpoint: POST /markets/nearest_market/"
echo "Request:"
curl -s -X POST "${API_URL}/markets/nearest_market/" \
  -H "Content-Type: application/json" \
  -d "{\"latitude\": ${CUSTOMER_LAT}, \"longitude\": ${CUSTOMER_LNG}}" \
  | python3 -m json.tool

echo -e "\n---"

# Get market ID from first test for second test
echo -e "\n💰 TEST 2: Calculate Fee with Context (order_total = 50000)"
echo "Note: First get a market ID from Test 1 output, then test this"
echo "Endpoint: POST /delivery-fee/calculate_with_context/"
echo "Request:"
# Using a valid UUID placeholder - would be replaced with actual market ID
curl -s -X POST "${API_URL}/delivery-fee/calculate_with_context/" \
  -H "Content-Type: application/json" \
  -d "{
    \"market_id\": \"550e8400-e29b-41d4-a716-446655440000\",
    \"latitude\": ${CUSTOMER_LAT},
    \"longitude\": ${CUSTOMER_LNG},
    \"order_total\": ${ORDER_TOTAL}
  }" \
  | python3 -m json.tool 2>&1 | head -50

echo -e "\n=========================================="
echo "✓ Tests completed"
echo "=========================================="
