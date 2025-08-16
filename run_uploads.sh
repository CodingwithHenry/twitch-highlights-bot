#!/bin/bash

VENV_PATH="/path/to/your/venv"
SCRIPT_PATH="/path/to/main.py"

source "$VENV_PATH/bin/activate"

# Run first game, ignore errors
python "$SCRIPT_PATH" --game "BATTLEFIELD 6" --amount 30 --languages en || echo "BATTLEFIELD 6 failed"

# Run second game, ignore errors
python "$SCRIPT_PATH" --game "League of Legends" --amount 30 --languages en de fr es || echo "League of Legends failed"

deactivate
