from setuptools import setup, find_packages
import os
import importlib.util

# Use importlib to load module with dashes in filename
spec = importlib.util.spec_from_file_location(
    "wifi_test_cli", 
    os.path.join(os.path.dirname(__file__), "wifi-test-cli.py")
)
wifi_test_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi_test_cli)

setup(
    name="wifitest",
    version="1.0.0",
    packages=find_packages(),
    scripts=["wifi-test-cli.py"],
    
    # Metadata
    author="Neural Config",
    author_email="info@neuralconfig.com",
    description="Wi-Fi Connection Test Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/neuralconfig/wifi-test",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: System :: Networking",
        "Topic :: Utilities",
    ],
    keywords="wifi, networking, testing, mac, ping, iperf",
    
    # Requirements
    python_requires=">=3.6",
    install_requires=[],  # No special Python packages required
    
    # Entry points for console scripts
    entry_points={
        "console_scripts": [
            "wifi-test=wifi_test_cli:main",
        ],
    },
)