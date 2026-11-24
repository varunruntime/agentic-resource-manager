from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AuthRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class AuthResponse(BaseModel):
    token: str


class WorkloadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workload_type: str = Field(min_length=1, max_length=40)
    initial_load: float = Field(ge=0, le=100)
    growth_rate: float = Field(default=0, ge=-100, le=100)
    duration_seconds: int = Field(default=300, ge=1, le=86400)


class Weights(BaseModel):
    performance: float = Field(default=0.40, ge=0, le=1)
    cost: float = Field(default=0.25, ge=0, le=1)
    energy: float = Field(default=0.20, ge=0, le=1)
    utilization: float = Field(default=0.15, ge=0, le=1)

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        total = self.performance + self.cost + self.energy + self.utilization
        if abs(total - 1.0) > 1e-6:
            raise ValueError("Objective weights must add up to 1.0")
        return self


class AgentRunRequest(BaseModel):
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    state: dict[str, Any]
    weights: Weights = Field(default_factory=Weights)
    mode: Literal["simulation", "recommendation"] = "simulation"


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workload_type: str = Field(min_length=1, max_length=40)
    # Compatibility name retained: this value is a count of simulated steps,
    # and every experiment step represents one simulated minute.
    duration_seconds: int = Field(default=60, ge=10, le=3600)
    seed: int = Field(default=42, ge=0, le=2147483647)


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
