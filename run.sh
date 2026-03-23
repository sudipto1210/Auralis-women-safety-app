#!/bin/bash
set -e

# Change to script directory (handle spaces in path)
cd -- "$(dirname "$0")"

# Set PYTHONPATH first so Backend imports work
export PYTHONPATH="$(pwd):$PYTHONPATH"

VENV_PYTHON="$(pwd)/venv/bin/python"

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    
    # Install dependencies
    echo "Installing dependencies..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Run the application using venv Python directly
export PYTHONPATH="$(pwd)"
$VENV_PYTHON Backend/server_backend.py

