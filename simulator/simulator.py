"""
DC Monitor - Metric Simulator
------------------------------
Simulates real datacenter servers by periodically POSTing metric snapshots
to the API. Each server has a distinct behavioral profile to make the
data realistic and interesting.
"""

import time
import random
import math
import urllib.request
import urllib.error
import json
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("simulator")

API_BASE = os.environ.get("API_BASE_URL", "http://api:8000")
INTERVAL = int(os.environ.get("INTERVAL_SECONDS", "10"))

# Server profiles: baseline and volatility per metric (baseline, volatility)
PROFILES = {
    "web-01":     {"cpu": (45, 20), "mem": (60, 10), "disk": (40, 2), "temp": (55, 8), "net_in": (50, 30),  "net_out": (80, 40)},
    "web-02":     {"cpu": (50, 25), "mem": (62, 10), "disk": (42, 2), "temp": (57, 8), "net_in": (55, 35),  "net_out": (85, 40)},
    "db-primary": {"cpu": (70, 15), "mem": (85, 5),  "disk": (65, 1), "temp": (65, 6), "net_in": (20, 10),  "net_out": (15, 8)},
    "db-replica": {"cpu": (30, 10), "mem": (75, 5),  "disk": (65, 1), "temp": (58, 5), "net_in": (15, 8),   "net_out": (10, 5)},
    "storage-01": {"cpu": (20, 8),  "mem": (40, 5),  "disk": (80, 1), "temp": (48, 4), "net_in": (100, 60), "net_out": (90, 55)},
    "cache-01":   {"cpu": (60, 20), "mem": (90, 3),  "disk": (25, 1), "temp": (62, 7), "net_in": (200, 80), "net_out": (195, 80)},
    "backup-01":  {"cpu": (15, 5), "mem": (35, 5), "disk": (85, 1), "temp": (45, 4), "net_in": (80, 40), "net_out": (75, 40)},
    "monitor-01": {"cpu": (40, 8), "mem": (55, 5), "disk": (50, 1), "temp": (52, 4), "net_in": (30, 10), "net_out": (25, 10)},
    "loadbalancer-01": {"cpu": (55, 30), "mem": (45, 8), "disk": (30, 1), "temp": (58, 6), "net_in": (300, 100), "net_out": (295, 100)},
}

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def simulate_value(baseline: float, volatility: float, t: float) -> float:
    """Generate a realistic-looking metric using a sine wave + noise."""
    wave = math.sin(t / 60) * (volatility * 0.4)
    noise = random.gauss(0, volatility * 0.3)
    return clamp(baseline + wave + noise, 0, 100)

def get_server_ids() -> dict:
    url = f"{API_BASE}/servers/"
    req = urllib.request.Request(
        url,
        headers={"X-API-Key": os.environ.get("API_KEY", "dc-monitor-secret-key")},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            servers = json.loads(resp.read())
            return {s["hostname"]: s["id"] for s in servers}
    except Exception as e:
        logger.error(f"[simulator] Could not fetch servers: {e}")
        return {}

def post_metric(server_id: int, payload: dict):
    url = f"{API_BASE}/servers/{server_id}/metrics/"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": os.environ.get("API_KEY", "dc-monitor-secret-key"),
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        logger.error(f"[simulator] HTTP {e.code} for server {server_id}")
    except Exception as e:
        logger.error(f"[simulator] Error posting to server {server_id}: {e}")

def wait_for_api(retries: int = 15, delay: int = 3) -> bool:
    """Wait until the API is reachable before starting."""
    logger.info(f"Waiting for API at {API_BASE}...")
    
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{API_BASE}/health", timeout=3):
                logger.info("API is up. Starting simulation.")
                return True
        except Exception:
            logger.warning(f"Attempt {attempt + 1}/{retries} - API not ready yet.")
            time.sleep(delay)
            
    logger.error("API did not become available. Exiting.")
    return False

def main():
    if not wait_for_api():
        return

    t = 0
    logger.info(f"Posting metrics every {INTERVAL}s. Press Ctrl+C to stop.")

    while True:
        server_ids = get_server_ids()

        if not server_ids:
            logger.warning("No servers found. Retrying in 30s...")
            time.sleep(30)
            continue

        for hostname, profile in PROFILES.items():
            server_id = server_ids.get(hostname)
            if not server_id:
                continue

            payload = {
                "cpu_usage":    round(simulate_value(*profile["cpu"], t), 2),
                "memory_usage": round(simulate_value(*profile["mem"], t), 2),
                "disk_usage":   round(simulate_value(*profile["disk"], t), 2),
                "temperature":  round(clamp(
                    profile["temp"][0]
                    + math.sin(t / 60) * profile["temp"][1] * 0.4
                    + random.gauss(0, profile["temp"][1] * 0.3),
                    0, 120), 2),
                "network_in":   round(max(0, random.gauss(*profile["net_in"])), 2),
                "network_out":  round(max(0, random.gauss(*profile["net_out"])), 2),
            }

            status = post_metric(server_id, payload)
            
            if status:
                logger.info(
                    f"{hostname:<16} "
                    f"CPU: {payload['cpu_usage']:5.1f}%  "
                    f"MEM: {payload['memory_usage']:5.1f}%  "
                    f"TEMP: {payload['temperature']:5.1f}C  "
                    f"NET↓: {payload['network_in']:6.1f} MB/s"
                )

        t += INTERVAL
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()