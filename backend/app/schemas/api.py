from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class AuthRequest(BaseModel):
    username: str
    password: str
class AuthResponse(BaseModel):
    token: str
class WorkloadCreate(BaseModel):
    name: str
    workload_type: str
    initial_load: float = Field(ge=0, le=100)
    growth_rate: float = 0
    duration_seconds: int = Field(default=300, ge=1)
class Weights(BaseModel):
    performance: float = 0.40
    cost: float = 0.25
    energy: float = 0.20
    utilization: float = 0.15
class ExperimentCreate(BaseModel):
    name: str
    workload_type: str
    duration_seconds: int = Field(default=60, ge=10, le=3600)
    seed: int = 42
class DecisionResponse(BaseModel):
    decision_id: str
    timestamp: datetime
    observation: Any
    prediction: Any
    detected_problem: Any
    candidate_actions: list[Any]
    selected_action: str
    reason: str
    safety: Any
    expected_result: Any
    actual_result: Any
    feedback: Any
    outcome: str