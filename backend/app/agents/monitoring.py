import math
import random
from datetime import datetime

import psutil


SIMULATED_CAPACITY_PER_INSTANCE = 60.0


class MonitoringAgent:
    def observe_real(self, instances=2, active_workloads=1):
        net = psutil.net_io_counters()
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "network_usage": float((net.bytes_sent + net.bytes_recv) % 1000) / 10,
            "active_workloads": active_workloads,
            "instances": instances,
        }

    def observe_simulated(
        self,
        load,
        instances=2,
        active_workloads=1,
        seed=None,
        cpu_capacity_multiplier=1.0,
    ):
        rng = random.Random(seed)
        safe_instances = max(1, int(instances))
        safe_multiplier = max(0.5, min(2.0, float(cpu_capacity_multiplier)))
        capacity = safe_instances * SIMULATED_CAPACITY_PER_INSTANCE * safe_multiplier

        cpu = max(0.0, min(100.0, (float(load) / capacity) * 100.0))
        cpu = max(0.0, min(100.0, cpu + rng.uniform(-2.0, 2.0)))
        memory = max(0.0, min(100.0, 35.0 + 0.55 * cpu + rng.uniform(-2.0, 2.0)))
        network = max(0.0, min(100.0, float(load) * 0.9 + rng.uniform(-3.0, 3.0))

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_percent": 40.0 + rng.uniform(-1.0, 1.0),
            "network_usage": network,
            "active_workloads": int(active_workloads),
            "instances": safe_instances,
            "cpu_capacity_multiplier": safe_multiplier,
        }

    def observe_snapshot(self, snapshot):
        """Normalize an already-collected metric snapshot for the agent pipeline."""
        result = dict(snapshot or {})
        numeric_defaults = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_percent": 0.0,
            "network_usage": 0.0,
            "active_workloads": 0,
            "instances": 1,
            "cpu_capacity_multiplier": 1.0,
        }

        for key, default in numeric_defaults.items():
            value = float(result.get(key, default))
            if not math.isfinite(value):
                raise ValueError(f"Metric {key} must be finite.")
            result[key] = value

        for key in ("cpu_percent", "memory_percent", "disk_percent", "network_usage"):
            result[key] = max(0.0, min(100.0, result[key]))

        result["active_workloads"] = max(0, int(result["active_workloads"]))
        result["instances"] = max(1, int(result["instances"]))
        result["cpu_capacity_multiplier"] = max(
            0.5, min(2.0, result["cpu_capacity_multiplier"])
        )
        result.setdefault("timestamp", datetime.utcnow().isoformat())
        return result
