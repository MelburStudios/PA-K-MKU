#!/bin/bash
echo "Setting up PA-K Management System..."
echo "Installing Python dependencies..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Create necessary directories
mkdir -p data
mkdir -p static

echo "Setup completed successfully!"
echo "Run './run.sh' to start the system"