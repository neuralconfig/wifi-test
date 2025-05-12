"""
Main module for direct execution of the package.
"""

import sys
import os
import importlib.util

# Add parent directory to path to find wifi-test-cli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module using the file path to handle dash in filename
spec = importlib.util.spec_from_file_location(
    "wifi_test_cli", 
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../wifi-test-cli.py'))
)
wifi_test_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi_test_cli)

if __name__ == "__main__":
    sys.exit(wifi_test_cli.main())