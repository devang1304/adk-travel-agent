"""
Async Context Managers for google-adk Framework
Provides proper resource management and cleanup patterns
"""

import asyncio
import aiohttp.web
from typing import Optional, AsyncGenerator, Dict, Any, List
from contextlib import asynccontextmanager
import logging

from .runtime_config import RuntimeManager, RuntimeConfig
from .logging_config import get_logger
from .exceptions import GoogleADKError, ResourceError, ResourceLeakError


class ResourceTracker:
    """Tracks and manages system resources"""
    
    def __init__(self):
        self.active_sessions: List[aiohttp.ClientSession] = []
        self.active_servers: List[Any] = []
        self.active_tasks: List[asyncio.Task] = []
        self.logger = get_logger("resource_tracker")
        
    def track_session(self, session: aiohttp.ClientSession) -> None:
        """Track an aiohttp session for cleanup"""
        self.active_sessions.append(session)
        
    def track_server(self, server: Any) -> None:
        """Track a server for cleanup"""
        self.active_servers.append(server)
        
    def track_task(self, task: asyncio.Task) -> None:
        """Track an async task for cleanup"""
        self.active_tasks.append(task)
        
    async def cleanup_all(self) -> None:
        """Clean up all tracked resources"""
        errors = []
        
        # Cancel and cleanup tasks
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    errors.append(f"Task cleanup error: {e}")
                    
        # Close HTTP sessions
        for session in self.active_sessions:
            try:
                if not session.closed:
                    await session.close()
            except Exception as e:
                errors.append(f"Session cleanup error: {e}")
                
        # Stop servers
        for server in self.active_servers:
            try:
                if hasattr(server, 'close'):
                    await server.close()
                elif hasattr(server, 'stop'):
                    await server.stop()
            except Exception as e:
                errors.append(f"Server cleanup error: {e}")
                
        if errors:
            self.logger.warning(f"Resource cleanup errors: {errors}")
            raise ResourceLeakError(f"Failed to clean up some resources: {errors}")
            
        self.active_sessions.clear()
        self.active_servers.clear()
        self.active_tasks.clear()


# Global resource tracker
_resource_tracker = ResourceTracker()


@asynccontextmanager
async def managed_runtime(config: RuntimeConfig) -> AsyncGenerator[RuntimeManager, None]:
    """Context manager for RuntimeManager with proper cleanup"""
    runtime = RuntimeManager(config)
    
    try:
        await runtime.start()
        yield runtime
    finally:
        try:
            await runtime.stop()
        except Exception as e:
            logging.getLogger("managed_runtime").error(f"Error stopping runtime: {e}")


@asynccontextmanager
async def managed_http_session(
    timeout: Optional[aiohttp.ClientTimeout] = None,
    connector_limit: int = 100,
    **kwargs
) -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Context manager for aiohttp ClientSession with proper cleanup"""
    
    if timeout is None:
        timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)
        
    connector = aiohttp.TCPConnector(
        limit=connector_limit,
        limit_per_host=20,
        ttl_dns_cache=300,
        use_dns_cache=True,
        keepalive_timeout=30
    )
    
    session = aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        **kwargs
    )
    
    _resource_tracker.track_session(session)
    
    try:
        yield session
    finally:
        try:
            if not session.closed:
                await session.close()
        except Exception as e:
            logging.getLogger("managed_http_session").error(f"Error closing session: {e}")


@asynccontextmanager
async def managed_mcp_server(
    host: str = "localhost",
    port: int = 8888
) -> AsyncGenerator[aiohttp.web.Application, None]:
    """Context manager for MCP server with proper cleanup"""
    
    app = aiohttp.web.Application()
    runner = aiohttp.web.AppRunner(app)
    
    try:
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, host, port)
        await site.start()
        
        _resource_tracker.track_server(runner)
        
        yield app
        
    finally:
        try:
            await runner.cleanup()
        except Exception as e:
            logging.getLogger("managed_mcp_server").error(f"Error cleaning up server: {e}")


@asynccontextmanager
async def managed_task_group() -> AsyncGenerator[List[asyncio.Task], None]:
    """Context manager for managing a group of async tasks"""
    
    tasks: List[asyncio.Task] = []
    
    try:
        yield tasks
    finally:
        # Cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()
                
        # Wait for all tasks to complete or be cancelled
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logging.getLogger("managed_task_group").error(f"Error in task group cleanup: {e}")


@asynccontextmanager
async def timeout_context(timeout_seconds: float) -> AsyncGenerator[None, None]:
    """Context manager for timeout handling"""
    
    try:
        async with asyncio.timeout(timeout_seconds):
            yield
    except asyncio.TimeoutError:
        raise GoogleADKError(
            f"Operation timed out after {timeout_seconds} seconds",
            error_code="TIMEOUT_ERROR"
        )


class AgentLifecycleManager:
    """Context manager for agent lifecycle with proper resource management"""
    
    def __init__(self, agent):
        self.agent = agent
        self.logger = get_logger(f"lifecycle.{agent.name}")
        
    async def __aenter__(self):
        """Start the agent and return it"""
        try:
            await self.agent.start()
            return self.agent
        except Exception as e:
            self.logger.error(f"Failed to start agent {self.agent.name}: {e}")
            raise
            
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop the agent and handle any exceptions"""
        try:
            await self.agent.stop()
        except Exception as e:
            self.logger.error(f"Error stopping agent {self.agent.name}: {e}")
            
        # Log if we're exiting due to an exception
        if exc_type is not None:
            self.logger.error(
                f"Agent {self.agent.name} context exiting due to {exc_type.__name__}: {exc_val}"
            )


def managed_agent(agent):
    """Create a managed agent context"""
    return AgentLifecycleManager(agent)


async def cleanup_global_resources() -> None:
    """Clean up all globally tracked resources"""
    await _resource_tracker.cleanup_all()


# Decorator for automatic resource cleanup
def with_resource_cleanup(func):
    """Decorator that ensures resource cleanup after function execution"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        finally:
            # Check for any leaked resources and log warnings
            if _resource_tracker.active_sessions:
                logging.getLogger("resource_cleanup").warning(
                    f"Found {len(_resource_tracker.active_sessions)} unclosed HTTP sessions"
                )
            if _resource_tracker.active_tasks:
                logging.getLogger("resource_cleanup").warning(
                    f"Found {len(_resource_tracker.active_tasks)} unfinished tasks"
                )
    return wrapper