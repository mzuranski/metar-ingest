"""
Database repository layer for simplified data access
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ObservationRepository:
    """Simplified interface for observation data access."""
    
    @staticmethod
    def insert_observation(station_id: str, obs_time: datetime, raw_metar: str,
                          is_correction: bool = False) -> Optional[int]:
        """
        Insert a new observation and return its ID.
        
        If is_correction is True, this will update an existing observation
        for the same station/time instead of skipping on conflict.
        """
        try:
            with DatabaseConnection.get_cursor() as cursor:
                if is_correction:
                    # For corrections, update existing or insert new
                    cursor.execute("""
                        INSERT INTO observations 
                        (station_id, observation_time, raw_metar)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (station_id, observation_time) DO UPDATE SET
                            raw_metar = EXCLUDED.raw_metar,
                            created_at = NOW()
                        RETURNING id
                    """, (station_id, obs_time, raw_metar))
                else:
                    # For normal observations, skip if exists
                    cursor.execute("""
                        INSERT INTO observations 
                        (station_id, observation_time, raw_metar)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (station_id, observation_time) DO NOTHING
                        RETURNING id
                    """, (station_id, obs_time, raw_metar))
                
                result = cursor.fetchone()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Error inserting observation: {e}", exc_info=True)
            return None
    
    @staticmethod
    def delete_observation_elements(obs_id: int) -> bool:
        """Delete all elements for an observation (used when replacing with correction)."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM observation_elements
                    WHERE observation_id = %s
                """, (obs_id,))
                return True
        except Exception as e:
            logger.error(f"Error deleting observation elements: {e}")
            return False
    
    @staticmethod
    def insert_element(obs_id: int, element_type: str, value: Optional[float], 
                       unit: Optional[str], text: Optional[str]) -> bool:
        """Insert a meteorological element."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO observation_elements 
                    (observation_id, element_type, element_value, element_unit, element_text)
                    VALUES (%s, %s, %s, %s, %s)
                """, (obs_id, element_type, value, unit, text))
                return True
        except Exception as e:
            logger.error(f"Error inserting element: {e}")
            return False
    
    @staticmethod
    def get_observations_with_location(start_time: datetime, 
                                       end_time: datetime) -> List[Dict]:
        """Retrieve observations with station location within a time range."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        o.id, o.station_id, o.observation_time, o.raw_metar,
                        s.station_name, s.latitude, s.longitude, s.elevation, s.country,
                        ST_Y(s.location::geometry) as geom_lat,
                        ST_X(s.location::geometry) as geom_lon
                    FROM observations o
                    LEFT JOIN stations s ON o.station_id = s.station_id
                    WHERE o.observation_time BETWEEN %s AND %s
                    ORDER BY o.observation_time DESC
                """, (start_time, end_time))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error retrieving observations: {e}")
            return []
    
    @staticmethod
    def get_observations_near_point(latitude: float, longitude: float, 
                                    radius_km: float = 50, 
                                    max_age_hours: int = 24) -> List[Dict]:
        """Get observations within radius of a point."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        o.id, o.station_id, o.observation_time, o.raw_metar,
                        s.station_name, s.latitude, s.longitude,
                        ST_Distance(
                            s.location::geography,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) / 1000 as distance_km
                    FROM observations o
                    JOIN stations s ON o.station_id = s.station_id
                    WHERE s.location IS NOT NULL
                      AND o.observation_time >= %s
                      AND ST_DWithin(
                          s.location::geography,
                          ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                          %s * 1000
                      )
                    ORDER BY distance_km, o.observation_time DESC
                """, (longitude, latitude, cutoff_time, longitude, latitude, radius_km))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error retrieving nearby observations: {e}")
            return []
    
    @staticmethod
    def delete_old_observations(days_old: int) -> int:
        """Delete observations older than specified days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM observations
                    WHERE observation_time < %s
                """, (cutoff_date,))
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error deleting old observations: {e}")
            return 0


class StationRepository:
    """Repository for station metadata."""
    
    @staticmethod
    def get_station_location(station_id: str) -> Optional[Dict]:
        """Get station location by ID."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    SELECT station_id, station_name, latitude, longitude, 
                           elevation, country
                    FROM stations
                    WHERE station_id = %s
                """, (station_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error retrieving station: {e}")
            return None
    
    @staticmethod
    def find_nearest_stations(latitude: float, longitude: float, 
                             limit: int = 10) -> List[Dict]:
        """Find nearest stations to a point."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        station_id, station_name, latitude, longitude, elevation, country,
                        ST_Distance(
                            location::geography,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                        ) / 1000 as distance_km
                    FROM stations
                    WHERE location IS NOT NULL
                    ORDER BY location <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    LIMIT %s
                """, (longitude, latitude, longitude, latitude, limit))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error finding nearest stations: {e}")
            return []


class MetricsRepository:
    """Simplified interface for metrics data access."""
    
    @staticmethod
    def insert_metrics(total: int, parsed: int, failed: int, 
                       errors: int, processing_time: int):
        """Insert processing metrics."""
        try:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ingest_metrics
                    (total_received, successfully_parsed, parse_failures, 
                     database_errors, processing_time_ms)
                    VALUES (%s, %s, %s, %s, %s)
                """, (total, parsed, failed, errors, processing_time))
        except Exception as e:
            logger.error(f"Error inserting metrics: {e}")
    
    @staticmethod
    def get_metrics_summary(hours: int = 24) -> Dict:
        """Get metrics summary for the last N hours."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        SUM(total_received) as total_received,
                        SUM(successfully_parsed) as successfully_parsed,
                        SUM(parse_failures) as parse_failures,
                        SUM(database_errors) as database_errors,
                        AVG(processing_time_ms) as avg_processing_time
                    FROM ingest_metrics
                    WHERE metric_time >= %s
                """, (cutoff_time,))
                return cursor.fetchone() or {}
        except Exception as e:
            logger.error(f"Error retrieving metrics summary: {e}")
            return {}