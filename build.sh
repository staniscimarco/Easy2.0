#!/bin/bash
# Build script for Render
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install build dependencies
pip install wheel setuptools

# Install requirements
pip install -r requirements.txt

