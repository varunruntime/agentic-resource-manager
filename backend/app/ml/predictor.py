import numpy as np
from sklearn.linear_model import LinearRegression


class DemandPredictor:
    """Linear time-index predictor with chronological holdout validation.

    MAE, RMSE and MAPE describe CPU forecasts only. They are deliberately
    not averaged across CPU percentage, memory percentage and workload count,
    because those targets have different units and scales.
    """

    TARGETS = (
        ("cpu", "cpu_percent"),
        ("memory", "memory_percent"),
        ("workload", "active_workloads"),
    )

    def __init__(self):
        self.models = {
            key: LinearRegression()
            for key, _ in self.TARGETS
        }

    @staticmethod
    def _metrics(actual, predicted):
        actual = np.asarray(actual, dtype=float)
        predicted = np.asarray(predicted, dtype=float)

        error = actual - predicted
        mae = float(np.mean(np.abs(error)))
        rmse = float(np.sqrt(np.mean(error ** 2)))

        nonzero = np.abs(actual) > 1e-8
        mape = (
            float(np.mean(np.abs(error[nonzero] / actual[nonzero])) * 100)
            if np.any(nonzero) else 0.0
        )
        return mae, rmse, mape

    def predict(self, history, horizons=(1, 3, 5, 10)):
        if len(history) < 4:
            latest = history[-1] if history else {}
            # No chronological holdout exists yet. A low confidence value
            # flags that the zero placeholders below are unavailable metrics,
            # not proof of a zero-error model.
            return [
                {
                    "horizon": horizon,
                    "cpu": float(latest.get("cpu_percent", 0)),
                    "memory": float(latest.get("memory_percent", 0)),
                    "workload": float(latest.get("active_workloads", 0)),
                    "confidence": 0.25,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "mape": 0.0,
                }
                for horizon in horizons
            ]

        x = np.arange(len(history), dtype=float).reshape(-1, 1)
        split = max(2, int(len(history) * 0.8))
        train_x = x[:split]
        test_x = x[split:]

        fitted = {}
        cpu_validation_metrics = None

        for key, target in self.TARGETS:
            y = np.array(
                [float(row.get(target, 0)) for row in history],
                dtype=float,
            )

            model = LinearRegression()
            model.fit(train_x, y[:split])

            if key == "cpu" and len(test_x):
                cpu_validation_metrics = self._metrics(
                    y[split:],
                    model.predict(test_x),
                )

            # Refit on all observations only after the chronological
            # holdout evaluation has been calculated.
            model.fit(x, y)
            fitted[key] = model

        if cpu_validation_metrics is None:
            mae = rmse = mape = 0.0
            confidence = 0.25
        else:
            mae, rmse, mape = cpu_validation_metrics
            confidence = max(
                0.05,
                min(0.99, 1.0 / (1.0 + rmse / 10.0)),
            )

        results = []
        for horizon in horizons:
            future_x = np.array(
                [[len(history) + horizon - 1]],
                dtype=float,
            )
            results.append({
                "horizon": horizon,
                "cpu": float(np.clip(fitted["cpu"].predict(future_x)[0], 0, 100)),
                "memory": float(np.clip(fitted["memory"].predict(future_x)[0], 0, 100)),
                "workload": float(max(0, fitted["workload"].predict(future_x)[0])),
                "confidence": float(confidence),
                "mae": float(mae),
                "rmse": float(rmse),
                "mape": float(mape),
            })

        return results
