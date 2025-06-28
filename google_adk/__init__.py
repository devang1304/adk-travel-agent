"""
google-adk Configuration Package
Main entry point for the google-adk framework components
"""

from .runtime_config import RuntimeConfig, AgentConfig, RuntimeManager
from .agent_factory import BaseAgent, AgentFactory
from .logging_config import configure_logging, get_logger
from .exceptions import GoogleADKError, AgentError, MCPError, ValidationError
from .context_managers import (
    managed_runtime, managed_http_session, managed_agent,
    cleanup_global_resources
)
from .security import SecurityConfig, create_security_middleware
from .orchestrator import AgentOrchestrator, ConversationStep

__version__ = "0.1.0"

__all__ = [
    # Core runtime
    "RuntimeConfig",
    "AgentConfig", 
    "RuntimeManager",
    
    # Agent system
    "BaseAgent",
    "AgentFactory",
    
    # Logging
    "configure_logging",
    "get_logger",
    
    # Exceptions
    "GoogleADKError",
    "AgentError",
    "MCPError", 
    "ValidationError",
    
    # Context managers
    "managed_runtime",
    "managed_http_session",
    "managed_agent",
    "cleanup_global_resources",
    
    # Security
    "SecurityConfig",
    "create_security_middleware",
    
    # Orchestration
    "AgentOrchestrator",
    "ConversationStep",
    
    # Metadata
    "__version__"
]