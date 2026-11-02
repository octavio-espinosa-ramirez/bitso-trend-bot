#!/bin/bash
# Mantiene la Mac despierta mientras corre el bot y lo reinicia si se cae.
cd "$(dirname "$0")"
[ -d venv ] || { python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt; }
exec caffeinate -i bash -c 'while true; do ./venv/bin/python main.py; echo "Bot se detuvo, reiniciando en 10s..."; sleep 10; done'
