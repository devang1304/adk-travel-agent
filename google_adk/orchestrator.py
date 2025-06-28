"""
Agent Orchestrator for multi-agent conversations and workflows
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .logging_config import get_logger
from .exceptions import WorkflowError


@dataclass
class ConversationStep:
    agent_name: str
    method: str
    params: Dict[str, Any]
    depends_on: List[str] = None
    
    
class AgentOrchestrator:
    """Orchestrates multi-agent conversations and workflows"""
    
    def __init__(self, agent_factory):
        self.agent_factory = agent_factory
        self.active_workflows: Dict[str, Dict] = {}
        self.logger = get_logger("orchestrator")
        
    async def execute_conversation(self, workflow_id: str, steps: List[ConversationStep]) -> Dict[str, Any]:
        """Execute a multi-step agent conversation"""
        results = {}
        
        for step in steps:
            # Wait for dependencies
            if step.depends_on:
                await self._wait_for_dependencies(step.depends_on, results)
                
            # Execute step
            agent = self.agent_factory.get_agent(step.agent_name)
            if not agent:
                raise WorkflowError(f"Agent {step.agent_name} not found")
                
            result = await agent.execute_task({
                "method": step.method,
                "params": step.params,
                "context": results
            })
            
            results[step.agent_name] = result
            
        return results
        
    async def _wait_for_dependencies(self, deps: List[str], results: Dict) -> None:
        """Wait for dependency completion"""
        while not all(dep in results for dep in deps):
            await asyncio.sleep(0.1)