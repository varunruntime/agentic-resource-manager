import json, uuid
from datetime import datetime
from app.agents.monitoring import MonitoringAgent
from app.agents.analysis import AnalysisAgent
from app.agents.reasoning import RuleBasedReasoningProvider, LLMReasoningProvider
from app.agents.planning import PlanningAgent
from app.agents.execution import ExecutionAgent
from app.agents.evaluation import EvaluationAgent
from app.ml.predictor import DemandPredictor
from app.policies.safety import validate

class AgentOrchestrator:
    def __init__(self, db, settings):
        self.db=db; self.monitor=MonitoringAgent(); self.analysis=AnalysisAgent(); self.predictor=DemandPredictor(); self.planner=PlanningAgent(); self.execution=ExecutionAgent(); self.evaluation=EvaluationAgent()
        self.reasoner=LLMReasoningProvider(settings.llm_api_key) if settings.llm_api_key else RuleBasedReasoningProvider()
    def run(self, history, state, weights, mode="simulation"):
        obs=history[-1] if history else state
        preds=self.predictor.predict(history)
        analysis=self.analysis.analyze(obs,preds)
        reasoning=self.reasoner.reason(obs,preds,analysis)
        plan=self.planner.rank(reasoning["candidate_actions"],obs,weights)
        selected=plan["selected"]
        safety=validate(selected,int(state.get("instances",2)),critical=False)
        if mode=="recommendation" or not safety.approved or mode!="simulation":
            before=state; after=state; outcome="REJECTED" if not safety.approved else "PENDING"
        else:
            before,after=self.execution.simulate(selected,state); outcome="SUCCESS"
        evaluation=self.evaluation.evaluate(before,after)
        did=str(uuid.uuid4())
        return {"decision_id":did,"timestamp":datetime.utcnow().isoformat(),"observation":obs,"prediction":preds,"detected_problem":analysis,"reasoning":reasoning,"plan":plan,"safety":{"approved":safety.approved,"reason":safety.reason},"selected_action":selected["action"],"actual_result":after,"evaluation":evaluation,"outcome":outcome}
