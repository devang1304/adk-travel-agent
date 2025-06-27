"""
MCP Message Types and Schemas
Defines the message structures for Model Context Protocol communication
"""

from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


class MessageType(str, Enum):
    """Types of MCP messages"""
    REQUEST = "request"
    RESPONSE = "response" 
    NOTIFICATION = "notification"
    ERROR = "error"


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MCPMessage(BaseModel):
    """Base MCP message structure"""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender: str
    recipient: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    content: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None


class RequestMessage(MCPMessage):
    """Request message for asking agents to perform tasks"""
    
    type: MessageType = MessageType.REQUEST
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    expects_response: bool = True
    timeout_seconds: int = 30


class ResponseMessage(MCPMessage):
    """Response message for replying to requests"""
    
    type: MessageType = MessageType.RESPONSE
    request_id: str
    success: bool = True
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NotificationMessage(MCPMessage):
    """Notification message for broadcasting information"""
    
    type: MessageType = MessageType.NOTIFICATION
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)


class ErrorMessage(MCPMessage):
    """Error message for reporting failures"""
    
    type: MessageType = MessageType.ERROR
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class AgentCapability(BaseModel):
    """Represents an agent capability"""
    
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    tools_required: List[str] = Field(default_factory=list)


class AgentInfo(BaseModel):
    """Information about an agent"""
    
    name: str
    agent_type: str
    status: str = "active"
    capabilities: List[AgentCapability] = Field(default_factory=list)
    endpoint: Optional[str] = None
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class ToolRequest(BaseModel):
    """Request to execute a tool"""
    
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    priority: MessagePriority = MessagePriority.NORMAL


class ToolResponse(BaseModel):
    """Response from tool execution"""
    
    tool_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class WorkflowStep(BaseModel):
    """A step in a multi-agent workflow"""
    
    step_id: str
    agent_name: str
    method: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    timeout_seconds: int = 30


class WorkflowDefinition(BaseModel):
    """Definition of a multi-agent workflow"""
    
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: datetime = Field(default_factory=datetime.utcnow)


def create_request(sender: str, recipient: str, method: str, params: Dict[str, Any] = None) -> RequestMessage:
    """Helper function to create a request message"""
    return RequestMessage(
        sender=sender,
        recipient=recipient,
        method=method,
        params=params or {},
        content={"method": method, "params": params or {}}
    )


def create_response(request: RequestMessage, success: bool = True, result: Dict[str, Any] = None, error: str = None) -> ResponseMessage:
    """Helper function to create a response message"""
    return ResponseMessage(
        sender=request.recipient or "unknown",
        recipient=request.sender,
        request_id=request.id,
        success=success,
        result=result,
        error=error,
        content={"result": result, "error": error},
        correlation_id=request.id
    )


def create_notification(sender: str, event: str, data: Dict[str, Any] = None) -> NotificationMessage:
    """Helper function to create a notification message"""
    return NotificationMessage(
        sender=sender,
        event=event,
        data=data or {},
        content={"event": event, "data": data or {}}
    )