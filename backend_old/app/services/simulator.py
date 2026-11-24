import random, math
from app.agents.monitoring import MonitoringAgent

class WorkloadSimulator:
    def trace(self, workload_type, steps=60, seed=42, initial=40, growth=1.0):
        rng=random.Random(seed); out=[]
        for i in range(steps):
            if workload_type=="Stable": load=initial+rng.uniform(-2,2)
            elif workload_type=="Increasing": load=initial+growth*i+rng.uniform(-2,2)
            elif workload_type=="Decreasing": load=max(0,initial-growth*i)+rng.uniform(-2,2)
            elif workload_type=="Sudden Spike": load=initial+(55 if i>=steps*0.65 else 0)+rng.uniform(-2,2)
            elif workload_type=="Periodic": load=initial+25*math.sin(i/5)+rng.uniform(-2,2)
            elif workload_type=="Anomaly": load=initial+growth*i+rng.uniform(-2,2)+(45 if i in {steps//2,steps//2+1} else 0)
            else: load=initial+rng.uniform(-10,10)
            out.append(max(0,min(100,load)))
        return out

    def metrics(self, load, instances, seed=None):
        return MonitoringAgent().observe_simulated(load,instances,1,seed)
