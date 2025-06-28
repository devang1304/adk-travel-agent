# Multi-Agent Travel Planning System

A production-ready multi-agent AI system built with google-adk framework that demonstrates agent orchestration, MCP (Model Context Protocol) communication, and tool sharing for travel planning scenarios.

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Git (for cloning the repository)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/devang1304/adk-travel-agent.git
   cd adk-travel-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the demo**
   ```bash
   PYTHONPATH=. python examples/workflow_demo.py
   ```

You should see structured JSON logs showing the multi-agent system in action, ending with "Travel plan generated successfully".

## 📋 What This System Does

This system simulates a **travel planning agency** with three AI agents working together:

1. **Research Agent** - Gathers information about destinations
2. **Planning Agent** - Creates itineraries and manages budgets  
3. **Coordinator Agent** - Finalizes plans and coordinates the workflow

The agents communicate through MCP protocol, share tools, vote on decisions, and can delegate tasks to each other.

## 🏗️ System Architecture

```
┌─────────────────────────────────┐
│        google-adk Runtime      │  ← Manages agent lifecycle
│     (Agent Orchestration)       │
└─────────────────┬───────────────┘
                  │
┌─────────────────┴───────────────┐
│         MCP Protocol            │  ← Handles agent communication
│    (Agent Communication)        │
└─────────────────┬───────────────┘
                  │
  ┌───────────────┼───────────────┐
  │               │               │
┌─▼─────────┐   ┌─▼─────────┐   ┌─▼─────────┐
│ Research  │   │ Planning  │   │Coordinator│  ← Three AI agents
│  Agent    │◄──┤  Agent    │◄──┤  Agent    │
└───────────┘   └───────────┘   └───────────┘
  │               │               │
  └───────────────┼───────────────┘
                  │
┌─────────────────▼───────────────┐
│         Shared Tools            │  ← 10 specialized tools
│  (Search, Planning, Validation) │
└─────────────────────────────────┘
```

## 📁 Project Structure

```
requirements-automation-adk/
├── agents/                     # AI Agent implementations
│   ├── research_agent.py      # Information gathering agent
│   ├── planning_agent.py      # Itinerary planning agent
│   └── coordinator_agent.py   # Workflow coordination agent
├── tools/                      # Shared tool implementations
│   ├── web_search.py          # Web research capabilities
│   ├── optimization_tools.py  # Planning and budget optimization
│   ├── quality_tools.py       # Data validation and quality
│   ├── reporting_tools.py     # Report and summary generation
│   └── composition_tools.py   # Tool chaining and composition
├── google_adk/                # Core framework
│   ├── runtime_config.py      # Runtime and configuration
│   ├── agent_factory.py       # Agent creation and management
│   ├── orchestrator.py        # Multi-agent orchestration
│   └── logging_config.py      # Structured logging
├── mcp/                       # MCP protocol implementation
├── workflows/                 # Workflow definitions
├── examples/                  # Usage examples and demos
├── tests/                     # Comprehensive test suite
└── docs/                      # Documentation
```

## 🔧 Core Components Explained

### 1. Agents (`agents/`)

#### Research Agent (`research_agent.py`)
**What it does:** Gathers information about travel destinations
- **Capabilities:** `research_destination`, `weather_lookup`, `consensus_vote`
- **Tools used:** Web search, data validation
- **Key method:** `_research_destination()` - researches destinations and weather

#### Planning Agent (`planning_agent.py`) 
**What it does:** Creates travel itineraries and manages budgets
- **Capabilities:** `create_itinerary`, `optimize_schedule`, `consensus_vote`
- **Tools used:** Budget optimizer, data validator
- **Key method:** `_create_itinerary()` - creates detailed travel plans

#### Coordinator Agent (`coordinator_agent.py`)
**What it does:** Finalizes plans and coordinates between agents
- **Capabilities:** `finalize_plan`, `coordinate_workflow`, `consensus_vote`
- **Tools used:** Report generator, summarizer
- **Key method:** `_finalize_plan()` - combines all agent outputs into final plan

### 2. Tools (`tools/`)

#### Core Tools
- **`web_search.py`** - Simulates web search for destination information
- **`validation_tools.py`** - Validates data quality and plan feasibility

#### Advanced Tools
- **`optimization_tools.py`** - Budget allocation and planning optimization
- **`quality_tools.py`** - Data quality scoring and validation
- **`reporting_tools.py`** - Report generation and summarization
- **`composition_tools.py`** - Tool chaining and parallel execution

#### Tool Registry (`tool_registry.py`)
**What it does:** Central registry for all tools
- **Key class:** `BaseTool` - Interface all tools implement
- **Key function:** `get_tool_registry()` - Global tool access

### 3. Framework (`google_adk/`)

#### Runtime Manager (`runtime_config.py`)
**What it does:** Manages the entire system lifecycle
- **Key class:** `RuntimeManager` - Starts/stops system, manages agents
- **Key methods:** 
  - `start()` - Initializes the runtime
  - `stop()` - Cleanly shuts down
  - `register_agent()` - Adds agents to the system

#### Agent Factory (`agent_factory.py`)
**What it does:** Creates and manages agents
- **Key class:** `BaseAgent` - All agents inherit from this
- **Key class:** `AgentFactory` - Creates agents of different types
- **Key methods:**
  - `register_agent_type()` - Registers new agent types
  - `create_agent()` - Creates and starts agent instances
  - `use_tool()` - Allows agents to use tools

#### Orchestrator (`orchestrator.py`)
**What it does:** Coordinates multi-agent conversations
- **Key class:** `AgentOrchestrator` - Manages agent workflows
- **Key features:**
  - **Consensus voting** - Agents vote on decisions
  - **Delegation** - Failed tasks automatically delegated
  - **State sync** - Shared state across agents
  - **Error recovery** - Retry logic with exponential backoff

### 4. Workflows (`workflows/`)

#### Travel Planning (`travel_planning.py`)
**What it does:** Defines the main travel planning workflow
- **Function:** `create_travel_workflow()` - Creates 3-step workflow
- **Steps:**
  1. Research Agent gathers destination info
  2. Planning Agent creates itinerary (depends on research)
  3. Coordinator Agent finalizes plan (depends on both)

## 🎯 How to Use the System

### Running Examples

#### 1. Basic Workflow Demo
```bash
PYTHONPATH=. python examples/workflow_demo.py
```
**What it does:** Runs complete Paris travel planning workflow for 3 days with $2000 budget

#### 2. Agent Communication Demo
```bash
PYTHONPATH=. python examples/agent_communication.py
```
**What it does:** Demonstrates direct agent-to-agent communication

#### 3. Tool Sharing Demo
```bash
PYTHONPATH=. python examples/tool_sharing.py
```
**What it does:** Shows how agents share and use tools

### Creating Custom Workflows

```python
from google_adk import RuntimeConfig, RuntimeManager, AgentFactory, AgentOrchestrator
from workflows.travel_planning import create_travel_workflow
from examples.tool_setup import setup_tools

async def custom_workflow():
    # Setup tools and runtime
    setup_tools()
    config = RuntimeConfig(environment="development")
    runtime = RuntimeManager(config)
    await runtime.start()
    
    # Create agents
    factory = AgentFactory(runtime)
    orchestrator = AgentOrchestrator(factory)
    
    # Register and create agents
    factory.register_agent_type("research", ResearchAgent)
    await factory.create_agent("researcher", "research")
    
    # Create custom workflow
    workflow = create_travel_workflow("Tokyo", 3000, 5)
    results = await orchestrator.execute_conversation("my_trip", workflow)
    
    await runtime.stop()
    return results
```

## 🛠️ Advanced Features

### 1. Consensus Voting
Agents can vote on decisions using majority, unanimous, or weighted consensus:

```python
from google_adk.orchestrator import ConsensusRequest, ConsensusType

consensus_request = ConsensusRequest(
    question="Should we book this hotel?",
    agents=["research_agent", "planning_agent"],
    consensus_type=ConsensusType.MAJORITY
)
result = await orchestrator.resolve_consensus(consensus_request)
```

### 2. Tool Composition
Chain multiple tools together for complex operations:

```python
# Sequential tool chain
chain_config = {
    "type": "sequential",
    "tools": [
        {"tool": "web_search", "params": {"query": "Paris hotels"}},
        {"tool": "data_quality", "params": {"required_fields": ["price", "rating"]}},
        {"tool": "budget_optimizer", "params": {"budget": 2000}}
    ]
}

result = await tool_chain.execute({"composition": chain_config})
```

### 3. Error Recovery
System automatically retries failed tasks and delegates to capable agents:

```python
from google_adk.orchestrator import ConversationStep

step = ConversationStep(
    agent_name="planning_agent",
    method="create_itinerary",
    params={"budget": 1500, "days": 3},
    max_retries=3,          # Retry up to 3 times
    can_delegate=True       # Allow delegation if agent fails
)
```

## 🧪 Testing

### Run All Tests
```bash
PYTHONPATH=. python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Unit tests only
PYTHONPATH=. python -m pytest tests/test_agents.py -v

# Integration tests only  
PYTHONPATH=. python -m pytest tests/test_integration.py -v

# MCP protocol tests
PYTHONPATH=. python -m pytest tests/test_mcp.py -v
```

### Test Individual Tools
```bash
# Test planning optimizer
PYTHONPATH=. python -c "
import asyncio
from tools.optimization_tools import PlanningOptimizerTool

async def test():
    tool = PlanningOptimizerTool()
    result = await tool.execute({'budget': 2000, 'days': 5})
    print('Result:', result)

asyncio.run(test())
"
```

## 📊 Understanding the Output

When you run the demo, you'll see structured JSON logs like:

```json
{
  "timestamp": "2025-06-28T00:24:00.582672Z",
  "level": "INFO", 
  "logger": "google_adk.runtime",
  "message": "Starting google-adk runtime v0.1.0",
  "operation": "runtime_start"
}
```

**Key log operations to watch for:**
- `runtime_start` - System starting up
- `agent_register` - Agents being registered
- `agent_start` - Individual agents starting
- `capability_add` - Agents gaining new capabilities
- `runtime_stop` - System shutting down cleanly

The final message will be:
```json
{
  "message": "Travel plan generated successfully",
  "plan": { /* Complete travel plan */ }
}
```

## 🚨 Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'google_adk'"**
   ```bash
   # Solution: Use PYTHONPATH
   PYTHONPATH=. python examples/workflow_demo.py
   ```

2. **"Agent not found" errors**
   - Make sure all agent types are registered before creating agents
   - Check that agents are created before running workflows

3. **Tool not found errors**
   - Ensure `setup_tools()` is called before running workflows
   - Check that required tools are imported in `tool_setup.py`

4. **Broken pipe errors in logs**
   - This is normal when using `head` command to limit output
   - The system is working correctly despite the logging errors

### Debug Mode
Set environment variable for verbose logging:
```bash
export LOG_LEVEL=DEBUG
PYTHONPATH=. python examples/workflow_demo.py
```

## 🔧 Configuration

### Environment Variables
- `LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Set runtime environment (development, production, test)

### Runtime Configuration
Modify `google_adk/runtime_config.py` for:
- Agent timeout settings
- MCP protocol configuration  
- Security settings
- Resource limits

## 📈 Production Deployment

For production use:

1. **Install production dependencies**
   ```bash
   pip install -r requirements.txt --production
   ```

2. **Set production environment**
   ```bash
   export ENVIRONMENT=production
   export LOG_LEVEL=INFO
   ```

3. **Run with proper PYTHONPATH**
   ```bash
   PYTHONPATH=/path/to/requirements-automation-adk python examples/workflow_demo.py
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🎯 Next Steps

- Add more specialized agents (booking, activity planning)
- Integrate with real travel APIs
- Add web interface for user interaction
- Implement persistent storage for complex workflows
- Add more sophisticated AI model integrations

---

**Need help?** Check the `docs/` folder for detailed technical documentation or run the examples to see the system in action!