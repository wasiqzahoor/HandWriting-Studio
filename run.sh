#!/bin/sh
# Handwriting Studio launcher (macOS Apple Silicon / Intel, Linux).
# First time: pip3 install -r requirements.txt
cd "$(dirname "$0")"
exec python3 main.py "$@"
