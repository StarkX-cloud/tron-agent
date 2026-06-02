#!/bin/bash

docker build -t tron-agent .

docker run -d \
  --name tron-agent \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/logs:/logs \
  tron-agent

echo "TRON Agent running..."
echo "Logs: ./logs/heartbeat.jsonl"