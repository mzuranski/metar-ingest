"""
Cleanup script to remove old observations
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from src.config.settings import LOGGING, DATA_RETENTION_DAYS
from src.database.connection import DatabaseConnection
from src.database.repositories import ObservationRepository


def setup_logging():
    """Configure logging with timed rotation."""
    LOGGING['log_dir'].mkdir(parents=True, exist_ok=True)
    
    log_file = LOGGING['log_dir'] / 'metar-cleanup.log'
    
    handler = TimedRotatingFileHandler(
        log_file,
        when=LOGGING['rotation_when'],
        interval=LOGGING['rotation_interval'],
        backupCount=LOGGING['backup_count'],
        utc=True
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOGGING['log_level']))
    root_logger.addHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def main():
    """Remove observations older than retention period."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting cleanup of observations older than {DATA_RETENTION_DAYS} days")
    
    try:
        DatabaseConnection.initialize()
        
        deleted_count = ObservationRepository.delete_old_observations(DATA_RETENTION_DAYS)
        
        logger.info(f"Cleanup complete: {deleted_count} observations deleted")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        return 1
    
    finally:
        DatabaseConnection.close_all()


if __name__ == '__main__':
    sys.exit(main())