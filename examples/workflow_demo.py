"""
Demo of multi-agent travel planning workflow
"""

import asyncio
from google_adk import RuntimeConfig, RuntimeManager, AgentFactory, AgentOrchestrator, get_logger
from agents.research_agent import ResearchAgent
from agents.planning_agent import PlanningAgent  
from agents.coordinator_agent import CoordinatorAgent
from workflows.travel_planning import create_travel_workflow


async def main():
    """Run travel planning demo"""
    logger = get_logger("demo")
    
    # Setup
    config = RuntimeConfig(environment="development")
    runtime = RuntimeManager(config)
    await runtime.start()
    
    factory = AgentFactory(runtime)
    orchestrator = AgentOrchestrator(factory)
    
    # Register agents
    factory.register_agent_type("research", ResearchAgent)
    factory.register_agent_type("planning", PlanningAgent)
    factory.register_agent_type("coordinator", CoordinatorAgent)
    
    # Create agents
    await factory.create_agent("research_agent", "research")
    await factory.create_agent("planning_agent", "planning") 
    await factory.create_agent("coordinator_agent", "coordinator")
    
    # Execute workflow
    workflow = create_travel_workflow("Paris", 2000, 3)
    results = await orchestrator.execute_conversation("demo", workflow)
    
    final_plan = results["coordinator_agent"]["final_plan"]
    logger.info("Travel plan generated successfully", extra={"plan": final_plan})
    
    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())