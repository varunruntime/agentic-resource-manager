"""In-process deterministic workload simulation state for local demonstrations.

Workload definitions and active state live in SQLite. The current trace cursor
is intentionally process-local; use one API worker for this demo runtime.
"""
from app.services.simulator import WorkloadSimulator

SIMULATION_TICK_SECONDS = 2
_simulator = WorkloadSimulator()
_runs: dict[int, dict] = {}


def start_workload_simulation(workload) -> None:
    workload_id = int(workload.id)
    duration_seconds = max(1, int(workload.duration_seconds or 1))
    steps = max(1, (duration_seconds + SIMULATION_TICK_SECONDS - 1) // SIMULATION_TICK_SECONDS)
    trace = _simulator.trace(
        workload.workload_type,
        steps=steps,
        seed=workload_id,
        initial=float(workload.initial_load),
        growth=float(workload.growth_rate),
    )
    _runs[workload_id] = {"trace": trace, "cursor": 0}


def stop_workload_simulation(workload_id: int) -> None:
    _runs.pop(int(workload_id), None)


def next_workload_load(workload) -> float | None:
    workload_id = int(workload.id)
    if workload_id not in _runs:
        start_workload_simulation(workload)

    run = _runs[workload_id]
    cursor = run["cursor"]
    trace = run["trace"]
    if cursor >= len(trace):
        stop_workload_simulation(workload_id)
        return None

    run["cursor"] = cursor + 1
    return float(trace[cursor])
