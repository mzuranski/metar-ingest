"""
Ingestion module for METAR data
"""

from .stdin_reader import StdinReader
from .batch_processor import BatchProcessor

__all__ = ['StdinReader', 'BatchProcessor']