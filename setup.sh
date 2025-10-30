#!/bin/bash

# Update system and install required packages
sudo apt-get update
sudo apt-get install -y libxml2-dev libxslt-dev python3-lxml

# Force reinstall core dependencies before FastF1
pip install --upgrade pip setuptools wheel
pip install --no-cache-dir numpy pandas lxml requests-cache requests

# Finally install FastF1
pip install --no-cache-dir fastf1==3.3.3

