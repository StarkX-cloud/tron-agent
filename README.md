# 🧠 TRON Agent

Lightweight container observability agent for Docker-native environments.

TRON gives you real-time visibility into container health, CPU, memory, and runtime behavior — without dashboards, external dependencies, or setup complexity.



# ⚡ What it does

- Live container CPU / Memory tracking
  
- Startup latency measurement (ms-level)
  
- Failure risk scoring engine

- Slow-death detection (degrading containers)
  
- Node health aggregation score
  
- JSONL telemetry stream (infra-ready format)

---

# 🚀 Quick Start

### 1. Clone repo

```bash
git clone https://github.com/YOUR_USERNAME/tron-agent.git
cd tron-agent
```


### 2. Run agent

### 🐧 Linux / WSL / Git Bash

```bash 
bash scripts/run.sh
```
---

### 🪟 Windows (PowerShell)
```Docker
docker run -d --name tron-agent -v //var/run/docker.sock:/var/run/docker.sock -v "${PWD}\logs:/logs" tron-agent
```

### 3. View logs

```Docker
docker logs -f tron-agent
```

### 4 Inspect raw telemetry file (optional)

### Linux / Mac
```Bash
tail -f logs/heartbeat.jsonl
```

### Windows PowerShell
```Bash
Get-Content .\logs\heartbeat.jsonl -Wait
```


# 📊 Each snapshot contains:

### - CPU usage per container
### - Memory footprint
### - Startup latency (ms)
### - Failure risk score (0–100)
### - Slow-death detection flag
### - Node-wide health score
---

# 🧠 Design philosophy

TRON is built on 3 principles:

-Zero configuration

-Local-first observability

-Minimal overhead, maximum signal

# ⚙️ Requirements
-Docker installed

-Linux / WSL / Docker Desktop

-Access to Docker socket (/var/run/docker.sock)

# 📦 Use cases
container debugging
runtime visibility
lightweight infra monitoring
local development observability

# ⚠️ Note
TRON is intentionally minimal.
No dashboards. No cloud lock-in. No external APIs.

It is designed to be embedded into infrastructure systems, not replace them.
