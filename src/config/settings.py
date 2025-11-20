"""
Configuration settings for METAR ingestion
"""

import logging
import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system environment variables only

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / 'config'
LOG_DIR = Path(os.getenv('LOG_DIR', str(BASE_DIR / 'logs')))

# Database configuration
DATABASE = {
    'config_file': CONFIG_DIR / 'database.yml',
    'pool_size': 10,
    'max_overflow': 20,
}

# Data retention (days)
DATA_RETENTION_DAYS = int(os.getenv('DATA_RETENTION_DAYS', '30'))

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'formatter': 'detailed',
            'filename': Path(LOG_DIR) / 'metar-ingest.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,  # Keep 30 days of logs
            'utc': True,
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'src': {  # Application logger
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}


def configure_logging():
    """Configure logging based on LOGGING settings."""
    # Create log directory if it doesn't exist
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Apply configuration
    import logging.config
    logging.config.dictConfig(LOGGING)


def set_log_level(level: str):
    """
    Change logging level at runtime.
    
    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    """
    level_value = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(level_value)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level_value)