
class PlanningAgent:
    def rank(self, candidates, obs, weights, predictions=None):
        if not candidates:
            raise ValueError("No candidate actions available.")

        predictions = predictions or []

        cpu = float(obs.get("cpu_percent", 0))
        memory = float(obs.get("memory_percent", 0))
        network = float(obs.get("network_usage", 0))

        predicted_cpu = max(
            (float(p.get("cpu", 0)) for p in predictions),
            default=cpu
        )
        predicted_memory = max(
            (float(p.get("memory", 0)) for p in predictions),
            default=memory
        )

        high_pressure = (
            cpu >= 80 or memory >= 90 or network > 85
            or predicted_cpu >= 80 or predicted_memory >= 90
        )

        low_utilization = cpu < 30 and memory < 70

        def score(action):
            name = action["action"]

            performance_gain = 0.0
            utilization_gain = 0.0

            if name in {"ADD_INSTANCE", "INCREASE_CPU"}:
                performance_gain = 1.0 if high_pressure else 0.2
                utilization_gain = 0.8 if high_pressure else 0.2

            elif name in {"REMOVE_INSTANCE", "DECREASE_CPU"}:
                performance_gain = 0.7 if low_utilization else 0.1
                utilization_gain = 1.0 if low_utilization else 0.1

            elif name == "PRIORITIZE_WORKLOAD":
                performance_gain = 0.8 if high_pressure else 0.3

            elif name == "DO_NOTHING":
                performance_gain = 0.1 if high_pressure else 0.5
                utilization_gain = 0.5

            cost = float(action.get("estimated_cost", 0))
            energy = float(action.get("estimated_energy", 0))

            return (
                weights.performance * performance_gain
                + weights.utilization * utilization_gain
                - weights.cost * cost
                - weights.energy * energy
            )

        ranked = [
            {**action, "score": score(action)}
            for action in candidates
        ]

        ranked.sort(key=lambda item: item["score"], reverse=True)

        return {
            "selected": ranked[0],
            "alternatives": ranked[1:]
        }
