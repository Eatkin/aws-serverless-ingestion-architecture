#!/bin/bash

echo "Setting up service venvs"
for SERVICE in services/*/; do
    # Remove trailing slash
    SERVICE=${SERVICE%/}

    # Only continue if requirements.txt exists
    if [ ! -f "$SERVICE/requirements.txt" ]; then
        echo "Skipping $SERVICE (no requirements.txt)"
        continue
    fi
    echo "Setting up $SERVICE..."
    VENV="$SERVICE/venv"
    if [ -d "$VENV" ]; then
        echo "Venv already exists, skipping..."
        continue
    fi

    python3 -m venv "$VENV"
    source "$SERVICE/venv/bin/activate"
    pip install --upgrade pip
    
    echo "Installing requirements"
    if [ -f "$SERVICE/requirements.txt" ]; then
        pip install -r "$SERVICE/requirements.txt"
    fi
    
    echo "Installing common scripts"
    pip install -e . 
    
    deactivate
done

echo "Quickstart complete!"
