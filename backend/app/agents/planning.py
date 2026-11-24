class PlanningAgent:
    def rank(self, candidates, obs, weights):
        def score(a):
            utilization_gain = 1.0 if a["action"] in {"ADD_INSTANCE","REMOVE_INSTANCE","INCREASE_CPU","DECREASE_CPU"} else 0.2
            latency_gain = 0.9 if a["action"] in {"ADD_INSTANCE","INCREASE_CPU","PRIORITIZE_WORKLOAD"} else 0.1
            cost = max(0,min(1,0.5+float(a.get("estimated_cost",0))))
            energy = cost
            return weights.performance*latency_gain + weights.utilization*utilization_gain - weights.cost*cost - weights.energy*energy
        ranked=[]
        for a in candidates:
            ranked.append({**a,"score":score(a)})
        ranked.sort(key=lambda x:x["score"], reverse=True)
        return {"selected":ranked[0],"alternatives":ranked[1:]}
