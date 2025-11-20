"""
Unit tests for METAR parser
"""

import pytest
from datetime import datetime

from src.parsers.metar_parser import MetarParser


class TestMetarParser:
    """Test suite for MetarParser class."""
    
    def test_parse_basic_metar(self):
        """Test parsing a basic METAR."""
        metar_text = "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034 RMK AO2 SLP279 T10441172"
        
        result = MetarParser.parse(metar_text)
        
        assert result is not None
        assert result['station_id'] == 'KJFK'
        assert result['raw_metar'] == metar_text
        assert len(result['elements']) > 0
    
    def test_parse_with_temperature(self):
        """Test that temperature is correctly extracted."""
        metar_text = "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034"
        
        result = MetarParser.parse(metar_text)
        
        # Find temperature element
        temp_elements = [e for e in result['elements'] if e[0] == 'temperature']
        assert len(temp_elements) == 1
        assert temp_elements[0][1] == -4.0  # M04 = -4°C
        assert temp_elements[0][2] == 'celsius'
    
    def test_parse_with_wind(self):
        """Test that wind data is correctly extracted."""
        metar_text = "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034"
        
        result = MetarParser.parse(metar_text)
        
        # Find wind elements
        wind_speed = [e for e in result['elements'] if e[0] == 'wind_speed']
        wind_dir = [e for e in result['elements'] if e[0] == 'wind_direction']
        
        assert len(wind_speed) == 1
        assert wind_speed[0][1] == 8.0
        assert wind_speed[0][2] == 'knots'
        
        assert len(wind_dir) == 1
        assert wind_dir[0][1] == 310.0
    
    def test_parse_invalid_metar(self):
        """Test that invalid METAR returns None."""
        metar_text = "INVALID METAR TEXT"
        
        result = MetarParser.parse(metar_text)
        
        assert result is None
    
    def test_parse_batch(self):
        """Test parsing multiple METARs."""
        metar_texts = [
            "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034",
            "METAR KLGA 201851Z 30010KT 10SM FEW250 M03/M16 A3035",
            "INVALID METAR",
        ]
        
        parsed, failed = MetarParser.parse_batch(metar_texts)
        
        assert len(parsed) == 2
        assert len(failed) == 1
        assert parsed[0]['station_id'] == 'KJFK'
        assert parsed[1]['station_id'] == 'KLGA'