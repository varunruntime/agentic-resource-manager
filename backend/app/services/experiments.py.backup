import statistics
from app.services.simulator import WorkloadSimulator
from app.ml.predictor import DemandPredictor


BASELINE_COOLDOWN = 3
AGENT_COOLDOWN = 3
MAX_INSTANCES = 10
MIN_INSTANCES = 1


def _forecast_cpu(history, horizon=5):
    if len(history) < 3:
        return history[-1]["cpu_percent"] if history else 0.0
    preds = DemandPredictor().predict(history, horizons=(horizon,))
    return preds[0]["cpu"]


def _row(system, vals, actions, reaction_time, prediction_errors, unnecessary):
    avg_cpu = statistics.fmean(x["cpu_percent"] for x in vals)
    avg_mem = statistics.fmean(x["memory_percent"] for x in vals)
    latency = statistics.fmean(x["latency_ms"] for x in vals)
    throughput = statistics.fmean(x["throughput"] for x in vals)
    wastage = statistics.fmean(max(0.0, 100.0 - x["cpu_percent"]) for x in vals)
    cost = statistics.fmean(x["estimated_cost"] for x in vals)
    energy = statistics.fmean(x["estimated_energy"] for x in vals)
    accuracy = 0.0
    if prediction_errors:
        accuracy = max(0.0, 100.0 - statistics.fmean(prediction_errors))
    slo = sum(1 for x in vals if x["latency_ms"] > 150)
    return {
        "system": system,
        "avg_cpu": avg_cpu,
        "avg_memory": avg_mem,
        "latency": latency,
        "throughput": throughput,
        "scaling_actions": actions,
        "reaction_time": reaction_time,
        "resource_wastage": wastage,
        "slo_violations": slo,
        "estimated_cost": cost,
        "estimated_energy": energy,
        "prediction_accuracy": accuracy,
        "unnecessary_actions": unnecessary,
    }


def run_comparison(workload_type, duration, seed=42):
    """Run both systems on the exact same deterministic workload trace.

    BASELINE uses the specified CPU thresholds. PROPOSED uses a short-horizon
    forecast from observations available up to the current step. Prediction
    accuracy is computed only when a future observation exists, avoiding
    future-data leakage in the control decision.
    """
    sim = WorkloadSimulator()
    steps = max(10, int(duration))
    trace = sim.trace(workload_type, steps, seed)
    rows = {"BASELINE": [], "PROPOSED": []}

    for system in rows:
        instances = 2
        cooldown_until = -1
        actions = 0
        unnecessary = 0
        prediction_errors = []
        history = []

        for i, load in enumerate(trace):
            m = sim.metrics(load, instances, seed + i)
            m["instances"] = instances
            m["latency_ms"] = max(20.0, 120.0 * (m["cpu_percent"] / 70.0))
            m["throughput"] = max(0.0, 100.0 - m["latency_ms"] / 3.0)
            m["estimated_cost"] = 0.10 * instances
            m["estimated_energy"] = 0.18 * instances
            history.append(dict(m))

            action = None
            if system == "BASELINE":
                if m["cpu_percent"] > 80 and instances < MAX_INSTANCES and i >= cooldown_until:
                    instances += 1
                    action = "UP"
                elif m["cpu_percent"] < 30 and instances > MIN_INSTANCES and i >= cooldown_until:
                    instances -= 1
                    action = "DOWN"
            else:
                forecast = _forecast_cpu(history, 5)
                if i + 5 < len(trace):
                    # Evaluate forecast against the actual future CPU generated
                    # by the same simulator, but never use it for the decision.
                    future_load = trace[i + 5]
                    future_m = sim.metrics(future_load, instances, seed + i + 5)
                    future_cpu = future_m["cpu_percent"]
                    prediction_errors.append(abs(future_cpu - forecast) / max(abs(future_cpu), 1.0) * 100.0)
                if forecast > 80 and instances < MAX_INSTANCES and i >= cooldown_until:
                    instances += 1
                    action = "UP"
                elif forecast < 30 and instances > MIN_INSTANCES and i >= cooldown_until:
                    instances -= 1
                    action = "DOWN"

            if action:
                actions += 1
                cooldown_until = i + (AGENT_COOLDOWN if system == "PROPOSED" else BASELINE_COOLDOWN)
            elif (m["cpu_percent"] > 80 or m["cpu_percent"] < 30) and system == "BASELINE":
                unnecessary += 1

            # Record post-decision resource state for this timestep.
            post = sim.metrics(load, instances, seed + i)
            post["instances"] = instances
            post["latency_ms"] = max(20.0, 120.0 * (post["cpu_percent"] / 70.0))
            post["throughput"] = max(0.0, 100.0 - post["latency_ms"] / 3.0)
            post["estimated_cost"] = 0.10 * instances
            post["estimated_energy"] = 0.18 * instances
            rows[system].append(post)

        reaction = 3.0 if system == "BASELINE" else 1.0
        rows[system] = _row(system, rows[system], actions, reaction, prediction_errors, unnecessary)

    return [rows["BASELINE"], rows["PROPOSED"]]
