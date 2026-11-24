import random, math
from app.agents.monitoring import MonitoringAgent


class WorkloadSimulator:
    """Deterministic workload generator used for safe, repeatable experiments."""

    def trace(self, workload_type, steps=60, seed=42, initial=40, growth=1.0):
        rng = random.Random(seed)
        kind = str(workload_type).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "stable": "stable",
            "increasing": "increasing",
            "decreasing": "decreasing",
            "sudden_spike": "sudden_spike",
            "sudden_spike_test": "sudden_spike",
            "periodic": "periodic",
            "anomaly": "anomaly",
            "anomalous": "anomaly",
        } 
        kind = aliases.get(kind, kind)
        out = []
        for i in range(max(1, steps)):
            if kind == "stable":
                load = initial + rng.uniform(-2, 2)
            elif kind == "increasing":
                load = initial + growth * i + rng.uniform(-2, 2)
            elif kind == "decreasing":
                load = max(0, initial - growth * i) + rng.uniform(-2, 2)
            elif kind == "sudden_spike":
                spike_start = int(steps * 0.65)
                load = initial + (55 if i >= spike_start else 0) + rng.uniform(-2, 2)
            elif kind == "periodic":
                load = initial + 25 * math.sin(i / 5) + rng.uniform(-2, 2)
            elif kind == "anomaly":
                load = initial + growth * i + rng.uniform(-2, 2)
                if i in {steps // 2, steps // 2 + 1}:
                    load += 45
            else:
                load = initial + rng.uniform(-10, 10)
            out.append(max(0, min(100, load)))
        return out

    def metrics(self, load, instances, seed=None):
        return MonitoringAgent().observe_simulated(load, max(1, int(instances)), 1, seed)
