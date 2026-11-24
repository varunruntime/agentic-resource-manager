import numpy as np
from sklearn.linear_model import LinearRegression


class DemandPredictor:
    """Simple, transparent time-series forecaster for the research prototype.

    Metrics are calculated only against observations that are actually available;
    no future values are used when producing a forecast.
    """

    TARGETS = (("cpu", "cpu_percent"), ("memory", "memory_percent"), ("workload", "active_workloads"))

    def __init__(self):
        self.models = {k: LinearRegression() for k, _ in self.TARGETS}

    @staticmethod
    def _metrics(y, pred):
        y = np.asarray(y, dtype=float)
        pred = np.asarray(pred, dtype=float)
        err = y - pred
        mae = float(np.mean(np.abs(err)))
        rmse = float(np.sqrt(np.mean(np.square(err))))
        nonzero = np.abs(y) > 1e-8
        mape = float(np.mean(np.abs(err[nonzero] / y[nonzero])) * 100) if np.any(nonzero) else 0.0
        return mae, rmse, mape

    def predict(self, history: list[dict], horizons=(1, 3, 5, 10)):
        if len(history) < 3:
            latest = history[-1] if history else {"cpu_percent": 0, "memory_percent": 0, "active_workloads": 0}
            return [
                {
                    "horizon": h,
                    "cpu": float(latest.get("cpu_percent", 0)),
                    "memory": float(latest.get("memory_percent", 0)),
                    "workload": float(latest.get("active_workloads", 0)),
                    "confidence": 0.25,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "mape": 0.0,
                }
                for h in horizons
            ]

        x = np.arange(len(history), dtype=float).reshape(-1, 1)
        fitted = {}
        errors = []
        for key, target in self.TARGETS:
            y = np.array([float(r.get(target, 0)) for r in history], dtype=float)
            model = self.models[key].fit(x, y)
            pred = model.predict(x)
            fitted[key] = model
            errors.append(self._metrics(y, pred))

        # Report a transparent aggregate across the three predicted variables.
        mae = float(np.mean([e[0] for e in errors]))
        rmse = float(np.mean([e[1] for e in errors]))
        mape = float(np.mean([e[2] for e in errors]))
        confidence = float(max(0.05, min(0.99, 1.0 / (1.0 + rmse / 10.0))))

        out = []
        for h in horizons:
            xx = np.array([[len(history) + h - 1]], dtype=float)
            cpu = float(max(0, min(100, fitted["cpu"].predict(xx)[0])))
            memory = float(max(0, min(100, fitted["memory"].predict(xx)[0])))
            workload = float(max(0, fitted["workload"].predict(xx)[0]))
            out.append({
                "horizon": h,
                "cpu": cpu,
                "memory": memory,
                "workload": workload,
                "confidence": confidence,
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            })
        return out
