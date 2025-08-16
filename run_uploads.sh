#!/bin/bash
# Absolute paths are recommended for cron

# Path to your virtual environment
VENV_PATH="/path/to/your/venv"
# Path to your Python script
SCRIPT_PATH="/path/to/main.py"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run your commands
python "$SCRIPT_PATH" --game "BATTLEFIELD 6" --amount 30 --languages en
python "$SCRIPT_PATH" --game "League of Legends" --amount 30 --languages en de fr es

# Optional: deactivate venv
deactivate
