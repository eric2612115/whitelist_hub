"""Coordinator agent for orchestrating the analysis process."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from crewai import Agent

from ..utils.ai_client import AIClient
from ..prompts.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """Coordinator agent responsible for planning and orchestrating analysis."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager
    ):
        """Initialize coordinator agent.
        
        Args:
            ai_client: AI client for agent
            prompt_manager: Prompt manager for agent templates
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self._agent = None
    
    def create_agent(
        self,
        name: str = "Coordinator",
        goal: str = "Lead the analysis process and ensure comprehensive and accurate results",
        backstory: Optional[str] = None,
        verbose: bool = True
    ) -> Agent:
        """Create a CrewAI agent for the coordinator.
        
        Args:
            name: Agent name
            goal: Agent goal
            backstory: Agent backstory
            verbose: Whether to enable verbose logging
            
        Returns:
            CrewAI Agent instance
        """
        if not backstory:
            backstory = """You are the lead analyst responsible for coordinating the blockchain
            project analysis process. With extensive experience in smart contract analysis, 
            cryptocurrency projects, and DeFi protocols, you create analysis plans, assign 
            tasks to specialized agents, and synthesize findings into comprehensive reports.
            You have a keen eye for detecting inconsistencies in analysis results and can identify
            important aspects of blockchain projects that require deeper investigation."""
        
        # Initialize the agent using the AIClient
        llm_config = {
            "model_name": "claude-3-opus-20240229",  # Default model
            "config": {
                "temperature": 0.1,
                "max_tokens": 4000,
            }
        }
        
        # Custom callback to use ai_client
        async def callback_function(message):
            response = await self.ai_client.get_completion(message, temperature=0.1, max_tokens=4000)
            return response["choices"][0]["message"]["content"]
        
        # Create the agent
        self._agent = Agent(
            name=name,
            role="Blockchain Analysis Coordinator",
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=True,
            tools=[
                self.create_analysis_plan,
                self.synthesize_analysis_results
            ],
            async_callbacks=[callback_function]
        )
        
        return self._agent
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance.
        
        Returns:
            CrewAI Agent instance
        """
        if not self._agent:
            return self.create_agent()
        return self._agent
    
    def create_analysis_plan(self, project_name: str, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an analysis plan for a blockchain project.
        
        Args:
            project_name: Name of the project to analyze
            project_data: Initial project data
            
        Returns:
            Analysis plan
        """
        # Structuring analysis plan
        contract_addresses = project_data.get("contract_addresses", [])
        websites = project_data.get("website", [""])
        github_repos = project_data.get("github_url", [""])
        
        plan = {
            "project_name": project_name,
            "analysis_time": datetime.now().isoformat(),
            "contract_analysis_plan": [
                {
                    "address": contract.get("address"),
                    "blockchain": contract.get("blockchain", "ethereum"),
                    "priority": "high" if i < 3 else "medium",
                    "analysis_tasks": [
                        "abi_analysis",
                        "proxy_detection",
                        "whitelist_detection",
                        "function_categorization"
                    ]
                }
                for i, contract in enumerate(contract_addresses[:10])  # Limit to 10 contracts
            ],
            "website_analysis_plan": [
                {
                    "url": website,
                    "analysis_tasks": [
                        "extract_project_description",
                        "identify_team_members",
                        "find_whitelist_instructions",
                        "locate_contract_addresses"
                    ]
                }
                for website in websites if website
            ],
            "github_analysis_plan": [
                {
                    "url": repo,
                    "analysis_tasks": [
                        "identify_key_repositories",
                        "analyze_contract_code",
                        "evaluate_code_quality",
                        "verify_contract_match"
                    ]
                }
                for repo in github_repos if repo
            ],
            "consolidation_tasks": [
                "verify_contract_authenticity",
                "map_project_functionality",
                "identify_whitelist_mechanisms",
                "assess_security_posture",
                "generate_user_flows",
                "prepare_final_report"
            ]
        }
        
        return plan
    
    def synthesize_analysis_results(
        self,
        project_name: str,
        project_overview: Dict[str, Any],
        contract_analyses: List[Dict[str, Any]],
        whitelist_mechanisms: List[Dict[str, Any]],
        user_flows: List[Dict[str, Any]],
        security_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize analysis results into a comprehensive report.
        
        Args:
            project_name: Name of the project
            project_overview: Project overview and general information
            contract_analyses: List of contract analyses
            whitelist_mechanisms: List of identified whitelist mechanisms
            user_flows: List of user interaction flows
            security_assessment: Security assessment results
            
        Returns:
            Synthesized analysis results
        """
        # Synthesize the results
        synthesis = {
            "project_name": project_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "project_overview": project_overview,
            "executive_summary": self._generate_executive_summary(
                project_name, 
                contract_analyses, 
                whitelist_mechanisms
            ),
            "contract_analyses": contract_analyses,
            "whitelist_mechanisms": whitelist_mechanisms,
            "user_flows": user_flows,
            "security_assessment": security_assessment,
            "conclusion_and_recommendations": self._generate_recommendations(
                contract_analyses,
                whitelist_mechanisms,
                security_assessment
            )
        }
        
        return synthesis
    
    def _generate_executive_summary(
        self,
        project_name: str,
        contract_analyses: List[Dict[str, Any]],
        whitelist_mechanisms: List[Dict[str, Any]]
    ) -> str:
        """Generate an executive summary of the analysis.
        
        Args:
            project_name: Name of the project
            contract_analyses: List of contract analyses
            whitelist_mechanisms: List of identified whitelist mechanisms
            
        Returns:
            Executive summary text
        """
        # Count contracts and whitelist mechanisms
        contract_count = len(contract_analyses)
        whitelist_count = len(whitelist_mechanisms)
        proxy_count = sum(1 for c in contract_analyses if c.get("is_proxy", False))
        
        # Generate summary
        summary = f"Analysis of {project_name} examined {contract_count} smart contracts "
        summary += f"({proxy_count} using proxy patterns) and identified {whitelist_count} "
        summary += f"distinct whitelist mechanisms. "
        
        if whitelist_count > 0:
            wl_types = set(wl.get("mechanism_type", "unknown") for wl in whitelist_mechanisms)
            summary += f"The project implements {', '.join(wl_types)} whitelist approaches. "
        else:
            summary += "The project does not implement explicit whitelist functionality. "
        
        # Add contract quality assessment
        verified_count = sum(1 for c in contract_analyses if c.get("verification", {}).get("verified", False))
        if contract_count > 0:
            verification_percentage = (verified_count / contract_count) * 100
            if verification_percentage > 80:
                summary += "The smart contracts are well-verified and documented. "
            elif verification_percentage > 50:
                summary += "Most smart contracts are verified, though some lack proper documentation. "
            else:
                summary += "The majority of smart contracts lack verification or proper documentation. "
        
        return summary
    
    def _generate_recommendations(
        self,
        contract_analyses: List[Dict[str, Any]],
        whitelist_mechanisms: List[Dict[str, Any]],
        security_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate recommendations based on analysis results.
        
        Args:
            contract_analyses: List of contract analyses
            whitelist_mechanisms: List of identified whitelist mechanisms
            security_assessment: Security assessment results
            
        Returns:
            Recommendations dictionary
        """
        # Generate recommendations
        recommendations = {
            "contract_recommendations": [],
            "whitelist_recommendations": [],
            "security_recommendations": []
        }
        
        # Contract recommendations
        if contract_analyses:
            # Check for unverified contracts
            unverified = [c.get("address") for c in contract_analyses 
                         if not c.get("verification", {}).get("verified", False)]
            if unverified:
                recommendations["contract_recommendations"].append({
                    "title": "Verify Smart Contracts",
                    "description": f"Verify {len(unverified)} unverified contracts on blockchain explorers to improve transparency.",
                    "priority": "high" if len(unverified) > len(contract_analyses) / 2 else "medium"
                })
            
            # Check for contracts without proxy patterns
            non_proxy = [c.get("address") for c in contract_analyses 
                        if not c.get("is_proxy", False)]
            if non_proxy and len(non_proxy) > 3:
                recommendations["contract_recommendations"].append({
                    "title": "Implement Proxy Patterns",
                    "description": "Consider implementing proxy patterns for upgradeable contracts to improve maintainability.",
                    "priority": "medium"
                })
        
        # Whitelist recommendations
        if whitelist_mechanisms:
            # Check for basic whitelist patterns
            basic_whitelist = [wl for wl in whitelist_mechanisms 
                              if wl.get("mechanism_type") == "basic"]
            if basic_whitelist:
                recommendations["whitelist_recommendations"].append({
                    "title": "Enhance Whitelist Implementation",
                    "description": "Consider upgrading basic whitelist implementations to use more gas-efficient approaches like Merkle proofs.",
                    "priority": "medium"
                })
            
            # Check for non-tiered whitelists
            non_tiered = [wl for wl in whitelist_mechanisms 
                         if not wl.get("tiered", False)]
            if non_tiered:
                recommendations["whitelist_recommendations"].append({
                    "title": "Implement Tiered Access",
                    "description": "Consider implementing tiered access in whitelist mechanisms for more granular control.",
                    "priority": "low"
                })
        else:
            recommendations["whitelist_recommendations"].append({
                "title": "Consider Whitelist Implementation",
                "description": "Consider implementing whitelist mechanisms for controlled access to key functions.",
                "priority": "medium"
            })
        
        # Security recommendations
        if security_assessment:
            risk_level = security_assessment.get("risk_level", "medium")
            findings = security_assessment.get("findings", [])
            
            if risk_level == "high" or len(findings) > 3:
                recommendations["security_recommendations"].append({
                    "title": "Address Security Findings",
                    "description": f"Address {len(findings)} security findings to reduce overall risk level.",
                    "priority": "high"
                })
            elif risk_level == "medium" or len(findings) > 0:
                recommendations["security_recommendations"].append({
                    "title": "Improve Security Posture",
                    "description": "Address identified security findings and consider additional security audits.",
                    "priority": "medium"
                })
            else:
                recommendations["security_recommendations"].append({
                    "title": "Maintain Security Posture",
                    "description": "Continue monitoring for security vulnerabilities and stay updated with best practices.",
                    "priority": "low"
                })
        
        return recommendations
