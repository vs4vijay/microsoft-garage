#!/bin/bash
# Activate virtual environment and run the application

source venv/bin/activate
python src/main.py "$@"
