from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

class ResourceMetric(Base):
    __tablename__ = "resource_metrics"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_usage = Column(Float, nullable=False)
    active_workloads = Column(Integer, nullable=False)
    instances = Column(Integer, nullable=False)
    latency_ms = Column(Float, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    estimated_energy = Column(Float, nullable=False)

class Workload(Base):
    __tablename__ = "workloads"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    workload_type = Column(String(40), nullable=False)
    initial_load = Column(Float, nullable=False)
    growth_rate = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    current_load = Column(Float, default=0)
    active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    horizon_minutes = Column(Integer, nullable=False)
    cpu_predicted = Column(Float, nullable=False)
    memory_predicted = Column(Float, nullable=False)
    workload_predicted = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    mae = Column(Float, nullable=False)
    rmse = Column(Float, nullable=False)
    mape = Column(Float, nullable=False)

class AgentDecision(Base):
    __tablename__ = "agent_decisions"
    id = Column(Integer, primary_key=True)
    decision_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    observation = Column(Text, nullable=False)
    prediction = Column(Text, nullable=False)
    detected_problem = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    plan = Column(Text, nullable=False)
    safety = Column(Text, nullable=False)
    action = Column(String(80), nullable=False)
    evaluation = Column(Text, nullable=False)
    outcome = Column(String(20), nullable=False)

class CandidateAction(Base):
    __tablename__ = "candidate_actions"
    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("agent_decisions.id"), nullable=False)
    action = Column(String(80), nullable=False)
    reason = Column(Text, nullable=False)
    expected_effect = Column(Text, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    score = Column(Float, nullable=False)
    decision = relationship("AgentDecision")

class ExecutedAction(Base):
    __tablename__ = "executed_actions"
    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("agent_decisions.id"), nullable=False)
    action = Column(String(80), nullable=False)
    mode = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)
    before_json = Column(Text, nullable=False)
    after_json = Column(Text, nullable=False)

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("agent_decisions.id"), nullable=False)
    cpu_improvement = Column(Float, nullable=False)
    memory_improvement = Column(Float, nullable=False)
    latency_improvement = Column(Float, nullable=False)
    cost_change = Column(Float, nullable=False)
    energy_change = Column(Float, nullable=False)
    resource_efficiency = Column(Float, nullable=False)
    slo_impact = Column(Float, nullable=False)

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    workload_type = Column(String(40), nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING")

class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    system = Column(String(30), nullable=False)
    avg_cpu = Column(Float, nullable=False)
    avg_memory = Column(Float, nullable=False)
    latency = Column(Float, nullable=False)
    throughput = Column(Float, nullable=False)
    scaling_actions = Column(Integer, nullable=False)
    reaction_time = Column(Float, nullable=False)
    resource_wastage = Column(Float, nullable=False)
    slo_violations = Column(Integer, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    estimated_energy = Column(Float, nullable=False)
    prediction_accuracy = Column(Float, nullable=False)
    unnecessary_actions = Column(Integer, nullable=False)

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    value = Column(String(255), nullable=False)
