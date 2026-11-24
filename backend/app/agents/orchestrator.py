from datetime import datetime
import uuid

from app.agents.monitoring import MonitoringAgent
from app.agents.analysis import AnalysisAgent
from app.ml.predictor import DemandPredictor
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.policies.safety import validate
from app.agents.reasoning import (
    RuleBasedReasoningProvider,
    LLMReasoningProvider,
)

class AgentOrchestrator:
    def __init__(self, db, settings):
        self.db = db

        # Agent pipeline
        self.monitor = MonitoringAgent()
        self.analysis = AnalysisAgent()
        self.predictor = DemandPredictor()
        self.reasoner = (
            LLMReasoningProvider(settings.llm_api_key)
            if settings.llm_api_key
            else RuleBasedReasoningProvider()
        )
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
    ):
        """
        Closed-loop agent cycle:

        OBSERVE
        -> ANALYZE
        -> PREDICT
        -> REASON
        -> PLAN
        -> SAFETY CHECK
        -> ACT
        -> EVALUATE
        -> FEEDBACK
        """

        # ---------------------------------------------------------
        # 1. OBSERVE
        # ---------------------------------------------------------
        if history:
            observation = dict(history[-1])
        else:
            observation = dict(state)

        # Preserve feedback from the previous cycle.
        if feedback is not None:
            observation["previous_feedback"] = feedback

        # ---------------------------------------------------------
        # 2. PREDICT
        # ---------------------------------------------------------
        prediction_history = history if history else [observation]

        predictions = self.predictor.predict(prediction_history)

        # ---------------------------------------------------------
        # 3. ANALYZE
        # ---------------------------------------------------------
        analysis = self.analysis.analyze(
            observation,
            predictions,
        )

        # ---------------------------------------------------------
        # 4. REASON
        # ---------------------------------------------------------
        reasoning = self.reasoner.reason(
            observation,
            predictions,
            analysis,
        )

        # ---------------------------------------------------------
        # 5. PLAN
        # ---------------------------------------------------------
        plan = self.planner.rank(
            reasoning["candidate_actions"],
            observation,
            weights,
        )

        selected = plan["selected"]

        # ---------------------------------------------------------
        # 6. SAFETY CHECK
        # ---------------------------------------------------------
        current_instances = int(
            state.get("instances", observation.get("instances", 2))
        )

        safety = validate(
            selected,
            current_instances,
            critical=False,
        )

        # ---------------------------------------------------------
        # 7. ACT
        # ---------------------------------------------------------
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
            before, after = self.execution.simulate(
                selected,
                state,
            )
            outcome = "SUCCESS"

        # ---------------------------------------------------------
        # 8. EVALUATE
        # ---------------------------------------------------------
        evaluation = self.evaluation.evaluate(
            before,
            after,
        )

        # ---------------------------------------------------------
        # 9. FEEDBACK
        # ---------------------------------------------------------
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

        decision_id = str(uuid.uuid4())

        return {
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),

            # Pipeline outputs
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