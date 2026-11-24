class ExecutionAgent:
    def simulate(self, action, state):
        before=dict(state)
        instances=int(state.get("instances",2))
        name=action["action"]
        if name=="ADD_INSTANCE": instances += max(1,int(action.get("delta",1)))
        elif name=="REMOVE_INSTANCE": instances -= max(1,int(action.get("delta",1)))
        factor=state.get("instances",2)/max(instances,1)
        after=dict(state); after["instances"]=instances
        if name in {"ADD_INSTANCE","REMOVE_INSTANCE","INCREASE_CPU","DECREASE_CPU"}:
            after["cpu_percent"]=max(0,min(100,state["cpu_percent"]*factor))
            after["memory_percent"]=max(0,min(100,state["memory_percent"]*factor))
            after["latency_ms"]=max(1,state.get("latency_ms",100)*factor)
        after["estimated_cost"]=max(0,state.get("estimated_cost",0.2)+(instances-2)*0.08)
        after["estimated_energy"]=max(0,state.get("estimated_energy",0.4)+(instances-2)*0.12)
        return before,after
