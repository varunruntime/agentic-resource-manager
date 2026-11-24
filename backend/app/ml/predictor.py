from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LinearRegression


class DemandPredictor:
    """Linear time-index predictor with chronological holdout validation.

    Timestamped histories use elapsed minutes on the time axis, so horizons
    (1, 3, 5, 10) represent minutes rather than row indexes. If timestamps are
    missing or invalid, the model falls back to one sample = one minute.

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
    def _time_axis(history):
        parsed = []
        try:
            for row in history:
                value = row.get("timestamp")
                if isinstance(value, datetime):
                    stamp = value
                elif isinstance(value, str) and value:
                    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    raise ValueError("Missing timestamp")

                if stamp.tzinfo is not None:
                    stamp = stamp.astimezone(timezone.utc).replace(tzinfo=None)
                parsed.append(stamp)
        except (TypeError, ValueError, OverflowError):
            return np.arange(len(history), dtype=float)

        elapsed = np.array(
            [(stamp - parsed[0]).total_seconds() / 60.0 for stamp in parsed],
            dtype=float,
        )
        if not np.all(np.isfinite(elapsed)) or np.any(np.diff(elapsed) <= 0):
            return np.arange(len(history), dtype=float)
        return elapsed

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
            # No chronological holdout exists yet. Confidence 0 means
            # validation metrics are unavailable, not that model error is 0.
            return [
                {
                    "horizon": horizon,
                    "cpu": float(latest.get("cpu_percent", 0)),
                    "memory": float(latest.get("memory_percent", 0)),
                    "workload": float(latest.get("active_workloads", 0)),
                    "confidence": 0.0,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "mape": 0.0,
                }
                for horizon in horizons
            ]

        x_values = self._time_axis(history)
        x = x_values.reshape(-1, 1)

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

            # Refit on all observations only after chronological holdout
            # evaluation has been calculated.
            model.fit(x, y)
            fitted[key] = model

        if cpu_validation_metrics is None:
            mae = rmse = mape = 0.0
            confidence = 0.0
        else:
            mae, rmse, mape = cpu_validation_metrics
            confidence = max(
                0.05,
                min(0.99, 1.0 / (1.0 + rmse / 10.0)),
            )

        results = []
        last_time = float(x_values[-1])
        for horizon in horizons:
            future_x = np.array(
                [[last_time + float(horizon)]],
                dtype=float,
            )
            results.append({
                "horizon": int(horizon),
                "cpu": float(np.clip(fitted["cpu"].predict(future_x)[0], 0, 100)),
                "memory": float(np.clip(fitted["memory"].predict(future_x)[0], 0, 100)),
                "workload": float(max(0, fitted["workload"].predict(future_x)[0])),
                "confidence": float(confidence),
                "mae": float(mae),
                "rmse": float(rmse),
                "mape": float(mape),
            })

        return results
