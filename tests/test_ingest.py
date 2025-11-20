"""
Unit tests for ingestion components
"""

import pytest
from io import StringIO
import sys

from src.ingest.stdin_reader import StdinReader
from src.ingest.batch_processor import BatchProcessor


class TestStdinReader:
    """Test suite for StdinReader class."""
    
    def test_read_single_metar(self, monkeypatch):
        """Test reading a single METAR from stdin."""
        test_input = "METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034\n"
        monkeypatch.setattr('sys.stdin', StringIO(test_input))
        
        metars = StdinReader.read_metars()
        
        assert len(metars) == 1
        assert metars[0].startswith("METAR KJFK")
    
    def test_read_multiple_metars(self, monkeypatch):
        """Test reading multiple METARs from stdin."""
        test_input = """METAR KJFK 201851Z 31008KT 10SM FEW250 M04/M17 A3034
METAR KLGA 201851Z 30010KT 10SM FEW250 M03/M16 A3035
METAR KEWR 201851Z 31009KT 10SM FEW250 M05/M18 A3033
"""
        monkeypatch.setattr('sys.stdin', StringIO(test_input))
        
        metars = StdinReader.read_metars()
        
        assert len(metars) == 3
        assert all(m.startswith("METAR") for m in metars)
    
    def test_read_empty_stdin(self, monkeypatch):
        """Test reading from empty stdin."""
        test_input = ""
        monkeypatch.setattr('sys.stdin', StringIO(test_input))
        
        metars = StdinReader.read_metars()
        
        assert len(metars) == 0


class TestBatchProcessor:
    """Test suite for BatchProcessor class."""
    
    def test_process_empty_batch(self):
        """Test processing an empty batch."""
        processor = BatchProcessor()
        stats = processor.process_batch([])
        
        assert stats['total'] == 0
        assert stats['parsed'] == 0
        assert stats['failed'] == 0