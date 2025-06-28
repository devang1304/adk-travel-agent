"""
Tool Registry and Interface
"""

from typing import Dict, Any, Callable
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Base interface for all tools"""
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass


class ToolRegistry:
    """Global tool registry for sharing between agents"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> BaseTool:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_available(self) -> list:
        """List all available tools"""
        return list(self.tools.keys())


# Global registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry"""
    return _tool_registry