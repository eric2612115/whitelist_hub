"""Verification agent for validating analysis results."""

import logging
import json
import jsonschema
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from deepdiff import DeepDiff

from crewai import Agent

from ..utils.ai_client import AIClient
from ..prompts.prompt_manager import PromptManager
from ..utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class VerificationAgent:
    """Verification agent for validating analysis results."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient
    ):
        """Initialize verification agent.
        
        Args:
            ai_client: AI client for agent
            prompt_manager: Prompt manager for agent templates
            blockchain_client: Blockchain client for contract interactions
        """
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.blockchain_client = blockchain_client
        self._agent = None
    
    def create_agent(
        self,
        name: str = "Verifier",
        goal: str = "Verify and validate contract analysis results for accuracy, consistency, and completeness",
        backstory: Optional[str] = None,
        verbose: bool = True
    ) -> Agent:
        """Create a CrewAI agent for verification.
        
        Args:
            name: Agent name
            goal: Agent goal
            backstory: Agent backstory
            verbose: Whether to enable verbose logging
            
        Returns:
            CrewAI Agent instance
        """
        if not backstory:
            backstory = """You are a specialized verification agent with expertise in
            blockchain technology and smart contract auditing. You have extensive experience
            in validating analysis results, checking for inconsistencies, and ensuring the
            accuracy of contract assessments. You have a meticulous eye for detail and can
            spot subtle discrepancies in contract analyses. Your role is critical for ensuring
            the reliability and trustworthiness of the project's findings."""
        
        # Custom callback to use ai_client
        async def callback_function(message):
            response = await self.ai_client.get_completion(message, temperature=0.1, max_tokens=4000)
            return response["choices"][0]["message"]["content"]
        
        # Create the agent
        self._agent = Agent(
            name=name,
            role="Analysis Verification Specialist",
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=False,
            tools=[
                self.verify_analysis_result,
                self.verify_schema_compliance,
                self.cross_validate_contracts,
                self.check_analysis_consistency,
                self.validate_whitelist_detection
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
    
    async def verify_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        contract_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Verify analysis result.
        
        Args:
            analysis_result: Analysis result to verify
            contract_schema: Schema for validation (optional)
            
        Returns:
            Tuple of (verified result, verification log)
        """
        verification_log = {
            "timestamp": datetime.now().isoformat(),
            "input_hash": str(hash(json.dumps(analysis_result, sort_keys=True))),
            "validation_steps": [],
            "warnings": [],
            "errors": [],
            "verified": False
        }
        
        try:
            # Create a copy for verification
            verified_result = analysis_result.copy() if analysis_result else {}
            
            # 1. Validate schema compliance if schema provided
            if contract_schema:
                schema_valid, schema_errors = self._validate_schema(verified_result, contract_schema)
                verification_log["validation_steps"].append({
                    "step": "schema_validation",
                    "passed": schema_valid,
                    "errors": schema_errors
                })
                
                if not schema_valid:
                    verification_log["errors"].extend([f"Schema validation error: {e}" for e in schema_errors])
            
            # 2. Check for required fields
            required_fields = ["contract_address", "blockchain"]
            missing_fields = [field for field in required_fields if field not in verified_result]
            
            if missing_fields:
                verification_log["validation_steps"].append({
                    "step": "required_fields_check",
                    "passed": False,
                    "missing_fields": missing_fields
                })
                verification_log["errors"].extend([f"Missing required field: {field}" for field in missing_fields])
                
                # Add missing fields with default values
                for field in missing_fields:
                    if field == "contract_address":
                        verified_result["contract_address"] = "unknown"
                    elif field == "blockchain":
                        verified_result["blockchain"] = "ethereum"
            else:
                verification_log["validation_steps"].append({
                    "step": "required_fields_check",
                    "passed": True
                })
            
            # 3. Validate blockchain name
            if "blockchain" in verified_result:
                blockchain = verified_result["blockchain"].lower()
                valid_blockchains = ["ethereum", "bsc", "polygon", "arbitrum", "optimism"]
                
                if blockchain not in valid_blockchains:
                    verification_log["validation_steps"].append({
                        "step": "blockchain_validation",
                        "passed": False,
                        "invalid_blockchain": blockchain,
                        "valid_blockchains": valid_blockchains
                    })
                    verification_log["warnings"].append(f"Invalid blockchain name: {blockchain}. Defaulting to ethereum.")
                    verified_result["blockchain"] = "ethereum"
                else:
                    verification_log["validation_steps"].append({
                        "step": "blockchain_validation",
                        "passed": True
                    })
            
            # 4. Validate contract address format
            if "contract_address" in verified_result and verified_result["contract_address"] != "unknown":
                address = verified_result["contract_address"]
                valid_address = address.startswith("0x") and len(address) == 42
                
                if not valid_address:
                    verification_log["validation_steps"].append({
                        "step": "address_format_validation",
                        "passed": False,
                        "invalid_address": address
                    })
                    verification_log["errors"].append(f"Invalid contract address format: {address}")
                else:
                    verification_log["validation_steps"].append({
                        "step": "address_format_validation",
                        "passed": True
                    })
            
            # 5. Check for data consistency
            consistency_issues = self._check_data_consistency(verified_result)
            
            if consistency_issues:
                verification_log["validation_steps"].append({
                    "step": "data_consistency_check",
                    "passed": False,
                    "consistency_issues": consistency_issues
                })
                verification_log["warnings"].extend(consistency_issues)
            else:
                verification_log["validation_steps"].append({
                    "step": "data_consistency_check",
                    "passed": True
                })
            
            # 6. Check for analysis completeness
            completeness_issues = self._check_analysis_completeness(verified_result)
            
            if completeness_issues:
                verification_log["validation_steps"].append({
                    "step": "completeness_check",
                    "passed": False,
                    "completeness_issues": completeness_issues
                })
                verification_log["warnings"].extend(completeness_issues)
            else:
                verification_log["validation_steps"].append({
                    "step": "completeness_check",
                    "passed": True
                })
            
            # Determine overall verification status
            verification_passed = len(verification_log["errors"]) == 0
            verification_log["verified"] = verification_passed
            
            # Add verification status to result
            verified_result["verification"] = {
                "verified": verification_passed,
                "timestamp": datetime.now().isoformat(),
                "warnings_count": len(verification_log["warnings"]),
                "errors_count": len(verification_log["errors"])
            }
            
            return verified_result, verification_log
            
        except Exception as e:
            logger.error(f"Error during verification: {e}")
            verification_log["errors"].append(f"Verification error: {str(e)}")
            verification_log["verified"] = False
            
            # Return original result with verification status
            if isinstance(analysis_result, dict):
                analysis_result["verification"] = {
                    "verified": False,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            else:
                analysis_result = {
                    "error": "Invalid input data",
                    "verification": {
                        "verified": False,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            return analysis_result, verification_log
    
    async def verify_schema_compliance(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify data against a JSON schema.
        
        Args:
            data: Data to verify
            schema: JSON schema
            
        Returns:
            Verification result
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "valid": False,
                "errors": []
            }
            
            try:
                jsonschema.validate(instance=data, schema=schema)
                result["valid"] = True
            except jsonschema.exceptions.ValidationError as e:
                result["valid"] = False
                result["errors"].append(str(e))
            
            return result
            
        except Exception as e:
            logger.error(f"Error during schema validation: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "valid": False,
                "errors": [f"Schema validation error: {str(e)}"]
            }
    
    async def cross_validate_contracts(
        self,
        contracts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Cross-validate multiple contract analyses.
        
        Args:
            contracts: List of contract analyses
            
        Returns:
            Cross-validation result
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "contracts_count": len(contracts),
                "inconsistencies": [],
                "related_contracts": []
            }
            
            # Skip if fewer than 2 contracts
            if len(contracts) < 2:
                return result
            
            # Find potential implementation-proxy relationships
            for i, contract1 in enumerate(contracts):
                for j, contract2 in enumerate(contracts):
                    if i == j:
                        continue
                    
                    # Check if contract1 is a proxy pointing to contract2
                    if (
                        contract1.get("is_proxy", False) and 
                        contract1.get("implementation_address") == contract2.get("contract_address")
                    ):
                        result["related_contracts"].append({
                            "proxy_address": contract1.get("contract_address"),
                            "implementation_address": contract2.get("contract_address"),
                            "relationship": "proxy_implementation"
                        })
            
            # Check for inconsistent whitelist detection
            whitelist_contracts = [c for c in contracts if c.get("has_whitelist", False)]
            
            # If multiple contracts have whitelists, check for inconsistencies
            if len(whitelist_contracts) > 1:
                mechanism_types = set(c.get("whitelist_analysis", {}).get("mechanism_type") 
                                    for c in whitelist_contracts 
                                    if "whitelist_analysis" in c)
                
                if len(mechanism_types) > 1:
                    result["inconsistencies"].append({
                        "type": "whitelist_mechanism",
                        "description": f"Different whitelist mechanism types detected: {', '.join(mechanism_types)}",
                        "affected_contracts": [c.get("contract_address") for c in whitelist_contracts]
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error during cross-validation: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "contracts_count": len(contracts) if isinstance(contracts, list) else 0,
                "error": str(e),
                "inconsistencies": []
            }
    
    async def check_analysis_consistency(
        self,
        original_analysis: Dict[str, Any],
        new_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check consistency between two analyses of the same contract.
        
        Args:
            original_analysis: Original analysis
            new_analysis: New analysis
            
        Returns:
            Consistency check result
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "matches": True,
                "differences": [],
                "similarity_score": 1.0
            }
            
            # Compare contract addresses
            if original_analysis.get("contract_address") != new_analysis.get("contract_address"):
                result["matches"] = False
                result["differences"].append({
                    "field": "contract_address",
                    "original": original_analysis.get("contract_address"),
                    "new": new_analysis.get("contract_address")
                })
            
            # Compare key fields using DeepDiff
            fields_to_compare = [
                "has_whitelist", 
                "has_owner", 
                "is_proxy",
                "function_count"
            ]
            
            for field in fields_to_compare:
                if field in original_analysis and field in new_analysis:
                    if original_analysis[field] != new_analysis[field]:
                        result["matches"] = False
                        result["differences"].append({
                            "field": field,
                            "original": original_analysis.get(field),
                            "new": new_analysis.get(field)
                        })
            
            # Compare function categories (more complex)
            if "function_categories" in original_analysis and "function_categories" in new_analysis:
                original_cats = original_analysis["function_categories"]
                new_cats = new_analysis["function_categories"]
                
                # Get all category names
                all_categories = set(original_cats.keys()).union(set(new_cats.keys()))
                
                for category in all_categories:
                    original_funcs = set(original_cats.get(category, []))
                    new_funcs = set(new_cats.get(category, []))
                    
                    # Check for differences
                    if original_funcs != new_funcs:
                        only_in_original = original_funcs - new_funcs
                        only_in_new = new_funcs - original_funcs
                        
                        if only_in_original or only_in_new:
                            result["matches"] = False
                            result["differences"].append({
                                "field": f"function_categories.{category}",
                                "only_in_original": list(only_in_original),
                                "only_in_new": list(only_in_new)
                            })
            
            # Calculate similarity score
            if result["differences"]:
                # Simple scoring: 1.0 - (num_differences / potential_fields)
                potential_fields = len(fields_to_compare) + len(original_analysis.get("function_categories", {}).keys())
                result["similarity_score"] = max(0.0, 1.0 - (len(result["differences"]) / potential_fields))
            
            return result
            
        except Exception as e:
            logger.error(f"Error during consistency check: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "matches": False,
                "error": str(e),
                "differences": ["Error performing comparison"],
                "similarity_score": 0.0
            }
    
    async def validate_whitelist_detection(
        self,
        contract_address: str,
        blockchain: str,
        whitelist_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate whitelist detection accuracy.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            whitelist_analysis: Whitelist analysis to validate
            
        Returns:
            Validation result
        """
        try:
            result = {
                "timestamp": datetime.now().isoformat(),
                "contract_address": contract_address,
                "blockchain": blockchain,
                "validation_passed": False,
                "confidence": 0.0,
                "issues": []
            }
            
            # Get contract ABI
            abi_json = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
            
            if not abi_json:
                result["issues"].append("Cannot validate without ABI")
                return result
            
            # Check if contract has whitelist functionality
            has_whitelist = whitelist_analysis.get("has_whitelist", False)
            whitelist_functions = whitelist_analysis.get("whitelist_functions", [])
            
            # Extract all function names from ABI
            abi_functions = []
            for item in abi_json:
                if item.get("type") == "function":
                    abi_functions.append({
                        "name": item.get("name", ""),
                        "inputs": item.get("inputs", []),
                        "state_mutability": item.get("stateMutability", "")
                    })
            
            # If analysis claims whitelist functionality but no whitelist functions found
            if has_whitelist and not whitelist_functions:
                # Check if there are potential whitelist functions in ABI
                whitelist_indicators = ["whitelist", "allowlist", "allowed", "permit", "authorize", "access"]
                potential_whitelist_funcs = []
                
                for func in abi_functions:
                    name = func.get("name", "").lower()
                    if any(indicator in name for indicator in whitelist_indicators):
                        potential_whitelist_funcs.append(name)
                
                if potential_whitelist_funcs:
                    result["issues"].append(f"Whitelist functionality claimed but functions not identified: {', '.join(potential_whitelist_funcs)}")
                else:
                    result["issues"].append("Whitelist functionality claimed but no supporting evidence in ABI")
            
            # If analysis claims no whitelist but there are suspicious functions
            if not has_whitelist:
                whitelist_indicators = ["whitelist", "allowlist", "allowed", "permit"]
                potential_whitelist_funcs = []
                
                for func in abi_functions:
                    name = func.get("name", "").lower()
                    if any(indicator in name for indicator in whitelist_indicators):
                        potential_whitelist_funcs.append(name)
                
                if potential_whitelist_funcs:
                    result["issues"].append(f"Potential whitelist functions found but not identified: {', '.join(potential_whitelist_funcs)}")
            
            # Validate whitelist mechanism type if provided
            mechanism_type = whitelist_analysis.get("mechanism_type", "unknown")
            if mechanism_type != "unknown" and has_whitelist:
                # Check for evidence supporting the mechanism type
                if mechanism_type == "merkle_proof":
                    merkle_indicators = ["merkle", "proof", "verify", "leaf", "root"]
                    if not any(any(indicator in func.get("name", "").lower() for indicator in merkle_indicators) for func in abi_functions):
                        result["issues"].append("Merkle proof mechanism claimed but no supporting evidence in ABI")
                
                elif mechanism_type == "signature_based":
                    signature_indicators = ["signature", "sign", "verify", "recover"]
                    if not any(any(indicator in func.get("name", "").lower() for indicator in signature_indicators) for func in abi_functions):
                        result["issues"].append("Signature-based mechanism claimed but no supporting evidence in ABI")
            
            # Calculate validation confidence
            if not result["issues"]:
                result["validation_passed"] = True
                result["confidence"] = 1.0
            else:
                # Reduce confidence based on number of issues
                result["confidence"] = max(0.0, 1.0 - (len(result["issues"]) * 0.2))
                if result["confidence"] >= 0.7:  # Still considered valid if confidence is high enough
                    result["validation_passed"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error during whitelist validation: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "contract_address": contract_address,
                "blockchain": blockchain,
                "validation_passed": False,
                "confidence": 0.0,
                "error": str(e),
                "issues": ["Error during validation"]
            }
    
    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data against a JSON schema.
        
        Args:
            data: Data to validate
            schema: JSON schema
            
        Returns:
            Tuple of (is_valid, errors)
        """
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Schema validation error: {str(e)}"]
    
    def _check_data_consistency(self, data: Dict[str, Any]) -> List[str]:
        """Check for internal data consistency issues.
        
        Args:
            data: Data to check
            
        Returns:
            List of inconsistency issues
        """
        issues = []
        
        # Check for proxy/implementation consistency
        if data.get("is_proxy", False) and not data.get("implementation_address"):
            issues.append("Contract marked as proxy but no implementation address provided")
        
        # Check for whitelist consistency
        if data.get("has_whitelist", False):
            whitelist_analysis = data.get("whitelist_analysis", {})
            if not whitelist_analysis:
                issues.append("Contract marked as having whitelist but no whitelist analysis provided")
            elif not whitelist_analysis.get("whitelist_functions"):
                issues.append("Contract marked as having whitelist but no whitelist functions identified")
        
        # Check function_categories consistency with functions
        if "function_categories" in data and "functions" in data:
            # Get all categorized functions
            categorized = set()
            for category, functions in data["function_categories"].items():
                categorized.update(functions)
            
            # Get all functions
            all_functions = set(f.get("name") for f in data["functions"] if "name" in f)
            
            # Check for functions in categories but not in functions list
            not_in_functions = categorized - all_functions
            if not_in_functions:
                issues.append(f"Functions in categories but not in functions list: {', '.join(not_in_functions)}")
        
        return issues
    
    def _check_analysis_completeness(self, data: Dict[str, Any]) -> List[str]:
        """Check for analysis completeness.
        
        Args:
            data: Data to check
            
        Returns:
            List of completeness issues
        """
        issues = []
        
        # Check for missing key sections
        key_sections = ["functions", "events", "function_categories"]
        for section in key_sections:
            if section not in data:
                issues.append(f"Missing key section: {section}")
        
        # Check for incomplete proxy analysis
        if data.get("is_proxy", False):
            if "proxy_type" not in data:
                issues.append("Proxy contract missing proxy_type")
                
            if "implementation_address" not in data or not data["implementation_address"]:
                issues.append("Proxy contract missing implementation_address")
        
        # Check for incomplete whitelist analysis
        if data.get("has_whitelist", False):
            if "whitelist_analysis" not in data:
                issues.append("Contract marked as having whitelist but missing whitelist_analysis")
            else:
                whitelist_analysis = data["whitelist_analysis"]
                required_whitelist_fields = ["mechanism_type", "whitelist_functions"]
                for field in required_whitelist_fields:
                    if field not in whitelist_analysis:
                        issues.append(f"Whitelist analysis missing required field: {field}")
        
        return issues
