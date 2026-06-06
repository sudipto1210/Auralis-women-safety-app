#!/bin/bash
set -e

echo "===== Building Women Safety App ====="

# Navigate to project directory
cd "$(dirname "$0")"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Upgrading pip..."
./venv/bin/pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
./venv/bin/pip install -r requirements.txt

echo "===== Build completed successfully ====="

