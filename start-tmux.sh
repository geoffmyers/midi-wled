#!/bin/bash

SESSION_NAME="piano-lights"
COMMAND="sudo /home/geoffmyers/midi-wled/venv/bin/python /home/geoffmyers/midi-wled/piano-lights.py"

# Check if the session already exists
if ! tmux has-session -t $SESSION_NAME 2>/dev/null; then
    tmux new-session -d -s $SESSION_NAME "$COMMAND"
fi
