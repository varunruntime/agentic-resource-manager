import csv, io, json, secrets
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
from app.agents.orchestrator import AgentOrchestrator
from app.policies.safety import *

router=APIRouter(prefix="/api")

def seed_db(db):
    if not db.query(Policy).count():
        for n,v in [("MAX_INSTANCES",str(MAX_INSTANCES)),("MIN_INSTANCES",str(MIN_INSTANCES)),("MAX_SCALE_STEP",str(MAX_SCALE_STEP)),("COOLDOWN_SECONDS",str(COOLDOWN_SECONDS))]: db.add(Policy(name=n,value=v))
        db.commit()

def metric_dict(m): return {k:getattr(m,k) for k in ["timestamp","cpu_percent","memory_percent","disk_percent","network_usage","active_workloads","instances","latency_ms","estimated_cost","estimated_energy"]}

@router.post("/auth/register",response_model=AuthResponse)
def register(req:AuthRequest,db:Session=Depends(get_db)):
    if db.query(User).filter_by(username=req.username).first(): raise HTTPException(409,"Username already exists")
    # For a student demo, token auth is intentionally simple; password is salted with a process-safe random salt.
    import hashlib
    salt=secrets.token_hex(16); ph=f"{salt}:{hashlib.sha256((salt+req.password).encode()).hexdigest()}"
    db.add(User(username=req.username,password_hash=ph)); db.commit(); return {"token":secrets.token_urlsafe(24)}

@router.post("/auth/login",response_model=AuthResponse)
def login(req:AuthRequest,db:Session=Depends(get_db)):
    import hashlib
    u=db.query(User).filter_by(username=req.username).first()
    if not u: raise HTTPException(401,"Invalid credentials")
    salt,digest=u.password_hash.split(":",1)
    if hashlib.sha256((salt+req.password).encode()).hexdigest()!=digest: raise HTTPException(401,"Invalid credentials")
    return {"token":secrets.token_urlsafe(24)}

@router.get("/resources/current")
def current(db:Session=Depends(get_db)):
    m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
    if not m:
        m=ResourceMetric(cpu_percent=0,memory_percent=0,disk_percent=0,network_usage=0,active_workloads=0,instances=2,latency_ms=50,estimated_cost=.2,estimated_energy=.4); db.add(m); db.commit(); db.refresh(m)
    return metric_dict(m)

@router.get("/resources/history")
def history(db:Session=Depends(get_db)): return [metric_dict(m) for m in db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).limit(200).all()][::-1]

@router.post("/workloads")
def create_workload(req:WorkloadCreate,db:Session=Depends(get_db)):
    w=Workload(**req.model_dump(),current_load=req.initial_load); db.add(w); db.commit(); db.refresh(w); return w.__dict__
@router.get("/workloads")
def workloads(db:Session=Depends(get_db)): return [w.__dict__ for w in db.query(Workload).order_by(Workload.id.desc()).all()]
@router.post("/workloads/{id}/start")
def start_workload(id:int,db:Session=Depends(get_db)):
    w=db.get(Workload,id)
    if not w: raise HTTPException(404,"Workload not found")
    w.active=True; db.commit(); return {"status":"STARTED","id":id}
@router.post("/workloads/{id}/stop")
def stop_workload(id:int,db:Session=Depends(get_db)):
    w=db.get(Workload,id)
    if not w: raise HTTPException(404,"Workload not found")
    w.active=False; db.commit(); return {"status":"STOPPED","id":id}

@router.get("/predictions/latest")
def latest_prediction(db:Session=Depends(get_db)):
    return [p.__dict__ for p in db.query(Prediction).order_by(Prediction.id.desc()).limit(4).all()]
@router.get("/predictions/history")
def prediction_history(db:Session=Depends(get_db)): return [p.__dict__ for p in db.query(Prediction).order_by(Prediction.id.desc()).limit(200).all()][::-1]

@router.post("/agents/run")
def run_agent(mode:str="simulation",weights:Weights=Weights(),db:Session=Depends(get_db)):
    m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
    if not m: current(db); m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
    hist=[metric_dict(x) for x in db.query(ResourceMetric).order_by(ResourceMetric.id).limit(200).all()]
    if len(hist)<3:
        for i in range(10):
            mm=ResourceMetric(cpu_percent=50+i*2,memory_percent=50+i,disk_percent=40,network_usage=30,active_workloads=2,instances=2,latency_ms=80,estimated_cost=.2,estimated_energy=.4); db.add(mm)
        db.commit(); hist=[metric_dict(x) for x in db.query(ResourceMetric).order_by(ResourceMetric.id).limit(200).all()]
        m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first()
    state=metric_dict(m); result=AgentOrchestrator(db,settings).run(hist,state,weights,mode)
    # Persist latest predictions and decision trace.
    for p in result["prediction"]: db.add(Prediction(horizon_minutes=p["horizon"],cpu_predicted=p["cpu"],memory_predicted=p["memory"],workload_predicted=p["workload"],confidence=p["confidence"],mae=p["mae"],rmse=p["rmse"],mape=p["mape"]))
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
); db.add(d); db.flush()
    for a in result["plan"]["alternatives"]+[result["plan"]["selected"]]: db.add(CandidateAction(decision_id=d.id,action=a["action"],reason=a["reason"],expected_effect=a["expected_effect"],estimated_cost=a["estimated_cost"],score=a["score"]))
    db.add(ExecutedAction(
    decision_id=d.id,
    action=result["selected_action"],
    mode=mode,
    status=result["outcome"],
    before_json=json.dumps(result["observation"], default=str),
    after_json=json.dumps(result["actual_result"], default=str)
))
    ev=result["evaluation"]; db.add(EvaluationResult(decision_id=d.id,**ev));
    after=result["actual_result"]; db.add(ResourceMetric(cpu_percent=after["cpu_percent"],memory_percent=after["memory_percent"],disk_percent=after.get("disk_percent",40),network_usage=after.get("network_usage",30),active_workloads=after.get("active_workloads",2),instances=after["instances"],latency_ms=after.get("latency_ms",80),estimated_cost=after.get("estimated_cost",.2),estimated_energy=after.get("estimated_energy",.4))); db.commit()
    return {
    "decision_id": result["decision_id"],
    "timestamp": result["timestamp"],
    "observation": result["observation"],
    "prediction": result["prediction"],
    "detected_problem": result["detected_problem"],
    "candidate_actions": (
        result["plan"]["alternatives"]
        + [result["plan"]["selected"]]
    ),
    "selected_action": result["selected_action"],
    "reason": result["reasoning"]["reason"],
    "safety": result["safety"],
    "expected_result": result["plan"]["selected"]["expected_effect"],
    "actual_result": result["actual_result"],
    "feedback": result.get("feedback"),
    "outcome": result["outcome"],
}

@router.get("/agents/status")
def agent_status(): return {"orchestrator":"READY","mode":"SIMULATION","llm_available":bool(settings.llm_api_key),"safety":"ENABLED"}
@router.get("/decisions")
def decisions(db:Session=Depends(get_db)): return [{"decision_id":d.decision_id,"timestamp":d.timestamp,"action":d.action,"outcome":d.outcome} for d in db.query(AgentDecision).order_by(AgentDecision.id.desc()).limit(100).all()]
@router.get("/decisions/{id}")
def decision(id:str,db:Session=Depends(get_db)):
    d=db.query(AgentDecision).filter_by(decision_id=id).first()
    if not d: raise HTTPException(404,"Decision not found")
    return {"decision_id":d.decision_id,"timestamp":d.timestamp,"observation":json.loads(d.observation),"prediction":json.loads(d.prediction),"detected_problem":json.loads(d.detected_problem),"reasoning":json.loads(d.reasoning),"plan":json.loads(d.plan),"safety":json.loads(d.safety),"action":d.action,"evaluation":json.loads(d.evaluation),"outcome":d.outcome}
@router.get("/actions")
def actions(db:Session=Depends(get_db)): return [a.__dict__ for a in db.query(CandidateAction).order_by(CandidateAction.id.desc()).limit(100).all()]

@router.post("/experiments")
def create_experiment(req:ExperimentCreate,db:Session=Depends(get_db)):
    e=Experiment(**req.model_dump()); db.add(e); db.commit(); db.refresh(e); return e.__dict__
@router.post("/experiments/{id}/start")
def start_experiment(id:int,db:Session=Depends(get_db)):
    e=db.get(Experiment,id)
    if not e: raise HTTPException(404,"Experiment not found")
    e.status="RUNNING"; db.commit(); results=run_comparison(e.workload_type,e.duration_seconds,e.seed)
    for r in results: db.add(ExperimentResult(experiment_id=e.id,**r))
    e.status="COMPLETED"; db.commit(); return results
@router.get("/experiments/{id}")
def experiment(id:int,db:Session=Depends(get_db)):
    e=db.get(Experiment,id)
    if not e: raise HTTPException(404,"Experiment not found")
    return e.__dict__
@router.get("/experiments/{id}/results")
def experiment_results(id:int,db:Session=Depends(get_db)): return [r.__dict__ for r in db.query(ExperimentResult).filter_by(experiment_id=id).all()]
@router.get("/metrics/summary")
def summary(db:Session=Depends(get_db)):
    hs=[metric_dict(x) for x in db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).limit(50).all()]
    if not hs: return {}
    return {"avg_cpu":sum(x["cpu_percent"] for x in hs)/len(hs),"avg_memory":sum(x["memory_percent"] for x in hs)/len(hs),"latency":sum(x["latency_ms"] for x in hs)/len(hs),"estimated_cost":sum(x["estimated_cost"] for x in hs)/len(hs),"estimated_energy":sum(x["estimated_energy"] for x in hs)/len(hs)}
@router.get("/metrics/history")
def metrics_history(db:Session=Depends(get_db)): return history(db)
@router.get("/decisions/export.csv")
def export_csv(db:Session=Depends(get_db)):
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Decision ID","Time","Action","Outcome","Safety"])
    for d in db.query(AgentDecision).order_by(AgentDecision.id.desc()).all(): w.writerow([d.decision_id,d.timestamp,d.action,d.outcome,d.safety])
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=decision_logs.csv"})
