"""
Custom Exceptions for google-adk Framework
Provides specific exception types for better error handling and debugging
"""

from typing import Optional, Dict, Any


class GoogleADKError(Exception):
    """Base exception for all google-adk framework errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(GoogleADKError):
    """Raised when there are configuration-related errors"""
    pass


class AgentError(GoogleADKError):
    """Base class for agent-related errors"""
    
    def __init__(self, message: str, agent_name: Optional[str] = None, 
                 error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, details)
        self.agent_name = agent_name
        if agent_name:
            self.details["agent_name"] = agent_name


class AgentNotFoundError(AgentError):
    """Raised when attempting to access a non-existent agent"""
    pass


class AgentAlreadyExistsError(AgentError):
    """Raised when attempting to create an agent that already exists"""
    pass


class AgentStartupError(AgentError):
    """Raised when an agent fails to start properly"""
    pass


class AgentCommunicationError(AgentError):
    """Raised when agent communication fails"""
    pass


class AgentCapabilityError(AgentError):
    """Raised when an agent lacks required capabilities"""
    pass


class MCPError(GoogleADKError):
    """Base class for MCP protocol errors"""
    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails"""
    pass


class MCPProtocolError(MCPError):
    """Raised when MCP protocol violations occur"""
    pass


class MCPTimeoutError(MCPError):
    """Raised when MCP operations timeout"""
    pass


class MCPMessageError(MCPError):
    """Raised when MCP message processing fails"""
    
    def __init__(self, message: str, message_id: Optional[str] = None,
                 message_type: Optional[str] = None, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, details)
        self.message_id = message_id
        self.message_type = message_type
        if message_id:
            self.details["message_id"] = message_id
        if message_type:
            self.details["message_type"] = message_type


class DiscoveryError(GoogleADKError):
    """Base class for discovery service errors"""
    pass


class RegistrationError(DiscoveryError):
    """Raised when agent registration fails"""
    pass


class DiscoveryTimeoutError(DiscoveryError):
    """Raised when discovery operations timeout"""
    pass


class WorkflowError(GoogleADKError):
    """Base class for workflow-related errors"""
    pass


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails"""
    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails"""
    pass


class ToolError(GoogleADKError):
    """Base class for tool-related errors"""
    pass


class ToolNotFoundError(ToolError):
    """Raised when a required tool is not found"""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails"""
    pass


class SecurityError(GoogleADKError):
    """Base class for security-related errors"""
    pass


class AuthenticationError(SecurityError):
    """Raised when authentication fails"""
    pass


class AuthorizationError(SecurityError):
    """Raised when authorization fails"""
    pass


class ValidationError(GoogleADKError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None, error_code: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, details)
        self.field = field
        self.value = value
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class ResourceError(GoogleADKError):
    """Base class for resource-related errors"""
    pass


class ResourceExhaustionError(ResourceError):
    """Raised when system resources are exhausted"""
    pass


class ResourceLeakError(ResourceError):
    """Raised when resource leaks are detected"""
    pass


def handle_exception(logger, operation: str, correlation_id: Optional[str] = None):
    """Decorator for standardized exception handling and logging"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except GoogleADKError as e:
                logger.error_operation(
                    operation, 
                    f"Framework error in {func.__name__}: {e.message}",
                    correlation_id,
                    extra={"error_details": e.to_dict()}
                )
                raise
            except Exception as e:
                logger.error_operation(
                    operation,
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    correlation_id,
                    exc_info=True
                )
                raise GoogleADKError(
                    f"Unexpected error in {operation}",
                    error_code="UNEXPECTED_ERROR",
                    details={"original_error": str(e), "function": func.__name__}
                )
                
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except GoogleADKError as e:
                logger.error_operation(
                    operation,
                    f"Framework error in {func.__name__}: {e.message}",
                    correlation_id,
                    extra={"error_details": e.to_dict()}
                )
                raise
            except Exception as e:
                logger.error_operation(
                    operation,
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    correlation_id,
                    exc_info=True
                )
                raise GoogleADKError(
                    f"Unexpected error in {operation}",
                    error_code="UNEXPECTED_ERROR",
                    details={"original_error": str(e), "function": func.__name__}
                )
                
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator