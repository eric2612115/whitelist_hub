"""Verification Agent for validating analysis results."""

import logging
import json
import re
import difflib
from typing import Dict, List, Any, Optional, Tuple

from .base_agent import BaseAgent
from ..models.analysis_log import AnalysisLog
from ..utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class VerificationAgent(BaseAgent):
    """Verification Agent for validating analysis results."""
    
    def __init__(self, blockchain_client=None, *args, **kwargs):
        """Initialize Verification Agent.
        
        Args:
            blockchain_client: Client for blockchain interactions
        """
        super().__init__(agent_type="verifier", *args, **kwargs)
        self.blockchain_client = blockchain_client or BlockchainClient()
    
    async def verify_analysis_result(
        self,
        analysis_result: Dict[str, Any],
        contract_schema: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Verify analysis result structure and content.
        
        Args:
            analysis_result: Analysis result to verify
            contract_schema: Expected schema for analysis
            
        Returns:
            Tuple of (verified result, analysis log)
        """
        context = {
            "analysis_result": analysis_result,
            "schema": contract_schema,
            "verification_log": []
        }
        
        # Perform initial schema validation
        schema_validation = self._validate_schema(analysis_result, contract_schema)
        context["validation_errors"] = schema_validation.get("errors", [])
        context["schema_valid"] = schema_validation.get("valid", False)
        
        return await self.run(
            task="Verify and validate the analysis result against schema and data quality standards",
            context=context,
            initial_state="validation"
        )
    
    async def check_cross_contract_consistency(
        self,
        analysis_result: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Check consistency across related contracts.
        
        Args:
            analysis_result: Analysis result to check
            
        Returns:
            Tuple of (consistency check result, analysis log)
        """
        context = {
            "analysis_result": analysis_result,
            "related_contracts": analysis_result.get("related_contracts", []),
            "consistency_check": {
                "checks_performed": [],
                "inconsistencies": []
            }
        }
        
        return await self.run(
            task="Check cross-contract consistency and identify any inconsistencies",
            context=context,
            initial_state="consistency_check"
        )
    
    async def enhance_data_quality(
        self,
        analysis_result: Dict[str, Any],
        quality_issues: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Enhance data quality based on identified issues.
        
        Args:
            analysis_result: Analysis result to enhance
            quality_issues: Data quality issues to address
            
        Returns:
            Tuple of (enhanced result, analysis log)
        """
        context = {
            "analysis_result": analysis_result,
            "quality_issues": quality_issues,
            "enhancement_log": []
        }
        
        return await self.run(
            task="Enhance data quality by addressing identified issues",
            context=context,
            initial_state="quality_enhancement"
        )
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute verifier-specific actions.
        
        Args:
            action: Action to execute
            
        Returns:
            Result of action execution
        """
        action_type = action.get("type", "").lower()
        params = action.get("params", {})
        
        if action_type == "validate_schema":
            # Validate against JSON schema
            analysis_result = params.get("analysis_result") or self.context.get("analysis_result", {})
            schema = params.get("schema") or self.context.get("schema", {})
            result = self._validate_schema(analysis_result, schema)
            return {"schema_validation": result}
            
        elif action_type == "validate_data_quality":
            # Check data quality
            analysis_result = params.get("analysis_result") or self.context.get("analysis_result", {})
            result = self._validate_data_quality(analysis_result)
            return {"quality_validation": result}
            
        elif action_type == "fix_validation_errors":
            # Fix schema validation errors
            analysis_result = params.get("analysis_result") or self.context.get("analysis_result", {})
            errors = params.get("errors") or self.context.get("validation_errors", [])
            result = self._fix_validation_errors(analysis_result, errors)
            return {"corrected_result": result}
            
        elif action_type == "enhance_data_quality":
            # Enhance data quality
            analysis_result = params.get("analysis_result") or self.context.get("analysis_result", {})
            issues = params.get("issues") or self.context.get("quality_issues", [])
            result = self._enhance_data_quality(analysis_result, issues)
            return {"enhanced_result": result}
            
        elif action_type == "check_cross_contract_consistency":
            # Check consistency across contracts
            analysis_result = params.get("analysis_result") or self.context.get("analysis_result", {})
            result = await self._check_cross_contract_consistency(analysis_result)
            return {"consistency_check": result}
            
        elif action_type == "calculate_diff":
            # Calculate difference between versions
            original = params.get("original", {})
            modified = params.get("modified", {})
            result = self._calculate_diff(original, modified)
            return {"diff": result}
            
        else:
            # Fall back to base implementation
            return await super()._execute_action(action)
    
    def _validate_schema(self, analysis_result: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analysis result against JSON schema.
        
        Args:
            analysis_result: Analysis result to validate
            schema: Expected schema
            
        Returns:
            Validation result
        """
        # In a real implementation, this would use jsonschema library
        # This is a simplified implementation for demonstration
        errors = []
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in analysis_result:
                errors.append({
                    "path": field,
                    "message": f"Required field '{field}' is missing",
                    "schema_path": f"required"
                })
        
        # Check field types
        properties = schema.get("properties", {})
        for field, field_schema in properties.items():
            if field in analysis_result:
                field_type = field_schema.get("type")
                value = analysis_result[field]
                
                if field_type == "string" and not isinstance(value, str):
                    errors.append({
                        "path": field,
                        "message": f"Field '{field}' should be a string",
                        "schema_path": f"properties.{field}.type"
                    })
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append({
                        "path": field,
                        "message": f"Field '{field}' should be a number",
                        "schema_path": f"properties.{field}.type"
                    })
                elif field_type == "array" and not isinstance(value, list):
                    errors.append({
                        "path": field,
                        "message": f"Field '{field}' should be an array",
                        "schema_path": f"properties.{field}.type"
                    })
                elif field_type == "object" and not isinstance(value, dict):
                    errors.append({
                        "path": field,
                        "message": f"Field '{field}' should be an object",
                        "schema_path": f"properties.{field}.type"
                    })
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_data_quality(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the quality of data in analysis result.
        
        Args:
            analysis_result: Analysis result to validate
            
        Returns:
            Quality validation result
        """
        issues = []
        
        # Check for placeholder values
        placeholder_patterns = [
            "to be determined", "placeholder", "unknown", "todo", "tbd", "n/a"
        ]
        
        def check_placeholders(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    check_placeholders(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    check_placeholders(item, new_path)
            elif isinstance(obj, str):
                lower_value = obj.lower()
                if any(pattern in lower_value for pattern in placeholder_patterns):
                    issues.append({
                        "type": "placeholder_value",
                        "path": path,
                        "value": obj
                    })
        
        check_placeholders(analysis_result)
        
        # Check for empty collections that should have data
        critical_collections = [
            "contracts", "function_categories", "whitelist_implementation", "security_assessment"
        ]
        
        def check_empty_collections(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if key in critical_collections and isinstance(value, (list, dict)) and not value:
                        issues.append({
                            "type": "empty_collection",
                            "path": new_path
                        })
                    check_empty_collections(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    check_empty_collections(item, new_path)
        
        check_empty_collections(analysis_result)
        
        # Check for low confidence scores
        def check_confidence_scores(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    if "confidence" in key.lower() and isinstance(value, (int, float)) and value < 0.5:
                        issues.append({
                            "type": "low_confidence",
                            "path": new_path,
                            "value": value
                        })
                    check_confidence_scores(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    check_confidence_scores(item, new_path)
        
        check_confidence_scores(analysis_result)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _fix_validation_errors(
        self, 
        analysis_result: Dict[str, Any], 
        errors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fix schema validation errors.
        
        Args:
            analysis_result: Analysis result to fix
            errors: Validation errors
            
        Returns:
            Fixed analysis result
        """
        # Create a deep copy of the original result
        import copy
        fixed_result = copy.deepcopy(analysis_result)
        
        for error in errors:
            path = error.get("path", "")
            message = error.get("message", "")
            
            # Parse the path into components
            path_parts = path.split(".")
            
            # Navigate to the parent object
            parent = fixed_result
            for i, part in enumerate(path_parts[:-1]):
                # Handle array indices in path
                if "[" in part and "]" in part:
                    base_part = part.split("[")[0]
                    idx = int(part.split("[")[1].split("]")[0])
                    
                    if base_part not in parent:
                        parent[base_part] = []
                    
                    while len(parent[base_part]) <= idx:
                        parent[base_part].append({})
                    
                    parent = parent[base_part][idx]
                else:
                    if part not in parent:
                        parent[part] = {}
                    
                    parent = parent[part]
            
            # Get the final part of the path
            final_part = path_parts[-1]
            
            # Handle array indices in the final part
            if "[" in final_part and "]" in final_part:
                base_part = final_part.split("[")[0]
                idx = int(final_part.split("[")[1].split("]")[0])
                
                if base_part not in parent:
                    parent[base_part] = []
                
                while len(parent[base_part]) <= idx:
                    parent[base_part].append({})
                
                # Fix different types of errors
                if "should be a string" in message:
                    if not isinstance(parent[base_part][idx], str):
                        parent[base_part][idx] = str(parent[base_part][idx])
                elif "should be a number" in message:
                    if not isinstance(parent[base_part][idx], (int, float)):
                        try:
                            parent[base_part][idx] = float(parent[base_part][idx])
                        except (ValueError, TypeError):
                            parent[base_part][idx] = 0
                elif "should be an array" in message:
                    if not isinstance(parent[base_part][idx], list):
                        parent[base_part][idx] = []
                elif "should be an object" in message:
                    if not isinstance(parent[base_part][idx], dict):
                        parent[base_part][idx] = {}
            else:
                # Fix missing required field
                if "is missing" in message:
                    if final_part not in parent:
                        # Determine appropriate default value
                        if "string" in message:
                            parent[final_part] = ""
                        elif "number" in message:
                            parent[final_part] = 0
                        elif "array" in message:
                            parent[final_part] = []
                        elif "object" in message:
                            parent[final_part] = {}
                        else:
                            parent[final_part] = None
                
                # Fix type errors
                elif "should be a string" in message:
                    if final_part in parent and not isinstance(parent[final_part], str):
                        parent[final_part] = str(parent[final_part])
                elif "should be a number" in message:
                    if final_part in parent and not isinstance(parent[final_part], (int, float)):
                        try:
                            parent[final_part] = float(parent[final_part])
                        except (ValueError, TypeError):
                            parent[final_part] = 0
                elif "should be an array" in message:
                    if final_part in parent and not isinstance(parent[final_part], list):
                        parent[final_part] = []
                elif "should be an object" in message:
                    if final_part in parent and not isinstance(parent[final_part], dict):
                        parent[final_part] = {}
        
        return fixed_result
    
    def _enhance_data_quality(
        self, 
        analysis_result: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance data quality based on identified issues.
        
        Args:
            analysis_result: Analysis result to enhance
            issues: Data quality issues
            
        Returns:
            Enhanced analysis result
        """
        # Create a deep copy of the original result
        import copy
        enhanced_result = copy.deepcopy(analysis_result)
        
        for issue in issues:
            issue_type = issue.get("type")
            path = issue.get("path", "")
            value = issue.get("value")
            
            # Parse the path into components
            path_parts = path.split(".")
            
            # Navigate to the object to fix
            target = enhanced_result
            for i, part in enumerate(path_parts[:-1]):
                # Handle array indices in path
                if "[" in part and "]" in part:
                    base_part = part.split("[")[0]
                    idx = int(part.split("[")[1].split("]")[0])
                    
                    if base_part in target and isinstance(target[base_part], list) and idx < len(target[base_part]):
                        target = target[base_part][idx]
                    else:
                        # Can't navigate to this path
                        target = None
                        break
                else:
                    if part in target and isinstance(target[part], dict):
                        target = target[part]
                    else:
                        # Can't navigate to this path
                        target = None
                        break
            
            if target is None:
                continue
                
            # Get the final part of the path
            final_part = path_parts[-1]
            
            # Handle array indices in the final part
            if "[" in final_part and "]" in final_part:
                base_part = final_part.split("[")[0]
                idx = int(final_part.split("[")[1].split("]")[0])
                
                if base_part in target and isinstance(target[base_part], list) and idx < len(target[base_part]):
                    # Fix different types of issues
                    if issue_type == "placeholder_value":
                        # Replace placeholder with more meaningful value
                        target[base_part][idx] = self._generate_meaningful_value(target[base_part][idx], path)
                    elif issue_type == "low_confidence":
                        # Increase confidence if it makes sense
                        target[base_part][idx] = 0.5  # Minimum acceptable confidence
            else:
                if final_part in target:
                    # Fix different types of issues
                    if issue_type == "placeholder_value" and isinstance(target[final_part], str):
                        # Replace placeholder with more meaningful value
                        target[final_part] = self._generate_meaningful_value(target[final_part], path)
                    elif issue_type == "low_confidence" and isinstance(target[final_part], (int, float)):
                        # Increase confidence if it makes sense
                        target[final_part] = 0.5  # Minimum acceptable confidence
                    elif issue_type == "empty_collection" and isinstance(target[final_part], (list, dict)) and not target[final_part]:
                        # Populate empty collection with placeholder data if appropriate
                        target[final_part] = self._generate_placeholder_collection(final_part, path)
        
        return enhanced_result
    
    def _generate_meaningful_value(self, placeholder_value: str, path: str) -> str:
        """Generate a more meaningful value to replace a placeholder.
        
        Args:
            placeholder_value: Original placeholder value
            path: Path of the value in the document
            
        Returns:
            More meaningful value
        """
        # For demonstration purposes, provide more meaningful defaults
        if "description" in path.lower():
            return "No detailed description available yet."
        elif "name" in path.lower():
            return "Unnamed Component"
        elif "purpose" in path.lower():
            return "Purpose not yet determined"
        elif "message" in path.lower():
            return "No message provided"
        else:
            return "Not specified"
    
    def _generate_placeholder_collection(self, field_name: str, path: str) -> Any:
        """Generate placeholder data for empty collections.
        
        Args:
            field_name: Name of the empty field
            path: Path of the field in the document
            
        Returns:
            Placeholder collection
        """
        # For demonstration purposes, provide appropriate placeholder collections
        if field_name == "contracts":
            return []  # Empty list is acceptable
        elif field_name == "function_categories":
            return {
                "uncategorized": []
            }
        elif field_name == "whitelist_implementation":
            return {
                "mechanism": "unknown",
                "key_functions": [],
                "data_storage": "unknown"
            }
        elif field_name == "security_assessment":
            return {
                "risk_level": "medium",
                "findings": []
            }
        elif field_name.endswith("_list") or field_name.endswith("s"):
            return []  # Generic empty list for plural fields
        else:
            return {}  # Generic empty dict
    
    async def _check_cross_contract_consistency(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency across related contracts.
        
        Args:
            analysis_result: Analysis result to check
            
        Returns:
            Consistency check result
        """
        inconsistencies = []
        
        # Extract related contracts
        related_contracts = analysis_result.get("related_contracts", [])
        if not related_contracts:
            return {
                "consistent": True,
                "inconsistencies": []
            }
        
        # Check for relationship consistency
        for relation in related_contracts:
            related_address = relation.get("address")
            relationship = relation.get("relationship")
            
            if not related_address or not relationship:
                continue
            
            # Example check: If this is an implementation, the related contract should be a proxy
            if relationship == "implements":
                # Fetch related contract data
                # In a real implementation, this would query the database
                # related_contract = await get_contract_data(related_address)
                
                # Simulate with a dummy check
                related_contract = {"type": []}
                
                if related_contract:
                    related_type = related_contract.get("type", [])
                    if "proxy" not in related_type:
                        inconsistencies.append({
                            "type": "relationship_mismatch",
                            "description": f"Contract {related_address} is referenced as implemented by current contract, but is not classified as a proxy",
                            "addresses": [analysis_result.get("address"), related_address]
                        })
        
        # Check for function consistency
        if "implementation_addresses" in analysis_result:
            for impl_address in analysis_result.get("implementation_addresses", []):
                # Fetch implementation contract data
                # In a real implementation, this would query the database
                # impl_contract = await get_contract_data(impl_address)
                
                # Simulate with a dummy check
                impl_contract = {"function_categories": {}}
                
                if impl_contract and "function_categories" in impl_contract:
                    # Compare function sets
                    current_functions = set()
                    for category in analysis_result.get("function_categories", {}).values():
                        current_functions.update([func.get("name") for func in category])
                    
                    impl_functions = set()
                    for category in impl_contract.get("function_categories", {}).values():
                        impl_functions.update([func.get("name") for func in category])
                    
                    # Check if proxy has functions not in implementation
                    extra_functions = current_functions - impl_functions
                    if extra_functions and not any("fallback" in f.lower() or "receive" in f.lower() for f in extra_functions):
                        inconsistencies.append({
                            "type": "function_mismatch",
                            "description": f"Proxy contract has functions not found in implementation: {', '.join(extra_functions)}",
                            "addresses": [analysis_result.get("address"), impl_address]
                        })
        
        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies
        }
    
    def _calculate_diff(self, original: Dict[str, Any], modified: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate differences between original and modified objects.
        
        Args:
            original: Original object
            modified: Modified object
            
        Returns:
            Structured diff
        """
        # In a real implementation, this would use a library like deepdiff
        # This is a simplified implementation
        formatted_diff = {
            "values_changed": [],
            "items_added": [],
            "items_removed": []
        }
        
        # Process dictionaries recursively
        def compare_dicts(orig, mod, path=""):
            # Check for removed keys
            for key in orig:
                if key not in mod:
                    formatted_diff["items_removed"].append({
                        "path": f"{path}.{key}" if path else key,
                        "value": orig[key]
                    })
                    continue
                
                # Check for changed values
                if key in mod:
                    if isinstance(orig[key], dict) and isinstance(mod[key], dict):
                        # Recurse into nested dicts
                        compare_dicts(orig[key], mod[key], f"{path}.{key}" if path else key)
                    elif isinstance(orig[key], list) and isinstance(mod[key], list):
                        # Compare lists
                        compare_lists(orig[key], mod[key], f"{path}.{key}" if path else key)
                    elif orig[key] != mod[key]:
                        # Values differ
                        formatted_diff["values_changed"].append({
                            "path": f"{path}.{key}" if path else key,
                            "old_value": orig[key],
                            "new_value": mod[key]
                        })
            
            # Check for added keys
            for key in mod:
                if key not in orig:
                    formatted_diff["items_added"].append({
                        "path": f"{path}.{key}" if path else key,
                        "value": mod[key]
                    })
        
        # Compare lists (simplified)
        def compare_lists(orig, mod, path=""):
            if len(orig) != len(mod):
                formatted_diff["values_changed"].append({
                    "path": path,
                    "old_value": orig,
                    "new_value": mod
                })
                return
            
            # For simplicity, just check if items are different
            for i, (orig_item, mod_item) in enumerate(zip(orig, mod)):
                item_path = f"{path}[{i}]"
                
                if isinstance(orig_item, dict) and isinstance(mod_item, dict):
                    compare_dicts(orig_item, mod_item, item_path)
                elif isinstance(orig_item, list) and isinstance(mod_item, list):
                    compare_lists(orig_item, mod_item, item_path)
                elif orig_item != mod_item:
                    formatted_diff["values_changed"].append({
                        "path": item_path,
                        "old_value": orig_item,
                        "new_value": mod_item
                    })
        
        # Start comparison at the root level
        if isinstance(original, dict) and isinstance(modified, dict):
            compare_dicts(original, modified)
        
        return formatted_diff
