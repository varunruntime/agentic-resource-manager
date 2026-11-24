# Agentic AI Approach for Efficient Computing Resources Management

B.Tech AI-ML minor project for Guru Gobind Singh Indraprastha University, University School of Automation & Robotics (USAR).

## Research contribution
This project does not claim predictive autoscaling is new. Its contribution is a measurable closed-loop integration of monitoring, prediction, analysis, reasoning, planning, multi-objective optimization, deterministic safety validation, controlled simulation, evaluation, feedback, transparent logging, and baseline comparison.

## Architecture
Observe → Analyze → Predict → Reason → Plan → Safety Check → Act → Evaluate → Feedback.

## Safety
Default mode is simulation. Recommendation mode does not execute actions. Simulation mode changes only simulated state. The controlled execution boundary accepts only predefined actions; no arbitrary shell commands are generated or executed by the LLM.

## Backend
Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite, NumPy, Pandas, scikit-learn, psutil, WebSockets.

### Run
```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend: http://localhost:8000, API docs: http://localhost:8000/docs

## Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend: http://localhost:5173

## Docker
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

## Manual 10-minute viva demo
1. Open Dashboard and show CPU/RAM/instances.
2. Click **Run Agent Cycle**.
3. Explain Observe → Analyze → Predict → Reason → Plan → Safety → Act → Evaluate.
4. Show prediction horizons (1, 3, 5, 10 minutes) and confidence/MAE/RMSE/MAPE.
5. Explain that the fallback is deterministic RuleBasedReasoningProvider when no LLM key is present.
6. Show the selected action and safety result.
7. Show before/after simulated metrics.
8. Open Decision Logs and show the unique decision ID.
9. Open Experiments, select **Sudden Spike**, run the comparison.
10. Explain that baseline and proposed systems use the same generated workload trace and runtime-calculated metrics.

## Required manual tests
- Stable: expect no unnecessary scaling.
- Increasing: use 40, 50, 62, 75, 84, 91 style load progression and verify predicted overload appears.
- Sudden spike: compare baseline vs proposed on the same trace.
- Safety: request > MAX_INSTANCES and expect rejection.
- Optimization: change weights in the API request and verify scores can change.
- Failure handling: remove LLM_API_KEY and verify rule-based reasoning continues.

## API highlights
POST /api/auth/register
POST /api/auth/login
GET /api/resources/current
GET /api/resources/history
POST /api/workloads
GET /api/workloads
POST /api/workloads/{id}/start
POST /api/workloads/{id}/stop
GET /api/predictions/latest
GET /api/predictions/history
POST /api/agents/run?mode=simulation
GET /api/agents/status
GET /api/decisions
GET /api/decisions/{id}
GET /api/actions
POST /api/experiments
POST /api/experiments/{id}/start
GET /api/experiments/{id}
GET /api/experiments/{id}/results
GET /api/metrics/summary
GET /api/metrics/history
GET /api/decisions/export.csv
WebSocket /ws/metrics

## Notes
Prediction accuracy is calculated from the model's historical residuals; the application does not insert fabricated accuracy claims. Experiment outputs are generated at runtime from the simulator.

## Frontend dependency setup note
The frontend is pinned to `@vitejs/plugin-react` 4.x to remain compatible with Vite 6, and includes the PostCSS/Autoprefixer configuration required by Tailwind CSS 3.4.17. From `frontend/`, run `npm install` and then `npm run dev`.
