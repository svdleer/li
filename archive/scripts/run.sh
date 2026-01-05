#!/bin/bash
"""
EVE LI XML Generator - Run Script
================================

Wrapper script to run EVE LI XML Generator with proper virtual environment activation.
This script ensures the virtual environment is activated before running the main script.
"""

# Configuration
VENV_PATH="/home/svdleer/python/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_SCRIPT="$SCRIPT_DIR/eve_li_xml_generator.py"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Check if main script exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "ERROR: Main script not found at $MAIN_SCRIPT"
    exit 1
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run the main script with all passed arguments
python "$MAIN_SCRIPT" "$@"

# Store exit code
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Exit with the same code as the main script
exit $EXIT_CODE
