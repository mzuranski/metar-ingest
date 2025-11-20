# METAR Ingestion System Architecture

## Overview
Real-time METAR observation ingestion system designed for LDM integration with PostgreSQL/PostGIS storage.

## System Flow
```
LDM (pqact -close) → Product Stream → Parser → Batch Processor → PostgreSQL/PostGIS
                          ↓
                    Persistent DB Pool
```

## Key Design Decisions

### Continuous Operation
- **Persistent Database Connections**: Connection pool remains open throughout runtime
- **Product-by-Product Processing**: Each LDM product triggers immediate processing
- **Batch Optimization**: Groups up to 100 observations before database write
- **No Restart Overhead**: Service runs continuously, avoiding reconnection costs

### LDM Integration
- **PIPE with `-close` flag**: Critical for real-time processing
  - Without `-close`: Products buffer until LDM shutdown
  - With `-close`: Each product closes pipe, forcing immediate processing
- **Product Format Handling**: Parses WMO headers, multi-line observations, continuation lines
- **Control Character Detection**: `\x01` marks product boundaries

## Components

### 1. Main Entry Point (`src/main.py`)
- Reads LDM products from stdin continuously
- Detects product boundaries via `\x01` control character
- Maintains persistent database connection pool
- Processes products immediately upon receipt
- Handles graceful shutdown (SIGTERM/SIGINT)

**LDM Product Format:**
```
^A                              # Control character (0x01)
367                             # Byte count (skipped)
SAUS99 KWBC 202115              # WMO header (skipped)
METAR                           # Report type
KDVP 202113Z AUTO 32009KT ...  # Observation line 1
     T00660050=                 # Continuation line (leading spaces)
KXVG 202113Z AUTO 29006KT ...  # Observation line 2
     AO2=                       # Continuation line
```

### 2. Parser (`src/parsers/metar_parser.py`)
- Uses `python-metar` library for parsing
- Handles multi-line observations (continuation lines)
- Extracts meteorological elements:
  - Temperature, dewpoint, pressure
  - Wind speed/direction/gust
  - Visibility
  - Sky conditions (converted to oktas: 0-8)
  - Present weather (converted to WMO codes)
  - Remarks
- Detects corrections (COR) and amendments (AMD)

### 3. Weather Codes (`src/parsers/weather_codes.py`)
- Maps METAR weather phenomena to WMO codes
- Converts sky cover abbreviations to oktas (eighths)
- Reference: WMO code table 4677

### 4. Database Layer

#### Connection Management (`src/database/connection.py`)
- Thread-safe connection pooling (psycopg2)
- Persistent connections for continuous operation
- Configurable pool size (default: 1-10 connections)
- Automatic transaction management
- Context managers for safe resource handling

**Why Persistent Connections?**
- Eliminates connection overhead (100-200ms per connect)
- Reduces database load
- Improves throughput for high-volume periods
- Connections only closed on service shutdown

#### Repositories (`src/database/repositories.py`)
- **ObservationRepository**: CRUD for observations and elements
- **StationRepository**: Station metadata and spatial queries
- **MetricsRepository**: Ingestion statistics

### 5. Database Schema

#### Tables
```sql
stations
  - station_id (PK, ICAO code)
  - station_name, country
  - latitude, longitude, elevation
  - location (PostGIS Point geometry, SRID 4326)

observations
  - id (PK)
  - station_id (FK to stations)
  - observation_time (UTC timestamp)
  - raw_metar (complete METAR text)
  - UNIQUE(station_id, observation_time)

observation_elements
  - id (PK)
  - observation_id (FK to observations, CASCADE DELETE)
  - element_type (temperature, wind_speed, sky_cover_layer_1, etc.)
  - element_value (numeric value)
  - element_unit (celsius, knots, oktas, etc.)
  - element_text (for text elements like remarks)

ingest_metrics
  - Tracks ingestion performance and errors
```

#### Key Features
- **Normalized design**: Station data stored once, referenced by FK
- **PostGIS integration**: Spatial queries on station locations
- **Flexible elements**: All parsed data in key-value structure
- **Correction handling**: COR/AMD overwrites existing observations

### 6. Batch Processing (`src/ingest/batch_processor.py`)
- Processes observations in batches for efficiency
- Handles corrections by updating existing records
- Tracks metrics: parsed, failed, DB errors, corrections, duplicates
- Minimal logging for performance (INFO level)

### 7. Station Loader (`scripts/load_stations.py`)
- Parses WMO station metadata (worldstanew.txt)
- Converts coordinates from degrees/minutes to decimal
- Populates PostGIS geometry column
- Handles US state codes → country normalization

### 8. Configuration (`src/config/`)
- `database.yml`: PostgreSQL connection settings
- `settings.py`: Application configuration
- Environment-based overrides supported

## Data Flow

### Real-Time Ingestion Process
1. **LDM Receives Product**: METAR bulletin arrives via IDD feed
2. **pqact Pipes to Script**: Using `-close` flag for immediate processing
3. **Product Boundary Detection**: Script detects `\x01` start-of-product marker
4. **Product Parsing**: 
   - Skip WMO header and byte count
   - Extract report type (METAR/SPECI)
   - Parse individual observations (handle multi-line)
   - Accumulate into batch
5. **Batch Processing** (when full or product complete):
   - Parse each METAR using python-metar
   - Extract all meteorological elements
   - Detect corrections (COR/AMD)
6. **Database Storage**:
   - Insert/update observation record
   - If correction: delete old elements, insert new
   - Insert all parsed elements
7. **Metrics Recording**: Track batch statistics

### Correction Handling
```
Normal:   INSERT ... ON CONFLICT DO NOTHING
          (Duplicate = skip, return NULL)

COR/AMD:  INSERT ... ON CONFLICT DO UPDATE
          (Overwrites observation)
          DELETE old elements
          INSERT new elements
```

### Multi-Line Observation Handling
```python
# Example multi-line METAR
KDVP 202113Z AUTO 32009KT 10SM OVC022 07/05 A3005 RMK AO2
     T00660050=

# Detected by:
# - First line: Starts with station ID (KDVP)
# - Second line: Starts with whitespace (continuation)
# - Ends with: = character (observation complete)
```

## Spatial Queries

PostGIS enables geographic queries:

```python
# Find observations near a point
ObservationRepository.get_observations_near_point(
    latitude=40.64, 
    longitude=-73.78, 
    radius_km=50,
    max_age_hours=24
)

# Find nearest stations
StationRepository.find_nearest_stations(
    latitude=40.64,
    longitude=-73.78,
    limit=10
)
```

## Performance Considerations

### Optimizations
- **Persistent connections**: Eliminate connection overhead
- **Batch processing**: Reduce transaction overhead
- **Product-level processing**: Process immediately, don't wait for EOF
- **Indexes**: 
  - B-tree on station_id, observation_time
  - GiST on PostGIS location column
- **Minimal logging**: INFO level, summaries only
- **Unbuffered I/O**: Line buffering for immediate log output

### Throughput
- Target: 1000+ METARs per minute
- Batch size: 100 observations
- Processing time: ~50-100ms per batch (typical)
- Connection overhead: 0ms (persistent pool)

## LDM Integration

### pqact.conf Entry
```bash
# CRITICAL: Must use -close flag for real-time processing
DDPLUS|IDS	^SAUS[^_]*
    PIPE	-close	/home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh
```

**Why `-close` is Required:**
- Without: LDM buffers products, only flushes on shutdown
- With: Each product closes the pipe, forcing script to process immediately
- The script reconnects automatically for the next product

### Wrapper Script
```bash
#!/bin/bash
cd /home/ldm/scripts/obs/metar || exit 1

# Use direct Python path (not conda run, which blocks stdin)
exec /home/ldm/.conda/envs/metar-ingest/bin/python -u src/main.py 2>&1 | \
    tee -a logs/metar-ingest.log
```

**Why Direct Python Path:**
- `conda run` blocks stdin, preventing real-time data flow
- Direct binary path avoids conda overhead
- `-u` flag ensures unbuffered output

### Environment
- User: ldm
- Python: conda environment (metar-ingest)
- Logs: `/home/ldm/scripts/obs/metar/logs/metar-ingest.log`

## Maintenance

### Database Cleanup
```bash
# Truncate all observations
python scripts/cleanup_database.py truncate

# Delete old observations
python scripts/cleanup_database.py delete 30

# Full reset (drop/recreate)
./scripts/reset_database.sh
```

### Station Updates
```bash
# Reload station metadata
python scripts/load_stations.py
```

### Monitoring
```bash
# Check logs
tail -f logs/metar-ingest.log

# Check real-time ingestion
watch -n 5 'psql -U metar_user -d metar_obs -c "
SELECT COUNT(*) as total, MAX(observation_time) as latest 
FROM observations 
WHERE observation_time > NOW() - INTERVAL '\''1 hour'\'';"'

# Query metrics
psql -U metar_user -d metar_obs -c "
SELECT * FROM ingest_metrics 
ORDER BY metric_time DESC 
LIMIT 10;"

# Check connection pool status
psql -U postgres -c "
SELECT count(*) as connections, state, wait_event_type
FROM pg_stat_activity 
WHERE datname = 'metar_obs'
GROUP BY state, wait_event_type;"
```

## Dependencies

### Python Packages
- `python-metar`: METAR parsing
- `psycopg2-binary`: PostgreSQL driver
- `pyyaml`: Configuration files

### Database
- PostgreSQL 12+
- PostGIS 3.0+

### System
- LDM 6.13+ with IDD DDPLUS feed
- Linux with bash

## Troubleshooting

### No Data Arriving
1. Check LDM is running: `ldmadmin isrunning`
2. Check pqact pattern: `ldmadmin pqactcheck`
3. Verify `-close` flag in pqact.conf
4. Test with FILE action first: `PIPE -close → FILE /tmp/test.log`

### Buffering Issues
- **Symptom**: Data only appears after LDM stop
- **Cause**: Missing `-close` flag in pqact.conf
- **Fix**: Add `-close` to PIPE action

### Connection Issues
- **Symptom**: "connection pool not initialized"
- **Cause**: Database config file not found
- **Fix**: Verify `config/database.yml` exists and is readable

### Performance Degradation
- Check connection pool: `SELECT * FROM pg_stat_activity`
- Review batch sizes in logs
- Check disk I/O (database storage)
- Verify indexes exist: `\di` in psql

## Future Enhancements
- [ ] RESTful API for data access (FastAPI/pygeoapi)
- [ ] Real-time notifications via WebSockets
- [ ] Data quality checks and validation
- [ ] Automated data retention policies
- [ ] Grafana dashboards for monitoring
- [ ] WIS2 publishing support
- [ ] High-availability setup with multiple ingesters