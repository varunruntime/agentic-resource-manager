class RuleBasedReasoningProvider:

    def reason(self, obs, prediction, analysis, feedback=None):
        issues = analysis.get("issue", ["NORMAL"])

        if isinstance(issues, str):
            issues = [issues]

        cpu = float(obs.get("cpu_percent", 0))
        memory = float(obs.get("memory_percent", 0))
        network = float(obs.get("network_usage", 0))

        predicted_cpu = max(
            (float(p.get("cpu", 0)) for p in prediction),
            default=cpu
        )
        predicted_memory = max(
            (float(p.get("memory", 0)) for p in prediction),
            default=memory
        )

        # Keep this threshold aligned with PlanningAgent's predicted-pressure
        # threshold so a forecast at/above 80% produces actionable candidates.
        high_pressure = (
            cpu >= 80
            or memory >= 90
            or network > 85
            or predicted_cpu >= 80
            or predicted_memory >= 90
        )
        underutilized = cpu < 30 and memory < 70

        if high_pressure:
            actions = [
                {
                    "action": "ADD_INSTANCE",
                    "delta": 1,
                    "reason": "Increase capacity to handle predicted demand.",
                    "expected_effect": "Reduce CPU, memory pressure and latency.",
                    "estimated_cost": 0.25,
                    "estimated_energy": 0.08
                },
                {
                    "action": "INCREASE_CPU",
                    "delta": 0,
                    "reason": "Increase available CPU capacity.",
                    "expected_effect": "Reduce CPU pressure and latency.",
                    "estimated_cost": 0.20,
                    "estimated_energy": 0.06
                },
                {
                    "action": "DO_NOTHING",
                    "delta": 0,
                    "reason": "Avoid unnecessary infrastructure changes.",
                    "expected_effect": "Maintain current allocation.",
                    "estimated_cost": 0.0,
                    "estimated_energy": 0.0
                }
            ]
        elif underutilized:
            actions = [
                {
                    "action": "REMOVE_INSTANCE",
                    "delta": 1,
                    "reason": "Reduce unused infrastructure capacity.",
                    "expected_effect": "Reduce infrastructure cost and energy.",
                    "estimated_cost": -0.10,
                    "estimated_energy": -0.04
                },
                {
                    "action": "DO_NOTHING",
                    "delta": 0,
                    "reason": "Preserve existing capacity.",
                    "expected_effect": "Maintain current allocation.",
                    "estimated_cost": 0.0,
                    "estimated_energy": 0.0
                }
            ]
        else:
            actions = [
                {
                    "action": "DO_NOTHING",
                    "delta": 0,
                    "reason": "Resource pressure is within acceptable limits.",
                    "expected_effect": "Maintain current allocation.",
                    "estimated_cost": 0.0,
                    "estimated_energy": 0.0
                }
            ]

        # Avoid repeating an unsuccessful or demonstrably harmful action.
        previous_action = None
        if feedback:
            outcome = feedback.get("outcome")
            cpu_improvement = float(feedback.get("cpu_improvement", 0))
            latency_improvement = float(feedback.get("latency_improvement", 0))

            if (
                outcome in {"REJECTED", "FAILED"}
                or (
                    outcome == "SUCCESS"
                    and cpu_improvement < 0
                    and latency_improvement < 0
                )
            ):
                previous_action = feedback.get("selected_action")

        if previous_action:
            actions = [
                action for action in actions
                if action["action"] != previous_action
            ]

        if not actions:
            actions = [{
                "action": "DO_NOTHING",
                "delta": 0,
                "reason": "Previous action failed. Avoid repeating it.",
                "expected_effect": "Maintain current allocation.",
                "estimated_cost": 0.0,
                "estimated_energy": 0.0
            }]

        return {
            "problem": analysis.get("reason", ", ".join(issues)),
            "detected_issues": issues,
            "predicted_peak_cpu": predicted_cpu,
            "predicted_peak_memory": predicted_memory,
            "candidate_actions": actions,
            "recommended_action": actions[0]["action"],
            "reason": "Evaluated current metrics, predictions and previous feedback."
        }


class LLMReasoningProvider(RuleBasedReasoningProvider):

    def __init__(self, api_key=None):
        self.api_key = api_key

    def reason(self, obs, prediction, analysis, feedback=None):
        # The LLM provider remains a safe rule-based boundary until a validated
        # structured LLM integration is explicitly implemented.
        return super().reason(obs, prediction, analysis, feedback)
