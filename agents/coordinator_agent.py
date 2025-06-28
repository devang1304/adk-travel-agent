"""
Coordinator Agent - Workflow coordination and management
"""

from google_adk import BaseAgent


class CoordinatorAgent(BaseAgent):
    """Agent for workflow coordination"""
    
    async def initialize(self):
        """Initialize coordination capabilities"""
        self.add_capability("finalize_plan")
        self.add_capability("coordinate_workflow")
        self.add_capability("consensus_vote")
        
    async def process_message(self, message):
        """Process coordination requests"""
        return {"status": "processed", "agent": self.name}
        
    async def execute_task(self, task):
        """Execute coordination tasks"""
        method = task.get("method")
        context = task.get("context", {})
        params = task.get("params", {})
        
        if method == "finalize_plan":
            return await self._finalize_plan(context)
        elif method == "consensus_vote":
            return await self._consensus_vote(params)
        
        return {"error": f"Unknown method: {method}"}
        
    async def _finalize_plan(self, context):
        """Finalize travel plan from all agent inputs"""
        research = context.get("research_agent", {})
        planning = context.get("planning_agent", {})
        
        return {
            "final_plan": {
                "destination": research.get("destination"),
                "attractions": research.get("attractions"),
                "schedule": planning.get("schedule"),
                "budget": planning.get("budget_allocated"),
                "status": "finalized"
            }
        }
        
    async def _consensus_vote(self, params):
        """Vote on consensus questions"""
        question = params.get("question", "")
        
        # Simple consensus logic for coordinator
        if "budget" in question.lower():
            return {"vote": "approve", "confidence": 0.8}
        elif "plan" in question.lower():
            return {"vote": "approve", "confidence": 0.9}
        else:
            return {"vote": "neutral", "confidence": 0.5}