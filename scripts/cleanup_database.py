"""
Database cleanup utilities
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import LOGGING
from src.database.connection import DatabaseConnection


def setup_logging():
    """Configure basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def truncate_all():
    """Truncate all observation tables."""
    logger = logging.getLogger(__name__)
    
    try:
        DatabaseConnection.initialize()
        
        with DatabaseConnection.get_cursor() as cursor:
            logger.info("Truncating observations...")
            cursor.execute("TRUNCATE observations CASCADE;")
            
            logger.info("Truncating metrics...")
            cursor.execute("TRUNCATE ingest_metrics CASCADE;")
        
        logger.info("Database truncated successfully")
        
    except Exception as e:
        logger.error(f"Error truncating database: {e}")
        return 1
    finally:
        DatabaseConnection.close_all()
    
    return 0


def delete_old(days: int):
    """Delete observations older than specified days."""
    logger = logging.getLogger(__name__)
    
    try:
        DatabaseConnection.initialize()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with DatabaseConnection.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM observations WHERE observation_time < %s
            """, (cutoff_date,))
            
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} observations older than {days} days")
        
    except Exception as e:
        logger.error(f"Error deleting old observations: {e}")
        return 1
    finally:
        DatabaseConnection.close_all()
    
    return 0


def main():
    """Run cleanup based on arguments."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/cleanup_database.py truncate      # Clear all observations")
        print("  python scripts/cleanup_database.py delete <days> # Delete obs older than N days")
        return 1
    
    command = sys.argv[1]
    
    if command == 'truncate':
        return truncate_all()
    elif command == 'delete' and len(sys.argv) == 3:
        try:
            days = int(sys.argv[2])
            return delete_old(days)
        except ValueError:
            logger.error("Days must be an integer")
            return 1
    else:
        logger.error(f"Unknown command: {command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())