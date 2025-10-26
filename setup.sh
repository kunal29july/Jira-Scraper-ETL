#!/bin/bash

echo "Setting up Jira ETL Pipeline environment..."

# Create virtual environment
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created successfully."
fi

# Activate virtual environment and install dependencies
echo "Installing dependencies..."
source venv/bin/activate

echo "Attempting to install dependencies with SSL verification bypassed..."
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies with SSL verification bypassed."
    echo "Trying standard installation method..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies."
        exit 1
    fi
fi
echo "Dependencies installed successfully."

# Create necessary directories
echo "Setting up directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p data/checkpoints
mkdir -p data/logs
echo "Directories created successfully."

echo
echo "================================================================================"
echo "Setup Complete!"
echo "================================================================================"
echo
echo "To activate the virtual environment:"
echo "    source venv/bin/activate"
echo
echo "To run the pipeline:"
echo "    python main.py"
echo
echo "To run the worker:"
echo "    python worker.py"
echo
echo "To deactivate the virtual environment when done:"
echo "    deactivate"
echo "================================================================================"
echo

# Make the script executable
chmod +x setup.sh
