#!/bin/bash

SESSION_NAME="piano-lights"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMAND="sudo ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/piano-lights.py"

# Check if the session already exists
if ! tmux has-session -t $SESSION_NAME 2>/dev/null; then
    tmux new-session -d -s $SESSION_NAME "$COMMAND"
fi
