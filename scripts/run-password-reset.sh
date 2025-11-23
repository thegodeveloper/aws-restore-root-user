#!/bin/bash
# Wrapper script to run password reset automation with proper Python environment
# Called by Terraform provisioner

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

# Setup Python environment first
bash "$SCRIPT_DIR/setup-python-env.sh"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run the Python script with all passed arguments
exec "$VENV_PYTHON" "$SCRIPT_DIR/automated-password-reset.py" "$@"
