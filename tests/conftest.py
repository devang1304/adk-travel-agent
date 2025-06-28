"""
Pytest configuration and fixtures for google-adk tests
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from google_adk.runtime_config import RuntimeConfig, AgentConfig, RuntimeManager
from google_adk.agent_factory import AgentFactory, BaseAgent
from google_adk.logging_config import configure_logging
from google_adk.context_managers import managed_runtime, cleanup_global_resources
from mcp.protocol import MCPProtocol
from mcp.discovery import AgentRegistry, DiscoveryClient
from mcp.messages import AgentInfo, AgentCapability


# Configure test logging
configure_logging(log_level="DEBUG", console_output=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def basic_runtime_config() -> RuntimeConfig:
    """Provide a basic runtime configuration for testing"""
    return RuntimeConfig(
        log_level="DEBUG",
        max_agents=5,
        mcp_port=9999,  # Use different port for tests
        mcp_host="localhost",
        environment="testing",
        debug_mode=True
    )


@pytest.fixture
def agent_config() -> AgentConfig:
    """Provide a basic agent configuration for testing"""
    return AgentConfig(
        name="test_agent",
        agent_type="test",
        max_concurrent_tasks=3,
        timeout_seconds=10,
        retry_attempts=2,
        capabilities=["test_capability", "mock_capability"]
    )


@pytest.fixture
async def runtime_manager(basic_runtime_config: RuntimeConfig) -> AsyncGenerator[RuntimeManager, None]:
    """Provide a managed runtime manager for testing"""
    async with managed_runtime(basic_runtime_config) as runtime:
        yield runtime


@pytest.fixture
async def agent_factory(runtime_manager: RuntimeManager) -> AgentFactory:
    """Provide an agent factory for testing"""
    return AgentFactory(runtime_manager)


@pytest.fixture
def mock_agent_class():
    """Provide a mock agent class for testing"""
    class MockAgent(BaseAgent):
        def __init__(self, name: str, config: AgentConfig, runtime: RuntimeManager):
            super().__init__(name, config, runtime)
            self.initialized = False
            self.messages_processed = []
            self.tasks_executed = []
            
        async def initialize(self) -> None:
            """Mock initialization"""
            await asyncio.sleep(0.01)  # Simulate some async work
            self.initialized = True
            
        async def process_message(self, message: dict) -> dict:
            """Mock message processing"""
            self.messages_processed.append(message)
            return {"status": "processed", "message_id": message.get("id")}
            
        async def execute_task(self, task: dict) -> dict:
            """Mock task execution"""
            self.tasks_executed.append(task)
            return {"status": "completed", "task_id": task.get("id"), "result": "mock_result"}
            
        async def _cleanup(self) -> None:
            """Mock cleanup"""
            self.initialized = False
            
    return MockAgent


@pytest.fixture
async def mock_agent(agent_config: AgentConfig, runtime_manager: RuntimeManager, mock_agent_class) -> BaseAgent:
    """Provide a mock agent instance for testing"""
    return mock_agent_class("test_agent", agent_config, runtime_manager)


@pytest.fixture
async def agent_registry() -> AsyncGenerator[AgentRegistry, None]:
    """Provide an agent registry for testing"""
    registry = AgentRegistry()
    await registry.start()
    yield registry
    await registry.stop()


@pytest.fixture
async def discovery_client(agent_registry: AgentRegistry) -> DiscoveryClient:
    """Provide a discovery client for testing"""
    return DiscoveryClient("test_client", agent_registry)


@pytest.fixture
def sample_agent_info() -> AgentInfo:
    """Provide sample agent info for testing"""
    capabilities = [
        AgentCapability(
            name="test_capability",
            description="A test capability",
            parameters={"param1": "value1"},
            tools_required=["test_tool"]
        )
    ]
    return AgentInfo(
        name="test_agent",
        agent_type="test",
        status="active",
        capabilities=capabilities
    )


@pytest.fixture
async def mcp_protocol() -> AsyncGenerator[MCPProtocol, None]:
    """Provide an MCP protocol instance for testing"""
    protocol = MCPProtocol("test_agent", host="localhost", port=9998)
    try:
        yield protocol
    finally:
        if protocol.is_connected:
            await protocol.stop()


@pytest.fixture
def mock_http_response():
    """Provide a mock HTTP response for testing"""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"status": "ok"})
    mock_response.text = AsyncMock(return_value="OK")
    return mock_response


@pytest.fixture
def mock_aiohttp_session(mock_http_response):
    """Provide a mock aiohttp session for testing"""
    mock_session = AsyncMock()
    mock_session.post = AsyncMock(return_value=mock_http_response)
    mock_session.get = AsyncMock(return_value=mock_http_response)
    mock_session.close = AsyncMock()
    mock_session.closed = False
    return mock_session


@pytest.fixture(autouse=True)
async def cleanup_resources():
    """Automatically cleanup resources after each test"""
    yield
    await cleanup_global_resources()


@pytest.mark.asyncio
async def pytest_configure(config):
    """Configure pytest for async testing"""
    pass


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location"""
    for item in items:
        # Add unit marker to all tests by default
        if "integration" not in item.keywords:
            item.add_marker(pytest.mark.unit)
            
        # Add specific markers based on test file location
        if "mcp" in str(item.fspath):
            item.add_marker(pytest.mark.mcp)
        elif "agent" in str(item.fspath):
            item.add_marker(pytest.mark.agent)
        elif "config" in str(item.fspath):
            item.add_marker(pytest.mark.config)


# Custom assertions for testing
class AssertionHelpers:
    """Helper methods for common test assertions"""
    
    @staticmethod
    def assert_agent_running(agent: BaseAgent) -> None:
        """Assert that an agent is running"""
        assert agent.is_running, f"Agent {agent.name} should be running"
        
    @staticmethod
    def assert_agent_stopped(agent: BaseAgent) -> None:
        """Assert that an agent is stopped"""
        assert not agent.is_running, f"Agent {agent.name} should be stopped"
        
    @staticmethod
    def assert_has_capability(agent: BaseAgent, capability: str) -> None:
        """Assert that an agent has a specific capability"""
        assert agent.has_capability(capability), f"Agent {agent.name} should have capability {capability}"
        
    @staticmethod
    def assert_config_valid(config: RuntimeConfig) -> None:
        """Assert that a runtime config is valid"""
        assert config.max_agents > 0, "max_agents must be positive"
        assert 1024 <= config.mcp_port <= 65535, "mcp_port must be in valid range"
        assert config.environment in {"development", "staging", "production", "testing"}


@pytest.fixture
def assert_helpers() -> AssertionHelpers:
    """Provide assertion helpers for tests"""
    return AssertionHelpers()