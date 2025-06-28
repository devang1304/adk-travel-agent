"""
Planning Agent - Itinerary planning and optimization
"""

from google_adk import BaseAgent


class PlanningAgent(BaseAgent):
    """Agent for itinerary planning"""
    
    async def initialize(self):
        """Initialize planning capabilities"""
        self.add_capability("create_itinerary")
        self.add_capability("optimize_schedule")
        
    async def process_message(self, message):
        """Process planning requests"""
        return {"status": "processed", "agent": self.name}
        
    async def execute_task(self, task):
        """Execute planning tasks"""
        method = task.get("method")
        params = task.get("params", {})
        context = task.get("context", {})
        
        if method == "create_itinerary":
            return await self._create_itinerary(params, context)
        
        return {"error": f"Unknown method: {method}"}
        
    async def _create_itinerary(self, params, context):
        """Create travel itinerary"""
        budget = params.get("budget")
        days = params.get("days")
        research_data = context.get("research_agent", {})
        
        return {
            "budget_allocated": budget,
            "duration": f"{days} days",
            "schedule": ["Day 1: Museum", "Day 2: Park"],
            "research_used": research_data.get("destination")
        }