"""
google-adk Runtime Configuration
Manages the runtime settings and lifecycle for the multi-agent system
"""

import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()


class AgentConfig(BaseModel):
    """Configuration for individual agents"""
    name: str
    agent_type: str
    max_concurrent_tasks: int = Field(default=5)
    timeout_seconds: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    capabilities: List[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    """Main runtime configuration for google-adk framework"""
    
    # Framework settings
    framework_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")
    
    # Agent settings
    max_agents: int = Field(default=10)
    agent_discovery_timeout: int = Field(default=10)
    
    # MCP settings
    mcp_port: int = Field(default=8888)
    mcp_host: str = Field(default="localhost")
    
    # Environment settings
    environment: str = Field(default="development")
    debug_mode: bool = Field(default=True)
    
    # Agent configurations
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """Load configuration from environment variables"""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_agents=int(os.getenv("MAX_AGENTS", "10")),
            mcp_port=int(os.getenv("MCP_PORT", "8888")),
            mcp_host=os.getenv("MCP_HOST", "localhost"),
            environment=os.getenv("ENVIRONMENT", "development"),
            debug_mode=os.getenv("DEBUG_MODE", "true").lower() == "true"
        )


class RuntimeManager:
    """Manages the google-adk runtime lifecycle"""
    
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.is_running = False
        self.agents: Dict[str, Any] = {}
        
    async def start(self):
        """Start the google-adk runtime"""
        if self.is_running:
            return
            
        print(f"Starting google-adk runtime v{self.config.framework_version}")
        print(f"Environment: {self.config.environment}")
        print(f"MCP Server: {self.config.mcp_host}:{self.config.mcp_port}")
        
        self.is_running = True
        
    async def stop(self):
        """Stop the google-adk runtime"""
        if not self.is_running:
            return
            
        print("Stopping google-adk runtime...")
        
        # Stop all agents
        for agent_name, agent in self.agents.items():
            await self._stop_agent(agent_name, agent)
            
        self.is_running = False
        
    async def _stop_agent(self, name: str, agent: Any):
        """Stop a specific agent"""
        try:
            if hasattr(agent, 'stop'):
                await agent.stop()
            print(f"Agent {name} stopped")
        except Exception as e:
            print(f"Error stopping agent {name}: {e}")
            
    def register_agent(self, name: str, agent: Any):
        """Register an agent with the runtime"""
        self.agents[name] = agent
        print(f"Agent {name} registered")
        
    def get_agent(self, name: str) -> Optional[Any]:
        """Get a registered agent by name"""
        return self.agents.get(name)