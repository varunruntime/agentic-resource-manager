import csv, io, json, secrets, hashlib, hmac
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.entities import *
from app.schemas.api import *
from app.core.config import settings
from app.services.simulator import WorkloadSimulator
from app.services.experiments import run_comparison
from app.services.runtime import start_workload_simulation, stop_workload_simulation
from app.agents.orchestrator import AgentOrchestrator
from app.policies.safety import *

router=APIRouter(prefix="/api")

def seed_db(db):
    if not db.query(Policy).count():
        for n,v in [("MAX_INSTANCES",str(MAX_INSTANCES)),("MIN_INSTANCES",str(MIN_INSTANCES)),("MAX_SCALE_STEP",str(MAX_SCALE_STEP)),("COOLDOWN_SECONDS",str(COOLDOWN_SECONDS))]: db.add(Policy(name=n,value=v))
        db.commit()

def metric_dict(m):
    result = {
        key: getattr(m, key)
        for key in [
            "timestamp", "cpu_percent", "memory_percent", "disk_percent",
            "network_usage", "active_workloads", "instances", "latency_ms",
            "estimated_cost", "estimated_energy",
        ]
    }
    # Preserve simulated CPU allocation across API cycles without adding a
    # database column: estimated_cost encodes 0.10 * instances * multiplier.
    result["cpu_capacity_multiplier"] = (
        float(m.estimated_cost) / max(0.10 * int(m.instances), 1e-9)
    )
    return result


def _hash_password(password: str) -> str:
    """PBKDF2-SHA256 password hash using a per-user random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return "pbkdf2_sha256$260000$" + salt.hex() + "$" + digest.hex()


def _verify_password(password: str, stored: str) -> bool:
    # Continue to accept the earlier salted SHA-256 format for existing demo DBs.
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt_hex, digest_hex = stored.split("$", 3)
            calculated = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                bytes.fromhex(salt_hex), int(iterations)
            ).hex()
            return hmac.compare_digest(calculated, digest_hex)
        except (ValueError, TypeError):
            return False
    try:
        salt, digest = stored.split(":", 1)
        calculated = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return hmac.compare_digest(calculated, digest)
    except (ValueError, TypeError):
        return False


def workload_dict(workload):
    return {
        "id": workload.id,
        "name": workload.name,
        "workload_type": workload.workload_type,
        "initial_load": workload.initial_load,
        "growth_rate": workload.growth_rate,
        "duration_seconds": workload.duration_seconds,
        "current_load": workload.current_load,
        "active": workload.active,
        "created_at": workload.created_at,
    }


def prediction_dict(prediction):
    return {
        "id": prediction.id,
        "timestamp": prediction.timestamp,
        "horizon_minutes": prediction.horizon_minutes,
        "cpu_predicted": prediction.cpu_predicted,
        "memory_predicted": prediction.memory_predicted,
        "workload_predicted": prediction.workload_predicted,
        "confidence": prediction.confidence,
        "mae": prediction.mae,
        "rmse": prediction.rmse,
        "mape": prediction.mape,
    }


def experiment_dict(experiment):
    return {
        "id": experiment.id,
        "name": experiment.name,
        "workload_type": experiment.workload_type,
        "duration_seconds": experiment.duration_seconds,
        "seed": experiment.seed,
        "status": experiment.status,
    }


@router.post("/auth/register", response_model=AuthResponse)
def register(req: AuthRequest, db: Session = Depends(get_db)):
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(422, "Username and password are required")
    if db.query(User).filter_by(username=username).first():
        raise HTTPException(409, "Username already exists")
    db.add(User(username=username, password_hash=_hash_password(req.password)))
    db.commit()
    return {"token": secrets.token_urlsafe(32)}


@router.post("/auth/login", response_model=AuthResponse)
def login(req: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=req.username.strip()).first()
    if not user or not _verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return {"token": secrets.token_urlsafe(32)}


@router.get("/resources/current")
def current(db:Session=Depends(get_db)):
    m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
    if not m:
        m=ResourceMetric(cpu_percent=0,memory_percent=0,disk_percent=0,network_usage=0,active_workloads=0,instances=2,latency_ms=50,estimated_cost=.2,estimated_energy=.4); db.add(m); db.commit(); db.refresh(m)
    return metric_dict(m)

@router.get("/resources/history")
def history(db:Session=Depends(get_db)): return [metric_dict(m) for m in db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).limit(200).all()][::-1]

@router.post("/workloads")
def create_workload(req: WorkloadCreate, db: Session = Depends(get_db)):
    workload = Workload(**req.model_dump(), current_load=req.initial_load)
    db.add(workload)
    db.commit()
    db.refresh(workload)
    return workload_dict(workload)


@router.get("/workloads")
def workloads(db: Session = Depends(get_db)):
    return [
        workload_dict(workload)
        for workload in db.query(Workload).order_by(Workload.id.desc()).all()
    ]


@router.post("/workloads/{id}/start")
def start_workload(id: int, db: Session = Depends(get_db)):
    workload = db.get(Workload, id)
    if workload is None:
        raise HTTPException(404, "Workload not found")
    if not workload.active:
        workload.active = True
        workload.current_load = workload.initial_load
        db.commit()
        start_workload_simulation(workload)
    return {"status": "STARTED", "id": id}


@router.post("/workloads/{id}/stop")
def stop_workload(id: int, db: Session = Depends(get_db)):
    workload = db.get(Workload, id)
    if workload is None:
        raise HTTPException(404, "Workload not found")
    workload.active = False
    db.commit()
    stop_workload_simulation(id)
    return {"status": "STOPPED", "id": id}


@router.get("/predictions/latest")
def latest_prediction(db: Session = Depends(get_db)):
    return [prediction_dict(p) for p in db.query(Prediction).order_by(Prediction.id.desc()).limit(4).all()]


@router.get("/predictions/history")
def prediction_history(db: Session = Depends(get_db)):
    rows = db.query(Prediction).order_by(Prediction.id.desc()).limit(200).all()
    return [prediction_dict(p) for p in reversed(rows)]


@router.post("/agents/run")
def run_agent(req: AgentRunRequest, db: Session = Depends(get_db)):
    # Rehydrate the previous cycle's measured feedback from persisted evaluation.
    previous_decision = (
        db.query(AgentDecision)
        .order_by(AgentDecision.id.desc())
        .first()
    )
    feedback = None
    if previous_decision is not None:
        previous_evaluation = (
            db.query(EvaluationResult)
            .filter_by(decision_id=previous_decision.id)
            .first()
        )
        if previous_evaluation is not None:
            feedback = {
                "selected_action": previous_decision.action,
                "outcome": previous_decision.outcome,
                "cpu_improvement": previous_evaluation.cpu_improvement,
                "memory_improvement": previous_evaluation.memory_improvement,
                "latency_improvement": previous_evaluation.latency_improvement,
                "cost_change": previous_evaluation.cost_change,
                "energy_change": previous_evaluation.energy_change,
                "slo_impact": previous_evaluation.slo_impact,
            }

    # Rehydrate the last successful instance-scaling time for cooldown checks.
    last_scaling_decision = (
        db.query(AgentDecision)
        .filter(
            AgentDecision.action.in_(("ADD_INSTANCE", "REMOVE_INSTANCE")),
            AgentDecision.outcome == "SUCCESS",
        )
        .order_by(AgentDecision.id.desc())
        .first()
    )
    last_action_time = (
        last_scaling_decision.timestamp
        if last_scaling_decision is not None
        else None
    )
    now = datetime.utcnow()

    result = AgentOrchestrator(db, settings).run(
        history=req.history,
        state=req.state,
        weights=req.weights,
        mode=req.mode,
        feedback=feedback,
        last_action_time=last_action_time,
        now=now,
    )

    for p in result["prediction"]:
        db.add(Prediction(
            horizon_minutes=p["horizon"],
            cpu_predicted=p["cpu"],
            memory_predicted=p["memory"],
            workload_predicted=p["workload"],
            confidence=p["confidence"],
            mae=p["mae"],
            rmse=p["rmse"],
            mape=p["mape"]
        ))

    d = AgentDecision(
        decision_id=result["decision_id"],
        observation=json.dumps(result["observation"], default=str),
        prediction=json.dumps(result["prediction"], default=str),
        detected_problem=json.dumps(result["detected_problem"], default=str),
        reasoning=json.dumps(result["reasoning"], default=str),
        plan=json.dumps(result["plan"], default=str),
        safety=json.dumps(result["safety"], default=str),
        action=result["selected_action"],
        evaluation=json.dumps(result["evaluation"], default=str),
        outcome=result["outcome"]
    )

    db.add(d)
    db.flush()

    for a in result["plan"]["alternatives"] + [result["plan"]["selected"]]:
        db.add(CandidateAction(
            decision_id=d.id,
            action=a["action"],
            reason=a["reason"],
            expected_effect=a["expected_effect"],
            estimated_cost=a["estimated_cost"],
            score=a["score"]
        ))

    db.add(ExecutedAction(
        decision_id=d.id,
        action=result["selected_action"],
        mode=req.mode,
        status=result["outcome"],
        before_json=json.dumps(result["observation"], default=str),
        after_json=json.dumps(result["actual_result"], default=str)
    ))

    db.add(EvaluationResult(
        decision_id=d.id,
        **result["evaluation"]
    ))

    after = result["actual_result"]

    db.add(ResourceMetric(
        cpu_percent=after["cpu_percent"],
        memory_percent=after["memory_percent"],
        disk_percent=after.get("disk_percent", 40),
        network_usage=after.get("network_usage", 30),
        active_workloads=after.get("active_workloads", 2),
        instances=after["instances"],
        latency_ms=after.get("latency_ms", 80),
        estimated_cost=after.get("estimated_cost", 0.2),
        estimated_energy=after.get("estimated_energy", 0.4)
    ))

    db.commit()

    return {
        "decision_id": result["decision_id"],
        "timestamp": result["timestamp"],
        "observation": result["observation"],
        "prediction": result["prediction"],
        "detected_problem": result["detected_problem"],
        "candidate_actions": (
            [result["plan"]["selected"]]
            + result["plan"]["alternatives"]
        ),
        "selected_action": result["selected_action"],
        "reason": result["reasoning"]["reason"],
        "safety": result["safety"],
        "expected_result": result["plan"]["selected"]["expected_effect"],
        "actual_result": result["actual_result"],
        "feedback": result.get("feedback"),
        "outcome": result["outcome"]
    }


@router.get("/agents/status")
def agent_status():
    return {
        "orchestrator": "READY",
        "mode": "SIMULATION",
        "llm_available": False,
        "llm_configured": bool(settings.llm_api_key),
        "reasoning_provider": "rule_based",
        "safety": "ENABLED",
    }
@router.get("/decisions")
def decisions(db: Session = Depends(get_db)):
    rows = db.query(AgentDecision).order_by(AgentDecision.id.desc()).limit(100).all()
    return [
        {"decision_id": row.decision_id, "timestamp": row.timestamp, "action": row.action, "outcome": row.outcome}
        for row in rows
    ]


@router.get("/decisions/export.csv")
def export_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Decision ID", "Time", "Action", "Outcome", "Safety"])
    for row in db.query(AgentDecision).order_by(AgentDecision.id.desc()).all():
        writer.writerow([row.decision_id, row.timestamp, row.action, row.outcome, row.safety])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=decision_logs.csv"})

@router.get("/decisions/{id}")
def decision(id: str, db: Session = Depends(get_db)):
    row = db.query(AgentDecision).filter_by(decision_id=id).first()
    if row is None:
        raise HTTPException(404, "Decision not found")
    executed = db.query(ExecutedAction).filter_by(decision_id=row.id).first()
    candidates = db.query(CandidateAction).filter_by(decision_id=row.id).order_by(CandidateAction.score.desc()).all()
    evaluation = db.query(EvaluationResult).filter_by(decision_id=row.id).first()
    return {
        "decision_id": row.decision_id,
        "timestamp": row.timestamp,
        "observation": json.loads(row.observation),
        "prediction": json.loads(row.prediction),
        "detected_problem": json.loads(row.detected_problem),
        "reasoning": json.loads(row.reasoning),
        "plan": json.loads(row.plan),
        "candidate_actions": [
            {"action": item.action, "reason": item.reason, "expected_effect": item.expected_effect,
             "estimated_cost": item.estimated_cost, "score": item.score}
            for item in candidates
        ],
        "safety": json.loads(row.safety),
        "action": row.action,
        "execution": ({
            "mode": executed.mode, "status": executed.status,
            "before": json.loads(executed.before_json), "after": json.loads(executed.after_json),
        } if executed else None),
        "evaluation": ({
            "cpu_improvement": evaluation.cpu_improvement,
            "memory_improvement": evaluation.memory_improvement,
            "latency_improvement": evaluation.latency_improvement,
            "cost_change": evaluation.cost_change,
            "energy_change": evaluation.energy_change,
            "resource_efficiency": evaluation.resource_efficiency,
            "slo_impact": evaluation.slo_impact,
        } if evaluation else json.loads(row.evaluation)),
        "feedback": {
            "selected_action": row.action,
            "outcome": row.outcome,
            **({
                "cpu_improvement": evaluation.cpu_improvement,
                "memory_improvement": evaluation.memory_improvement,
                "latency_improvement": evaluation.latency_improvement,
                "cost_change": evaluation.cost_change,
                "energy_change": evaluation.energy_change,
                "slo_impact": evaluation.slo_impact,
            } if evaluation else json.loads(row.evaluation)),
        },
        "outcome": row.outcome,
    }


@router.get("/actions")
def actions(db: Session = Depends(get_db)):
    rows = db.query(CandidateAction).order_by(CandidateAction.id.desc()).limit(100).all()
    return [
        {
            "id": row.id,
            "decision_id": row.decision.decision_id if row.decision else None,
            "action": row.action,
            "reason": row.reason,
            "expected_effect": row.expected_effect,
            "estimated_cost": row.estimated_cost,
            "score": row.score,
        }
        for row in rows
    ]

@router.get("/experiments")
def experiments(db: Session = Depends(get_db)):
    rows = db.query(Experiment).order_by(Experiment.id.desc()).limit(100).all()
    return [experiment_dict(row) for row in rows]


@router.post("/experiments")
def create_experiment(req: ExperimentCreate, db: Session = Depends(get_db)):
    experiment = Experiment(**req.model_dump())
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment_dict(experiment)


@router.post("/experiments/{id}/start")
def start_experiment(id: int, db: Session = Depends(get_db)):
    experiment = db.get(Experiment, id)
    if experiment is None:
        raise HTTPException(404, "Experiment not found")
    if experiment.status == "RUNNING":
        raise HTTPException(409, "Experiment is already running")

    db.query(ExperimentResult).filter_by(experiment_id=experiment.id).delete()
    experiment.status = "RUNNING"
    db.commit()
    try:
        results = run_comparison(experiment.workload_type, experiment.duration_seconds, experiment.seed)
        if len(results) != 2 or {item.get("system") for item in results} != {"BASELINE", "PROPOSED"}:
            raise ValueError("Experiment did not produce both controller results")
        for result in results:
            db.add(ExperimentResult(experiment_id=experiment.id, **result))
        experiment.status = "COMPLETED"
        db.commit()
        return results
    except Exception:
        db.rollback()
        failed = db.get(Experiment, id)
        if failed is not None:
            failed.status = "FAILED"
            db.commit()
        raise


@router.get("/experiments/{id}")
def experiment(id: int, db: Session = Depends(get_db)):
    row = db.get(Experiment, id)
    if row is None:
        raise HTTPException(404, "Experiment not found")
    return experiment_dict(row)


@router.get("/experiments/{id}/results")
def experiment_results(id: int, db: Session = Depends(get_db)):
    if db.get(Experiment, id) is None:
        raise HTTPException(404, "Experiment not found")
    return [
        {
            "id": row.id, "experiment_id": row.experiment_id, "system": row.system,
            "avg_cpu": row.avg_cpu, "avg_memory": row.avg_memory, "latency": row.latency,
            "throughput": row.throughput, "scaling_actions": row.scaling_actions,
            "reaction_time": row.reaction_time, "resource_wastage": row.resource_wastage,
            "slo_violations": row.slo_violations, "estimated_cost": row.estimated_cost,
            "estimated_energy": row.estimated_energy, "prediction_accuracy": row.prediction_accuracy,
            "unnecessary_actions": row.unnecessary_actions,
        }
        for row in db.query(ExperimentResult).filter_by(experiment_id=id).all()
    ]


@router.get("/metrics/summary")
def summary(db: Session = Depends(get_db)):
    rows = db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).limit(50).all()
    if not rows:
        return {"samples": 0, "avg_cpu": 0, "avg_memory": 0, "avg_latency": 0,
                "estimated_cost": 0, "estimated_energy": 0}
    count = len(rows)
    return {
        "samples": count,
        "avg_cpu": sum(float(row.cpu_percent) for row in rows) / count,
        "avg_memory": sum(float(row.memory_percent) for row in rows) / count,
        "avg_latency": sum(float(row.latency_ms) for row in rows) / count,
        "estimated_cost": sum(float(row.estimated_cost) for row in rows) / count,
        "estimated_energy": sum(float(row.estimated_energy) for row in rows) / count,
    }


@router.get("/metrics/history")
def metrics_history(db: Session = Depends(get_db)):
    return history(db)


