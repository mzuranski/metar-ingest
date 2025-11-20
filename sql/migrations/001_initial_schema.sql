-- Initial schema migration

-- This migration creates the initial database schema
-- Apply with: psql -U metar_user -d metar_obs -f 001_initial_schema.sql

BEGIN;

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Main observations table
CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(4) NOT NULL,
    observation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_metar TEXT NOT NULL,
    raw_remarks TEXT,
    location GEOGRAPHY(POINT, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(station_id, observation_time)
);

COMMENT ON TABLE observations IS 'Main table storing METAR observations';
COMMENT ON COLUMN observations.station_id IS 'ICAO station identifier';
COMMENT ON COLUMN observations.observation_time IS 'Time of observation (UTC)';
COMMENT ON COLUMN observations.raw_metar IS 'Complete raw METAR text';
COMMENT ON COLUMN observations.raw_remarks IS 'Remarks section of METAR';
COMMENT ON COLUMN observations.location IS 'Geographic location (PostGIS point)';

-- Individual meteorological elements
CREATE TABLE IF NOT EXISTS observation_elements (
    id SERIAL PRIMARY KEY,
    observation_id INTEGER REFERENCES observations(id) ON DELETE CASCADE,
    element_type VARCHAR(50) NOT NULL,
    element_value NUMERIC,
    element_unit VARCHAR(20),
    element_quality VARCHAR(20) DEFAULT 'unknown',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE observation_elements IS 'Individual meteorological elements extracted from METARs';
COMMENT ON COLUMN observation_elements.element_type IS 'Type of element (e.g., temperature, dewpoint, wind_speed)';
COMMENT ON COLUMN observation_elements.element_quality IS 'Quality flag (good, suspect, bad, unknown)';

-- Station metadata
CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(4) PRIMARY KEY,
    station_name VARCHAR(255),
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    elevation NUMERIC(6,1),
    country VARCHAR(2),
    location GEOGRAPHY(POINT, 4326),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE stations IS 'Weather station metadata';

-- Processing metrics
CREATE TABLE IF NOT EXISTS ingest_metrics (
    id SERIAL PRIMARY KEY,
    metric_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_received INTEGER DEFAULT 0,
    successfully_parsed INTEGER DEFAULT 0,
    parse_failures INTEGER DEFAULT 0,
    database_errors INTEGER DEFAULT 0,
    processing_time_ms INTEGER
);

COMMENT ON TABLE ingest_metrics IS 'Metrics for monitoring ingestion process';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_obs_station_time ON observations(station_id, observation_time DESC);
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(observation_time DESC);
CREATE INDEX IF NOT EXISTS idx_obs_location ON observations USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_elements_obs_id ON observation_elements(observation_id);
CREATE INDEX IF NOT EXISTS idx_elements_type ON observation_elements(element_type);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON ingest_metrics(metric_time DESC);

COMMIT;