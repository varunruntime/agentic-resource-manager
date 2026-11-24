from datetime import datetime
import uuid

from app.agents.monitoring import MonitoringAgent
from app.agents.analysis import AnalysisAgent
from app.ml.predictor import DemandPredictor
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.policies.safety import validate
from app.agents.reasoning import RuleBasedReasoningProvider


class AgentOrchestrator:
    def __init__(self, db, settings):
        self.db = db

        self.monitor = MonitoringAgent()
        self.analysis = AnalysisAgent()
        self.predictor = DemandPredictor()
        # No external LLM API call is implemented yet. Keep the active
        # provider deterministic and rule-based even when an API key is set.
        self.reasoner = RuleBasedReasoningProvider()
        self.planner = PlanningAgent()
        self.execution = ExecutionAgent()
        self.evaluation = EvaluationAgent()

    def run(
        self,
        history,
        state,
        weights,
        mode="simulation",
        active_workloads=1,
        feedback=None,
        last_action_time=None,
        now=None,
        critical=False,
    ):
        """
        Closed-loop agent cycle:
        OBSERVE -> ANALYZE -> PREDICT -> REASON -> PLAN
        -> SAFETY CHECK -> ACT -> EVALUATE -> FEEDBACK.

        last_action_time/now use the same clock so callers can enforce the
        deterministic scaling cooldown. Experiments supply a simulated clock.
        """

        # 1. OBSERVE: normalize the latest already-collected snapshot.
        raw_observation = history[-1] if history else state
        observation = self.monitor.observe_snapshot(raw_observation)

        if feedback is not None:
            observation["previous_feedback"] = feedback

        # 2. ANALYZE current resource conditions.
        analysis = self.analysis.analyze(observation)

        # 3. PREDICT from past/current observations only.
        prediction_history = history if history else [observation]
        predictions = self.predictor.predict(prediction_history)

        # 4. REASON using current metrics, predictions and prior feedback.
        reasoning = self.reasoner.reason(
            observation,
            predictions,
            analysis,
            feedback,
        )

        # 5. PLAN and rank the candidate actions.
        plan = self.planner.rank(
            reasoning["candidate_actions"],
            observation,
            weights,
            predictions,
        )
        selected = plan["selected"]

        # 6. SAFETY CHECK, including scaling cooldown.
        current_instances = int(
            state.get("instances", observation.get("instances", 2))
        )
        decision_time = now or datetime.utcnow()
        safety = validate(
            selected,
            current_instances,
            last_action_time=last_action_time,
            now=decision_time,
            critical=critical,
        )

        # 7. ACT only in simulation mode and only after safety approval.
        if mode == "recommendation":
            before = dict(state)
            after = dict(state)
            outcome = "PENDING"
        elif mode != "simulation":
            before = dict(state)
            after = dict(state)
            outcome = "PENDING"
        elif not safety.approved:
            before = dict(state)
            after = dict(state)
            outcome = "REJECTED"
        else:
            before, after = self.execution.simulate(selected, state)
            outcome = "SUCCESS"

        # 8. EVALUATE the measured simulated before/after state.
        evaluation = self.evaluation.evaluate(before, after)

        # 9. FEEDBACK is returned to the caller for the next cycle.
        feedback_result = {
            "selected_action": selected["action"],
            "outcome": outcome,
            "cpu_improvement": evaluation["cpu_improvement"],
            "memory_improvement": evaluation["memory_improvement"],
            "latency_improvement": evaluation["latency_improvement"],
            "cost_change": evaluation["cost_change"],
            "energy_change": evaluation["energy_change"],
            "slo_impact": evaluation["slo_impact"],
        }

        return {
            "decision_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "observation": observation,
            "prediction": predictions,
            "detected_problem": analysis,
            "reasoning": reasoning,
            "plan": plan,
            "safety": {
                "approved": safety.approved,
                "reason": safety.reason,
            },
            "selected_action": selected["action"],
            "actual_result": after,
            "evaluation": evaluation,
            "feedback": feedback_result,
            "outcome": outcome,
        }
