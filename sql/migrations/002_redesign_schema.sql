-- Schema redesign migration

BEGIN;

-- Drop old tables
DROP TABLE IF EXISTS observation_elements CASCADE;
DROP TABLE IF EXISTS observations CASCADE;
DROP TABLE IF EXISTS ingest_metrics CASCADE;
DROP TABLE IF EXISTS stations CASCADE;

-- Main observations table (simplified)
CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(4) NOT NULL,
    observation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_metar TEXT NOT NULL,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    present_weather TEXT,
    sky_conditions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(station_id, observation_time)
);

COMMENT ON TABLE observations IS 'Main table storing METAR observations';
COMMENT ON COLUMN observations.station_id IS 'ICAO station identifier';
COMMENT ON COLUMN observations.observation_time IS 'Time of observation (UTC)';
COMMENT ON COLUMN observations.raw_metar IS 'Complete raw METAR text';
COMMENT ON COLUMN observations.latitude IS 'Station latitude (if available)';
COMMENT ON COLUMN observations.longitude IS 'Station longitude (if available)';
COMMENT ON COLUMN observations.present_weather IS 'Weather phenomena (e.g., -RA, +SN)';
COMMENT ON COLUMN observations.sky_conditions IS 'Sky cover conditions';

-- Individual meteorological elements
CREATE TABLE observation_elements (
    id SERIAL PRIMARY KEY,
    observation_id INTEGER REFERENCES observations(id) ON DELETE CASCADE,
    element_type VARCHAR(50) NOT NULL,
    element_value NUMERIC,
    element_unit VARCHAR(20),
    element_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE observation_elements IS 'Individual meteorological elements extracted from METARs';
COMMENT ON COLUMN observation_elements.element_type IS 'Type of element (e.g., temperature, dewpoint, wind_speed, remarks)';
COMMENT ON COLUMN observation_elements.element_value IS 'Numeric value (NULL for text elements like remarks)';
COMMENT ON COLUMN observation_elements.element_text IS 'Text value (for remarks, weather codes, etc.)';

-- Station metadata (for future use)
CREATE TABLE stations (
    station_id VARCHAR(4) PRIMARY KEY,
    station_name VARCHAR(255),
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    elevation NUMERIC(6,1),
    country VARCHAR(2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE stations IS 'Weather station metadata';

-- Processing metrics
CREATE TABLE ingest_metrics (
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
CREATE INDEX idx_obs_station_time ON observations(station_id, observation_time DESC);
CREATE INDEX idx_obs_time ON observations(observation_time DESC);
CREATE INDEX idx_obs_coords ON observations(latitude, longitude) WHERE latitude IS NOT NULL;
CREATE INDEX idx_elements_obs_id ON observation_elements(observation_id);
CREATE INDEX idx_elements_type ON observation_elements(element_type);
CREATE INDEX idx_metrics_time ON ingest_metrics(metric_time DESC);

COMMIT;

-- Add PostGIS geometry columns

BEGIN;

-- Add geometry column to observations table
ALTER TABLE observations 
ADD COLUMN IF NOT EXISTS location geometry(Point, 4326);

-- Create spatial index
CREATE INDEX IF NOT EXISTS idx_obs_location ON observations USING GIST(location);

-- Add geometry column to stations table  
ALTER TABLE stations
ADD COLUMN IF NOT EXISTS location geometry(Point, 4326);

-- Create spatial index on stations
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations USING GIST(location);

-- Update existing records to populate geometry from lat/lon
UPDATE observations 
SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL;

UPDATE stations
SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL;

COMMENT ON COLUMN observations.location IS 'PostGIS point geometry (SRID 4326 - WGS84)';
COMMENT ON COLUMN stations.location IS 'PostGIS point geometry (SRID 4326 - WGS84)';

COMMIT;