"""
Initialize tools for the system
"""

from tools.tool_registry import get_tool_registry
from tools.web_search import WebSearchTool
from tools.validation_tools import ValidationTool


def setup_tools():
    """Register all available tools"""
    registry = get_tool_registry()
    
    # Register tools
    registry.register(WebSearchTool())
    registry.register(ValidationTool())
    
    return registry