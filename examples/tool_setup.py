"""
Initialize tools for the system
"""

from tools.tool_registry import get_tool_registry
from tools.web_search import WebSearchTool
from tools.validation_tools import ValidationTool
from tools.optimization_tools import PlanningOptimizerTool, BudgetOptimizerTool
from tools.quality_tools import DataQualityTool, PlanValidatorTool
from tools.reporting_tools import ReportGeneratorTool, SummaryTool
from tools.composition_tools import ToolChainTool, ToolComposerTool


def setup_tools():
    """Register all available tools"""
    registry = get_tool_registry()
    
    # Core tools
    registry.register(WebSearchTool())
    registry.register(ValidationTool())
    
    # Optimization tools
    registry.register(PlanningOptimizerTool())
    registry.register(BudgetOptimizerTool())
    
    # Quality tools
    registry.register(DataQualityTool())
    registry.register(PlanValidatorTool())
    
    # Reporting tools
    registry.register(ReportGeneratorTool())
    registry.register(SummaryTool())
    
    # Composition tools
    registry.register(ToolChainTool())
    registry.register(ToolComposerTool())
    
    return registry