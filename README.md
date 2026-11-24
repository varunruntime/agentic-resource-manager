# Agentic AI Approach for Efficient Computing Resources Management

B.Tech AI-ML minor project for Guru Gobind Singh Indraprastha University, University School of Automation & Robotics (USAR).

## Research contribution

This project does not claim predictive autoscaling is new. Its contribution is a measurable closed-loop integration of resource observation, time-aware demand prediction, analysis, rule-based reasoning, multi-objective planning, deterministic safety validation, controlled simulation, post-action evaluation, feedback-driven adaptation, transparent logging, and comparison with a conventional threshold controller.

## Closed-loop architecture

`OBSERVE → ANALYZE → PREDICT → REASON → PLAN → SAFETY CHECK → ACT → EVALUATE → FEEDBACK`

The experiment's PROPOSED system invokes the same `AgentOrchestrator` on every simulated timestep. The previous timestep's measured feedback is passed to the next reasoning cycle. The current feedback adapter is a deterministic heuristic: it avoids repeating a rejected or demonstrably harmful action. It is not reinforcement learning and does not train a model.

## Technology stack

**Backend:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite, NumPy, Pandas, scikit-learn, psutil, WebSockets.

**Frontend:** React, TypeScript, Vite, Axios, Recharts and Tailwind CSS.

## Safety and integration status

- Simulation mode is the default. Recommendation mode does not execute actions.
- The executor changes simulated resource state only; it does not provision or modify real cloud infrastructure.
- Safety rules restrict action names, scaling deltas, instance bounds, critical workloads and cooldown.
- No arbitrary shell commands are generated or executed.
- No external LLM API call is currently implemented. The active reasoning provider is deterministic `RuleBasedReasoningProvider`, even if `LLM_API_KEY` is configured. The `LLMReasoningProvider` class is currently a safe rule-based adapter, not a live LLM integration.
- The authentication endpoints are for local demonstration only. The returned demo token is not currently enforced as an API session. Do not expose this demo backend publicly or use it for real user accounts.
- Estimated cost, energy and throughput are simulator proxies, not actual cloud billing or measured power/requests-per-second.

## Experiment methodology

Both systems are given the exact same deterministic workload trace, seed and initial instance count. Their resource states evolve independently.

### BASELINE
- Scale out when CPU is above 80%.
- Scale in when CPU is below 30%.
- Respect the 60-second cooldown and instance limits.
- Use a five-minute persistence forecast for the forecast-score comparison.

### PROPOSED
- Run the actual nine-stage AgentOrchestrator on every simulated timestep.
- Use the time-aware predictor and the previous cycle's feedback.
- Apply the same deterministic 60-second safety cooldown before instance scaling.
- Evaluate actions against the before/after simulated state.

### Workload scenarios
- Stable
- Increasing
- Sudden Spike
- Decreasing
- Anomaly

The existing API field `duration_seconds` is retained for compatibility, but the experiment engine currently interprets its value as a number of simulation steps. **One experiment step represents one simulated minute**, so a value of 60 represents 60 simulated minutes, not 60 wall-clock seconds.

### Metric definitions and caveats
- Average CPU and memory: arithmetic mean of the simulated per-step readings.
- Latency: simulated latency proxy derived from CPU pressure and post-action latency changes.
- Throughput: a derived simulator proxy based on latency; it is not measured requests per second.
- Scaling actions: successful capacity actions (instance and CPU capacity changes).
- Reaction time: minutes from the first observed current/predicted pressure signal to the first successful scale-up/CPU-increase action. A value of zero means an action happened in the same simulated minute.
- SLO violations: number of steps with simulated latency above 150 ms.
- Estimated cost and energy: simulator proxies based on instance count and CPU-capacity multiplier.
- CPU headroom: `100 - average CPU`; it is not a full memory/disk/network wastage measure.
- CPU forecast score: bounded `100 - CPU MAPE`; it is a comparison score, not classification accuracy.
- CPU MAE, RMSE and MAPE are computed from chronological holdout forecasts in CPU percentage units. They are unavailable until enough historical readings exist; the UI displays N/A in that case.
- Prediction horizons use elapsed timestamps in minutes. When timestamps are absent or invalid, the predictor falls back to one sample = one minute.

Do not present one scenario or one seed as conclusive evidence. Run multiple seeds and report the full results, including cases where BASELINE performs better, before making research claims.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Frontend: http://localhost:5173

### Docker

```bash
docker compose up --build
```

## Tests

```bash
cd backend
pytest -q

cd ../frontend
npm test
npm run build
```

GitHub Actions runs the backend test suite and frontend build/tests on pushes to the development branch and pull requests to `main`.

## Manual 10-minute viva demo

1. Open Dashboard and explain CPU/RAM/instance metrics.
2. Click **Run Agent Cycle** and show the selected action.
3. Explain the nine stages and the safety result.
4. Show CPU prediction horizons and explain the CPU-only MAE/RMSE/MAPE.
5. Explain that the active reasoning provider is rule-based; no live LLM service is connected.
6. Show before/after simulated metrics and the feedback returned by the cycle.
7. Open Decision Logs and inspect a decision ID.
8. Open Experiments, select **Sudden Spike**, and run the BASELINE vs PROPOSED comparison.
9. Explain that both controllers receive the same trace but maintain independent resource states.
10. Discuss the metric definitions and limitations honestly.

## API highlights

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/resources/current`
- `GET /api/resources/history`
- `POST /api/workloads`
- `GET /api/workloads`
- `POST /api/workloads/{id}/start`
- `POST /api/workloads/{id}/stop`
- `GET /api/predictions/latest`
- `GET /api/predictions/history`
- `POST /api/agents/run`
- `GET /api/agents/status`
- `GET /api/decisions`
- `GET /api/decisions/{id}`
- `GET /api/actions`
- `POST /api/experiments`
- `POST /api/experiments/{id}/start`
- `GET /api/experiments/{id}`
- `GET /api/experiments/{id}/results`
- `GET /api/metrics/summary`
- `GET /api/metrics/history`
- `GET /api/decisions/export.csv`
- WebSocket: `/ws/metrics`

## Frontend dependency note

The frontend is pinned to `@vitejs/plugin-react` 4.x for Vite 6 compatibility and includes the PostCSS/Autoprefixer configuration required by Tailwind CSS 3.4.17.
