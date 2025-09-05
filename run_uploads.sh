#!/bin/bash

VENV_PATH="/home/henry/twitch-highlights-bot/venv"
SCRIPT_PATH="/home/henry/twitch-highlights-bot/main.py"

source "$VENV_PATH/bin/activate"

# Run first game, ignore errors
#python "$SCRIPT_PATH" --game "BATTLEFIELD 6" --amount 20 --languages en || echo "BATTLEFIELD 6 failed"

# Run second game, ignore errors
python "$SCRIPT_PATH" --game "League of Legends" --amount 30 --languages en de es fr || echo "League of Legends failed"

deactivate
