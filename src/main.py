"""
Main entry point for METAR ingestion
"""

import logging
import signal
import sys
import re
from typing import List

from src.config.settings import configure_logging
from src.database.connection import DatabaseConnection
from src.ingest.batch_processor import BatchProcessor

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def is_wmo_header(line: str) -> bool:
    """Check if line is a WMO header (e.g., SAUS99 KWBC 202115)."""
    return bool(re.match(r'^[A-Z]{4}\d{2}\s+[A-Z]{4}\s+\d{6}', line))


def is_station_line(line: str) -> bool:
    """Check if line starts a new observation (station ID + timestamp)."""
    return bool(re.match(r'^[A-Z]{4}\s+\d{6}Z', line))


def extract_metars_from_product(product_lines: List[str]) -> List[str]:
    """
    Extract METAR/SPECI observations from product lines.
    
    Handles:
    - Multi-line observations (continuation lines start with whitespace)
    - WMO headers (skip)
    - Report type declarations (METAR/SPECI)
    - Equals signs as terminators
    """
    metars = []
    report_type = None
    current_obs = []
    
    for line in product_lines:
        line_stripped = line.strip()
        
        if not line_stripped:
            continue
        
        # Skip WMO headers
        if is_wmo_header(line_stripped):
            continue
        
        # Check for report type
        if line_stripped in ('METAR', 'SPECI'):
            report_type = line_stripped
            continue
        
        # Check if this starts a new observation
        if is_station_line(line_stripped):
            # Save previous observation if any
            if current_obs and report_type:
                obs_text = ' '.join(current_obs).rstrip('=').strip()
                metars.append(f"{report_type} {obs_text}")
            
            # Start new observation
            current_obs = [line_stripped.rstrip('=').strip()]
            
            # Check if this line completes the observation
            if line_stripped.endswith('='):
                obs_text = ' '.join(current_obs).rstrip('=').strip()
                if report_type:
                    metars.append(f"{report_type} {obs_text}")
                current_obs = []
        
        # Continuation line (starts with whitespace in original)
        elif current_obs and line.startswith(' '):
            current_obs.append(line_stripped.rstrip('=').strip())
            
            # Check if this completes the observation
            if line_stripped.endswith('='):
                obs_text = ' '.join(current_obs).rstrip('=').strip()
                if report_type:
                    metars.append(f"{report_type} {obs_text}")
                current_obs = []
    
    # Handle any incomplete observation
    if current_obs and report_type:
        obs_text = ' '.join(current_obs).rstrip('=').strip()
        metars.append(f"{report_type} {obs_text}")
    
    return metars


def process_stream(batch_size: int = 100):
    """
    Process LDM product stream continuously.
    
    Reads stdin line by line, detects product boundaries,
    and processes each complete product immediately.
    
    This function runs indefinitely until EOF or shutdown signal.
    Database connections remain open for performance.
    """
    logger = logging.getLogger(__name__)
    processor = BatchProcessor()
    
    batch: List[str] = []
    product_lines: List[str] = []
    product_count = 0
    total_processed = 0
    
    logger.info("Listening for LDM products on stdin (continuous mode)...")
    logger.info("Database connection pool active, ready for real-time ingestion")
    
    try:
        for line in sys.stdin:
            if shutdown_requested:
                logger.info("Shutdown requested, processing remaining data...")
                break
            
            # Detect start of new product (^A)
            if line.startswith('\x01'):
                # Process previous product if we have one
                if product_lines:
                    product_count += 1
                    metars = extract_metars_from_product(product_lines)
                    
                    if metars:
                        logger.debug(f"Product {product_count}: extracted {len(metars)} METARs")
                        batch.extend(metars)
                        
                        # Process batch if full
                        if len(batch) >= batch_size:
                            logger.info(f"Processing batch of {len(batch)}")
                            stats = processor.process_batch(batch)
                            total_processed += stats['parsed']
                            batch = []
                    else:
                        logger.debug(f"Product {product_count}: no METARs extracted")
                
                # Start new product
                product_lines = []
                continue
            
            # Skip byte count line (first line after ^A, typically just digits)
            if not product_lines and line.strip().isdigit():
                continue
            
            # Accumulate product lines (preserve original spacing for continuation detection)
            product_lines.append(line.rstrip('\n\r'))
        
        # Process final product and batch
        if product_lines:
            product_count += 1
            metars = extract_metars_from_product(product_lines)
            batch.extend(metars)
        
        if batch:
            logger.info(f"Processing final batch of {len(batch)}")
            stats = processor.process_batch(batch)
            total_processed += stats['parsed']
        
        logger.info(f"Stream ended. Products: {product_count}, Observations: {total_processed}")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        if batch:
            logger.info(f"Processing interrupted batch of {len(batch)}")
            processor.process_batch(batch)
    except Exception as e:
        logger.error(f"Error in stream processing: {e}", exc_info=True)
        if batch:
            logger.info(f"Processing error batch of {len(batch)}")
            processor.process_batch(batch)


def main():
    """Main entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Configure logging
    configure_logging()
    logger = logging.getLogger(__name__)
    
    # Ensure unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    logger.info("Starting METAR ingestion service (LDM mode)")
    
    try:
        # Initialize database connection pool
        # Connection remains open for the lifetime of the process
        DatabaseConnection.initialize()
        logger.info("Database connection pool initialized and ready")
        
        # Process LDM product stream continuously
        process_stream(batch_size=100)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        return 1
    finally:
        # Only close connections on shutdown
        logger.info("Shutting down...")
        DatabaseConnection.close_all()
        logger.info("METAR ingestion service stopped")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())