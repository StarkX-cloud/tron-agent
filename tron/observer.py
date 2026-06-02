import docker
import time
import json
from datetime import datetime
from collections import defaultdict, deque

client = docker.from_env()

LOG_FILE = "/logs/heartbeat.jsonl"

# =========================
# STATE
# =========================
startup_registry = {}
last_seen = {}

history = defaultdict(lambda: deque(maxlen=20))
node_history = deque(maxlen=50)


# =========================
# UTIL
# =========================
def now():
    return datetime.utcnow().isoformat()


def log(data):
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(data) + "\n")


# =========================
# METRICS ENGINE
# =========================
def get_metrics(container):
    try:
        stats = container.stats(stream=False)

        mem = stats["memory_stats"]["usage"]
        limit = stats["memory_stats"]["limit"]

        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                    stats["precpu_stats"]["cpu_usage"]["total_usage"]

        sys_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                    stats["precpu_stats"]["system_cpu_usage"]

        cpu = (cpu_delta / sys_delta) * 100 if sys_delta > 0 else 0
        mem_pct = (mem / limit) * 100 if limit else 0

        return {
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(mem / 1024 / 1024, 2),
            "memory_percent": round(mem_pct, 2)
        }

    except:
        return {
            "cpu_percent": 0,
            "memory_mb": 0,
            "memory_percent": 0
        }


# =========================
# STARTUP TIME (READINESS)
# =========================
def get_container_startup_time(cid):
    if cid not in startup_registry:
        startup_registry[cid] = time.time()

    return int((time.time() - startup_registry[cid]) * 1000)


# =========================
# STUCK DETECTION
# =========================
def detect_stuck(cid, status, metrics):
    if status != "running":
        return False

    return metrics["cpu_percent"] < 0.5


# =========================
# FAILURE RISK ENGINE
# =========================
def failure_risk(metrics, stuck):
    cpu = metrics["cpu_percent"]
    mem = metrics["memory_percent"]

    risk = 0

    if cpu < 0.5:
        risk += 30
    if mem > 80:
        risk += 40
    if stuck:
        risk += 50
    if cpu > 85:
        risk += 25

    return min(risk, 100)


# =========================
# SLOW DEATH DETECTION
# =========================
def slow_death(cid, metrics):
    history[cid].append(metrics["cpu_percent"])

    if len(history[cid]) < 10:
        return False

    values = list(history[cid])

    slope = values[-1] - values[0]

    return slope < 0.2


# =========================
# NODE HEALTH SCORE
# =========================
def compute_node_health(containers):
    if not containers:
        return 100

    cpu_avg = sum(c["metrics"]["cpu_percent"] for c in containers) / len(containers)
    mem_avg = sum(c["metrics"]["memory_percent"] for c in containers) / len(containers)

    stuck_count = sum(1 for c in containers if c["stuck_risk"])

    score = 100
    score -= cpu_avg * 0.3
    score -= mem_avg * 0.3
    score -= stuck_count * 10

    return round(max(score, 0), 2)


# =========================
# NODE DEGRADATION
# =========================
def node_degradation_score(node_health):
    node_history.append(node_health)

    if len(node_history) < 5:
        return 0

    return round(node_history[-1] - node_history[0], 2)


# =========================
# SNAPSHOT ENGINE (CORE LOOP)
# =========================
def snapshot():
    containers = client.containers.list()

    snapshot_data = {
        "ts": now(),
        "node_health": 100,
        "node_degradation": 0,
        "containers": []
    }

    for c in containers:
        cid = c.short_id

        metrics = get_metrics(c)

        stuck = detect_stuck(cid, c.status, metrics)
        risk = failure_risk(metrics, stuck)
        slow = slow_death(cid, metrics)
        startup_ms = get_container_startup_time(cid)

        last_seen[cid] = metrics

        snapshot_data["containers"].append({
            "id": cid,
            "name": c.name,
            "status": c.status,
            "metrics": metrics,
            "startup_ms": startup_ms,
            "stuck_risk": stuck,
            "failure_risk": risk,
            "slow_death": slow
        })

    snapshot_data["node_health"] = compute_node_health(snapshot_data["containers"])
    snapshot_data["node_degradation"] = node_degradation_score(snapshot_data["node_health"])

    log(snapshot_data)


# =========================
# RUN LOOP
# =========================
def run():
    while True:
        snapshot()
        time.sleep(10)


if __name__ == "__main__":
    run()