#!/bin/bash

set -e

echo "Installing TRON Agent..."

# create folder
mkdir -p tron-agent
cd tron-agent

# pull repo (for now local copy version)
curl -o observer.py https://raw.githubusercontent.com/YOUR_REPO/observer.py
curl -o Dockerfile https://raw.githubusercontent.com/YOUR_REPO/Dockerfile
curl -o run.sh https://raw.githubusercontent.com/YOUR_REPO/run.sh

chmod +x run.sh

echo "Building and starting agent..."

./run.sh

echo ""
echo "TRON Agent is now running."
echo "Logs: ./logs/heartbeat.jsonl"