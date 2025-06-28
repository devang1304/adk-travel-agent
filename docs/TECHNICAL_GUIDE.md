# Technical Guide - Multi-Agent Travel Planning System

This guide provides deep technical details for developers who want to understand or extend the system.

## 🏛️ Architecture Deep Dive

### Agent Lifecycle Management

```python
# Agent Creation Flow
RuntimeManager.start() 
  ↓
AgentFactory.register_agent_type("research", ResearchAgent)
  ↓  
AgentFactory.create_agent("research_agent", "research")
  ↓
BaseAgent.__init__() → BaseAgent.start() → ResearchAgent.initialize()
  ↓
Agent registered and running
```

### MCP Protocol Implementation

The Model Context Protocol (MCP) handles all inter-agent communication:

```python
# Message Flow
Agent A → MCPProtocol.send_message() → Agent B
Agent B → MCPProtocol.send_response() → Agent A
```

**Message Types:**
- `Request` - Agent requesting action from another agent
- `Response` - Response to a request
- `Notification` - Broadcast message to multiple agents
- `Error` - Error responses with details

### Tool Registry Pattern

```python
# Tool Registration Flow
setup_tools()
  ↓
ToolRegistry.register(WebSearchTool())
  ↓
Agent.use_tool("web_search", params)
  ↓
ToolRegistry.get("web_search").execute(params)
```

## 🔧 Component Details

### BaseAgent Class (`google_adk/agent_factory.py`)

**Core Interface:**
```python
class BaseAgent(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Agent-specific initialization"""
        
    @abstractmethod 
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming messages"""
        
    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific tasks"""
```

**Key Methods:**
- `start()` - Starts agent with error handling and logging
- `stop()` - Cleanly shuts down agent
- `add_capability()/remove_capability()` - Manages agent capabilities
- `use_tool()` - Accesses tools from registry

### AgentOrchestrator Class (`google_adk/orchestrator.py`)

**Advanced Features:**

#### 1. Consensus Mechanisms
```python
class ConsensusType(Enum):
    MAJORITY = "majority"      # > 50% agreement
    UNANIMOUS = "unanimous"    # 100% agreement  
    WEIGHTED = "weighted"      # Weighted by confidence scores
```

#### 2. Error Recovery System
```python
async def _execute_step_with_recovery(self, step, context):
    for attempt in range(step.max_retries + 1):
        try:
            # Try executing on primary agent
            result = await agent.execute_task(task)
            return result
        except Exception as e:
            if step.can_delegate and attempt < step.max_retries:
                # Find capable delegate
                delegate = await self._find_delegate(step.method)
                if delegate:
                    agent = delegate
            # Exponential backoff
            await asyncio.sleep(1.0 * (attempt + 1))
```

#### 3. State Synchronization
```python
async def sync_agent_state(self, agent_names: List[str], key: str, value: Any):
    """Synchronizes state across multiple agents"""
    for agent_name in agent_names:
        self.agent_state[agent_name][key] = value
```

### Tool Architecture

#### BaseTool Interface
```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier"""
        
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with parameters"""
```

#### Tool Composition
```python
# Sequential Execution
tools = [tool1, tool2, tool3]
data = initial_data
for tool in tools:
    data = await tool.execute({"data": data, **tool_params})

# Parallel Execution  
tasks = [tool.execute(params) for tool in tools]
results = await asyncio.gather(*tasks)
```

## 🔍 Detailed Module Breakdown

### 1. Runtime Configuration (`google_adk/runtime_config.py`)

**Key Classes:**
```python
@dataclass
class RuntimeConfig:
    environment: str = "development"
    log_level: str = "INFO" 
    mcp_host: str = "localhost"
    mcp_port: int = 8888
    max_agents: int = 50
    agent_timeout: float = 30.0

@dataclass  
class AgentConfig:
    name: str
    agent_type: str
    capabilities: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: float = 30.0
```

**RuntimeManager Methods:**
- `start()` - Initializes MCP server, agent registry, logging
- `stop()` - Graceful shutdown with agent cleanup
- `register_agent()` - Adds agent to runtime registry
- `get_agent()` - Retrieves agent by name
- `health_check()` - System health monitoring

### 2. Logging System (`google_adk/logging_config.py`)

**Structured Logging:**
```python
class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        return json.dumps(log_data)
```

**Operation Logging:**
```python
# Usage in agents
self.logger.info_operation(
    "agent_start",
    "Starting agent", 
    extra={"agent_name": self.name}
)
```

### 3. Exception Handling (`google_adk/exceptions.py`)

**Custom Exceptions:**
```python
class GoogleADKError(Exception):
    """Base exception for google-adk framework"""

class AgentError(GoogleADKError):
    """Agent-specific errors"""
    
class WorkflowError(GoogleADKError):
    """Workflow execution errors"""
    
class ToolError(GoogleADKError):
    """Tool execution errors"""
```

**Decorator for Error Handling:**
```python
@handle_exception(logger, "operation_name")
async def risky_operation():
    # Automatically logs errors and re-raises with context
    pass
```

### 4. Security Layer (`google_adk/security.py`)

**Security Middleware:**
```python
class SecurityMiddleware:
    async def authenticate_request(self, request):
        """JWT/API key authentication"""
        
    async def authorize_action(self, agent, action):
        """Role-based access control"""
        
    async def sanitize_input(self, data):
        """Input validation and sanitization"""
```

## 🧪 Testing Architecture

### Test Structure
```
tests/
├── conftest.py           # Pytest fixtures and configuration
├── test_agents.py        # Unit tests for agents
├── test_integration.py   # Integration and workflow tests  
├── test_mcp.py          # MCP protocol tests
└── test_workflows.py     # Workflow-specific tests
```

### Key Test Fixtures
```python
@pytest.fixture
async def runtime_setup():
    """Complete system setup for testing"""
    config = RuntimeConfig(environment="test")
    runtime = RuntimeManager(config)
    await runtime.start()
    factory = AgentFactory(runtime) 
    yield factory
    await runtime.stop()
```

### Testing Patterns

#### Unit Testing Agents
```python
async def test_research_agent_capabilities():
    agent = ResearchAgent("test", config, runtime)
    await agent.start()
    
    assert agent.has_capability("research_destination")
    assert agent.has_capability("consensus_vote")
    
    task = {"method": "research_destination", "params": {"destination": "Paris"}}
    result = await agent.execute_task(task)
    
    assert "destination" in result
    assert result["destination"] == "Paris"
```

#### Integration Testing
```python
async def test_full_workflow():
    # Setup complete system
    workflow = create_travel_workflow("Barcelona", 2500, 4)
    results = await orchestrator.execute_conversation("test", workflow)
    
    # Verify all agents participated
    assert "research_agent" in results
    assert "planning_agent" in results 
    assert "coordinator_agent" in results
    
    # Verify final plan structure
    final_plan = results["coordinator_agent"]["final_plan"]
    assert final_plan["destination"] == "Barcelona"
```

## 🚀 Performance Considerations

### Async Patterns
```python
# Good: Concurrent agent operations
tasks = []
for agent_name in agent_names:
    task = agent.execute_task(task_config)
    tasks.append(task)
results = await asyncio.gather(*tasks)

# Bad: Sequential operations
results = []
for agent_name in agent_names:
    result = await agent.execute_task(task_config) 
    results.append(result)
```

### Memory Management
```python
# Context managers for resource cleanup
async with managed_agent(agent) as running_agent:
    result = await running_agent.execute_task(task)
# Agent automatically stopped and cleaned up
```

### Connection Pooling
```python
# MCP protocol uses connection pooling
class MCPProtocol:
    def __init__(self):
        self.connection_pool = asyncio.Queue(maxsize=10)
        self.active_connections = set()
```

## 🔧 Extension Points

### Adding New Agent Types
```python
class BookingAgent(BaseAgent):
    async def initialize(self):
        self.add_capability("book_hotel")
        self.add_capability("book_flight")
        
    async def execute_task(self, task):
        method = task.get("method")
        if method == "book_hotel":
            return await self._book_hotel(task["params"])
        # ...

# Register with factory
factory.register_agent_type("booking", BookingAgent)
```

### Adding New Tools
```python
class FlightSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "flight_search"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implement flight search logic
        return {"flights": search_results}

# Register with registry
registry.register(FlightSearchTool())
```

### Custom Workflows
```python
def create_booking_workflow(destination: str, dates: tuple) -> List[ConversationStep]:
    return [
        ConversationStep(
            agent_name="research_agent",
            method="research_destination", 
            params={"destination": destination}
        ),
        ConversationStep(
            agent_name="booking_agent",
            method="book_flight",
            params={"destination": destination, "dates": dates},
            depends_on=["research_agent"]
        )
    ]
```

## 📊 Monitoring and Observability

### Metrics Collection
```python
# Built-in metrics
runtime.get_metrics() # Returns:
{
    "active_agents": 3,
    "completed_workflows": 15,
    "average_response_time": 1.2,
    "error_rate": 0.02
}
```

### Health Checks
```python
async def health_check():
    status = await runtime.health_check()
    return {
        "status": "healthy" if status["healthy"] else "degraded",
        "agents": status["agent_count"], 
        "uptime": status["uptime_seconds"]
    }
```

### Tracing
```python
# Correlation IDs for request tracing
logger.info_operation(
    "workflow_start",
    "Starting workflow",
    correlation_id="wf-123-abc",
    extra={"workflow_type": "travel_planning"}
)
```

## 🔐 Security Best Practices

### Input Validation
```python
# All agent inputs validated
def validate_task_input(task: Dict[str, Any]):
    if "method" not in task:
        raise ValidationError("Task must specify method")
    
    method = task["method"] 
    if not isinstance(method, str) or not method.strip():
        raise ValidationError("Method must be non-empty string")
```

### Secure Tool Access
```python
# Tools access controlled by capabilities
async def use_tool(self, tool_name: str, params: Dict[str, Any]):
    if not self.has_capability(f"use_{tool_name}"):
        raise SecurityError(f"Agent lacks permission for tool: {tool_name}")
    
    tool = self.tool_registry.get(tool_name)
    return await tool.execute(params)
```

### Audit Logging
```python
# All security events logged
self.logger.security_event(
    "tool_access",
    f"Agent {self.name} accessed tool {tool_name}",
    extra={"agent": self.name, "tool": tool_name, "authorized": True}
)
```

This technical guide provides the foundation for understanding, extending, and maintaining the multi-agent travel planning system.