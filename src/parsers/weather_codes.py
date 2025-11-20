"""
Weather phenomena to WMO code mapping
Based on: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
"""

# WMO present weather codes (ww)
WEATHER_CODE_MAP = {
    # Precipitation
    'DZ': 50,      # Drizzle
    '-DZ': 50,     # Light drizzle
    'DZ': 51,      # Moderate drizzle
    '+DZ': 53,     # Heavy drizzle
    'RA': 60,      # Rain
    '-RA': 58,     # Light rain
    'RA': 61,      # Moderate rain
    '+RA': 63,     # Heavy rain
    'FZRA': 66,    # Freezing rain
    '-FZRA': 66,   # Light freezing rain
    '+FZRA': 67,   # Heavy freezing rain
    'RASN': 68,    # Rain and snow
    'SN': 70,      # Snow
    '-SN': 70,     # Light snow
    'SN': 71,      # Moderate snow
    '+SN': 73,     # Heavy snow
    'SG': 77,      # Snow grains
    'IC': 76,      # Ice crystals
    'PL': 79,      # Ice pellets
    'GR': 89,      # Hail
    'GS': 87,      # Snow pellets/small hail
    
    # Showers
    'SHRA': 80,    # Rain showers
    '-SHRA': 80,   # Light rain showers
    '+SHRA': 81,   # Heavy rain showers
    'SHRASN': 83,  # Rain and snow showers
    'SHSN': 85,    # Snow showers
    '-SHSN': 85,   # Light snow showers
    '+SHSN': 86,   # Heavy snow showers
    'SHGR': 89,    # Hail showers
    'SHGS': 87,    # Snow pellet showers
    
    # Thunderstorms
    'TS': 95,      # Thunderstorm
    'TSRA': 95,    # Thunderstorm with rain
    '-TSRA': 95,   # Thunderstorm with light rain
    '+TSRA': 97,   # Thunderstorm with heavy rain
    'TSSN': 95,    # Thunderstorm with snow
    'TSPL': 95,    # Thunderstorm with ice pellets
    'TSGR': 96,    # Thunderstorm with hail
    'TSGS': 96,    # Thunderstorm with snow pellets
    
    # Obscuration
    'BR': 10,      # Mist
    'FG': 45,      # Fog
    'FZFG': 49,    # Freezing fog
    'FU': 4,       # Smoke
    'VA': 4,       # Volcanic ash
    'DU': 6,       # Dust
    'SA': 7,       # Sand
    'HZ': 5,       # Haze
    'PY': 4,       # Spray
    
    # Other
    'PO': 8,       # Dust/sand whirls
    'SQ': 18,      # Squalls
    'FC': 19,      # Funnel cloud/tornado/waterspout
    'SS': 31,      # Sandstorm
    'DS': 31,      # Duststorm
    '+FC': 19,     # Tornado/waterspout
}

def get_weather_code(weather_string: str) -> int:
    """
    Convert weather phenomenon string to WMO code.
    
    Args:
        weather_string: Weather code from METAR (e.g., '-RA', 'TSRA', 'FG')
    
    Returns:
        WMO code (ww) or 0 if not found
    """
    if not weather_string:
        return 0
    
    # Try exact match first
    if weather_string in WEATHER_CODE_MAP:
        return WEATHER_CODE_MAP[weather_string]
    
    # Try without intensity prefix
    for prefix in ['-', '+']:
        if weather_string.startswith(prefix):
            base_wx = weather_string[1:]
            if base_wx in WEATHER_CODE_MAP:
                return WEATHER_CODE_MAP[base_wx]
    
    # Default to 0 (unknown)
    return 0


def parse_sky_cover_oktas(sky_string: str) -> tuple[int, str]:
    """
    Convert sky cover abbreviation to oktas (eighths).
    
    Args:
        sky_string: Sky cover code (SKC, FEW, SCT, BKN, OVC, VV)
    
    Returns:
        Tuple of (oktas: int, description: str)
        oktas: 0-8 for sky cover, 9 for obscured, 10 for missing
    """
    sky_oktas_map = {
        'SKC': (0, 'clear'),              # Sky clear
        'CLR': (0, 'clear'),              # Clear (automated)
        'NSC': (0, 'no_significant'),     # No significant clouds
        'FEW': (2, 'few'),                # Few (1-2 oktas)
        'SCT': (4, 'scattered'),          # Scattered (3-4 oktas)
        'BKN': (6, 'broken'),             # Broken (5-7 oktas)
        'OVC': (8, 'overcast'),           # Overcast (8 oktas)
        'VV': (9, 'obscured'),            # Vertical visibility (sky obscured)
        '///': (10, 'missing'),           # Missing
    }
    
    if not sky_string:
        return (10, 'missing')
    
    # Extract cover type (first 3 chars usually)
    cover_type = sky_string[:3].upper()
    
    return sky_oktas_map.get(cover_type, (10, 'missing'))