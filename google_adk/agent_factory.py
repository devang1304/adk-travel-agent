"""
Agent Factory for google-adk Framework
Handles agent instantiation, registration, and lifecycle management
"""

import asyncio
from typing import Dict, Any, Type, Optional, List
from abc import ABC, abstractmethod

from .runtime_config import RuntimeConfig, AgentConfig, RuntimeManager
from .logging_config import get_logger
from .exceptions import (
    AgentError, AgentNotFoundError, AgentAlreadyExistsError,
    AgentStartupError, ValidationError, ToolError, handle_exception
)
from tools.tool_registry import get_tool_registry


class BaseAgent(ABC):
    """Base class for all google-adk agents"""
    
    def __init__(self, name: str, config: AgentConfig, runtime: RuntimeManager):
        if not name or not name.strip():
            raise ValidationError("Agent name cannot be empty")
        if not isinstance(config, AgentConfig):
            raise ValidationError("Agent config must be AgentConfig instance")
        if not isinstance(runtime, RuntimeManager):
            raise ValidationError("Runtime must be RuntimeManager instance")
            
        self.name = name.strip()
        self.config = config
        self.runtime = runtime
        self.is_running = False
        self.capabilities = config.capabilities.copy()
        self.logger = get_logger(f"agent.{self.name}", agent_name=self.name)
        self.tool_registry = get_tool_registry()
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent
        
        Raises:
            AgentStartupError: If initialization fails
        """
        pass
        
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming messages
        
        Args:
            message: The message to process
            
        Returns:
            Dict containing the response
            
        Raises:
            AgentError: If message processing fails
        """
        pass
        
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific task
        
        Args:
            task: The task to execute
            
        Returns:
            Dict containing the task result
            
        Raises:
            AgentError: If task execution fails
        """
        pass
        
    @handle_exception(get_logger("agent.base"), "agent_start")
    async def start(self) -> None:
        """Start the agent"""
        if self.is_running:
            self.logger.warning("Agent already running, ignoring start request")
            return
            
        self.logger.info_operation(
            "agent_start",
            f"Starting agent",
            extra={
                "agent_name": self.name,
                "agent_type": self.config.agent_type,
                "capabilities": self.capabilities
            }
        )
        
        try:
            await self.initialize()
            self.is_running = True
            
            self.logger.info_operation(
                "agent_start",
                "Agent started successfully",
                extra={"agent_name": self.name, "status": "running"}
            )
            
        except Exception as e:
            self.logger.error_operation(
                "agent_start",
                f"Failed to start agent: {str(e)}",
                extra={"agent_name": self.name},
                exc_info=True
            )
            raise AgentStartupError(f"Failed to start agent {self.name}: {str(e)}", agent_name=self.name)
        
    @handle_exception(get_logger("agent.base"), "agent_stop")
    async def stop(self) -> None:
        """Stop the agent"""
        if not self.is_running:
            self.logger.warning("Agent not running, ignoring stop request")
            return
            
        self.logger.info_operation(
            "agent_stop",
            "Stopping agent",
            extra={"agent_name": self.name}
        )
        
        try:
            await self._cleanup()
            self.is_running = False
            
            self.logger.info_operation(
                "agent_stop",
                "Agent stopped successfully",
                extra={"agent_name": self.name, "status": "stopped"}
            )
            
        except Exception as e:
            self.logger.error_operation(
                "agent_stop",
                f"Error during agent shutdown: {str(e)}",
                extra={"agent_name": self.name},
                exc_info=True
            )
            self.is_running = False
            raise AgentError(f"Error stopping agent {self.name}: {str(e)}", agent_name=self.name)
            
    async def _cleanup(self) -> None:
        """Cleanup resources during shutdown. Override in subclasses if needed."""
        pass
        
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities.copy()
        
    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability"""
        if not capability or not capability.strip():
            return False
        return capability.strip() in self.capabilities
        
    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent"""
        if not capability or not capability.strip():
            raise ValidationError("Capability cannot be empty")
        capability = capability.strip()
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.logger.info_operation(
                "capability_add",
                f"Added capability: {capability}",
                extra={"agent_name": self.name, "capability": capability}
            )
            
    def remove_capability(self, capability: str) -> bool:
        """Remove a capability from the agent"""
        if not capability or not capability.strip():
            return False
        capability = capability.strip()
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            self.logger.info_operation(
                "capability_remove",
                f"Removed capability: {capability}",
                extra={"agent_name": self.name, "capability": capability}
            )
            return True
        return False
        
    async def use_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Use a tool from the registry"""
        tool = self.tool_registry.get(tool_name)
        if not tool:
            raise ToolError(f"Tool {tool_name} not found")
        return await tool.execute(params)


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