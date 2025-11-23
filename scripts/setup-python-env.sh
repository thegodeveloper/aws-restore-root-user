#!/bin/bash
# Setup Python virtual environment for AWS password reset automation
# This script is called by Terraform before executing Python scripts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed or not in PATH"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install/upgrade pip
pip install --upgrade pip --quiet

# Install requirements
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing Python dependencies..."
    pip install -r "$REQUIREMENTS_FILE" --quiet
else
    echo "WARNING: requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

echo "Python environment ready at: $VENV_DIR"
echo "Python: $(which python3)"
echo "Pip: $(which pip)"
