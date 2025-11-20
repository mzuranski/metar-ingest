"""
METAR parser using python-metar library
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from metar.Metar import Metar
from src.parsers.weather_codes import get_weather_code, parse_sky_cover_oktas

logger = logging.getLogger(__name__)


class MetarParser:
    """Parses METAR observations into structured data."""
    
    @staticmethod
    def parse(metar_text: str, lookup_station: bool = True) -> Optional[Dict]:
        """
        Parse a METAR string into structured data.
        
        Returns a dictionary with:
        - station_id: Station identifier
        - obs_time: Observation datetime
        - raw_metar: Original METAR text
        - is_correction: Whether this is a correction (COR) or amendment (AMD)
        - elements: List of (type, value, unit, text) tuples
        """
        try:
            obs = Metar(metar_text)
            
            elements = []
            
            # Check if this is a correction or amendment
            is_correction = False
            if hasattr(obs, 'mod'):
                # mod can be 'COR' (correction), 'AMD' (amendment), 'AUTO' (automated), etc.
                if obs.mod and obs.mod.upper() in ['COR', 'AMD']:
                    is_correction = True
                    logger.info(f"Processing {obs.mod} for {obs.station_id} at {obs.time}")
            
            # Extract temperature
            if obs.temp:
                temp_c = obs.temp.value('C')
                elements.append(('temperature', temp_c, 'celsius', None))
            
            # Extract dewpoint
            if obs.dewpt:
                dewpt_c = obs.dewpt.value('C')
                elements.append(('dewpoint', dewpt_c, 'celsius', None))
            
            # Extract pressure
            if obs.press:
                press_hpa = obs.press.value('HPA')
                elements.append(('pressure', press_hpa, 'hPa', None))
            
            # Extract wind
            if obs.wind_speed:
                wind_kts = obs.wind_speed.value('KT')
                elements.append(('wind_speed', wind_kts, 'knots', None))
            
            if obs.wind_dir:
                wind_dir_val = obs.wind_dir.value()
                if wind_dir_val and wind_dir_val != 'VRB':
                    try:
                        elements.append(('wind_direction', float(wind_dir_val), 
                                       'degrees', None))
                    except (ValueError, TypeError):
                        pass
            
            if obs.wind_gust:
                gust_kts = obs.wind_gust.value('KT')
                elements.append(('wind_gust', gust_kts, 'knots', None))
            
            # Extract visibility
            if obs.vis:
                vis_m = obs.vis.value('M')
                elements.append(('visibility', vis_m, 'meters', None))
            
            # Get observation time
            obs_time = obs.time
            if callable(obs_time):
                obs_time = obs_time()
            
            if not obs_time or not isinstance(obs_time, datetime):
                logger.warning(f"Invalid observation time for {obs.station_id}, using current time")
                obs_time = datetime.utcnow()
            
            # Get remarks as a text element
            raw_remarks = None
            if hasattr(obs, 'remarks'):
                if callable(obs.remarks):
                    raw_remarks = obs.remarks()
                else:
                    raw_remarks = obs.remarks
                
                if raw_remarks:
                    elements.append(('remarks', None, None, raw_remarks))
            
            # Extract present weather with WMO codes
            if hasattr(obs, 'weather') and obs.weather:
                for wx in obs.weather:
                    wx_str = ''.join([part for part in wx if part])
                    if wx_str:
                        wmo_code = get_weather_code(wx_str)
                        elements.append(('present_weather', wmo_code, 'wmo_code', wx_str))
            
            # Extract sky conditions as oktas
            if hasattr(obs, 'sky') and obs.sky:
                for layer_idx, layer in enumerate(obs.sky):
                    cover = layer[0] if len(layer) > 0 else ''
                    height = layer[1] if len(layer) > 1 else None
                    
                    if cover:
                        oktas, description = parse_sky_cover_oktas(cover)
                        
                        # Store sky cover as oktas
                        elements.append((f'sky_cover_layer_{layer_idx + 1}', oktas, 'oktas', cover))
                        
                        # Store cloud base height if available
                        if height:
                            try:
                                if hasattr(height, 'value'):
                                    height_ft = int(height.value('FT'))
                                else:
                                    height_ft = int(height)
                                elements.append((f'cloud_base_layer_{layer_idx + 1}', height_ft, 'feet', None))
                            except (ValueError, TypeError, AttributeError):
                                pass
            
            return {
                'station_id': obs.station_id,
                'obs_time': obs_time,
                'raw_metar': metar_text.strip(),
                'is_correction': is_correction,
                'elements': elements,
            }
            
        except Exception as e:
            logger.error(f"Error parsing METAR '{metar_text}': {e}", exc_info=True)
            return None
    
    @staticmethod
    def parse_batch(metar_texts: List[str], lookup_station: bool = True) -> Tuple[List[Dict], List[str]]:
        """
        Parse multiple METAR strings.
        
        Returns:
        - List of successfully parsed observations
        - List of failed METAR texts
        """
        parsed = []
        failed = []
        
        for metar_text in metar_texts:
            result = MetarParser.parse(metar_text, lookup_station=lookup_station)
            if result:
                parsed.append(result)
            else:
                failed.append(metar_text)
        
        return parsed, failed