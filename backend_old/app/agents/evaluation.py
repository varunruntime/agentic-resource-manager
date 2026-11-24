class EvaluationAgent:
    def evaluate(self,before,after):
        cpu_imp=before["cpu_percent"]-after["cpu_percent"]
        mem_imp=before["memory_percent"]-after["memory_percent"]
        lat_imp=before.get("latency_ms",100)-after.get("latency_ms",100)
        return {"cpu_improvement":cpu_imp,"memory_improvement":mem_imp,"latency_improvement":lat_imp,"cost_change":after.get("estimated_cost",0)-before.get("estimated_cost",0),"energy_change":after.get("estimated_energy",0)-before.get("estimated_energy",0),"resource_efficiency":max(0,min(100,100-after["cpu_percent"])),"slo_impact":1.0 if after.get("latency_ms",100)<=150 else -1.0}
