# 🧠 TRON Agent

Lightweight container observability agent for Docker-native environments.

TRON gives you real-time visibility into container health, CPU, memory, and runtime behavior — without dashboards, external dependencies, or setup complexity.



# ⚡ What it does

-Tracks container CPU usage

-Tracks memory usage

-Streams live container state every 10 seconds

-Runs fully inside Docker

-Outputs simple JSONL logs


# 🚀 Quick Start

### 1. Clone repo

```bash
git clone https://github.com/YOUR_USERNAME/tron-agent.git
cd tron-agent
```


### 2. Run agent

```bash 
bash scripts/run.sh
```

### 3. View logs
```bash
tail -f logs/heartbeat.jsonl
```

# 📊 Example Output

```json
{
  "ts": "2026-06-01T17:53:31Z",
  "id": "a81f3c2",
  "name": "ai-runtime",
  "status": "running",
  "metrics": {
    "cpu_percent": 12.4,
    "memory_mb": 312.2,
    "memory_percent": 24.8
  }
}
```

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
