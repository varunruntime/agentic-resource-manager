class RuleBasedReasoningProvider:
    def reason(self, obs, prediction, analysis):
        issue=analysis["issue"]
        if issue in {"PREDICTED_OVERLOAD","OVERLOAD"}:
            actions=[{"action":"ADD_INSTANCE","delta":1,"reason":"Increase capacity before/while CPU is high.","expected_effect":"Lower CPU and latency.","estimated_cost":0.25},{"action":"INCREASE_CPU","delta":0,"reason":"Add CPU capacity to current allocation.","expected_effect":"Lower CPU pressure.","estimated_cost":0.20},{"action":"PRIORITIZE_WORKLOAD","delta":0,"reason":"Protect high-priority workload service levels.","expected_effect":"Reduce SLO risk without scaling.","estimated_cost":0.05}]
            rec="ADD_INSTANCE"
        elif issue=="UNDERUTILIZATION":
            actions=[{"action":"REMOVE_INSTANCE","delta":1,"reason":"Reduce idle capacity.","expected_effect":"Improve utilization and cost.","estimated_cost":-0.20},{"action":"DECREASE_CPU","delta":0,"reason":"Reduce overprovisioned CPU.","expected_effect":"Lower cost and energy.","estimated_cost":-0.10},{"action":"DO_NOTHING","delta":0,"reason":"Avoid action when load may recover.","expected_effect":"No direct change.","estimated_cost":0.0}]
            rec="REMOVE_INSTANCE"
        else:
            actions=[{"action":"DO_NOTHING","delta":0,"reason":"No significant issue detected.","expected_effect":"Preserve current allocation.","estimated_cost":0.0}]
            rec="DO_NOTHING"
        return {"problem":analysis.get("reason", analysis.get("issue", "Condition detected.")),"candidate_actions":actions,"recommended_action":rec,"reason":"Rule-based fallback selected the safest capacity response for the detected condition."}

class LLMReasoningProvider(RuleBasedReasoningProvider):
    def __init__(self, api_key=None): self.api_key=api_key
    def reason(self, obs, prediction, analysis):
        # Provider boundary is intentionally safe: arbitrary tool/shell execution is impossible.
        return super().reason(obs,prediction,analysis)
