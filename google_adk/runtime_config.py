"""
google-adk Runtime Configuration
Manages the runtime settings and lifecycle for the multi-agent system
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

from .logging_config import get_logger
from .exceptions import (
    ConfigurationError, AgentError, AgentStartupError, 
    ValidationError, handle_exception
)

load_dotenv()


class AgentConfig(BaseModel):
    """Configuration for individual agents"""
    name: str
    agent_type: str
    max_concurrent_tasks: int = Field(default=5, ge=1, le=100)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    capabilities: List[str] = Field(default_factory=list)
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValidationError("Agent name cannot be empty")
        if len(v) > 100:
            raise ValidationError("Agent name too long (max 100 characters)")
        return v.strip()
    
    @validator('agent_type')
    def validate_agent_type(cls, v):
        if not v or not v.strip():
            raise ValidationError("Agent type cannot be empty")
        return v.strip()


class RuntimeConfig(BaseModel):
    """Main runtime configuration for google-adk framework"""
    
    # Framework settings
    framework_version: str = Field(default="0.1.0")
    log_level: str = Field(default="INFO")
    
    # Agent settings
    max_agents: int = Field(default=10, ge=1, le=1000)
    agent_discovery_timeout: int = Field(default=10, ge=1, le=300)
    
    # MCP settings
    mcp_port: int = Field(default=8888, ge=1024, le=65535)
    mcp_host: str = Field(default="localhost")
    
    # Environment settings
    environment: str = Field(default="development")
    debug_mode: bool = Field(default=True)
    
    # Agent configurations
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValidationError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator('environment')
    def validate_environment(cls, v):
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValidationError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v.lower()
    
    @validator('mcp_host')
    def validate_mcp_host(cls, v):
        if not v or not v.strip():
            raise ValidationError("MCP host cannot be empty")
        return v.strip()
    
    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """Load configuration from environment variables"""
        try:
            return cls(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                max_agents=int(os.getenv("MAX_AGENTS", "10")),
                mcp_port=int(os.getenv("MCP_PORT", "8888")),
                mcp_host=os.getenv("MCP_HOST", "localhost"),
                environment=os.getenv("ENVIRONMENT", "development"),
                debug_mode=os.getenv("DEBUG_MODE", "true").lower() == "true"
            )
        except ValueError as e:
            raise ConfigurationError(f"Invalid environment configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from environment: {e}")


class RuntimeManager:
    """Manages the google-adk runtime lifecycle"""
    
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.is_running = False
        self.agents: Dict[str, Any] = {}
        self.logger = get_logger("google_adk.runtime")
        
        # Configure logging based on config
        from .logging_config import configure_logging
        configure_logging(
            log_level=config.log_level,
            log_format="structured" if not config.debug_mode else "text"
        )
        
    @handle_exception(get_logger("google_adk.runtime"), "runtime_start")
    async def start(self) -> None:
        """Start the google-adk runtime"""
        if self.is_running:
            self.logger.warning("Runtime already running, ignoring start request")
            return
            
        self.logger.info_operation(
            "runtime_start",
            f"Starting google-adk runtime v{self.config.framework_version}",
            extra={
                "framework_version": self.config.framework_version,
                "environment": self.config.environment,
                "mcp_host": self.config.mcp_host,
                "mcp_port": self.config.mcp_port,
                "max_agents": self.config.max_agents
            }
        )
        
        try:
            # Initialize runtime components
            await self._initialize_runtime()
            self.is_running = True
            
            self.logger.info_operation(
                "runtime_start",
                "Runtime started successfully",
                extra={"status": "running"}
            )
            
        except Exception as e:
            self.logger.error_operation(
                "runtime_start",
                f"Failed to start runtime: {str(e)}",
                exc_info=True
            )
            raise AgentStartupError(f"Runtime startup failed: {str(e)}")
        
    @handle_exception(get_logger("google_adk.runtime"), "runtime_stop")
    async def stop(self) -> None:
        """Stop the google-adk runtime"""
        if not self.is_running:
            self.logger.warning("Runtime not running, ignoring stop request")
            return
            
        self.logger.info_operation("runtime_stop", "Stopping google-adk runtime...")
        
        try:
            # Stop all agents with timeout
            stop_tasks = []
            for agent_name, agent in self.agents.items():
                task = asyncio.create_task(self._stop_agent(agent_name, agent))
                stop_tasks.append(task)
                
            if stop_tasks:
                # Wait for all agents to stop with timeout
                await asyncio.wait_for(
                    asyncio.gather(*stop_tasks, return_exceptions=True),
                    timeout=30.0
                )
                
            self.is_running = False
            self.logger.info_operation(
                "runtime_stop", 
                "Runtime stopped successfully",
                extra={"agents_stopped": len(self.agents)}
            )
            
        except asyncio.TimeoutError:
            self.logger.error_operation(
                "runtime_stop",
                "Timeout while stopping agents, forcing shutdown"
            )
            self.is_running = False
        except Exception as e:
            self.logger.error_operation(
                "runtime_stop",
                f"Error during runtime shutdown: {str(e)}",
                exc_info=True
            )
            self.is_running = False
            raise
        
    async def _initialize_runtime(self) -> None:
        """Initialize runtime components"""
        # Future: Initialize MCP server, discovery service, etc.
        pass
        
    async def _stop_agent(self, name: str, agent: Any) -> None:
        """Stop a specific agent with proper error handling"""
        try:
            if hasattr(agent, 'stop'):
                await asyncio.wait_for(agent.stop(), timeout=10.0)
                
            self.logger.info_operation(
                "agent_stop",
                f"Agent stopped successfully",
                extra={"agent_name": name}
            )
            
        except asyncio.TimeoutError:
            self.logger.error_operation(
                "agent_stop",
                f"Timeout stopping agent",
                extra={"agent_name": name}
            )
            raise AgentError(f"Timeout stopping agent {name}")
            
        except Exception as e:
            self.logger.error_operation(
                "agent_stop",
                f"Error stopping agent: {str(e)}",
                extra={"agent_name": name},
                exc_info=True
            )
            raise AgentError(f"Failed to stop agent {name}: {str(e)}", agent_name=name)
            
    def register_agent(self, name: str, agent: Any) -> None:
        """Register an agent with the runtime"""
        if not name or not name.strip():
            raise ValidationError("Agent name cannot be empty")
            
        if name in self.agents:
            raise AgentError(f"Agent {name} already registered", agent_name=name)
            
        if len(self.agents) >= self.config.max_agents:
            raise AgentError(
                f"Maximum number of agents reached ({self.config.max_agents})",
                agent_name=name
            )
            
        self.agents[name] = agent
        self.logger.info_operation(
            "agent_register",
            f"Agent registered successfully",
            extra={
                "agent_name": name,
                "total_agents": len(self.agents),
                "max_agents": self.config.max_agents
            }
        )
        
    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent from the runtime"""
        if name not in self.agents:
            self.logger.warning(f"Attempted to unregister non-existent agent: {name}")
            return False
            
        del self.agents[name]
        self.logger.info_operation(
            "agent_unregister",
            f"Agent unregistered successfully",
            extra={
                "agent_name": name,
                "remaining_agents": len(self.agents)
            }
        )
        return True
        
    def get_agent(self, name: str) -> Optional[Any]:
        """Get a registered agent by name"""
        return self.agents.get(name)
        
    def list_agents(self) -> Dict[str, Any]:
        """List all registered agents"""
        return dict(self.agents)
        
    def get_runtime_stats(self) -> Dict[str, Any]:
        """Get runtime statistics"""
        return {
            "is_running": self.is_running,
            "total_agents": len(self.agents),
            "max_agents": self.config.max_agents,
            "environment": self.config.environment,
            "framework_version": self.config.framework_version,
            "agent_names": list(self.agents.keys())
        }