import statistics
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.simulator import WorkloadSimulator
from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings
from app.policies.safety import COOLDOWN_SECONDS


# Each experiment sample represents one simulated second.
BASELINE_COOLDOWN = COOLDOWN_SECONDS
MAX_INSTANCES = 10
MIN_INSTANCES = 1


def _add_derived_metrics(metrics, instances, cpu_capacity_multiplier=1.0):
    result = dict(metrics)
    result["instances"] = instances

    # Raw simulator readings do not contain derived metrics. Post-action
    # readings do, and those measured values must not be overwritten here.
    result.setdefault(
        "latency_ms",
        max(20.0, 120.0 * (result["cpu_percent"] / 70.0)),
    )
    result.setdefault(
        "throughput",
        max(0.0, 100.0 - result["latency_ms"] / 3.0),
    )
    result.setdefault("cpu_capacity_multiplier", cpu_capacity_multiplier)
    result.setdefault("estimated_cost", 0.10 * instances * cpu_capacity_multiplier)
    result.setdefault("estimated_energy", 0.18 * instances * cpu_capacity_multiplier)

    return result


def _relative_error(actual, predicted):
    return abs(actual - predicted) / max(abs(actual), 1.0) * 100.0


def _row(system, vals, actions, reaction_times, prediction_errors, unnecessary):
    avg_cpu = statistics.fmean(x["cpu_percent"] for x in vals)
    avg_mem = statistics.fmean(x["memory_percent"] for x in vals)
    latency = statistics.fmean(x["latency_ms"] for x in vals)
    throughput = statistics.fmean(x["throughput"] for x in vals)
    wastage = statistics.fmean(
        max(0.0, 100.0 - x["cpu_percent"]) for x in vals
    )
    cost = statistics.fmean(x["estimated_cost"] for x in vals)
    energy = statistics.fmean(x["estimated_energy"] for x in vals)

    # Accuracy is 100 - mean absolute percentage error, clamped to [0, 100].
    # Both systems now report a value using the same five-step target.
    accuracy = (
        max(0.0, min(100.0, 100.0 - statistics.fmean(prediction_errors)))
        if prediction_errors else 0.0
    )

    slo = sum(1 for x in vals if x["latency_ms"] > 150)
    reaction_time = (
        statistics.fmean(reaction_times)
        if reaction_times else 0.0
    )

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


def _prediction_at_horizon(predictions, horizon=5):
    for prediction in predictions:
        if prediction.get("horizon") == horizon:
            return float(prediction["cpu"])
    return None


def _run_baseline(trace, sim, seed):
    instances = 2
    cooldown_until = -1
    actions = 0
    unnecessary = 0
    values = []
    reaction_times = []
    prediction_errors = []
    pending_forecasts = {}
    overload_start = None

    for i, load in enumerate(trace):
        current = _add_derived_metrics(
            sim.metrics(load, instances, seed + i),
            instances
        )

        if current["cpu_percent"] > 80 and overload_start is None:
            overload_start = i

        # Score the forecast created five timesteps earlier against the
        # actual observation now, after any intervening baseline actions.
        if i in pending_forecasts:
            prediction_errors.append(
                _relative_error(current["cpu_percent"], pending_forecasts.pop(i))
            )

        # Baseline uses a persistence forecast: next CPU is predicted to
        # equal the current observed CPU. Future observations are never read
        # before they occur.
        if i + 5 < len(trace):
            pending_forecasts[i + 5] = current["cpu_percent"]

        action = None
        if i >= cooldown_until:
            if current["cpu_percent"] > 80 and instances < MAX_INSTANCES:
                instances += 1
                action = "ADD_INSTANCE"
            elif current["cpu_percent"] < 30 and instances > MIN_INSTANCES:
                instances -= 1
                action = "REMOVE_INSTANCE"

        if action:
            actions += 1
            cooldown_until = i + BASELINE_COOLDOWN

            if overload_start is not None and action == "ADD_INSTANCE":
                reaction_times.append(i - overload_start)
                overload_start = None
        elif current["cpu_percent"] > 80 or current["cpu_percent"] < 30:
            unnecessary += 1

        post = _add_derived_metrics(
            sim.metrics(load, instances, seed + i),
            instances
        )
        values.append(post)

    return _row(
        "BASELINE",
        values,
        actions,
        reaction_times,
        prediction_errors,
        unnecessary
    )


def _run_proposed(trace, sim, seed):
    instances = 2
    cpu_capacity_multiplier = 1.0
    actions = 0
    unnecessary = 0
    history = []
    values = []
    prediction_errors = []
    reaction_times = []

    feedback = None
    last_action_time = None
    pending_forecasts = {}
    overload_start = None

    weights = SimpleNamespace(
        performance=0.40,
        cost=0.25,
        energy=0.20,
        utilization=0.15,
    )
    orchestrator = AgentOrchestrator(db=None, settings=settings)
    experiment_start = datetime(2026, 1, 1)

    for i, load in enumerate(trace):
        current = _add_derived_metrics(
            sim.metrics(load, instances, seed + i, cpu_capacity_multiplier),
            instances,
            cpu_capacity_multiplier,
        )
        history.append(dict(current))

        if current["cpu_percent"] > 80 and overload_start is None:
            overload_start = i

        # Use a deterministic simulation clock so the same 60-second
        # cooldown is enforced by the orchestrator in repeatable runs.
        cycle_time = experiment_start + timedelta(seconds=i)

        # Run the actual nine-stage orchestrator. The first cycle receives
        # None; subsequent cycles receive the previous cycle's feedback.
        result = orchestrator.run(
            history=history,
            state=current,
            weights=weights,
            mode="simulation",
            active_workloads=current["active_workloads"],
            feedback=feedback,
            last_action_time=last_action_time,
            now=cycle_time,
        )

        action = result["selected_action"]
        outcome = result["outcome"]

        # Score a five-step forecast issued earlier against the actual
        # current observation. That observation includes the real state
        # produced by intervening agent decisions; no future data is leaked.
        if i in pending_forecasts:
            prediction_errors.append(
                _relative_error(current["cpu_percent"], pending_forecasts.pop(i))
            )

        forecast = _prediction_at_horizon(result["prediction"], 5)
        if forecast is not None and i + 5 < len(trace):
            pending_forecasts[i + 5] = forecast

        predicted_peak_cpu = max(
            (float(item.get("cpu", 0.0)) for item in result["prediction"]),
            default=current["cpu_percent"],
        )
        predicted_peak_memory = max(
            (float(item.get("memory", 0.0)) for item in result["prediction"]),
            default=current["memory_percent"],
        )
        predicted_pressure = (
            current["cpu_percent"] >= 80
            or current["memory_percent"] >= 90
            or current["network_usage"] > 85
            or predicted_peak_cpu >= 80
            or predicted_peak_memory >= 90
        )

        after = result["actual_result"]

        capacity_actions = {
            "ADD_INSTANCE",
            "REMOVE_INSTANCE",
            "INCREASE_CPU",
            "DECREASE_CPU",
        }
        if outcome == "SUCCESS" and action in capacity_actions:
            actions += 1

            if action in {"ADD_INSTANCE", "REMOVE_INSTANCE"}:
                last_action_time = cycle_time

            if action in {"ADD_INSTANCE", "INCREASE_CPU"} and not predicted_pressure:
                unnecessary += 1
            elif action in {"REMOVE_INSTANCE", "DECREASE_CPU"} and not (
                current["cpu_percent"] < 30 and current["memory_percent"] < 70
            ):
                unnecessary += 1

            if overload_start is not None and action in {
                "ADD_INSTANCE",
                "INCREASE_CPU",
            }:
                reaction_times.append(i - overload_start)
                overload_start = None

        instances = int(after.get("instances", instances))
        cpu_capacity_multiplier = float(after.get("cpu_capacity_multiplier", cpu_capacity_multiplier))
        values.append(_add_derived_metrics(after, instances, cpu_capacity_multiplier))

        # Carry this cycle's feedback into the next cycle.
        feedback = result["feedback"]

    return _row(
        "PROPOSED",
        values,
        actions,
        reaction_times,
        prediction_errors,
        unnecessary
    )


def run_comparison(workload_type, duration, seed=42):
    """
    Compare a threshold baseline with the actual nine-stage orchestrator.

    Both systems receive the same deterministic workload trace, seed,
    initial instance count and one-second sample interval.
    """
    sim = WorkloadSimulator()
    steps = max(10, int(duration))
    trace = sim.trace(workload_type, steps, seed)

    baseline = _run_baseline(trace, sim, seed)
    proposed = _run_proposed(trace, sim, seed)
    return [baseline, proposed]
