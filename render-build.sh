#!/usr/bin/env bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Downloading spaCy English model..."
python -m spacy download en_core_web_sm

echo "Build completed successfully."
