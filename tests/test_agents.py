"""
Unit tests for individual agents and tools
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from google_adk.agent_factory import BaseAgent, AgentFactory
from google_adk.runtime_config import AgentConfig, RuntimeManager, RuntimeConfig
from google_adk.exceptions import AgentError, AgentStartupError, ValidationError
from google_adk.context_managers import managed_agent
from agents.research_agent import ResearchAgent
from agents.planning_agent import PlanningAgent
from agents.coordinator_agent import CoordinatorAgent
from tools.optimization_tools import PlanningOptimizerTool, BudgetOptimizerTool
from tools.quality_tools import DataQualityTool, PlanValidatorTool


@pytest.fixture
async def runtime_setup():
    """Setup runtime for testing"""
    config = RuntimeConfig(environment="test")
    runtime = RuntimeManager(config)
    await runtime.start()
    factory = AgentFactory(runtime)
    yield factory
    await runtime.stop()


@pytest.mark.asyncio
class TestSpecificAgents:
    """Test specific agent implementations"""
    
    async def test_research_agent_initialization(self, runtime_setup):
        """Test research agent initialization"""
        factory = runtime_setup
        factory.register_agent_type("research", ResearchAgent)
        agent = await factory.create_agent("test_research", "research")
        
        assert agent.name == "test_research"
        assert agent.has_capability("research_destination")
        assert agent.has_capability("consensus_vote")
        
    async def test_planning_agent_task_execution(self, runtime_setup):
        """Test planning agent task execution"""
        factory = runtime_setup
        factory.register_agent_type("planning", PlanningAgent)
        agent = await factory.create_agent("test_planning", "planning")
        
        task = {
            "method": "create_itinerary",
            "params": {"budget": 1500, "days": 3},
            "context": {"research_agent": {"destination": "Paris"}}
        }
        
        result = await agent.execute_task(task)
        assert "budget_allocated" in result
        assert result["budget_allocated"] == 1500
        
    async def test_coordinator_consensus_voting(self, runtime_setup):
        """Test coordinator consensus voting"""
        factory = runtime_setup
        factory.register_agent_type("coordinator", CoordinatorAgent)
        agent = await factory.create_agent("test_coordinator", "coordinator")
        
        task = {
            "method": "consensus_vote",
            "params": {"question": "Approve final plan?"}
        }
        
        result = await agent.execute_task(task)
        assert "vote" in result
        assert "confidence" in result


@pytest.mark.asyncio
class TestAdvancedTools:
    """Test advanced tool implementations"""
    
    async def test_planning_optimizer_tool(self):
        """Test planning optimizer"""
        tool = PlanningOptimizerTool()
        
        params = {"budget": 2000, "days": 5, "priorities": ["cost"]}
        result = await tool.execute(params)
        
        assert "optimized_plan" in result
        assert "budget_allocation" in result["optimized_plan"]
        assert result["optimized_plan"]["cost_savings"] > 0
        
    async def test_budget_optimizer_tool(self):
        """Test budget optimizer"""
        tool = BudgetOptimizerTool()
        
        params = {"budget": 1000}
        result = await tool.execute(params)
        
        assert "allocations" in result
        assert "total" in result
        assert result["total"] <= 1000
        
    async def test_data_quality_tool(self):
        """Test data quality checker"""
        tool = DataQualityTool()
        
        # Test good data
        params = {
            "data": {"budget": 1500, "destination": "Paris", "days": 3},
            "required_fields": ["budget", "destination"]
        }
        result = await tool.execute(params)
        
        assert result["quality_score"] > 0.5
        assert result["status"] in ["good", "needs_improvement"]
        
    async def test_plan_validator_tool(self):
        """Test plan validator"""
        tool = PlanValidatorTool()
        
        params = {
            "plan": {
                "budget": 1500,
                "destination": "Paris",
                "schedule": ["Day 1: Museum"]
            }
        }
        result = await tool.execute(params)
        
        assert "valid" in result
        assert "checks" in result
        assert result["confidence"] > 0


class TestBaseAgent:
    """Test cases for BaseAgent class"""
    
    def test_agent_initialization_valid(self, agent_config, runtime_manager, mock_agent_class):
        """Test successful agent initialization"""
        agent = mock_agent_class("test_agent", agent_config, runtime_manager)
        
        assert agent.name == "test_agent"
        assert agent.config == agent_config
        assert agent.runtime == runtime_manager
        assert not agent.is_running
        assert agent.capabilities == agent_config.capabilities
        
    def test_agent_initialization_invalid_name(self, agent_config, runtime_manager, mock_agent_class):
        """Test agent initialization with invalid name"""
        with pytest.raises(ValidationError, match="Agent name cannot be empty"):
            mock_agent_class("", agent_config, runtime_manager)
            
        with pytest.raises(ValidationError, match="Agent name cannot be empty"):
            mock_agent_class("   ", agent_config, runtime_manager)
            
    def test_agent_initialization_invalid_config(self, runtime_manager, mock_agent_class):
        """Test agent initialization with invalid config"""
        with pytest.raises(ValidationError, match="Agent config must be AgentConfig instance"):
            mock_agent_class("test_agent", "invalid_config", runtime_manager)
            
    def test_agent_initialization_invalid_runtime(self, agent_config, mock_agent_class):
        """Test agent initialization with invalid runtime"""
        with pytest.raises(ValidationError, match="Runtime must be RuntimeManager instance"):
            mock_agent_class("test_agent", agent_config, "invalid_runtime")
            
    @pytest.mark.asyncio
    async def test_agent_start_success(self, mock_agent):
        """Test successful agent start"""
        assert not mock_agent.is_running
        assert not mock_agent.initialized
        
        await mock_agent.start()
        
        assert mock_agent.is_running
        assert mock_agent.initialized
        
    @pytest.mark.asyncio
    async def test_agent_start_already_running(self, mock_agent):
        """Test starting an already running agent"""
        await mock_agent.start()
        assert mock_agent.is_running
        
        # Starting again should not raise an error
        await mock_agent.start()
        assert mock_agent.is_running
        
    @pytest.mark.asyncio
    async def test_agent_start_initialization_failure(self, agent_config, runtime_manager, mock_agent_class):
        """Test agent start with initialization failure"""
        class FailingAgent(mock_agent_class):
            async def initialize(self):
                raise RuntimeError("Initialization failed")
                
        agent = FailingAgent("failing_agent", agent_config, runtime_manager)
        
        with pytest.raises(AgentStartupError, match="Failed to start agent failing_agent"):
            await agent.start()
            
        assert not agent.is_running
        
    @pytest.mark.asyncio
    async def test_agent_stop_success(self, mock_agent):
        """Test successful agent stop"""
        await mock_agent.start()
        assert mock_agent.is_running
        
        await mock_agent.stop()
        assert not mock_agent.is_running
        assert not mock_agent.initialized  # Mock cleanup sets this to False
        
    @pytest.mark.asyncio
    async def test_agent_stop_not_running(self, mock_agent):
        """Test stopping a non-running agent"""
        assert not mock_agent.is_running
        
        # Stopping should not raise an error
        await mock_agent.stop()
        assert not mock_agent.is_running
        
    def test_capability_management(self, mock_agent):
        """Test capability add/remove/check operations"""
        # Initial capabilities
        assert mock_agent.has_capability("test_capability")
        assert mock_agent.has_capability("mock_capability")
        assert not mock_agent.has_capability("non_existent")
        
        # Add capability
        mock_agent.add_capability("new_capability")
        assert mock_agent.has_capability("new_capability")
        assert "new_capability" in mock_agent.get_capabilities()
        
        # Remove capability
        assert mock_agent.remove_capability("new_capability")
        assert not mock_agent.has_capability("new_capability")
        
        # Remove non-existent capability
        assert not mock_agent.remove_capability("non_existent")
        
    def test_capability_validation(self, mock_agent):
        """Test capability validation"""
        with pytest.raises(ValidationError, match="Capability cannot be empty"):
            mock_agent.add_capability("")
            
        with pytest.raises(ValidationError, match="Capability cannot be empty"):
            mock_agent.add_capability("   ")
            
        # Empty capability checks should return False
        assert not mock_agent.has_capability("")
        assert not mock_agent.has_capability("   ")
        
    @pytest.mark.asyncio
    async def test_managed_agent_context(self, mock_agent):
        """Test agent lifecycle with context manager"""
        assert not mock_agent.is_running
        
        async with managed_agent(mock_agent) as agent:
            assert agent.is_running
            assert agent.initialized
            
        assert not mock_agent.is_running
        assert not mock_agent.initialized


class TestAgentFactory:
    """Test cases for AgentFactory class"""
    
    @pytest.mark.asyncio
    async def test_factory_initialization(self, runtime_manager):
        """Test factory initialization"""
        factory = AgentFactory(runtime_manager)
        
        assert factory.runtime == runtime_manager
        assert len(factory.agent_types) == 0
        assert len(factory.agents) == 0
        
    def test_register_agent_type(self, agent_factory, mock_agent_class):
        """Test agent type registration"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        assert "mock" in agent_factory.agent_types
        assert agent_factory.agent_types["mock"] == mock_agent_class
        
    @pytest.mark.asyncio
    async def test_create_agent_success(self, agent_factory, mock_agent_class, agent_config):
        """Test successful agent creation"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        agent = await agent_factory.create_agent("test_agent", "mock", agent_config)
        
        assert agent.name == "test_agent"
        assert agent.is_running
        assert "test_agent" in agent_factory.agents
        
    @pytest.mark.asyncio
    async def test_create_agent_unknown_type(self, agent_factory, agent_config):
        """Test creating agent with unknown type"""
        with pytest.raises(ValueError, match="Unknown agent type: unknown"):
            await agent_factory.create_agent("test_agent", "unknown", agent_config)
            
    @pytest.mark.asyncio
    async def test_create_agent_default_config(self, agent_factory, mock_agent_class):
        """Test creating agent with default config"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        agent = await agent_factory.create_agent("test_agent", "mock")
        
        assert agent.name == "test_agent"
        assert agent.config.agent_type == "mock"
        assert agent.is_running
        
    def test_get_agent(self, agent_factory, mock_agent_class):
        """Test getting agent by name"""
        # Non-existent agent
        assert agent_factory.get_agent("non_existent") is None
        
    @pytest.mark.asyncio
    async def test_get_agents_by_capability(self, agent_factory, mock_agent_class):
        """Test getting agents by capability"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        config1 = AgentConfig(name="agent1", agent_type="mock", capabilities=["cap1", "cap2"])
        config2 = AgentConfig(name="agent2", agent_type="mock", capabilities=["cap2", "cap3"])
        
        agent1 = await agent_factory.create_agent("agent1", "mock", config1)
        agent2 = await agent_factory.create_agent("agent2", "mock", config2)
        
        # Test capability filtering
        agents_with_cap1 = agent_factory.get_agents_by_capability("cap1")
        assert len(agents_with_cap1) == 1
        assert agents_with_cap1[0].name == "agent1"
        
        agents_with_cap2 = agent_factory.get_agents_by_capability("cap2")
        assert len(agents_with_cap2) == 2
        
        agents_with_cap3 = agent_factory.get_agents_by_capability("cap3")
        assert len(agents_with_cap3) == 1
        assert agents_with_cap3[0].name == "agent2"
        
    @pytest.mark.asyncio
    async def test_stop_all_agents(self, agent_factory, mock_agent_class):
        """Test stopping all agents"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        agent1 = await agent_factory.create_agent("agent1", "mock")
        agent2 = await agent_factory.create_agent("agent2", "mock")
        
        assert agent1.is_running
        assert agent2.is_running
        
        await agent_factory.stop_all_agents()
        
        assert not agent1.is_running
        assert not agent2.is_running
        
    def test_list_available_types(self, agent_factory, mock_agent_class):
        """Test listing available agent types"""
        assert len(agent_factory.list_available_types()) == 0
        
        agent_factory.register_agent_type("mock1", mock_agent_class)
        agent_factory.register_agent_type("mock2", mock_agent_class)
        
        types = agent_factory.list_available_types()
        assert len(types) == 2
        assert "mock1" in types
        assert "mock2" in types
        
    @pytest.mark.asyncio
    async def test_list_active_agents(self, agent_factory, mock_agent_class):
        """Test listing active agents"""
        agent_factory.register_agent_type("mock", mock_agent_class)
        
        assert len(agent_factory.list_active_agents()) == 0
        
        agent = await agent_factory.create_agent("test_agent", "mock")
        
        active_agents = agent_factory.list_active_agents()
        assert len(active_agents) == 1
        
        agent_info = active_agents[0]
        assert agent_info["name"] == "test_agent"
        assert agent_info["type"] == "mock"
        assert agent_info["running"] is True