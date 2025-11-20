"""
Database models (currently using raw SQL, but models defined for reference)
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, Float, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Metar(Base):
    __tablename__ = 'metar_data'

    id = Column(Integer, primary_key=True)
    temperature = Column(Float)
    dewpoint = Column(Float)
    visibility = Column(Float)
    full_metar = Column(Text)
    remarks = Column(Text)

    def __repr__(self):
        return f"<Metar(id={self.id}, temperature={self.temperature}, dewpoint={self.dewpoint}, visibility={self.visibility}, full_metar='{self.full_metar}', remarks='{self.remarks}')>"


class Observation:
    """Model representing a METAR observation."""
    
    def __init__(self, station_id: str, observation_time: datetime,
                 raw_metar: str, raw_remarks: Optional[str] = None,
                 latitude: float = 0.0, longitude: float = 0.0):
        self.station_id = station_id
        self.observation_time = observation_time
        self.raw_metar = raw_metar
        self.raw_remarks = raw_remarks
        self.latitude = latitude
        self.longitude = longitude


class ObservationElement:
    """Model representing a meteorological element."""
    
    def __init__(self, observation_id: int, element_type: str,
                 element_value: float, element_unit: str,
                 element_quality: str = 'good'):
        self.observation_id = observation_id
        self.element_type = element_type
        self.element_value = element_value
        self.element_unit = element_unit
        self.element_quality = element_quality


class Station:
    """Model representing a weather station."""
    
    def __init__(self, station_id: str, station_name: str,
                 latitude: float, longitude: float,
                 elevation: Optional[float] = None,
                 country: Optional[str] = None):
        self.station_id = station_id
        self.station_name = station_name
        self.latitude = latitude
        self.longitude = longitude
        self.elevation = elevation
        self.country = country


class IngestMetric:
    """Model representing ingestion metrics."""
    
    def __init__(self, total_received: int, successfully_parsed: int,
                 parse_failures: int, database_errors: int,
                 processing_time_ms: int):
        self.total_received = total_received
        self.successfully_parsed = successfully_parsed
        self.parse_failures = parse_failures
        self.database_errors = database_errors
        self.processing_time_ms = processing_time_ms