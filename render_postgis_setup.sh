#!/bin/bash
# render_postgis_setup.sh

echo "Setting up PostGIS on Render..."

# Get database URL from environment
DATABASE_URL=${DATABASE_URL}

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

# Extract connection parameters
DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@\([^:]*\).*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
DB_NAME=$(echo $DATABASE_URL | sed -e 's/.*\/\([^?]*\).*/\1/')
DB_USER=$(echo $DATABASE_URL | sed -e 's/.*\/\/\([^:]*\).*/\1/')
DB_PASS=$(echo $DATABASE_URL | sed -e 's/.*:\([^@]*\)@.*/\1/')

echo "Connecting to: $DB_HOST:$DB_PORT"

# Install PostGIS extension using psql
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<EOF
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Verify installation
SELECT PostGIS_Version();
SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'postgis%';

-- List all extensions
\dx
EOF

if [ $? -eq 0 ]; then
    echo "✅ PostGIS setup completed successfully!"
else
    echo "❌ PostGIS setup failed"
    exit 1
fi