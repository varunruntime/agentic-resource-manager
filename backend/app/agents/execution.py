class ExecutionAgent:
    """Simulation-only executor. It never runs shell commands or touches a real host."""

    def simulate(self, action, state):
        before = dict(state)
        instances = max(1, int(state.get("instances", 2)))
        name = action["action"]
        delta = max(1, int(action.get("delta", 1)))

        if name == "ADD_INSTANCE":
            instances += delta
        elif name == "REMOVE_INSTANCE":
            instances = max(1, instances - delta)

        cpu = float(state.get("cpu_percent", 0))
        memory = float(state.get("memory_percent", 0))
        latency = float(state.get("latency_ms", 100))

        if name in {"ADD_INSTANCE", "REMOVE_INSTANCE"}:
            factor = float(state.get("instances", 2)) / max(instances, 1)
            cpu *= factor
            memory *= factor
            latency *= factor
        elif name == "INCREASE_CPU":
            cpu *= 0.85
            latency *= 0.90
        elif name == "DECREASE_CPU":
            cpu *= 1.15
            latency *= 1.10
        elif name == "PRIORITIZE_WORKLOAD":
            latency *= 0.92

        after = dict(state)
        after["instances"] = instances
        after["cpu_percent"] = max(0, min(100, cpu))
        after["memory_percent"] = max(0, min(100, memory))
        after["latency_ms"] = max(1, latency)
        after["estimated_cost"] = max(0, 0.10 * instances)
        after["estimated_energy"] = max(0, 0.18 * instances)
        return before, after
