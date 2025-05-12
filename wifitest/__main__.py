"""
Main module for direct execution of the package.
"""

import sys
import os

# Add parent directory to path to find wifi_test_cli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wifi_test_cli import main

if __name__ == "__main__":
    sys.exit(main())