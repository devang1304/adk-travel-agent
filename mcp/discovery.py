"""
Agent Discovery and Registration System
Manages agent discovery, registration, and capability lookup
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from .messages import AgentInfo, AgentCapability, create_notification


@dataclass
class ServiceEndpoint:
    """Service endpoint information"""
    host: str
    port: int
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


class AgentRegistry:
    """Central registry for agent discovery and capabilities"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.endpoints: Dict[str, ServiceEndpoint] = {}
        self.capabilities_index: Dict[str, Set[str]] = {}  # capability -> set of agent names
        self.logger = logging.getLogger("AgentRegistry")
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 60  # seconds
        
    async def start(self):
        """Start the registry and cleanup task"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.logger.info("Agent registry started")
        
    async def stop(self):
        """Stop the registry"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Agent registry stopped")
        
    async def register_agent(self, agent_info: AgentInfo, endpoint: ServiceEndpoint) -> bool:
        """Register an agent with the registry"""
        try:
            agent_name = agent_info.name
            
            # Store agent info
            agent_info.last_seen = datetime.utcnow()
            self.agents[agent_name] = agent_info
            self.endpoints[agent_name] = endpoint
            
            # Update capabilities index
            self._update_capabilities_index(agent_name, agent_info.capabilities)
            
            self.logger.info(f"Agent '{agent_name}' registered with {len(agent_info.capabilities)} capabilities")
            
            # Notify other agents about new registration
            await self._broadcast_agent_event("agent_registered", {
                "agent_name": agent_name,
                "agent_type": agent_info.agent_type,
                "capabilities": [cap.name for cap in agent_info.capabilities]
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error registering agent {agent_info.name}: {e}")
            return False
            
    async def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent from the registry"""
        try:
            if agent_name not in self.agents:
                return False
                
            # Remove from capabilities index
            agent_info = self.agents[agent_name]
            for capability in agent_info.capabilities:
                if capability.name in self.capabilities_index:
                    self.capabilities_index[capability.name].discard(agent_name)
                    if not self.capabilities_index[capability.name]:
                        del self.capabilities_index[capability.name]
                        
            # Remove agent
            del self.agents[agent_name]
            del self.endpoints[agent_name]
            
            self.logger.info(f"Agent '{agent_name}' unregistered")
            
            # Notify other agents
            await self._broadcast_agent_event("agent_unregistered", {
                "agent_name": agent_name
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error unregistering agent {agent_name}: {e}")
            return False
            
    def update_agent_heartbeat(self, agent_name: str) -> bool:
        """Update agent's last seen timestamp"""
        if agent_name in self.agents:
            self.agents[agent_name].last_seen = datetime.utcnow()
            return True
        return False
        
    def get_agent_info(self, agent_name: str) -> Optional[AgentInfo]:
        """Get information about a specific agent"""
        return self.agents.get(agent_name)
        
    def get_agent_endpoint(self, agent_name: str) -> Optional[ServiceEndpoint]:
        """Get endpoint for a specific agent"""
        return self.endpoints.get(agent_name)
        
    def list_agents(self, agent_type: str = None, capability: str = None) -> List[AgentInfo]:
        """List agents, optionally filtered by type or capability"""
        agents = list(self.agents.values())
        
        if agent_type:
            agents = [agent for agent in agents if agent.agent_type == agent_type]
            
        if capability:
            # Filter by capability
            agents_with_capability = self.capabilities_index.get(capability, set())
            agents = [agent for agent in agents if agent.name in agents_with_capability]
            
        return agents
        
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agent names that have a specific capability"""
        return list(self.capabilities_index.get(capability, set()))
        
    def get_all_capabilities(self) -> List[str]:
        """Get all available capabilities across all agents"""
        return list(self.capabilities_index.keys())
        
    def is_agent_available(self, agent_name: str, max_age_seconds: int = 120) -> bool:
        """Check if an agent is considered available based on last heartbeat"""
        agent = self.agents.get(agent_name)
        if not agent:
            return False
            
        age = datetime.utcnow() - agent.last_seen
        return age.total_seconds() <= max_age_seconds
        
    def _update_capabilities_index(self, agent_name: str, capabilities: List[AgentCapability]):
        """Update the capabilities index for an agent"""
        # Remove old capabilities for this agent
        for capability_name, agent_set in self.capabilities_index.items():
            agent_set.discard(agent_name)
            
        # Add new capabilities
        for capability in capabilities:
            if capability.name not in self.capabilities_index:
                self.capabilities_index[capability.name] = set()
            self.capabilities_index[capability.name].add(agent_name)
            
    async def _periodic_cleanup(self):
        """Periodically clean up stale agents"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_stale_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
                
    async def _cleanup_stale_agents(self, max_age_seconds: int = 300):
        """Remove agents that haven't been seen recently"""
        stale_agents = []
        cutoff_time = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        
        for agent_name, agent_info in self.agents.items():
            if agent_info.last_seen < cutoff_time:
                stale_agents.append(agent_name)
                
        for agent_name in stale_agents:
            self.logger.warning(f"Removing stale agent: {agent_name}")
            await self.unregister_agent(agent_name)
            
    async def _broadcast_agent_event(self, event: str, data: Dict):
        """Broadcast agent-related events to other agents"""
        # In a real implementation, this would use the MCP protocol
        # to notify other agents about registry changes
        self.logger.debug(f"Broadcasting event: {event} - {data}")


class DiscoveryClient:
    """Client for agents to interact with the discovery service"""
    
    def __init__(self, agent_name: str, registry: AgentRegistry):
        self.agent_name = agent_name
        self.registry = registry
        self.logger = logging.getLogger(f"Discovery.{agent_name}")
        
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30  # seconds
        
    async def register(self, agent_info: AgentInfo, endpoint: ServiceEndpoint) -> bool:
        """Register this agent with the discovery service"""
        success = await self.registry.register_agent(agent_info, endpoint)
        
        if success:
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        return success
        
    async def unregister(self) -> bool:
        """Unregister this agent from the discovery service"""
        # Stop heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
                
        return await self.registry.unregister_agent(self.agent_name)
        
    async def find_agents_with_capability(self, capability: str) -> List[AgentInfo]:
        """Find agents that have a specific capability"""
        return self.registry.list_agents(capability=capability)
        
    async def get_agent_endpoint(self, agent_name: str) -> Optional[ServiceEndpoint]:
        """Get the endpoint for a specific agent"""
        return self.registry.get_agent_endpoint(agent_name)
        
    async def list_available_capabilities(self) -> List[str]:
        """List all available capabilities in the system"""
        return self.registry.get_all_capabilities()
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain registration"""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                self.registry.update_agent_heartbeat(self.agent_name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat: {e}")


# Global registry instance (in a real system, this might be a separate service)
_global_registry = AgentRegistry()


async def get_registry() -> AgentRegistry:
    """Get the global agent registry"""
    return _global_registry


async def create_discovery_client(agent_name: str) -> DiscoveryClient:
    """Create a discovery client for an agent"""
    registry = await get_registry()
    return DiscoveryClient(agent_name, registry)