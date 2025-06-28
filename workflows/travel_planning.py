"""
Simple travel planning workflow
"""

from google_adk.orchestrator import ConversationStep


def create_travel_workflow(destination: str, budget: int, days: int) -> list:
    """Create travel planning workflow steps"""
    return [
        ConversationStep(
            agent_name="research_agent",
            method="research_destination", 
            params={"destination": destination, "duration_days": days}
        ),
        ConversationStep(
            agent_name="planning_agent",
            method="create_itinerary",
            params={"budget": budget, "days": days},
            depends_on=["research_agent"]
        ),
        ConversationStep(
            agent_name="coordinator_agent", 
            method="finalize_plan",
            params={},
            depends_on=["research_agent", "planning_agent"]
        )
    ]