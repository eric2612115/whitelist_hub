"""Coordinator Agent for orchestrating the analysis workflow."""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import asyncio

from .base_agent import BaseAgent
from ..models.analysis_log import AnalysisLog

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """Coordinator Agent for orchestrating the analysis workflow."""
    
    def __init__(self, *args, **kwargs):
        """Initialize Coordinator Agent."""
        super().__init__(agent_type="coordinator", *args, **kwargs)
    
    async def create_analysis_plan(
        self, 
        project_name: str, 
        project_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Create an analysis plan for a project.
        
        Args:
            project_name: Name of the project
            project_data: Project data
            
        Returns:
            Tuple of (analysis plan, analysis log)
        """
        context = {
            "project_name": project_name,
            "project_website": project_data.get("website", ""),
            "project_github": project_data.get("github_url", ""),
            "project_category": project_data.get("category", ""),
            "project_data": project_data
        }
        
        return await self.run(
            task="Create a comprehensive analysis plan for this blockchain project",
            context=context,
            initial_state="initial_planning"
        )
    
    async def assess_analysis_progress(
        self, 
        project_name: str, 
        current_status: Dict[str, Any],
        completed_tasks: List[Dict[str, Any]],
        pending_tasks: List[Dict[str, Any]],
        issues: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Assess progress of project analysis.
        
        Args:
            project_name: Name of the project
            current_status: Current analysis status
            completed_tasks: Completed analysis tasks
            pending_tasks: Pending analysis tasks
            issues: Issues encountered
            
        Returns:
            Tuple of (progress assessment, analysis log)
        """
        context = {
            "project_name": project_name,
            "current_status_json": current_status,
            "completed_tasks_json": completed_tasks,
            "pending_tasks_json": pending_tasks,
            "issues_json": issues,
            "resource_utilization_json": {},  # Would be populated with resource usage data
            "elapsed_time": "00:00:00",  # Would be calculated
            "estimated_completion_time": "00:00:00"  # Would be estimated
        }
        
        return await self.run(
            task="Assess the progress of the analysis and optimize the remaining tasks",
            context=context,
            initial_state="progress_assessment"
        )
    
    async def synthesize_analysis_results(
        self, 
        project_name: str, 
        project_overview: Dict[str, Any],
        contract_analyses: List[Dict[str, Any]],
        whitelist_mechanisms: List[Dict[str, Any]],
        user_flows: List[Dict[str, Any]],
        security_assessment: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Synthesize analysis results into a cohesive report.
        
        Args:
            project_name: Name of the project
            project_overview: Project overview
            contract_analyses: Contract analysis results
            whitelist_mechanisms: Whitelist mechanism analyses
            user_flows: User interaction flows
            security_assessment: Security assessment results
            
        Returns:
            Tuple of (final synthesis, analysis log)
        """
        context = {
            "project_name": project_name,
            "project_overview_json": project_overview,
            "contract_analyses_json": contract_analyses,
            "whitelist_mechanisms_json": whitelist_mechanisms,
            "user_flows_json": user_flows,
            "security_assessment_json": security_assessment,
            "confidence_metrics_json": {
                "overall": self._calculate_overall_confidence_from_results(contract_analyses),
                "contract_analysis": self._calculate_average_confidence(contract_analyses, "analysis_confidence.overall"),
                "whitelist_detection": self._calculate_average_confidence(whitelist_mechanisms, "confidence"),
                "security_assessment": security_assessment.get("confidence", 0.0)
            }
        }
        
        return await self.run(
            task="Create a comprehensive synthesis of all analysis results",
            context=context,
            initial_state="final_synthesis"
        )
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordinator-specific actions.
        
        Args:
            action: Action to execute
            
        Returns:
            Result of action execution
        """
        action_type = action.get("type", "").lower()
        params = action.get("params", {})
        
        if action_type == "create_task_assignments":
            # Create task assignments for different agents
            return {
                "task_assignments": self._create_task_assignments(params)
            }
        elif action_type == "prioritize_tasks":
            # Prioritize tasks based on dependencies and resources
            return {
                "prioritized_tasks": self._prioritize_tasks(params)
            }
        elif action_type == "optimize_resource_allocation":
            # Optimize resource allocation for tasks
            return {
                "optimized_resources": self._optimize_resource_allocation(params)
            }
        elif action_type == "resolve_conflicts":
            # Resolve conflicts in task assignments or results
            return {
                "resolved_conflicts": self._resolve_conflicts(params)
            }
        elif action_type == "calculate_completion_metrics":
            # Calculate completion metrics for the analysis
            return {
                "completion_metrics": self._calculate_completion_metrics(params)
            }
        elif action_type == "generate_executive_summary":
            # Generate executive summary of analysis results
            return {
                "executive_summary": self._generate_executive_summary(params)
            }
        else:
            # Fall back to base implementation
            return await super()._execute_action(action)
    
    def _create_task_assignments(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create task assignments for different agents based on plan.
        
        Args:
            params: Task parameters
            
        Returns:
            List of task assignments
        """
        # Extract task information
        tasks = params.get("tasks", [])
        agents = params.get("agents", ["crawler", "analyzer", "verifier"])
        priorities = params.get("priorities", {})
        
        # Create assignments
        assignments = []
        
        for task in tasks:
            agent_type = task.get("agent") or self._determine_best_agent(task)
            
            assignments.append({
                "task_id": f"task_{len(assignments) + 1}",
                "task_name": task.get("name", "Unnamed Task"),
                "description": task.get("description", ""),
                "agent_type": agent_type,
                "priority": priorities.get(task.get("name"), "medium"),
                "depends_on": task.get("depends_on", []),
                "estimated_complexity": task.get("complexity", "medium"),
                "parameters": task.get("parameters", {})
            })
        
        return assignments
    
    def _determine_best_agent(self, task: Dict[str, Any]) -> str:
        """Determine the most appropriate agent for a task.
        
        Args:
            task: Task information
            
        Returns:
            Agent type
        """
        task_name = task.get("name", "").lower()
        
        if any(keyword in task_name for keyword in ["crawl", "collect", "scrape", "fetch"]):
            return "crawler"
        elif any(keyword in task_name for keyword in ["analyze", "classify", "detect"]):
            return "analyzer"
        elif any(keyword in task_name for keyword in ["verify", "validate", "check"]):
            return "verifier"
        else:
            # Default to analyzer
            return "analyzer"
    
    def _prioritize_tasks(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize tasks based on dependencies and importance.
        
        Args:
            params: Task parameters
            
        Returns:
            Prioritized list of tasks
        """
        tasks = params.get("tasks", [])
        
        # Create dependency graph
        dependency_graph = {}
        for task in tasks:
            task_id = task.get("task_id")
            dependency_graph[task_id] = task.get("depends_on", [])
        
        # Topological sort to respect dependencies
        sorted_tasks = self._topological_sort(dependency_graph)
        
        # Create prioritized list
        prioritized = []
        priority_values = {"high": 3, "medium": 2, "low": 1}
        
        for task_id in sorted_tasks:
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            if task:
                # Calculate a priority score
                priority = priority_values.get(task.get("priority", "medium"), 2)
                complexity = priority_values.get(task.get("estimated_complexity", "medium"), 2)
                
                # Higher priority, lower complexity is better
                score = priority * 100 - complexity * 10
                
                prioritized.append({
                    **task,
                    "priority_score": score
                })
        
        # Sort by priority score
        return sorted(prioritized, key=lambda x: x.get("priority_score", 0), reverse=True)
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on a dependency graph.
        
        Args:
            graph: Dependency graph
            
        Returns:
            Topologically sorted list
        """
        # Track visited nodes and result
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node):
            if node in temp_visited:
                # Cycle detected
                return
            if node in visited:
                return
            
            temp_visited.add(node)
            
            # Visit dependencies first
            for dependency in graph.get(node, []):
                visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        # Visit all nodes
        for node in graph:
            if node not in visited:
                visit(node)
        
        return result
    
    def _optimize_resource_allocation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize resource allocation for tasks.
        
        Args:
            params: Task parameters
            
        Returns:
            Optimized resource allocation
        """
        tasks = params.get("tasks", [])
        available_resources = params.get("available_resources", {})
        
        # Simple allocation strategy - distribute based on priority
        allocation = {}
        
        for task in tasks:
            task_id = task.get("task_id")
            priority = task.get("priority", "medium")
            
            # Allocate resources based on priority
            if priority == "high":
                cpu = 0.3
                memory = 0.3
            elif priority == "medium":
                cpu = 0.2
                memory = 0.2
            else:
                cpu = 0.1
                memory = 0.1
            
            allocation[task_id] = {
                "cpu": cpu,
                "memory": memory
            }
        
        return {
            "task_allocation": allocation,
            "allocation_strategy": "priority_based"
        }
    
    def _resolve_conflicts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts in task assignments or results.
        
        Args:
            params: Conflict parameters
            
        Returns:
            Resolved conflicts
        """
        conflicts = params.get("conflicts", [])
        resolution_strategy = params.get("strategy", "majority")
        
        # Resolve each conflict
        resolutions = []
        
        for conflict in conflicts:
            conflict_type = conflict.get("type")
            conflicting_values = conflict.get("values", [])
            
            if not conflicting_values:
                continue
            
            if resolution_strategy == "majority":
                # Use the most common value
                value_counts = {}
                for value in conflicting_values:
                    str_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                    value_counts[str_value] = value_counts.get(str_value, 0) + 1
                
                most_common = max(value_counts.items(), key=lambda x: x[1])
                resolved_value = json.loads(most_common[0]) if most_common[0].startswith(("{", "[")) else most_common[0]
                
            elif resolution_strategy == "highest_confidence":
                # Use the value with highest confidence
                highest_confidence = -1
                resolved_value = None
                
                for value in conflicting_values:
                    confidence = value.get("confidence", 0) if isinstance(value, dict) else 0
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        resolved_value = value
            
            else:
                # Default to first value
                resolved_value = conflicting_values[0]
            
            resolutions.append({
                "conflict_type": conflict_type,
                "resolved_value": resolved_value,
                "resolution_strategy": resolution_strategy,
                "confidence": 0.7  # Default confidence
            })
        
        return {
            "resolutions": resolutions,
            "unresolved_conflicts": []
        }
    
    def _calculate_completion_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate completion metrics for the analysis.
        
        Args:
            params: Calculation parameters
            
        Returns:
            Completion metrics
        """
        completed_tasks = params.get("completed_tasks", [])
        total_tasks = params.get("total_tasks", [])
        resource_usage = params.get("resource_usage", {})
        
        # Calculate overall completion percentage
        completion_percentage = (len(completed_tasks) / len(total_tasks)) * 100 if total_tasks else 0
        
        # Calculate completion by agent type
        agent_completion = {}
        for agent_type in ["crawler", "analyzer", "verifier"]:
            agent_total = sum(1 for task in total_tasks if task.get("agent_type") == agent_type)
            agent_completed = sum(1 for task in completed_tasks if task.get("agent_type") == agent_type)
            
            agent_completion[agent_type] = {
                "total": agent_total,
                "completed": agent_completed,
                "percentage": (agent_completed / agent_total) * 100 if agent_total else 0
            }
        
        # Calculate estimated time to completion
        avg_task_time = sum(task.get("execution_time", 0) for task in completed_tasks) / len(completed_tasks) if completed_tasks else 0
        remaining_tasks = len(total_tasks) - len(completed_tasks)
        estimated_remaining_time = avg_task_time * remaining_tasks
        
        return {
            "overall_completion": completion_percentage,
            "agent_completion": agent_completion,
            "estimated_remaining_time": estimated_remaining_time,
            "total_execution_time": sum(task.get("execution_time", 0) for task in completed_tasks),
            "resource_efficiency": self._calculate_resource_efficiency(resource_usage)
        }
    
    def _calculate_resource_efficiency(self, resource_usage: Dict[str, Any]) -> float:
        """Calculate resource efficiency from usage data.
        
        Args:
            resource_usage: Resource usage data
            
        Returns:
            Efficiency score (0-1)
        """
        # Simple placeholder implementation
        # In a real system, this would analyze CPU, memory usage patterns
        return 0.8
    
    def _generate_executive_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of analysis results.
        
        Args:
            params: Summary parameters
            
        Returns:
            Executive summary
        """
        project_data = params.get("project_data", {})
        analysis_results = params.get("analysis_results", {})
        
        # Extract key information
        project_name = project_data.get("name", "Unknown Project")
        whitelist_info = analysis_results.get("whitelist_mechanisms", [])
        security_info = analysis_results.get("security_assessment", {})
        contracts_info = analysis_results.get("contracts", [])
        
        # Create summary sections
        project_summary = {
            "name": project_name,
            "category": project_data.get("category", "Unknown"),
            "contract_count": len(contracts_info),
            "has_whitelist": bool(whitelist_info),
            "security_score": security_info.get("risk_level", "Unknown")
        }
        
        whitelist_summary = {
            "mechanisms": [wl.get("mechanism_type", "Unknown") for wl in whitelist_info],
            "accessibility": analysis_results.get("whitelist_accessibility", "Unknown"),
            "key_features": self._extract_whitelist_key_features(whitelist_info)
        }
        
        technical_summary = {
            "key_contracts": self._extract_key_contracts(contracts_info),
            "architecture_patterns": self._extract_architecture_patterns(contracts_info),
            "security_findings": self._extract_security_findings(security_info)
        }
        
        return {
            "project_summary": project_summary,
            "whitelist_summary": whitelist_summary,
            "technical_summary": technical_summary,
            "analysis_confidence": analysis_results.get("confidence", 0.0),
            "generated_at": self.context.get("timestamp", "Unknown")
        }
    
    def _extract_whitelist_key_features(self, whitelist_info: List[Dict[str, Any]]) -> List[str]:
        """Extract key features from whitelist mechanisms.
        
        Args:
            whitelist_info: Whitelist mechanism information
            
        Returns:
            List of key features
        """
        features = set()
        
        for wl in whitelist_info:
            mechanism = wl.get("mechanism_type", "").lower()
            properties = wl.get("properties", {})
            
            if mechanism:
                features.add(f"{mechanism} whitelist")
            
            if properties.get("time_limited"):
                features.add("time-limited access")
            
            if properties.get("tiered"):
                features.add("tiered access levels")
            
            if properties.get("transferable"):
                features.add("transferable whitelist spots")
        
        return list(features)
    
    def _extract_key_contracts(self, contracts_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract key contracts from contract information.
        
        Args:
            contracts_info: Contract information
            
        Returns:
            List of key contracts
        """
        # Find the most important contracts
        key_contracts = []
        
        for contract in contracts_info:
            # Check if this is a core contract
            is_key = False
            contract_type = contract.get("type", [])
            
            # Proxies and implementations are usually important
            if "proxy" in contract_type or "implementation" in contract_type:
                is_key = True
            
            # Contracts with whitelist functionality are important
            if contract.get("function_categories", {}).get("whitelist"):
                is_key = True
            
            # Contracts with token sale functionality are important
            if contract.get("function_categories", {}).get("token_sale"):
                is_key = True
            
            if is_key:
                key_contracts.append({
                    "address": contract.get("address"),
                    "name": contract.get("name", "Unnamed Contract"),
                    "type": contract_type,
                    "key_functions": self._extract_key_functions(contract)
                })
        
        return key_contracts
    
    def _extract_key_functions(self, contract: Dict[str, Any]) -> List[str]:
        """Extract key functions from a contract.
        
        Args:
            contract: Contract information
            
        Returns:
            List of key function names
        """
        key_functions = []
        categories = contract.get("function_categories", {})
        
        # Include whitelist functions
        for func in categories.get("whitelist", []):
            key_functions.append(func.get("name"))
        
        # Include token sale functions
        for func in categories.get("token_sale", []):
            key_functions.append(func.get("name"))
        
        # Include user-accessible entry points
        for category in categories.values():
            for func in category:
                if func.get("is_entry_point") and func.get("user_accessible"):
                    key_functions.append(func.get("name"))
        
        return list(set(key_functions))
    
    def _extract_architecture_patterns(self, contracts_info: List[Dict[str, Any]]) -> List[str]:
        """Extract architecture patterns from contracts.
        
        Args:
            contracts_info: Contract information
            
        Returns:
            List of architecture patterns
        """
        patterns = set()
        
        # Look for common patterns
        proxy_count = sum(1 for c in contracts_info if "proxy" in c.get("type", []))
        if proxy_count > 0:
            patterns.add("upgradeable proxy pattern")
        
        factory_count = sum(1 for c in contracts_info if "factory" in c.get("type", []))
        if factory_count > 0:
            patterns.add("factory pattern")
        
        router_count = sum(1 for c in contracts_info if "router" in c.get("type", []))
        if router_count > 0:
            patterns.add("router pattern")
        
        # Check for ERC standards
        for contract in contracts_info:
            abi = contract.get("abi", [])
            
            # Very simplified ERC detection
            # In a real system, this would be much more sophisticated
            if any(f.get("name") == "transfer" for f in abi):
                patterns.add("ERC20 token standard")
            
            if any(f.get("name") == "safeTransferFrom" for f in abi):
                patterns.add("ERC721 NFT standard")
        
        return list(patterns)
    
    def _extract_security_findings(self, security_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract security findings summary.
        
        Args:
            security_info: Security assessment information
            
        Returns:
            Summarized security findings
        """
        findings = security_info.get("findings", [])
        
        # Group by severity
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "informational": []
        }
        
        for finding in findings:
            severity = finding.get("severity", "").lower()
            if severity in grouped:
                grouped[severity].append({
                    "title": finding.get("title"),
                    "type": finding.get("type"),
                    "impact": finding.get("impact")
                })
        
        # Create summary
        summary = []
        for severity, items in grouped.items():
            if items:
                summary.append({
                    "severity": severity,
                    "count": len(items),
                    "types": list(set(item.get("type") for item in items))
                })
        
        return summary
    
    def _calculate_overall_confidence_from_results(self, contract_analyses: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence from contract analyses.
        
        Args:
            contract_analyses: Contract analysis results
            
        Returns:
            Overall confidence score (0-1)
        """
        if not contract_analyses:
            return 0.5
        
        # Extract confidence scores from all analyses
        confidences = []
        
        for analysis in contract_analyses:
            metadata = analysis.get("metadata", {})
            analysis_confidence = metadata.get("analysis_confidence", {})
            
            if isinstance(analysis_confidence, dict):
                overall = analysis_confidence.get("overall")
                if overall is not None:
                    confidences.append(overall)
        
        if not confidences:
            return 0.5
        
        # Calculate weighted average
        return sum(confidences) / len(confidences)
    
    def _calculate_average_confidence(self, items: List[Dict[str, Any]], path: str) -> float:
        """Calculate average confidence from a nested field path.
        
        Args:
            items: List of items
            path: Dot-separated path to confidence field
            
        Returns:
            Average confidence score (0-1)
        """
        if not items:
            return 0.5
        
        # Extract confidences from path
        confidences = []
        path_parts = path.split(".")
        
        for item in items:
            value = item
            for part in path_parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            
            if value is not None and isinstance(value, (int, float)):
                confidences.append(value)
        
        if not confidences:
            return 0.5
        
        return sum(confidences) / len(confidences)
