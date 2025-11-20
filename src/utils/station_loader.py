"""
Parser and loader for WMO station metadata
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StationLoader:
    """Load and parse WMO station metadata files."""
    
    # US state codes that appear in the CD column
    US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC', 'PR', 'VI', 'GU', 'AS', 'MP'  # US territories
    }
    
    @staticmethod
    def parse_worldstanew(filepath: Path) -> List[Dict]:
        """
        Parse worldstanew.txt station file.
        
        Expected fixed-width format:
        CD  STATION         ICAO  IATA  SYNOP   LAT     LON    ELEV(m)S  T  U  F  H
        AE ABU DHABI        OMAA  AUH   41217  24 26N  054 39E   27   X     X  X  X
        NY NYC/JFK INTL     KJFK  JFK   74486  40 38N  073 47W    4   X  X  X  X  X
        
        Returns list of station dictionaries.
        """
        stations = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip header line and empty lines
                    if line_num == 1:
                        continue
                    if not line.strip():
                        continue
                    
                    # Try to parse the line
                    station = StationLoader._parse_station_line(line)
                    if station:
                        stations.append(station)
            
            logger.info(f"Parsed {len(stations)} stations from {filepath}")
            return stations
            
        except Exception as e:
            logger.error(f"Error reading station file {filepath}: {e}")
            return []
    
    @staticmethod
    def _parse_station_line(line: str) -> Optional[Dict]:
        """
        Parse a single station line from worldstanew.txt format.
        
        Fixed-width positions:
        - Country/State: 0-2
        - Station name: 3-18
        - ICAO: 19-24
        - IATA: 25-29
        - SYNOP: 30-36
        - Latitude: 37-44 (format: DD MMN/S)
        - Longitude: 45-53 (format: DDD MME/W)
        - Elevation: 54-62
        """
        try:
            # Extract fields
            cd_code = line[0:2].strip() if len(line) > 2 else None
            station_name = line[3:19].strip() if len(line) > 19 else None
            icao = line[19:25].strip() if len(line) > 25 else None
            lat_str = line[37:45].strip() if len(line) > 45 else None
            lon_str = line[45:54].strip() if len(line) > 54 else None
            elev_str = line[54:62].strip() if len(line) > 62 else None
            
            # Must have ICAO code
            if not icao or len(icao) != 4:
                return None
            
            # Normalize country code - convert US state codes to "US"
            country = None
            if cd_code:
                if cd_code in StationLoader.US_STATES:
                    country = 'US'
                else:
                    country = cd_code
            
            # Parse latitude (format: "24 26N" or "24 26S")
            latitude = StationLoader._parse_coordinate(lat_str, is_latitude=True)
            
            # Parse longitude (format: "054 39E" or "054 39W")
            longitude = StationLoader._parse_coordinate(lon_str, is_latitude=False)
            
            # Parse elevation
            elevation = None
            if elev_str:
                try:
                    elevation = float(elev_str)
                except ValueError:
                    pass
            
            return {
                'station_id': icao,
                'station_name': station_name if station_name else None,
                'country': country,
                'latitude': latitude,
                'longitude': longitude,
                'elevation': elevation,
            }
            
        except Exception as e:
            logger.debug(f"Could not parse line: {line.strip()[:50]}... Error: {e}")
            return None
    
    @staticmethod
    def _parse_coordinate(coord_str: Optional[str], is_latitude: bool) -> Optional[float]:
        """
        Parse coordinate string in format "DD MMN/S" or "DDD MME/W".
        
        Examples:
        - "24 26N" -> 24.433333
        - "054 39E" -> 54.65
        - "24 26S" -> -24.433333
        - "054 39W" -> -54.65
        """
        if not coord_str:
            return None
        
        try:
            # Match pattern: digits space digits N/S/E/W
            pattern = r'(\d+)\s+(\d+)([NSEW])'
            match = re.match(pattern, coord_str)
            
            if not match:
                return None
            
            degrees = int(match.group(1))
            minutes = int(match.group(2))
            direction = match.group(3)
            
            # Convert to decimal degrees
            decimal = degrees + (minutes / 60.0)
            
            # Apply sign based on direction
            if direction in ['S', 'W']:
                decimal = -decimal
            
            return round(decimal, 6)
            
        except Exception as e:
            logger.debug(f"Could not parse coordinate '{coord_str}': {e}")
            return None
    
    @staticmethod
    def load_to_database(stations: List[Dict], connection_pool) -> int:
        """
        Load stations into database with PostGIS geometry.
        
        Returns number of stations loaded.
        """
        from src.database.connection import DatabaseConnection
        
        loaded = 0
        
        try:
            with DatabaseConnection.get_cursor() as cursor:
                for station in stations:
                    try:
                        # If we have coordinates, include PostGIS geometry
                        if station['latitude'] is not None and station['longitude'] is not None:
                            cursor.execute("""
                                INSERT INTO stations 
                                (station_id, station_name, latitude, longitude, elevation, country, location)
                                VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                                ON CONFLICT (station_id) DO UPDATE SET
                                    station_name = EXCLUDED.station_name,
                                    latitude = EXCLUDED.latitude,
                                    longitude = EXCLUDED.longitude,
                                    elevation = EXCLUDED.elevation,
                                    country = EXCLUDED.country,
                                    location = EXCLUDED.location,
                                    last_updated = NOW()
                            """, (
                                station['station_id'],
                                station['station_name'],
                                station['latitude'],
                                station['longitude'],
                                station['elevation'],
                                station['country'],
                                station['longitude'],  # PostGIS: longitude first
                                station['latitude']    # PostGIS: latitude second
                            ))
                        else:
                            # No coordinates, insert without location
                            cursor.execute("""
                                INSERT INTO stations 
                                (station_id, station_name, latitude, longitude, elevation, country)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (station_id) DO UPDATE SET
                                    station_name = EXCLUDED.station_name,
                                    latitude = EXCLUDED.latitude,
                                    longitude = EXCLUDED.longitude,
                                    elevation = EXCLUDED.elevation,
                                    country = EXCLUDED.country,
                                    last_updated = NOW()
                            """, (
                                station['station_id'],
                                station['station_name'],
                                station['latitude'],
                                station['longitude'],
                                station['elevation'],
                                station['country']
                            ))
                        
                        loaded += 1
                        
                        # Log progress every 1000 stations
                        if loaded % 1000 == 0:
                            logger.info(f"Loaded {loaded} stations...")
                            
                    except Exception as e:
                        logger.error(f"Error inserting station {station.get('station_id')}: {e}")
            
            logger.info(f"Loaded {loaded} stations to database")
            return loaded
            
        except Exception as e:
            logger.error(f"Error loading stations to database: {e}")
            return 0