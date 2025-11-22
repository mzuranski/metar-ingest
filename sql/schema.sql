-- METAR Observation Database Schema

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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_obs_station_time ON observations(station_id, observation_time DESC);
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(observation_time DESC);
CREATE INDEX IF NOT EXISTS idx_obs_location ON observations USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_elements_obs_id ON observation_elements(observation_id);
CREATE INDEX IF NOT EXISTS idx_elements_type ON observation_elements(element_type);
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON ingest_metrics(metric_time DESC);

-- View for pygeoapi: combines observations with station location data and flattened elements
CREATE OR REPLACE VIEW observations_with_location AS
SELECT 
    o.id,
    o.station_id,
    o.observation_time,
    o.raw_metar,
    o.created_at,
    s.location,
    s.station_name,
    s.latitude,
    s.longitude,
    s.elevation,
    s.country,
    -- Flattened meteorological elements
    MAX(CASE WHEN e.element_type = 'temperature' THEN e.element_value END) AS temperature,
    MAX(CASE WHEN e.element_type = 'temperature' THEN e.element_unit END) AS temperature_unit,
    MAX(CASE WHEN e.element_type = 'dewpoint' THEN e.element_value END) AS dewpoint,
    MAX(CASE WHEN e.element_type = 'dewpoint' THEN e.element_unit END) AS dewpoint_unit,
    MAX(CASE WHEN e.element_type = 'wind_speed' THEN e.element_value END) AS wind_speed,
    MAX(CASE WHEN e.element_type = 'wind_speed' THEN e.element_unit END) AS wind_speed_unit,
    MAX(CASE WHEN e.element_type = 'wind_direction' THEN e.element_value END) AS wind_direction,
    MAX(CASE WHEN e.element_type = 'wind_gust' THEN e.element_value END) AS wind_gust,
    MAX(CASE WHEN e.element_type = 'wind_gust' THEN e.element_unit END) AS wind_gust_unit,
    MAX(CASE WHEN e.element_type = 'visibility' THEN e.element_value END) AS visibility,
    MAX(CASE WHEN e.element_type = 'visibility' THEN e.element_unit END) AS visibility_unit,
    MAX(CASE WHEN e.element_type = 'pressure' THEN e.element_value END) AS pressure,
    MAX(CASE WHEN e.element_type = 'pressure' THEN e.element_unit END) AS pressure_unit,
    MAX(CASE WHEN e.element_type = 'present_weather' THEN e.element_text END) AS present_weather,
    MAX(CASE WHEN e.element_type = 'remarks' THEN e.element_text END) AS remarks,
    -- Sky condition layers
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_1' THEN e.element_text END) AS sky_cover_layer_1,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_1' THEN e.element_value END) AS cloud_base_layer_1,
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_2' THEN e.element_text END) AS sky_cover_layer_2,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_2' THEN e.element_value END) AS cloud_base_layer_2,
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_3' THEN e.element_text END) AS sky_cover_layer_3,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_3' THEN e.element_value END) AS cloud_base_layer_3,
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_4' THEN e.element_text END) AS sky_cover_layer_4,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_4' THEN e.element_value END) AS cloud_base_layer_4,
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_5' THEN e.element_text END) AS sky_cover_layer_5,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_5' THEN e.element_value END) AS cloud_base_layer_5,
    MAX(CASE WHEN e.element_type = 'sky_cover_layer_6' THEN e.element_text END) AS sky_cover_layer_6,
    MAX(CASE WHEN e.element_type = 'cloud_base_layer_6' THEN e.element_value END) AS cloud_base_layer_6
FROM observations o
LEFT JOIN stations s ON o.station_id = s.station_id
LEFT JOIN observation_elements e ON o.id = e.observation_id
WHERE o.observation_time >= NOW() - INTERVAL '1 hour'
GROUP BY o.id, o.station_id, o.observation_time, o.raw_metar, o.created_at,
         s.location, s.station_name, s.latitude, s.longitude, s.elevation, s.country
ORDER BY o.observation_time DESC;

COMMENT ON VIEW observations_with_location IS 
    'View combining observations with station location data and flattened meteorological elements for pygeoapi';