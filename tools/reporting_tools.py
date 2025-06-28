"""
Reporting and summary generation tools
"""

from .tool_registry import BaseTool
from typing import Dict, Any, List
import json


class ReportGeneratorTool(BaseTool):
    """Generate comprehensive reports"""
    
    @property
    def name(self) -> str:
        return "report_generator"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate travel plan report"""
        plan_data = params.get("plan_data", {})
        format_type = params.get("format", "summary")
        
        if format_type == "detailed":
            return self._detailed_report(plan_data)
        else:
            return self._summary_report(plan_data)
            
    def _summary_report(self, data: Dict) -> Dict[str, Any]:
        """Generate summary report"""
        return {
            "report_type": "summary",
            "destination": data.get("destination", "Unknown"),
            "total_budget": data.get("budget", 0),
            "duration": data.get("days", 0),
            "key_highlights": [
                f"Budget: ${data.get('budget', 0)}",
                f"Duration: {data.get('days', 0)} days",
                f"Activities: {len(data.get('activities', []))}"
            ],
            "status": "Ready for travel"
        }
        
    def _detailed_report(self, data: Dict) -> Dict[str, Any]:
        """Generate detailed report"""
        return {
            "report_type": "detailed",
            "executive_summary": self._summary_report(data),
            "budget_breakdown": data.get("budget_allocation", {}),
            "daily_schedule": data.get("schedule", []),
            "recommendations": data.get("recommendations", []),
            "risk_assessment": "Low risk for standard travel",
            "alternatives": ["Budget option", "Premium option"]
        }


class SummaryTool(BaseTool):
    """Quick summary generation"""
    
    @property
    def name(self) -> str:
        return "summarizer"
        
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quick summary"""
        data = params.get("data", {})
        max_points = params.get("max_points", 5)
        
        summary_points = []
        
        if "destination" in data:
            summary_points.append(f"Destination: {data['destination']}")
        if "budget" in data:
            summary_points.append(f"Budget: ${data['budget']}")
        if "days" in data:
            summary_points.append(f"Duration: {data['days']} days")
        if "activities" in data:
            summary_points.append(f"Activities planned: {len(data['activities'])}")
        if "status" in data:
            summary_points.append(f"Status: {data['status']}")
            
        return {
            "summary": summary_points[:max_points],
            "word_count": sum(len(point.split()) for point in summary_points[:max_points])
        }