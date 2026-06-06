#!/bin/bash
set -e

# Change to script directory (handle spaces in path)
cd -- "$(dirname "$0")"

# Set PYTHONPATH first so api/database/src imports work
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Resolve venv python (check parent directory root, or local venv)
if [ -d "../venv" ]; then
    VENV_PYTHON="$(pwd)/../venv/bin/python"
    VENV_DIR="../venv"
else
    VENV_PYTHON="$(pwd)/venv/bin/python"
    VENV_DIR="venv"
fi

# Check if virtual environment exists, if not create it
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv "$VENV_DIR"
    
    # Install dependencies
    echo "Installing dependencies..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r requirements.txt
fi

# Run the application using venv Python directly
export PYTHONPATH="$(pwd)"
$VENV_PYTHON api/server_backend.py

