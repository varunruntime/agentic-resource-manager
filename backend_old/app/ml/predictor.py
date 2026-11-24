import numpy as np
from sklearn.linear_model import LinearRegression

class DemandPredictor:
    def __init__(self):
        self.models = {k: LinearRegression() for k in ("cpu", "memory", "workload")}

    def predict(self, history: list[dict], horizons=(1,3,5,10)):
        if len(history) < 3:
            latest = history[-1] if history else {"cpu_percent": 0, "memory_percent": 0, "active_workloads": 0}
            return [{"horizon": h, "cpu": latest["cpu_percent"], "memory": latest["memory_percent"], "workload": latest["active_workloads"], "confidence": 0.25, "mae": 0.0, "rmse": 0.0, "mape": 0.0} for h in horizons]
        x = np.arange(len(history)).reshape(-1,1)
        out=[]
        for key, target in (("cpu","cpu_percent"),("memory","memory_percent"),("workload","active_workloads")):
            y=np.array([float(r[target]) for r in history])
            self.models[key].fit(x,y)
        for h in horizons:
            xx=np.array([[len(history)+h-1]])
            vals={k: float(max(0, min(100, self.models[k].predict(xx)[0]))) for k in ("cpu","memory")}
            vals["workload"]=float(max(0,self.models["workload"].predict(xx)[0]))
            errors=[]
            for key,target in (("cpu","cpu_percent"),("memory","memory_percent"),("workload","active_workloads")):
                pred=self.models[key].predict(x)
                y=np.array([float(r[target]) for r in history])
                errors.extend((y-pred).tolist())
            mae=float(np.mean(np.abs(errors))) if errors else 0
            rmse=float(np.sqrt(np.mean(np.square(errors)))) if errors else 0
            mape=float(np.mean([abs(e)/max(abs(yv),1) for e,yv in zip(errors, np.tile(np.array([float(r['cpu_percent']) for r in history]),3))]))*100 if errors else 0
            confidence=float(max(0.05,min(0.99,1/(1+rmse/10))))
            out.append({"horizon":h,**vals,"confidence":confidence,"mae":mae,"rmse":rmse,"mape":mape})
        return out
