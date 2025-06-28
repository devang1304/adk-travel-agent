"""
Data validation and quality checking tools
"""

from .tool_registry import BaseTool
from typing import Dict, Any, List


class DataQualityTool(BaseTool):
    """Data quality validation and scoring"""
    
    @property
    def name(self) -> str:
        return "data_quality"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check data quality"""
        data = params.get("data", {})
        
        quality_score = 0.0
        issues = []
        
        # Check completeness
        required_fields = params.get("required_fields", [])
        missing_fields = [f for f in required_fields if f not in data or not data[f]]
        if missing_fields:
            issues.append(f"Missing fields: {missing_fields}")
            quality_score -= 0.3
        else:
            quality_score += 0.4
            
        # Check data types
        if any(isinstance(v, str) and not v.strip() for v in data.values()):
            issues.append("Empty string values found")
            quality_score -= 0.2
        else:
            quality_score += 0.3
            
        # Check ranges
        budget = data.get("budget")
        if budget and (budget < 100 or budget > 50000):
            issues.append("Budget outside reasonable range")
            quality_score -= 0.2
        else:
            quality_score += 0.3
            
        quality_score = max(0.0, min(1.0, quality_score))
        
        return {
            "quality_score": quality_score,
            "issues": issues,
            "status": "good" if quality_score > 0.7 else "needs_improvement"
        }


class PlanValidatorTool(BaseTool):
    """Travel plan validation"""
    
    @property
    def name(self) -> str:
        return "plan_validator"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate travel plan feasibility"""
        plan = params.get("plan", {})
        
        validation_results = {
            "budget_check": self._validate_budget(plan),
            "schedule_check": self._validate_schedule(plan),
            "location_check": self._validate_locations(plan)
        }
        
        overall_valid = all(r["valid"] for r in validation_results.values())
        
        return {
            "valid": overall_valid,
            "checks": validation_results,
            "confidence": 0.9 if overall_valid else 0.4
        }
        
    def _validate_budget(self, plan: Dict) -> Dict[str, Any]:
        budget = plan.get("budget", 0)
        return {
            "valid": budget > 0,
            "message": "Budget valid" if budget > 0 else "Invalid budget"
        }
        
    def _validate_schedule(self, plan: Dict) -> Dict[str, Any]:
        schedule = plan.get("schedule", [])
        return {
            "valid": len(schedule) > 0,
            "message": "Schedule valid" if schedule else "No schedule provided"
        }
        
    def _validate_locations(self, plan: Dict) -> Dict[str, Any]:
        destination = plan.get("destination")
        return {
            "valid": bool(destination and destination.strip()),
            "message": "Destination valid" if destination else "No destination specified"
        }