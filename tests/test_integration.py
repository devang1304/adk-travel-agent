"""
Integration tests for agent communication and workflow execution
"""

import pytest
import asyncio
from google_adk import RuntimeConfig, RuntimeManager, AgentFactory, AgentOrchestrator
from agents.research_agent import ResearchAgent
from agents.planning_agent import PlanningAgent
from agents.coordinator_agent import CoordinatorAgent
from workflows.travel_planning import create_travel_workflow
from examples.tool_setup import setup_tools


@pytest.fixture
async def full_system_setup():
    """Setup complete system for integration testing"""
    # Setup tools
    setup_tools()
    
    # Setup runtime
    config = RuntimeConfig(environment="test")
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
    
    yield factory, orchestrator
    
    await runtime.stop()


@pytest.mark.asyncio
class TestAgentCommunication:
    """Test agent-to-agent communication patterns"""
    
    async def test_basic_agent_communication(self, full_system_setup):
        """Test basic agent message passing"""
        factory, orchestrator = full_system_setup
        
        research_agent = factory.get_agent("research_agent")
        
        # Test message processing
        message = {"type": "request", "data": "test"}
        result = await research_agent.process_message(message)
        
        assert result["status"] == "processed"
        assert result["agent"] == "research_agent"
        
    async def test_consensus_mechanism(self, full_system_setup):
        """Test consensus voting across agents"""
        factory, orchestrator = full_system_setup
        
        from google_adk.orchestrator import ConsensusRequest, ConsensusType
        
        consensus_request = ConsensusRequest(
            question="Should we proceed with Paris trip?",
            agents=["research_agent", "planning_agent", "coordinator_agent"],
            consensus_type=ConsensusType.MAJORITY
        )
        
        result = await orchestrator.resolve_consensus(consensus_request)
        
        assert "consensus" in result
        assert "votes" in result
        
    async def test_agent_delegation(self, full_system_setup):
        """Test agent delegation patterns"""
        factory, orchestrator = full_system_setup
        
        # Create step that requires delegation if agent fails
        from google_adk.orchestrator import ConversationStep
        
        step = ConversationStep(
            agent_name="non_existent_agent",
            method="research_destination",
            params={"destination": "Tokyo"},
            can_delegate=True
        )
        
        # Should delegate to research agent with capability
        result = await orchestrator._execute_step_with_recovery(step, {})
        
        assert "destination" in result
        assert result["destination"] == "Tokyo"


@pytest.mark.asyncio 
class TestWorkflowExecution:
    """Test end-to-end workflow execution"""
    
    async def test_travel_planning_workflow(self, full_system_setup):
        """Test complete travel planning workflow"""
        factory, orchestrator = full_system_setup
        
        # Execute travel workflow
        workflow = create_travel_workflow("Barcelona", 2500, 4)
        results = await orchestrator.execute_conversation("test_workflow", workflow)
        
        # Verify all agents executed
        assert "research_agent" in results
        assert "planning_agent" in results
        assert "coordinator_agent" in results
        
        # Verify final plan structure
        final_plan = results["coordinator_agent"]["final_plan"]
        assert final_plan["destination"] == "Barcelona"
        assert final_plan["budget"] == 2500
        assert final_plan["status"] == "finalized"
        
    async def test_workflow_with_dependencies(self, full_system_setup):
        """Test workflow dependency resolution"""
        factory, orchestrator = full_system_setup
        
        from google_adk.orchestrator import ConversationStep
        
        steps = [
            ConversationStep(
                agent_name="research_agent",
                method="research_destination",
                params={"destination": "Rome"}
            ),
            ConversationStep(
                agent_name="planning_agent", 
                method="create_itinerary",
                params={"budget": 1800, "days": 3},
                depends_on=["research_agent"]
            )
        ]
        
        results = await orchestrator.execute_conversation("dependency_test", steps)
        
        # Planning should have access to research results
        planning_result = results["planning_agent"]
        assert planning_result["research_used"] == "Rome"
        
    async def test_error_recovery_workflow(self, full_system_setup):
        """Test workflow error recovery"""
        factory, orchestrator = full_system_setup
        
        from google_adk.orchestrator import ConversationStep
        
        # Create step with retry configuration
        step = ConversationStep(
            agent_name="planning_agent",
            method="create_itinerary", 
            params={"budget": 1500, "days": 2},
            max_retries=2
        )
        
        # Should succeed even with retries
        result = await orchestrator._execute_step_with_recovery(step, {})
        
        assert "budget_allocated" in result
        assert result["budget_allocated"] == 1500


@pytest.mark.asyncio
class TestPerformanceBasics:
    """Basic performance and scalability tests"""
    
    async def test_concurrent_agent_operations(self, full_system_setup):
        """Test concurrent agent task execution"""
        factory, orchestrator = full_system_setup
        
        # Create multiple concurrent tasks
        tasks = []
        for i in range(5):
            agent = factory.get_agent("research_agent")
            task = agent.execute_task({
                "method": "research_destination",
                "params": {"destination": f"City{i}"}
            })
            tasks.append(task)
            
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["destination"] == f"City{i}"
            
    async def test_workflow_execution_time(self, full_system_setup):
        """Test workflow execution performance"""
        import time
        
        factory, orchestrator = full_system_setup
        
        start_time = time.time()
        
        workflow = create_travel_workflow("Berlin", 2000, 3)
        results = await orchestrator.execute_conversation("perf_test", workflow)
        
        execution_time = time.time() - start_time
        
        # Should complete within reasonable time (10 seconds for test env)
        assert execution_time < 10.0
        assert "coordinator_agent" in results
        
    async def test_memory_usage_stability(self, full_system_setup):
        """Test basic memory usage patterns"""
        factory, orchestrator = full_system_setup
        
        # Execute multiple workflows to check for memory leaks
        for i in range(3):
            workflow = create_travel_workflow(f"TestCity{i}", 1000, 2)
            results = await orchestrator.execute_conversation(f"mem_test_{i}", workflow)
            assert len(results) == 3  # All agents should respond
            
        # Test passes if no memory exceptions occur