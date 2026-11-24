import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.database.session import Base, get_db


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_resource_endpoints_return_stable_metric_shapes(client):
    current = client.get("/api/resources/current")
    assert current.status_code == 200
    assert current.json()["instances"] == 2
    assert "cpu_capacity_multiplier" in current.json()

    history = client.get("/api/resources/history")
    assert history.status_code == 200
    assert len(history.json()) == 1


def test_workload_create_start_stop_and_serialization(client):
    created = client.post("/api/workloads", json={
        "name": "API spike",
        "workload_type": "Sudden Spike",
        "initial_load": 35,
        "growth_rate": 2,
        "duration_seconds": 10,
    })
    assert created.status_code == 200
    body = created.json()
    assert body["active"] is False
    assert "_sa_instance_state" not in body

    workload_id = body["id"]
    started = client.post(f"/api/workloads/{workload_id}/start")
    assert started.status_code == 200
    rows = client.get("/api/workloads").json()
    assert rows[0]["active"] is True

    stopped = client.post(f"/api/workloads/{workload_id}/stop")
    assert stopped.status_code == 200
    rows = client.get("/api/workloads").json()
    assert rows[0]["active"] is False


def test_agent_simulation_persists_full_decision_trace(client):
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
    response = client.post("/api/agents/run", json={
        "history": [state],
        "state": state,
        "mode": "simulation",
    })
    assert response.status_code == 200
    decision_id = response.json()["decision_id"]
    assert response.json()["feedback"]["outcome"] == response.json()["outcome"]

    detail = client.get(f"/api/decisions/{decision_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["reasoning"]
    assert body["candidate_actions"]
    assert body["safety"]
    assert body["execution"]["mode"] == "simulation"
    assert body["evaluation"]
    assert body["feedback"]["selected_action"] == body["action"]

    actions = client.get("/api/actions")
    assert actions.status_code == 200
    assert actions.json()
    assert all("_sa_instance_state" not in item for item in actions.json())


def test_agent_endpoint_rejects_unknown_execution_mode(client):
    response = client.post("/api/agents/run", json={
        "history": [],
        "state": {"cpu_percent": 30},
        "mode": "real_cloud",
    })
    assert response.status_code == 422


def test_experiment_lifecycle_saves_and_retrieves_both_systems(client):
    created = client.post("/api/experiments", json={
        "name": "API sudden spike",
        "workload_type": "Sudden Spike",
        "duration_seconds": 10,
        "seed": 7,
    })
    assert created.status_code == 200
    experiment_id = created.json()["id"]

    started = client.post(f"/api/experiments/{experiment_id}/start")
    assert started.status_code == 200
    assert {row["system"] for row in started.json()} == {"BASELINE", "PROPOSED"}

    history = client.get("/api/experiments")
    assert history.status_code == 200
    assert history.json()[0]["status"] == "COMPLETED"

    saved = client.get(f"/api/experiments/{experiment_id}/results")
    assert saved.status_code == 200
    assert {row["system"] for row in saved.json()} == {"BASELINE", "PROPOSED"}


def test_demo_auth_register_and_login(client):
    registered = client.post("/api/auth/register", json={
        "username": "demo-user",
        "password": "strong-demo-password",
    })
    assert registered.status_code == 200
    assert registered.json()["token"]

    logged_in = client.post("/api/auth/login", json={
        "username": "demo-user",
        "password": "strong-demo-password",
    })
    assert logged_in.status_code == 200
    assert logged_in.json()["token"]

    rejected = client.post("/api/auth/login", json={
        "username": "demo-user",
        "password": "wrong-password",
    })
    assert rejected.status_code == 401


def test_metrics_summary_and_decision_export_endpoints(client):
    summary = client.get("/api/metrics/summary")
    assert summary.status_code == 200
    assert summary.json()["samples"] == 0

    export = client.get("/api/decisions/export.csv")
    assert export.status_code == 200
    assert "Decision ID" in export.text
