import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from app.agents.monitoring import MonitoringAgent
from app.agents.analysis import AnalysisAgent
from app.agents.reasoning import RuleBasedReasoningProvider
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.policies.safety import validate

def test_monitoring_simulation(): assert 0 <= MonitoringAgent().observe_simulated(80,2)["cpu_percent"] <= 100
def test_analysis_overload(): assert AnalysisAgent().analyze({"cpu_percent":78,"network_usage":20},{"cpu":94,"memory":60})["issue"]=="PREDICTED_OVERLOAD"
def test_reasoning_candidates(): assert RuleBasedReasoningProvider().reason({},[],{"issue":"OVERLOAD","severity":"HIGH"})["candidate_actions"]
def test_planning(): assert PlanningAgent().rank([{"action":"ADD_INSTANCE","estimated_cost":.2,"reason":"x","expected_effect":"y"}],{},type('W',(),{'performance':.4,'cost':.25,'energy':.2,'utilization':.15})())["selected"]["action"]=="ADD_INSTANCE"
def test_safety_limits(): assert not validate({"action":"ADD_INSTANCE","delta":10},2).approved
def test_safety_unknown(): assert not validate({"action":"SHELL","delta":0},2).approved
def test_execution():
    b,a=ExecutionAgent().simulate({"action":"ADD_INSTANCE","delta":1},{"instances":2,"cpu_percent":90,"memory_percent":60,"latency_ms":100,"estimated_cost":.2,"estimated_energy":.4}); assert a["instances"]==3 and a["cpu_percent"]<b["cpu_percent"]
def test_evaluation():
    e=EvaluationAgent().evaluate({"cpu_percent":90,"memory_percent":60,"latency_ms":100,"estimated_cost":.2,"estimated_energy":.4},{"cpu_percent":60,"memory_percent":50,"latency_ms":80,"estimated_cost":.3,"estimated_energy":.5}); assert e["cpu_improvement"]==30
