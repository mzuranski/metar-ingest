# METAR Ingestion Operations Guide

## Quick Start

### Initial Setup

1. **Install dependencies:**
```bash
cd /home/ldm/scripts/obs/metar
conda env create -f environment.yml
conda activate metar-ingest
```

2. **Configure database:**
```bash
# Edit config/database.yml with your credentials
nano config/database.yml

# Run migrations
psql -U postgres -c "CREATE DATABASE metar_obs OWNER metar_user;"
psql -U postgres -d metar_obs -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -U metar_user -d metar_obs -f sql/migrations/001_initial_schema.sql
psql -U metar_user -d metar_obs -f sql/migrations/002_add_indexes.sql
psql -U metar_user -d metar_obs -f sql/migrations/003_add_postgis_location.sql
psql -U metar_user -d metar_obs -f sql/migrations/004_simplify_observations.sql
```

3. **Load station data:**
```bash
python scripts/load_stations.py
```

4. **Configure LDM:**
```bash
# Edit ~ldm/etc/pqact.conf and add:
DDPLUS|IDS	^SAUS[^_]*
    PIPE	-close	/home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh

# IMPORTANT: The -close flag is REQUIRED for real-time processing
```

5. **Make scripts executable:**
```bash
chmod +x scripts/ldm_ingest.sh
chmod +x scripts/reset_database.sh
```

6. **Start LDM:**
```bash
ldmadmin restart
```

### Testing

#### Test Parser Directly
```bash
# Single METAR
echo "METAR KJFK 202051Z 31008KT 10SM FEW250 M04/M17 A3034 RMK AO2" | \
    /home/ldm/.conda/envs/metar-ingest/bin/python -u src/main.py

# Simulate LDM product format
cat > /tmp/test_product.txt << 'EOF'
367
SAUS99 KWBC 202115
METAR
KDVP 202113Z AUTO 32009KT 10SM OVC022 07/05 A3005 RMK AO2
     T00660050=
KXVG 202113Z AUTO 29006KT 8SM BKN015 02/M02 A2998 RMK AO2=
EOF

# Add control character
printf '\x01' > /tmp/test_ldm.txt
cat /tmp/test_product.txt >> /tmp/test_ldm.txt

# Test
cat /tmp/test_ldm.txt | /home/ldm/.conda/envs/metar-ingest/bin/python -u src/main.py
```

#### Test LDM Integration
```bash
# First, test that LDM is sending data
# Temporarily change pqact.conf to:
DDPLUS|IDS	^SAUS[^_]*
    FILE	-close	/tmp/metar_test.txt

ldmadmin restart

# Wait 1 minute, then check:
tail /tmp/metar_test.txt  # Should see METAR products

# If data appears, change back to PIPE and restart:
DDPLUS|IDS	^SAUS[^_]*
    PIPE	-close	/home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh

ldmadmin restart
```

### Verify Data

```bash
# Check recent observations
psql -U metar_user -d metar_obs -c "
SELECT 
    o.station_id,
    s.station_name,
    o.observation_time,
    COUNT(e.id) as elements
FROM observations o
JOIN stations s ON o.station_id = s.station_id
LEFT JOIN observation_elements e ON o.id = e.observation_id
WHERE o.observation_time > NOW() - INTERVAL '1 hour'
GROUP BY o.id, o.station_id, s.station_name, o.observation_time
ORDER BY o.observation_time DESC
LIMIT 20;
"

# Check ingestion rate
psql -U metar_user -d metar_obs -c "
SELECT 
    date_trunc('minute', observation_time) as minute,
    COUNT(*) as obs_count
FROM observations
WHERE observation_time > NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute DESC
LIMIT 10;
"
```

### Spatial Queries

```bash
# Find observations near New York (within 50km, last 6 hours)
psql -U metar_user -d metar_obs -c "
SELECT 
    o.station_id,
    s.station_name,
    o.observation_time,
    ROUND(ST_Distance(
        s.location::geography,
        ST_SetSRID(ST_MakePoint(-73.935242, 40.730610), 4326)::geography
    ) / 1000, 2) as distance_km
FROM observations o
JOIN stations s ON o.station_id = s.station_id
WHERE s.location IS NOT NULL
  AND o.observation_time > NOW() - INTERVAL '6 hours'
  AND ST_DWithin(
      s.location::geography,
      ST_SetSRID(ST_MakePoint(-73.935242, 40.730610), 4326)::geography,
      50000
  )
ORDER BY distance_km
LIMIT 10;
"
```

## Troubleshooting

### Problem: No data appearing in database

**Diagnosis:**
```bash
# 1. Check if LDM is running
ldmadmin isrunning

# 2. Check if script is being called
ps aux | grep metar | grep python

# 3. Check logs
tail -f /home/ldm/scripts/obs/metar/logs/metar-ingest.log

# 4. Check LDM logs
tail -f ~ldm/logs/ldmd.log
tail -f ~ldm/logs/pqact.log
```

**Solutions:**
1. **LDM not sending data**: Check feed subscription, firewall
2. **Script not running**: Check pqact.conf syntax, script permissions
3. **Missing `-close` flag**: Products buffer until LDM stops
4. **Database connection**: Verify config/database.yml settings

### Problem: Data only appears after LDM stops

**Cause:** Missing `-close` flag in pqact.conf

**Fix:**
```bash
# Edit ~ldm/etc/pqact.conf
# Change from:
PIPE	/home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh

# To:
PIPE	-close	/home/ldm/scripts/obs/metar/scripts/ldm_ingest.sh

# Restart
ldmadmin restart
```

### Problem: Slow processing

**Diagnosis:**
```bash
# Check log level (should be INFO, not DEBUG)
grep "level" config/settings.py

# Check batch processing times
grep "Batch:" logs/metar-ingest.log | tail -20

# Check database performance
psql -U metar_user -d metar_obs -c "
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**Solutions:**
1. Set log level to INFO
2. Run `VACUUM ANALYZE observations;`
3. Check indexes exist
4. Increase connection pool size in database.yml

### Problem: Parse errors

**Diagnosis:**
```bash
# Check for parse failures
grep "Error parsing" logs/metar-ingest.log | tail -20

# Check specific METAR
psql -U metar_user -d metar_obs -c "
SELECT raw_metar FROM observations 
WHERE station_id = 'KJFK' 
ORDER BY observation_time DESC 
LIMIT 1;
"
```

**Common Issues:**
- Non-standard METAR format
- Missing station in database
- Corrupted product data

### Problem: Foreign key violations

**Cause:** Station not in database

**Fix:**
```bash
# Reload stations
python scripts/load_stations.py

# Or add specific station
psql -U metar_user -d metar_obs -c "
INSERT INTO stations (station_id, station_name, country, latitude, longitude, elevation)
VALUES ('KJFK', 'John F Kennedy Intl Airport', 'US', 40.6398, -73.7789, 4);
"
```

## Monitoring

### Real-Time Monitoring

```bash
# Watch log in real-time
tail -f logs/metar-ingest.log

# Watch database growth
watch -n 5 'psql -U metar_user -d metar_obs -c "
SELECT 
    COUNT(*) as total_obs,
    COUNT(DISTINCT station_id) as stations,
    MAX(observation_time) as latest_obs,
    NOW() - MAX(observation_time) as lag
FROM observations;"'

# Monitor ingestion rate
watch -n 10 'psql -U metar_user -d metar_obs -c "
SELECT 
    SUM(total_received) as received,
    SUM(successfully_parsed) as parsed,
    SUM(parse_failures) as failed,
    AVG(processing_time_ms) as avg_ms
FROM ingest_metrics
WHERE metric_time > NOW() - INTERVAL '\''10 minutes'\'';"'
```

### Performance Metrics

```sql
-- Hourly ingestion stats
SELECT 
    date_trunc('hour', metric_time) as hour,
    SUM(total_received) as received,
    SUM(successfully_parsed) as parsed,
    SUM(parse_failures) as failed,
    AVG(processing_time_ms) as avg_ms
FROM ingest_metrics
WHERE metric_time > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Top stations by observation count
SELECT 
    station_id,
    COUNT(*) as obs_count,
    MAX(observation_time) as latest
FROM observations
WHERE observation_time > NOW() - INTERVAL '24 hours'
GROUP BY station_id
ORDER BY obs_count DESC
LIMIT 20;

-- Database connection status
SELECT count(*), state, wait_event_type
FROM pg_stat_activity 
WHERE datname = 'metar_obs'
GROUP BY state, wait_event_type;
```

### Health Checks

```bash
# Create health check script
cat > /home/ldm/scripts/obs/metar/check_health.sh << 'EOF'
#!/bin/bash

# Check if process is running
if ! pgrep -f "python.*metar.*main.py" > /dev/null; then
    echo "ERROR: METAR ingestion process not running"
    exit 1
fi

# Check database connectivity
if ! psql -U metar_user -d metar_obs -c "SELECT 1;" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to database"
    exit 1
fi

# Check recent data (should have obs within last 10 minutes)
RECENT=$(psql -U metar_user -d metar_obs -t -c "
SELECT COUNT(*) FROM observations 
WHERE observation_time > NOW() - INTERVAL '10 minutes';
")

if [ "$RECENT" -eq 0 ]; then
    echo "WARNING: No observations in last 10 minutes"
    exit 1
fi

echo "OK: Process running, database connected, recent data present"
exit 0
EOF

chmod +x check_health.sh

# Run health check
./check_health.sh
```

## Maintenance Schedule

### Daily
- Monitor logs for errors: `grep ERROR logs/metar-ingest.log`
- Check ingestion metrics (see Performance Metrics above)
- Verify recent data arrival

### Weekly
- Review database size: `SELECT pg_size_pretty(pg_database_size('metar_obs'));`
- Check for slow queries: Review pg_stat_statements
- Analyze batch processing times

### Monthly
- Run `VACUUM ANALYZE` on all tables
- Review and adjust data retention policy
- Update station metadata if needed: `python scripts/load_stations.py`
- Review and archive old logs

## Emergency Procedures

### Service Down
```bash
# Check process status
ps aux | grep python.*metar
ps aux | grep ldm

# Check what killed it
dmesg | tail -50
journalctl -u ldm -n 50

# Restart LDM (will restart ingestion)
ldmadmin restart

# Verify it's working
tail -f logs/metar-ingest.log
```

### Database Issues
```bash
# Check connections
psql -U postgres -c "
SELECT * FROM pg_stat_activity 
WHERE datname = 'metar_obs';"

# Kill hung connections
psql -U postgres -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'metar_obs' 
AND state = 'idle in transaction';"

# Restart PostgreSQL
sudo systemctl restart postgresql

# Restart LDM (will reconnect)
ldmadmin restart
```

### Clear Everything and Start Fresh
```bash
# Stop LDM
ldmadmin stop

# Reset database
./scripts/reset_database.sh

# Start LDM
ldmadmin start

# Monitor
tail -f logs/metar-ingest.log
```

### High Load / Performance Issues
```bash
# Check system resources
top
iotop
df -h

# Check database performance
psql -U postgres -c "
SELECT * FROM pg_stat_database 
WHERE datname = 'metar_obs';"

# If needed, increase connection pool
# Edit config/database.yml:
pool:
  min_connections: 2
  max_connections: 20

# Restart LDM
ldmadmin restart
```

## Best Practices

1. **Always use `-close` flag** in pqact.conf for real-time ingestion
2. **Monitor logs regularly** for parse errors or database issues
3. **Keep station data updated** - reload periodically
4. **Set up log rotation** to prevent disk fill
5. **Run VACUUM ANALYZE monthly** to maintain performance
6. **Test changes** in development before production
7. **Monitor database size** and implement retention policy
8. **Use persistent connections** - don't restart unnecessarily
9. **Keep backups** of configuration files
10. **Document custom changes** to station data or config

## Advanced Configuration

### Adjust Batch Size
```python
# In src/main.py, line with process_stream():
process_stream(batch_size=200)  # Increase for higher throughput
```

### Change Log Level
```bash
# Temporarily (for debugging):
export LOG_LEVEL=DEBUG
ldmadmin restart

# Permanently in config/settings.py:
'level': 'DEBUG'  # Change INFO to DEBUG
```

### Increase Connection Pool
```yaml
# In config/database.yml:
pool:
  min_connections: 5    # More persistent connections
  max_connections: 25   # Higher peak capacity
```

### Custom Data Retention
```bash
# Delete observations older than 7 days (run daily via cron)
python scripts/cleanup_database.py delete 7

# Add to crontab:
0 2 * * * /home/ldm/scripts/obs/metar/scripts/cleanup_database.py delete 7
```