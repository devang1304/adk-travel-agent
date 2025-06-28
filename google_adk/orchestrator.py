"""
Agent Orchestrator for multi-agent conversations and workflows
"""

import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .logging_config import get_logger
from .exceptions import WorkflowError


class ConsensusType(Enum):
    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"


@dataclass
class ConversationStep:
    agent_name: str
    method: str
    params: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    can_delegate: bool = True
    

@dataclass
class ConsensusRequest:
    question: str
    agents: List[str]
    consensus_type: ConsensusType = ConsensusType.MAJORITY
    timeout: float = 30.0
    
    
class AgentOrchestrator:
    """Orchestrates multi-agent conversations and workflows"""
    
    def __init__(self, agent_factory):
        self.agent_factory = agent_factory
        self.active_workflows: Dict[str, Dict] = {}
        self.agent_state: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("orchestrator")
        
    async def execute_conversation(self, workflow_id: str, steps: List[ConversationStep]) -> Dict[str, Any]:
        """Execute a multi-step agent conversation with error recovery"""
        results = {}
        
        for step in steps:
            # Wait for dependencies
            if step.depends_on:
                await self._wait_for_dependencies(step.depends_on, results)
                
            # Execute step with retry and delegation
            result = await self._execute_step_with_recovery(step, results)
            results[step.agent_name] = result
            
        return results
        
    async def _execute_step_with_recovery(self, step: ConversationStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute step with error handling and recovery"""
        for attempt in range(step.max_retries + 1):
            try:
                agent = self.agent_factory.get_agent(step.agent_name)
                if not agent:
                    if step.can_delegate and attempt < step.max_retries:
                        # Try delegation
                        delegated_agent = await self._find_delegate(step.method)
                        if delegated_agent:
                            agent = delegated_agent
                            self.logger.info(f"Delegating {step.method} to {agent.name}")
                    
                    if not agent:
                        raise WorkflowError(f"Agent {step.agent_name} not found and no delegate available")
                
                result = await agent.execute_task({
                    "method": step.method,
                    "params": step.params,
                    "context": context
                })
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Step failed (attempt {attempt + 1}): {str(e)}")
                if attempt == step.max_retries:
                    raise WorkflowError(f"Step {step.method} failed after {step.max_retries} retries: {str(e)}")
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
        
    async def _wait_for_dependencies(self, deps: List[str], results: Dict) -> None:
        """Wait for dependency completion"""
        while not all(dep in results for dep in deps):
            await asyncio.sleep(0.1)
            
    async def _find_delegate(self, method: str) -> Optional[Any]:
        """Find agent capable of delegated task"""
        for agent in self.agent_factory.agents.values():
            if agent.has_capability(method) and agent.is_running:
                return agent
        return None
        
    async def resolve_consensus(self, request: ConsensusRequest) -> Dict[str, Any]:
        """Resolve consensus among agents"""
        responses = {}
        
        # Collect responses from agents
        tasks = []
        for agent_name in request.agents:
            agent = self.agent_factory.get_agent(agent_name)
            if agent:
                task = agent.execute_task({
                    "method": "consensus_vote",
                    "params": {"question": request.question}
                })
                tasks.append((agent_name, task))
                
        # Wait for responses with timeout
        try:
            for agent_name, task in tasks:
                response = await asyncio.wait_for(task, timeout=request.timeout)
                responses[agent_name] = response
        except asyncio.TimeoutError:
            self.logger.warning(f"Consensus timeout for: {request.question}")
            
        # Calculate consensus
        return self._calculate_consensus(responses, request.consensus_type)
        
    def _calculate_consensus(self, responses: Dict[str, Any], consensus_type: ConsensusType) -> Dict[str, Any]:
        """Calculate consensus from agent responses"""
        votes = [r.get("vote") for r in responses.values() if r.get("vote")]
        
        if consensus_type == ConsensusType.MAJORITY:
            if len(votes) == 0:
                return {"consensus": False, "result": None}
            from collections import Counter
            vote_counts = Counter(votes)
            winner = vote_counts.most_common(1)[0]
            consensus_reached = winner[1] > len(votes) / 2
            return {
                "consensus": consensus_reached,
                "result": winner[0] if consensus_reached else None,
                "votes": dict(vote_counts)
            }
            
        elif consensus_type == ConsensusType.UNANIMOUS:
            if len(votes) == 0:
                return {"consensus": False, "result": None}
            unanimous_vote = votes[0] if all(v == votes[0] for v in votes) else None
            return {
                "consensus": unanimous_vote is not None,
                "result": unanimous_vote,
                "votes": {v: votes.count(v) for v in set(votes)}
            }
            
        return {"consensus": False, "result": None}
        
    async def sync_agent_state(self, agent_names: List[str], state_key: str, state_value: Any) -> None:
        """Synchronize state across agents"""
        for agent_name in agent_names:
            if agent_name not in self.agent_state:
                self.agent_state[agent_name] = {}
            self.agent_state[agent_name][state_key] = state_value
            
        self.logger.info(f"Synced state {state_key} across {len(agent_names)} agents")
        
    def get_agent_state(self, agent_name: str, state_key: str) -> Any:
        """Get synchronized state for agent"""
        return self.agent_state.get(agent_name, {}).get(state_key)