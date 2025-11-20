"""
Batch processing of METAR observations
"""

import logging
import time
from typing import Dict, List

from src.parsers.metar_parser import MetarParser
from src.database.repositories import ObservationRepository, MetricsRepository

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processes batches of METAR observations."""
    
    def __init__(self):
        self.stats = {
            'total': 0,
            'parsed': 0,
            'failed': 0,
            'db_errors': 0,
            'corrections': 0,
        }
    
    def process_batch(self, metar_texts: List[str]) -> Dict:
        """Process a batch of METAR texts."""
        start_time = time.time()
        
        batch_total = len(metar_texts)
        
        # Parse all METARs
        parsed_obs, failed_metars = MetarParser.parse_batch(metar_texts)
        batch_parsed = len(parsed_obs)
        batch_failed = len(failed_metars)
        
        # Only log if there are failures
        if batch_failed > 0:
            logger.warning(f"Failed to parse {batch_failed}/{batch_total} observations")
        
        # Store parsed observations
        stored_count = 0
        batch_corrections = 0
        batch_db_errors = 0
        
        for obs_data in parsed_obs:
            result = self._store_observation(obs_data)
            if result:
                stored_count += 1
                if obs_data.get('is_correction'):
                    batch_corrections += 1
            else:
                batch_db_errors += 1
        
        # Update totals
        self.stats['total'] += batch_total
        self.stats['parsed'] += batch_parsed
        self.stats['failed'] += batch_failed
        self.stats['db_errors'] += batch_db_errors
        self.stats['corrections'] += batch_corrections
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Store metrics
        MetricsRepository.insert_metrics(
            batch_total,
            batch_parsed,
            batch_failed,
            batch_db_errors,
            processing_time
        )
        
        # Log summary
        logger.info(f"Batch: {stored_count}/{batch_total} stored in {processing_time}ms "
                   f"({batch_corrections} COR, {batch_db_errors} errors)")
        
        return {
            'total': batch_total,
            'parsed': batch_parsed,
            'failed': batch_failed,
            'db_errors': batch_db_errors,
            'corrections': batch_corrections,
        }
    
    def _store_observation(self, obs_data: Dict) -> bool:
        """Store a single observation with its elements."""
        try:
            is_correction = obs_data.get('is_correction', False)
            
            # Insert or update observation
            obs_id = ObservationRepository.insert_observation(
                obs_data['station_id'],
                obs_data['obs_time'],
                obs_data['raw_metar'],
                is_correction=is_correction
            )
            
            if not obs_id:
                # Duplicate - only log corrections at debug level
                return False
            
            # If this is a correction, delete old elements first
            if is_correction:
                ObservationRepository.delete_observation_elements(obs_id)
            
            # Insert all elements
            for element_type, value, unit, text in obs_data['elements']:
                ObservationRepository.insert_element(
                    obs_id, element_type, value, unit, text
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing {obs_data.get('station_id')}: {e}")
            return False