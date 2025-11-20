# METAR Observation Ingestion System

A Python-based system for ingesting, parsing, and storing METAR observations in PostgreSQL/PostGIS with metrics tracking.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

## Features

- 24/7 daemon process for continuous ingestion
- Batch and single METAR processing via stdin
- PostgreSQL/PostGIS storage with simplified repository pattern
- Individual meteorological element extraction
- Automated data cleanup (30-day retention)
- Comprehensive metrics and logging
- Telegraf integration for InfluxDB metrics
- Daily log rotation with 7-day retention

## Installation

### Option 1: Using Conda (Recommended)

1. Create and activate conda environment:
   ```bash
   conda create -f environment.yml
   conda activate metar-ingest
   ```

### Option 2: Using System Python

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

### Setup:

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Initialize database:
   ```bash
   psql -U postgres -f sql/schema.sql
   bash scripts/reset_database.sh
   ```

5. Install as package:
   ```bash
   pip install -e .
   ```

## Usage

**Note:** Always activate the conda environment first:
```bash
conda activate metar-ingest
```

### Run as one-time process (for cron/LDM):
```bash
echo "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034" | python src/main.py
```

### Run cleanup:
```bash
python src/cleanup.py
```

### Setup with LDM:
Add to your LDM pqact.conf:
```
WMO	^S[AP].*
    PIPE	-close /home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh
```

**Note:** The -close is required or no METARs will be processed until LDM is closed.

### Setup cron for cleanup:
```bash
crontab -e
# Add: 0 2 * * * /home/ldm/miniconda3/envs/metar-ingest/bin/python /home/ldm/scripts/obs/metar/src/cleanup.py
```

## Database Structure

- `observations`: Main table with raw METAR and location
- `observation_elements`: Individual meteorological elements
- `stations`: Station metadata
- `ingest_metrics`: Processing statistics

## Metrics

Metrics are stored in PostgreSQL and can be exported to InfluxDB via Telegraf:

```bash
telegraf --config config/telegraf.conf
```

## Logs

Logs are stored in `/var/log/metar-ingest/` and rotate daily at midnight, keeping 7 days of history.
