"""
Reads METAR data from stdin
"""

import logging
import sys
from typing import List

logger = logging.getLogger(__name__)


class StdinReader:
    """Reads METAR observations from stdin."""
    
    @staticmethod
    def read_metars() -> List[str]:
        """
        Read METAR data from stdin.
        Can handle single METARs or batches separated by newlines.
        """
        metars = []
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if line and line.startswith(('METAR', 'SPECI')) or \
                   (len(line) > 4 and line[0:4].isalpha()):
                    metars.append(line)
        except KeyboardInterrupt:
            logger.info("Stdin reading interrupted")
        except Exception as e:
            logger.error(f"Error reading from stdin: {e}")
        
        return metars