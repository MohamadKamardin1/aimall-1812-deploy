# test_db.py
import os
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AIMall.settings')
django.setup()

def test_database():
    try:
        with connection.cursor() as cursor:
            # Test 1: Basic connection
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()
            print(f"✅ PostgreSQL Version: {db_version[0]}")
            
            # Test 2: PostGIS extension
            cursor.execute("SELECT PostGIS_Version();")
            postgis_version = cursor.fetchone()
            print(f"✅ PostGIS Version: {postgis_version[0]}")
            
            # Test 3: List tables (check Django migrations)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables in database")
            
            if tables:
                print("First 5 tables:", [t[0] for t in tables[:5]])
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def test_gdal():
    try:
        from django.contrib.gis.gdal import GDAL_VERSION
        print(f"✅ GDAL Version: {GDAL_VERSION}")
        return True
    except Exception as e:
        print(f"❌ GDAL test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Database Connection...")
    print("-" * 40)
    
    db_ok = test_database()
    print("\nTesting GDAL...")
    print("-" * 40)
    gdal_ok = test_gdal()
    
    print("\n" + "=" * 40)
    if db_ok and gdal_ok:
        print("🎉 All tests passed! Ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check configuration.")