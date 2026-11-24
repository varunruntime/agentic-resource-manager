import statistics
from types import SimpleNamespace

from app.services.simulator import WorkloadSimulator
from app.agents.orchestrator import AgentOrchestrator
from app.core.config import settings


BASELINE_COOLDOWN = 3
MAX_INSTANCES = 10
MIN_INSTANCES = 1


def _add_derived_metrics(metrics, instances):
    result = dict(metrics)
    result["instances"] = instances

    result["latency_ms"] = max(
        20.0,
        120.0 * (result["cpu_percent"] / 70.0)
    )
    result["throughput"] = max(
        0.0,
        100.0 - result["latency_ms"] / 3.0
    )
    result["estimated_cost"] = 0.10 * instances
    result["estimated_energy"] = 0.18 * instances

    return result


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

    accuracy = (
        max(0.0, 100.0 - statistics.fmean(prediction_errors))
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
    history = []
    values = []
    reaction_times = []

    overload_start = None

    for i, load in enumerate(trace):
        current = _add_derived_metrics(
            sim.metrics(load, instances, seed + i),
            instances
        )

        history.append(dict(current))

        if current["cpu_percent"] > 80 and overload_start is None:
            overload_start = i

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

            if overload_start is not None:
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
        [],
        unnecessary
    )


def _run_proposed(trace, sim, seed):
    instances = 2

    actions = 0
    unnecessary = 0
    history = []
    values = []
    prediction_errors = []
    reaction_times = []

    feedback = None
    overload_start = None

    weights = SimpleNamespace(
        performance=0.40,
        cost=0.25,
        energy=0.20,
        utilization=0.15,
    )

    orchestrator = AgentOrchestrator(
        db=None,
        settings=settings
    )

    for i, load in enumerate(trace):
        current = _add_derived_metrics(
            sim.metrics(load, instances, seed + i),
            instances
        )

        history.append(dict(current))

        if current["cpu_percent"] > 80 and overload_start is None:
            overload_start = i

        # Run the actual nine-stage orchestrator.
        result = orchestrator.run(
            history=history,
            state=current,
            weights=weights,
            mode="simulation",
            active_workloads=current["active_workloads"],
            feedback = result["feedback"],
        )

        action = result["selected_action"]
        outcome = result["outcome"]

        # Evaluate prediction against a future observation.
        # Future data is NOT passed into the decision.
        forecast = _prediction_at_horizon(result["prediction"], 5)

        if forecast is not None and i + 5 < len(trace):
            future_metrics = sim.metrics(
                trace[i + 5],
                instances,
                seed + i + 5
            )
            actual_future_cpu = future_metrics["cpu_percent"]

            error = (
                abs(actual_future_cpu - forecast)
                / max(abs(actual_future_cpu), 1.0)
            ) * 100.0

            prediction_errors.append(error)

        after = result["actual_result"]

        if outcome == "SUCCESS":
            if action in {"ADD_INSTANCE", "REMOVE_INSTANCE"}:
                actions += 1

                if overload_start is not None and action == "ADD_INSTANCE":
                    reaction_times.append(i - overload_start)
                    overload_start = None

                if current["cpu_percent"] <= 80 and action == "ADD_INSTANCE":
                    unnecessary += 1

                if current["cpu_percent"] >= 30 and action == "REMOVE_INSTANCE":
                    unnecessary += 1

        # Carry the actual simulated state into the next timestep.
        instances = int(after.get("instances", instances))

        post = _add_derived_metrics(
            after,
            instances
        )

        values.append(post)

        # Feedback from this cycle becomes input to the next cycle.
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
    Compare a threshold baseline against the actual nine-stage orchestrator.

    Both systems receive the same deterministic workload trace and
    initial instance count.
    """

    sim = WorkloadSimulator()
    steps = max(10, int(duration))

    trace = sim.trace(
        workload_type,
        steps,
        seed
    )

    baseline = _run_baseline(trace, sim, seed)
    proposed = _run_proposed(trace, sim, seed)

    return [baseline, proposed]