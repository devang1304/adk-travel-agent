"""
Tool composition and chaining capabilities
"""

from .tool_registry import BaseTool, get_tool_registry
from typing import Dict, Any, List
import asyncio


class ToolChainTool(BaseTool):
    """Chain multiple tools together"""
    
    @property
    def name(self) -> str:
        return "tool_chain"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a chain of tools"""
        chain = params.get("chain", [])
        initial_data = params.get("data", {})
        
        registry = get_tool_registry()
        results = {"initial_data": initial_data}
        current_data = initial_data
        
        for step in chain:
            tool_name = step.get("tool")
            tool_params = step.get("params", {})
            
            # Merge current data with step params
            merged_params = {**tool_params, "data": current_data}
            
            tool = registry.get(tool_name)
            if tool:
                result = await tool.execute(merged_params)
                results[f"step_{tool_name}"] = result
                current_data = result
            else:
                results[f"error_{tool_name}"] = f"Tool {tool_name} not found"
                
        return {"chain_results": results, "final_data": current_data}


class ToolComposerTool(BaseTool):
    """Compose tools in parallel or sequence"""
    
    @property
    def name(self) -> str:
        return "tool_composer"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compose multiple tools"""
        composition = params.get("composition", {})
        execution_type = composition.get("type", "parallel")  # parallel or sequential
        tools_config = composition.get("tools", [])
        shared_data = params.get("data", {})
        
        registry = get_tool_registry()
        
        if execution_type == "parallel":
            return await self._execute_parallel(tools_config, shared_data, registry)
        else:
            return await self._execute_sequential(tools_config, shared_data, registry)
            
    async def _execute_parallel(self, tools_config: List, shared_data: Dict, registry) -> Dict[str, Any]:
        """Execute tools in parallel"""
        tasks = []
        
        for config in tools_config:
            tool_name = config.get("tool")
            tool_params = {**config.get("params", {}), "data": shared_data}
            
            tool = registry.get(tool_name)
            if tool:
                tasks.append((tool_name, tool.execute(tool_params)))
                
        results = {}
        if tasks:
            completed = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            for i, (tool_name, _) in enumerate(tasks):
                results[tool_name] = completed[i] if not isinstance(completed[i], Exception) else str(completed[i])
                
        return {"execution_type": "parallel", "results": results}
        
    async def _execute_sequential(self, tools_config: List, shared_data: Dict, registry) -> Dict[str, Any]:
        """Execute tools sequentially"""
        results = {}
        current_data = shared_data
        
        for config in tools_config:
            tool_name = config.get("tool")
            tool_params = {**config.get("params", {}), "data": current_data}
            
            tool = registry.get(tool_name)
            if tool:
                result = await tool.execute(tool_params)
                results[tool_name] = result
                # Pass result to next tool
                current_data = {**current_data, **result}
                
        return {"execution_type": "sequential", "results": results}