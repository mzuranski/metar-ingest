-- Simplify observations table to use station FK and move data to elements

BEGIN;

-- Drop and recreate observations table (simpler structure)
DROP TABLE IF EXISTS observation_elements CASCADE;
DROP TABLE IF EXISTS observations CASCADE;

CREATE TABLE observations (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(4) NOT NULL REFERENCES stations(station_id),
    observation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_metar TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(station_id, observation_time)
);

COMMENT ON TABLE observations IS 'Main table storing METAR observations';
COMMENT ON COLUMN observations.station_id IS 'ICAO station identifier (FK to stations)';
COMMENT ON COLUMN observations.observation_time IS 'Time of observation (UTC)';
COMMENT ON COLUMN observations.raw_metar IS 'Complete raw METAR text';

-- Observation elements with all parsed data
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
COMMENT ON COLUMN observation_elements.element_type IS 'Type: temperature, dewpoint, wind_speed, wind_direction, pressure, visibility, sky_cover, present_weather, remarks, etc.';
COMMENT ON COLUMN observation_elements.element_value IS 'Numeric value (NULL for text elements)';
COMMENT ON COLUMN observation_elements.element_unit IS 'Unit of measurement (celsius, knots, hPa, oktas, etc.)';
COMMENT ON COLUMN observation_elements.element_text IS 'Text value (for remarks, weather codes, etc.)';

-- Indexes
CREATE INDEX idx_obs_station_time ON observations(station_id, observation_time DESC);
CREATE INDEX idx_obs_time ON observations(observation_time DESC);
CREATE INDEX idx_elements_obs_id ON observation_elements(observation_id);
CREATE INDEX idx_elements_type ON observation_elements(element_type);

COMMIT;