class AnalysisAgent:
    def analyze(self, obs, pred):
        cpu=max([p["cpu"] for p in pred], default=obs["cpu_percent"]) if isinstance(pred, list) else float(pred.get("cpu", obs["cpu_percent"]))
        if cpu>=90: issue,severity="PREDICTED_OVERLOAD","HIGH"
        elif obs["cpu_percent"]>=80: issue,severity="OVERLOAD","HIGH"
        elif obs["cpu_percent"]<30: issue,severity="UNDERUTILIZATION","MEDIUM"
        elif obs["network_usage"]>85: issue,severity="NETWORK_BOTTLENECK","MEDIUM"
        else: issue,severity="NORMAL","LOW"
        return {"issue":issue,"severity":severity,"reason":f"Current CPU={obs['cpu_percent']:.1f}%, predicted peak CPU={cpu:.1f}%."}
