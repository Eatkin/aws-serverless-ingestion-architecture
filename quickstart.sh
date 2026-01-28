#!/bin/bash

echo "Setting up service venvs"
SERVICES=("services/webhook-handler" "services/processor")

for SERVICE in "${SERVICES[@]}"; do
    echo "Setting up $SERVICE..."
    VENV="$SERVICE/venv"
    if [ -d "$VENV" ]; then
        echo "Venv already exists, skipping..."
        continue
    fi

    python3 -m venv "$VENV"
    source "$SERVICE/venv/activate"
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