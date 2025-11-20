#!/bin/bash
# Reset the METAR database to a clean state

set -e

echo "Resetting METAR database..."

# Truncate observation tables
psql -U metar_user -d metar_obs <<EOF
TRUNCATE observations CASCADE;
TRUNCATE ingest_metrics CASCADE;
TRUNCATE stations CASCADE;
EOF

echo "Database tables cleared."

# Reload stations
echo "Reloading station data..."
cd "$(dirname "$0")/.."
python scripts/load_stations.py

echo "Database reset complete!"