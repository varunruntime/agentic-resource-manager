import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.agents.monitoring import MonitoringAgent
from app.agents.analysis import AnalysisAgent
from app.agents.reasoning import RuleBasedReasoningProvider
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.agents.orchestrator import AgentOrchestrator
from app.policies.safety import validate
from app.services.experiments import run_comparison, _add_derived_metrics


WEIGHTS = SimpleNamespace(
    performance=0.40,
    cost=0.25,
    energy=0.20,
    utilization=0.15,
)
SETTINGS = SimpleNamespace(llm_api_key=None)


def test_monitoring_simulation_bounds_and_capacity_response():
    monitor = MonitoringAgent()
    one_instance = monitor.observe_simulated(90, instances=1, seed=7)
    two_instances = monitor.observe_simulated(90, instances=2, seed=7)

    assert 0 <= one_instance["cpu_percent"] <= 100
    assert 0 <= two_instances["cpu_percent"] <= 100
    assert one_instance["cpu_percent"] > two_instances["cpu_percent"]


def test_monitoring_snapshot_normalizes_values():
    observed = MonitoringAgent().observe_snapshot({
        "cpu_percent": 125,
        "memory_percent": 55,
        "disk_percent": 40,
        "network_usage": -2,
        "active_workloads": 2,
        "instances": 0,
    })

    assert observed["cpu_percent"] == 100
    assert observed["network_usage"] == 0
    assert observed["instances"] == 1


def test_monitoring_rejects_non_finite_metrics():
    with pytest.raises(ValueError):
        MonitoringAgent().observe_snapshot({"cpu_percent": float("nan")})


def test_analysis_reports_current_overload():
    result = AnalysisAgent().analyze({
        "cpu_percent": 85,
        "memory_percent": 65,
        "network_usage": 20,
    })
    assert "OVERLOAD" in result["issue"]
    assert result["severity"] == "HIGH"


def test_reasoning_creates_capacity_actions_for_predicted_pressure():
    result = RuleBasedReasoningProvider().reason(
        {"cpu_percent": 55, "memory_percent": 60, "network_usage": 20},
        [{"horizon": 5, "cpu": 86, "memory": 70}],
        {"issue": ["NORMAL"], "severity": "LOW"},
    )
    actions = {item["action"] for item in result["candidate_actions"]}
    assert "ADD_INSTANCE" in actions
    assert "DO_NOTHING" in actions


def test_reasoning_avoids_repeating_rejected_action():
    result = RuleBasedReasoningProvider().reason(
        {"cpu_percent": 90, "memory_percent": 75, "network_usage": 20},
        [],
        {"issue": ["OVERLOAD"], "severity": "HIGH"},
        feedback={"selected_action": "ADD_INSTANCE", "outcome": "REJECTED"},
    )
    actions = {item["action"] for item in result["candidate_actions"]}
    assert "ADD_INSTANCE" not in actions
    assert actions


def test_planning_returns_ranked_candidate():
    result = PlanningAgent().rank(
        [{
            "action": "ADD_INSTANCE",
            "estimated_cost": 0.2,
            "estimated_energy": 0.05,
            "reason": "capacity",
            "expected_effect": "lower pressure",
        }],
        {"cpu_percent": 90, "memory_percent": 80},
        WEIGHTS,
        [{"cpu": 90, "memory": 80}],
    )
    assert result["selected"]["action"] == "ADD_INSTANCE"
    assert isinstance(result["selected"]["score"], float)


def test_safety_rejects_excessive_scale_step():
    assert not validate({"action": "ADD_INSTANCE", "delta": 10}, 2).approved


def test_safety_rejects_unknown_action():
    assert not validate({"action": "SHELL", "delta": 0}, 2).approved


def test_safety_rejects_negative_scale_delta():
    assert not validate({"action": "ADD_INSTANCE", "delta": -1}, 2).approved


def test_safety_rejects_non_integer_delta():
    assert not validate({"action": "ADD_INSTANCE", "delta": "one"}, 2).approved


def test_safety_enforces_scaling_cooldown():
    now = datetime(2026, 1, 1, 0, 0, 30)
    last_action = now - timedelta(seconds=30)
    result = validate(
        {"action": "ADD_INSTANCE", "delta": 1},
        2,
        last_action_time=last_action,
        now=now,
    )
    assert not result.approved
    assert "Cooldown" in result.reason


def test_safety_allows_scaling_after_cooldown():
    now = datetime(2026, 1, 1, 0, 1, 1)
    last_action = now - timedelta(seconds=61)
    assert validate(
        {"action": "ADD_INSTANCE", "delta": 1},
        2,
        last_action_time=last_action,
        now=now,
    ).approved


def test_safety_protects_minimum_instances_and_critical_workloads():
    assert not validate({"action": "REMOVE_INSTANCE", "delta": 1}, 1).approved
    assert not validate(
        {"action": "REMOVE_INSTANCE", "delta": 1},
        2,
        critical=True,
    ).approved


def test_execution_add_instance_reduces_pressure():
    before, after = ExecutionAgent().simulate(
        {"action": "ADD_INSTANCE", "delta": 1},
        {
            "instances": 2,
            "cpu_percent": 90,
            "memory_percent": 60,
            "latency_ms": 100,
            "estimated_cost": 0.2,
            "estimated_energy": 0.4,
        },
    )
    assert after["instances"] == 3
    assert after["cpu_percent"] < before["cpu_percent"]


def test_evaluation_reports_before_after_changes():
    result = EvaluationAgent().evaluate(
        {"cpu_percent": 90, "memory_percent": 60, "latency_ms": 100,
         "estimated_cost": 0.2, "estimated_energy": 0.4},
        {"cpu_percent": 60, "memory_percent": 50, "latency_ms": 80,
         "estimated_cost": 0.3, "estimated_energy": 0.5},
    )
    assert result["cpu_improvement"] == 30
    assert result["latency_improvement"] == 20


def test_orchestrator_returns_decision_and_feedback():
    state = {
        "cpu_percent": 45,
        "memory_percent": 55,
        "disk_percent": 40,
        "network_usage": 20,
        "active_workloads": 1,
        "instances": 2,
        "latency_ms": 70,
        "estimated_cost": 0.2,
        "estimated_energy": 0.36,
    }
    result = AgentOrchestrator(None, SETTINGS).run(
        history=[state],
        state=state,
        weights=WEIGHTS,
        mode="simulation",
    )
    assert result["decision_id"]
    assert result["selected_action"]
    assert result["feedback"]["outcome"] == result["outcome"]
    assert result["observation"]["cpu_percent"] == 45


@pytest.mark.parametrize(
    "workload",
    ["Stable", "Increasing", "Sudden Spike", "Decreasing", "Anomaly"],
)
def test_experiment_comparison_returns_two_finite_system_rows(workload):
    rows = run_comparison(workload, duration=24, seed=42)
    assert [row["system"] for row in rows] == ["BASELINE", "PROPOSED"]

    for row in rows:
        for key in (
            "avg_cpu",
            "avg_memory",
            "latency",
            "throughput",
            "estimated_cost",
            "estimated_energy",
            "prediction_accuracy",
        ):
            assert isinstance(row[key], (int, float))
            assert row[key] >= 0


def test_execution_cpu_increase_persists_capacity_multiplier():
    state = {
        "instances": 2,
        "cpu_percent": 90,
        "memory_percent": 70,
        "latency_ms": 150,
        "estimated_cost": 0.2,
        "estimated_energy": 0.36,
        "cpu_capacity_multiplier": 1.0,
    }
    _, after = ExecutionAgent().simulate(
        {"action": "INCREASE_CPU", "delta": 0},
        state,
    )
    assert after["cpu_capacity_multiplier"] > state["cpu_capacity_multiplier"]

    monitor = MonitoringAgent()
    before_metrics = monitor.observe_simulated(90, instances=2, seed=11)
    after_metrics = monitor.observe_simulated(
        90,
        instances=2,
        seed=11,
        cpu_capacity_multiplier=after["cpu_capacity_multiplier"],
    )
    assert after_metrics["cpu_percent"] < before_metrics["cpu_percent"]


def test_sudden_spike_scenario_exercises_threshold_scaling():
    baseline, proposed = run_comparison("Sudden Spike", duration=24, seed=42)
    assert baseline["scaling_actions"] >= 1
    assert proposed["scaling_actions"] >= 1


def test_derived_metrics_preserves_post_action_values():
    post_action = {
        "cpu_percent": 50.0,
        "memory_percent": 60.0,
        "latency_ms": 75.0,
        "throughput": 84.0,
        "estimated_cost": 0.30,
        "estimated_energy": 0.50,
        "cpu_capacity_multiplier": 1.5,
    }

    result = _add_derived_metrics(
        post_action,
        instances=2,
        cpu_capacity_multiplier=1.5,
    )

    assert result["latency_ms"] == 75.0
    assert result["throughput"] == 84.0
    assert result["estimated_cost"] == 0.30
    assert result["estimated_energy"] == 0.50


def test_experiment_comparison_is_deterministic_for_same_seed():
    first = run_comparison("Sudden Spike", duration=24, seed=123)
    second = run_comparison("Sudden Spike", duration=24, seed=123)
    assert first == second
