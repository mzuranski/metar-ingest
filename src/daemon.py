"""
Daemon process for continuous METAR ingestion
"""

import logging
import signal
import sys
from pathlib import Path

import daemon
from daemon import pidfile

from src.config.settings import DAEMON, LOGGING
from src.main import setup_logging, main as process_main


logger = logging.getLogger(__name__)
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating shutdown")
    shutdown_requested = True


def run_daemon():
    """Run the ingestion process as a daemon."""
    setup_logging()
    logger.info("METAR ingestion daemon starting")
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while not shutdown_requested:
            try:
                process_main()
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}", exc_info=True)
                if shutdown_requested:
                    break
    finally:
        logger.info("METAR ingestion daemon shutting down")


def main():
    """Main entry point for daemon."""
    # Ensure PID file directory exists
    pid_dir = Path(DAEMON['pid_file']).parent
    pid_dir.mkdir(parents=True, exist_ok=True)
    
    # Create daemon context
    context = daemon.DaemonContext(
        working_directory=DAEMON['working_dir'],
        pidfile=pidfile.TimeoutPIDLockFile(DAEMON['pid_file']),
        signal_map={
            signal.SIGTERM: signal_handler,
            signal.SIGINT: signal_handler,
        },
    )
    
    with context:
        run_daemon()


if __name__ == '__main__':
    main()