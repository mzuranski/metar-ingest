"""
Database connection management with connection pooling
"""

import logging
import yaml
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from src.config.settings import DATABASE

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connection pooling."""
    
    _pool: Optional[pool.ThreadedConnectionPool] = None
    _config: Optional[dict] = None
    
    @classmethod
    def _load_config(cls):
        """Load database configuration from YAML file."""
        if cls._config is None:
            try:
                config_file = DATABASE['config_file']
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                
                # Extract database section
                if 'database' in config_data:
                    cls._config = config_data['database']
                else:
                    cls._config = config_data
                
                logger.debug(f"Loaded database config from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load database config: {e}")
                raise
        return cls._config
    
    @classmethod
    def initialize(cls):
        """Initialize the connection pool."""
        if cls._pool is not None:
            logger.warning("Database pool already initialized")
            return
        
        try:
            config = cls._load_config()
            
            # Get pool settings
            pool_config = config.get('pool', {})
            min_conn = pool_config.get('min_connections', 1)
            max_conn = pool_config.get('max_connections', DATABASE.get('pool_size', 10))
            
            # Build connection parameters
            conn_params = {
                'minconn': min_conn,
                'maxconn': max_conn,
                'host': config.get('host', 'localhost'),
                'port': config.get('port', 5432),
                'database': config.get('name'),  # 'name' in YAML, 'database' for psycopg2
                'user': config.get('user'),
                'password': config.get('password'),
            }
            
            # Add timeouts if specified
            timeouts = config.get('timeouts', {})
            if 'connect_timeout' in timeouts:
                conn_params['connect_timeout'] = timeouts['connect_timeout']
            
            logger.info(f"Connecting to {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
            
            cls._pool = pool.ThreadedConnectionPool(**conn_params)
            
            logger.info("Database connection pool initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @classmethod
    @contextmanager
    def get_connection(cls):
        """
        Get a connection from the pool.
        
        Usage:
            with DatabaseConnection.get_connection() as conn:
                # use connection
        """
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized. Call initialize() first.")
        
        conn = None
        try:
            conn = cls._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            if conn:
                cls._pool.putconn(conn)
    
    @classmethod
    @contextmanager
    def get_cursor(cls):
        """
        Get a cursor from a pooled connection.
        
        Usage:
            with DatabaseConnection.get_cursor() as cursor:
                cursor.execute("SELECT ...")
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()
    
    @classmethod
    def close_all(cls):
        """Close all connections in the pool."""
        if cls._pool:
            cls._pool.closeall()
            cls._pool = None
            logger.info("Database connection pool closed")
    
    @classmethod
    def test_connection(cls) -> bool:
        """Test database connectivity."""
        try:
            with cls.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False