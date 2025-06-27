"""
Agent Factory for google-adk Framework
Handles agent instantiation, registration, and lifecycle management
"""

import asyncio
from typing import Dict, Any, Type, Optional
from abc import ABC, abstractmethod
from google_adk.runtime_config import RuntimeConfig, AgentConfig, RuntimeManager


class BaseAgent(ABC):
    """Base class for all google-adk agents"""
    
    def __init__(self, name: str, config: AgentConfig, runtime: RuntimeManager):
        self.name = name
        self.config = config
        self.runtime = runtime
        self.is_running = False
        self.capabilities = config.capabilities
        
    @abstractmethod
    async def initialize(self):
        """Initialize the agent"""
        pass
        
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages"""
        pass
        
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task"""
        pass
        
    async def start(self):
        """Start the agent"""
        if self.is_running:
            return
            
        await self.initialize()
        self.is_running = True
        print(f"Agent {self.name} started")
        
    async def stop(self):
        """Stop the agent"""
        if not self.is_running:
            return
            
        self.is_running = False
        print(f"Agent {self.name} stopped")
        
    def get_capabilities(self) -> list:
        """Get agent capabilities"""
        return self.capabilities
        
    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities


class AgentFactory:
    """Factory for creating and managing agents"""
    
    def __init__(self, runtime: RuntimeManager):
        self.runtime = runtime
        self.agent_types: Dict[str, Type[BaseAgent]] = {}
        self.agents: Dict[str, BaseAgent] = {}
        
    def register_agent_type(self, agent_type: str, agent_class: Type[BaseAgent]):
        """Register an agent type with the factory"""
        self.agent_types[agent_type] = agent_class
        print(f"Agent type '{agent_type}' registered")
        
    async def create_agent(self, name: str, agent_type: str, config: Optional[AgentConfig] = None) -> BaseAgent:
        """Create and register a new agent"""
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        if config is None:
            config = AgentConfig(name=name, agent_type=agent_type)
            
        agent_class = self.agent_types[agent_type]
        agent = agent_class(name, config, self.runtime)
        
        # Register with runtime
        self.runtime.register_agent(name, agent)
        self.agents[name] = agent
        
        # Start the agent
        await agent.start()
        
        return agent
        
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self.agents.get(name)
        
    def get_agents_by_capability(self, capability: str) -> list:
        """Get all agents that have a specific capability"""
        return [
            agent for agent in self.agents.values()
            if agent.has_capability(capability)
        ]
        
    async def stop_all_agents(self):
        """Stop all agents"""
        for agent in self.agents.values():
            await agent.stop()
            
    def list_available_types(self) -> list:
        """List all registered agent types"""
        return list(self.agent_types.keys())
        
    def list_active_agents(self) -> list:
        """List all active agents"""
        return [
            {
                "name": agent.name,
                "type": agent.config.agent_type,
                "running": agent.is_running,
                "capabilities": agent.capabilities
            }
            for agent in self.agents.values()
        ]