"""
Script to load station metadata into database
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import LOGGING
from src.database.connection import DatabaseConnection
from src.utils.station_loader import StationLoader


def setup_logging():
    """Configure basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Load station metadata from file."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Path to station file
    base_dir = Path(__file__).resolve().parent.parent
    station_file = base_dir / 'config' / 'worldstanew.txt'
    
    if not station_file.exists():
        logger.error(f"Station file not found: {station_file}")
        return 1
    
    logger.info(f"Loading stations from {station_file}")
    
    try:
        # Initialize database
        DatabaseConnection.initialize()
        
        # Parse station file
        stations = StationLoader.parse_worldstanew(station_file)
        
        if not stations:
            logger.warning("No stations parsed from file")
            return 1
        
        logger.info(f"Parsed {len(stations)} stations")
        
        # Load to database
        loaded = StationLoader.load_to_database(stations, None)
        
        logger.info(f"Successfully loaded {loaded} stations")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error loading stations: {e}", exc_info=True)
        return 1
    
    finally:
        DatabaseConnection.close_all()


if __name__ == '__main__':
    sys.exit(main())