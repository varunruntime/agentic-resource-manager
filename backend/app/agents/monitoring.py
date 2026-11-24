import psutil, random
from datetime import datetime
class MonitoringAgent:
    def observe_real(self, instances=2, active_workloads=1):
        net=psutil.net_io_counters()
        return {"timestamp":datetime.utcnow().isoformat(),"cpu_percent":psutil.cpu_percent(interval=None),"memory_percent":psutil.virtual_memory().percent,"disk_percent":psutil.disk_usage('/').percent,"network_usage":float((net.bytes_sent+net.bytes_recv)%1000)/10,"active_workloads":active_workloads,"instances":instances}
    def observe_simulated(self, load, instances=2, active_workloads=1, seed=None):
        rng=random.Random(seed)
        cpu=max(0,min(100,load/max(instances,1)+rng.uniform(-2,2)))
        mem=max(0,min(100,35+0.45*load/max(instances,1)+rng.uniform(-2,2)))
        return {"timestamp":datetime.utcnow().isoformat(),"cpu_percent":cpu,"memory_percent":mem,"disk_percent":40+rng.uniform(-1,1),"network_usage":max(0,min(100,load*0.45+rng.uniform(-3,3))),"active_workloads":active_workloads,"instances":instances}
