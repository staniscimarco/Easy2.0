#!/bin/bash
# Build script for Render
set -o errexit

# Render crea automaticamente un virtual environment in .venv
# Usiamo quello invece di installare globalmente
if [ -d ".venv" ]; then
    # Usa il virtual environment di Render
    source .venv/bin/activate
    pip install --upgrade pip
    pip install wheel setuptools
    pip install -r requirements.txt
else
    # Fallback: usa python3 -m pip per evitare problemi con externally-managed-environment
    python3 -m pip install --upgrade pip --user
    python3 -m pip install wheel setuptools --user
    python3 -m pip install -r requirements.txt --user
fi

