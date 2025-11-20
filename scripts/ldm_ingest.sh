#!/bin/bash
# Wrapper script for LDM integration

# Set working directory
cd /home/ldm/scripts/obs/metar || exit 2

# Activate conda environment
# source /home/ldm/.conda/etc/profile.d/conda.sh
# conda activate metar-ingest

# Log startup
echo "$(date): Starting METAR ingestion" >> var/logs/metar_wrapper.log
echo "Python: $(which python)" >> var/logs/metar_wrapper.log
echo "User: $(whoami)" >> var/logs/metar_wrapper.log

# Run the script with unbuffered output
exec /home/ldm/.conda/envs/metar-ingest/bin/python -u src/main.py || exit 3
# Or with extra debugging:
# exec tee -a /tmp/metar_raw_input.log | /home/ldm/.conda/envs/metar-ingest/bin/python -u src/main.py 2>&1 | tee -a /tmp/metar_debug.log