"""In-process deterministic workload simulation state for the local demo.

The database stores workload definitions and active flags; this module stores
only the current trace cursor. Workload metrics are persisted by the telemetry
loop, so browser clients and the agent always read the same observations.
"""
from app.services.simulator import WorkloadSimulator

_simulator = WorkloadSimulator()
_runs: dict[int, dict] = {}


def start_workload_simulation(workload) -> None:
    workload_id = int(workload.id)
    duration = max(1, int(workload.duration_seconds or 1))
    trace = _simulator.trace(
        workload.workload_type,
        steps=duration,
        seed=workload_id,
        initial=float(workload.initial_load),
        growth=float(workload.growth_rate),
    )
    _runs[workload_id] = {"trace": trace, "cursor": 0}


def stop_workload_simulation(workload_id: int) -> None:
    _runs.pop(int(workload_id), None)


def has_workload_simulation(workload_id: int) -> bool:
    return int(workload_id) in _runs


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
