"""
Logging setup module for the Wi-Fi test tool.
"""

import logging
import os
from typing import Optional

def setup_logging(log_file: str = "wifi_test.log", log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        log_file: Path to the log file
        log_level: Logging level (default: DEBUG)

    Returns:
        Logger instance
    """
    # Ensure parent directory exists for log file
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("wifitest")
    logger.info("Wi-Fi Test Tool initialized")
    
    return logger