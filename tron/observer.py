import docker
import time
import json
import hashlib
from datetime import datetime
from collections import defaultdict, deque

client = docker.from_env()

LOG_FILE = "/logs/heartbeat.jsonl"
FLAT_METRICS_FILE = "/logs/metrics.flat.jsonl"
EVENT_TIMELINE_FILE = "/logs/events.timeline.jsonl"


# =========================
# MEMORY LAYERS
# =========================

cpu_history = defaultdict(lambda: deque(maxlen=15))
mem_history = defaultdict(lambda: deque(maxlen=15))
state_memory = defaultdict(lambda: "healthy")
risk_memory = defaultdict(float)
event_memory = deque(maxlen=200)


# =========================
# UTIL
# =========================

def now():
    return datetime.utcnow().isoformat()


def write_json(file, data):
    with open(file, "a") as f:
        f.write(json.dumps(data) + "\n")


def log_structured(payload):
    print(json.dumps(payload, indent=2, sort_keys=False), flush=True)
    write_json(LOG_FILE, payload)


def log_flat(container_id, metrics, state, risk, anomaly):
    flat = {
        "ts": now(),
        "id": container_id,
        "cpu": metrics["cpu_percent"],
        "mem": metrics["memory_percent"],
        "state": state,
        "risk": risk,
        "anomaly": anomaly
    }
    write_json(FLAT_METRICS_FILE, flat)


def log_event(event_type, cid, message):
    event = {
        "ts": now(),
        "type": event_type,
        "container": cid,
        "message": message
    }
    event_memory.append(event)
    write_json(EVENT_TIMELINE_FILE, event)


# =========================
# METRICS ENGINE
# =========================

def get_metrics(container):
    try:
        stats = container.stats(stream=False)

        mem = stats["memory_stats"]["usage"]
        limit = stats["memory_stats"]["limit"]

        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        sys_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]

        cpu = (cpu_delta / sys_delta) * 100 if sys_delta > 0 else 0
        mem_pct = (mem / limit) * 100 if limit else 0

        return {
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(mem / 1024 / 1024, 2),
            "memory_percent": round(mem_pct, 2)
        }

    except:
        return {"cpu_percent": 0, "memory_mb": 0, "memory_percent": 0}


# =========================
# ANOMALY FINGERPRINTING
# =========================

def fingerprint(metrics, state):
    raw = f"{metrics['cpu_percent']}:{metrics['memory_percent']}:{state}"
    return hashlib.md5(raw.encode()).hexdigest()[:10]


# =========================
# ROOT CAUSE CLUSTERING (LIGHTWEIGHT)
# =========================

def cluster_signature(metrics, stuck, slow):
    if stuck:
        return "idle_cluster"
    if slow:
        return "degrading_cluster"
    if metrics["memory_percent"] > 80:
        return "memory_pressure_cluster"
    if metrics["cpu_percent"] > 80:
        return "cpu_spike_cluster"
    return "normal_cluster"


# =========================
# STATE ENGINE
# =========================

def classify_state(score):
    if score < 20:
        return "healthy"
    if score < 45:
        return "drifting"
    if score < 70:
        return "degraded"
    return "critical"


# =========================
# STUCK / SLOW DETECTION
# =========================

def detect_stuck(cid, metrics):
    cpu_history[cid].append(metrics["cpu_percent"])

    if len(cpu_history[cid]) < 8:
        return False

    avg = sum(cpu_history[cid]) / len(cpu_history[cid])
    variance = max(cpu_history[cid]) - min(cpu_history[cid])

    return avg < 0.4 and variance < 0.2


def slow_death(cid, metrics):
    cpu_history[cid].append(metrics["cpu_percent"])

    if len(cpu_history[cid]) < 10:
        return False

    vals = list(cpu_history[cid])
    slope = (vals[-1] - vals[0]) / len(vals)

    return slope < -0.05


# =========================
# ANOMALY SCORE ENGINE
# =========================

def anomaly_score(cid, metrics, stuck, slow):
    base = 0

    if metrics["cpu_percent"] < 0.5:
        base += 20
    if metrics["memory_percent"] > 80:
        base += 25
    if stuck:
        base += 35
    if slow:
        base += 30

    return min(base, 100)


# =========================
# FAILURE RISK + ACTION ENGINE
# =========================

def action_engine(state, risk):
    if state == "critical" or risk > 80:
        return "RESTART_RECOMMENDED"
    if risk > 60:
        return "INVESTIGATE"
    if state == "degraded":
        return "WATCH"
    return "NO_ACTION"


# =========================
# NODE HEALTH
# =========================

def node_health(containers):
    if not containers:
        return 100

    avg_cpu = sum(c["metrics"]["cpu_percent"] for c in containers) / len(containers)
    avg_mem = sum(c["metrics"]["memory_percent"] for c in containers) / len(containers)
    avg_anomaly = sum(c["anomaly"] for c in containers) / len(containers)

    return round(max(0, 100 - avg_cpu*0.3 - avg_mem*0.3 - avg_anomaly*0.4), 2)


# =========================
# SNAPSHOT ENGINE
# =========================

def snapshot():

    containers = client.containers.list()

    processed = []
    clusters = defaultdict(int)

    for c in containers:

        cid = c.short_id

        try:
            c.reload()
        except:
            continue

        metrics = get_metrics(c)

        stuck = detect_stuck(cid, metrics)
        slow = slow_death(cid, metrics)

        anomaly = anomaly_score(cid, metrics, stuck, slow)
        state = classify_state(anomaly)

        risk_memory[cid] = (risk_memory[cid] * 0.8) + (anomaly * 0.2)

        risk = int(risk_memory[cid])

        cluster = cluster_signature(metrics, stuck, slow)
        clusters[cluster] += 1

        fingerprint_id = fingerprint(metrics, state)

        action = action_engine(state, risk)

        processed.append({
            "id": cid,
            "name": c.name,
            "state": state,
            "metrics": metrics,
            "anomaly": anomaly,
            "risk": risk,
            "cluster": cluster,
            "fingerprint": fingerprint_id,
            "action": action
        })

        log_flat(cid, metrics, state, risk, anomaly)

        if state == "critical":
            log_event("CRITICAL", cid, "Container entered critical state")

        if action == "RESTART_RECOMMENDED":
            log_event("ACTION", cid, "Restart recommended due to sustained risk")

    payload = {
        "ts": now(),

        "signal": "ANALYZED",

        "node": {
            "health": node_health(processed)
        },

        "summary": {
            "containers": len(processed),
            "clusters": dict(clusters)
        },

        "insights": {
            "dominant_cluster": max(clusters, key=clusters.get) if clusters else "none",
            "system_state": "multi-dimensional-analysis-active"
        },

        "recommendations": [
            c for c in processed if c["action"] == "RESTART_RECOMMENDED"
        ],

        "containers": processed
    }

    log_structured(payload)


# =========================
# RUN LOOP
# =========================

def run():
    while True:
        try:
            snapshot()
        except Exception as e:
            log_structured({"error": str(e), "ts": now()})
        time.sleep(10)


if __name__ == "__main__":
    run()
