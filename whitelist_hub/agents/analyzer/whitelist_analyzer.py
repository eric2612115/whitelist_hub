"""Whitelist mechanism analysis component."""

import logging
import re
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


class WhitelistAnalyzer:
    """Component for analyzing whitelist mechanisms in contracts."""
    
    def analyze_pattern(
        self,
        whitelist_functions: List[Dict[str, Any]],
        source_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze whitelist implementation pattern.
        
        Args:
            whitelist_functions: Whitelist-related functions
            source_code: Contract source code if available
            
        Returns:
            Whitelist pattern analysis
        """
        analysis = {
            "mechanism_detected": False,
            "mechanism_type": "unknown",
            "key_functions": [],
            "tiered": False,
            "time_limited": False,
            "transferable": False,
            "confidence": 0.0
        }
        
        # If no whitelist functions, return early
        if not whitelist_functions:
            return analysis
        
        # Collect function names and properties
        function_names = [func.get("name", "").lower() for func in whitelist_functions]
        function_signatures = [func.get("signature", "") for func in whitelist_functions]
        
        # Mark as detected since we have whitelist functions
        analysis["mechanism_detected"] = True
        analysis["key_functions"] = [func.get("name") for func in whitelist_functions]
        
        # Classify mechanism type
        mechanism_type = self._classify_mechanism_type(function_names, whitelist_functions, source_code)
        analysis["mechanism_type"] = mechanism_type
        
        # Check for tiered structure
        analysis["tiered"] = self._check_tiered_whitelist(function_names, source_code)
        
        # Check for time limitations
        analysis["time_limited"] = self._check_time_limited(function_names, whitelist_functions, source_code)
        
        # Check for transferability
        analysis["transferable"] = self._check_transferable(function_names, source_code)
        
        # Additional properties from source code if available
        if source_code:
            additional_props = self._extract_additional_properties(source_code)
            analysis.update(additional_props)
        
        # Calculate confidence based on available information
        confidence = 0.6  # Base confidence since we have identified functions
        
        if source_code:
            confidence += 0.2  # Higher confidence with source code
        
        if mechanism_type != "unknown":
            confidence += 0.2  # Higher confidence with identified mechanism type
        
        analysis["confidence"] = confidence
        
        return analysis
    
    def _classify_mechanism_type(
        self,
        function_names: List[str],
        whitelist_functions: List[Dict[str, Any]],
        source_code: Optional[str]
    ) -> str:
        """Classify the type of whitelist mechanism.
        
        Args:
            function_names: Function names
            whitelist_functions: Whitelist function details
            source_code: Contract source code if available
            
        Returns:
            Mechanism type classification
        """
        # Check for common patterns in function names
        merkle_indicators = ["merkle", "proof", "verify", "root"]
        mapping_indicators = ["mapping", "list", "set", "add", "remove"]
        token_indicators = ["token", "balance", "owner", "hold"]
        
        # Look for indicators in function names
        if any(indicator in ' '.join(function_names) for indicator in merkle_indicators):
            return "merkle"
        
        if any(indicator in ' '.join(function_names) for indicator in mapping_indicators):
            return "mapping"
        
        if any(indicator in ' '.join(function_names) for indicator in token_indicators):
            return "token-based"
        
        # Check source code if available
        if source_code:
            source_lower = source_code.lower()
            
            if "merkle" in source_lower or "keccak256" in source_lower and "proof" in source_lower:
                return "merkle"
            
            if "mapping(address => bool)" in source_lower:
                return "mapping"
            
            if "balanceof" in source_lower and "whitelist" in source_lower:
                return "token-based"
        
        # Check function inputs for clues
        for func in whitelist_functions:
            inputs = func.get("inputs", [])
            
            # Check for merkle proof inputs
            proof_inputs = [inp for inp in inputs if "proof" in inp.get("name", "").lower()]
            if proof_inputs and any(inp.get("type", "") == "bytes32[]" for inp in proof_inputs):
                return "merkle"
            
            # Check for address inputs in setters (typical for mappings)
            if "add" in func.get("name", "").lower() or "set" in func.get("name", "").lower():
                address_inputs = [inp for inp in inputs if inp.get("type", "") == "address"]
                if address_inputs:
                    return "mapping"
        
        # Default if no clear indicators
        return "unknown"
    
    def _check_tiered_whitelist(self, function_names: List[str], source_code: Optional[str]) -> bool:
        """Check if whitelist has tiered structure.
        
        Args:
            function_names: Function names
            source_code: Contract source code if available
            
        Returns:
            Whether whitelist appears to be tiered
        """
        # Look for tier indicators in function names
        tier_indicators = ["tier", "level", "stage", "phase", "group", "category"]
        
        if any(indicator in ' '.join(function_names) for indicator in tier_indicators):
            return True
        
        # Check source code if available
        if source_code:
            source_lower = source_code.lower()
            
            # Look for tiered structure patterns
            if "enum" in source_lower and any(indicator in source_lower for indicator in tier_indicators):
                return True
            
            if "mapping(address => uint" in source_lower and "tier" in source_lower:
                return True
            
            # Look for multiple whitelist variables
            whitelist_vars = re.findall(r'(whitelist\w+|allowlist\w+)', source_lower)
            if len(set(whitelist_vars)) > 1:
                return True
        
        return False
    
    def _check_time_limited(
        self,
        function_names: List[str],
        whitelist_functions: List[Dict[str, Any]],
        source_code: Optional[str]
    ) -> bool:
        """Check if whitelist has time limitations.
        
        Args:
            function_names: Function names
            whitelist_functions: Whitelist function details
            source_code: Contract source code if available
            
        Returns:
            Whether whitelist appears to be time-limited
        """
        # Look for time indicators in function names
        time_indicators = ["time", "period", "duration", "start", "end", "deadline", "open", "close"]
        
        if any(indicator in ' '.join(function_names) for indicator in time_indicators):
            return True
        
        # Check source code if available
        if source_code:
            source_lower = source_code.lower()
            
            # Look for time variables
            if "uint" in source_lower and any(f"{indicator} " in source_lower for indicator in time_indicators):
                return True
            
            # Look for block.timestamp comparisons
            if "block.timestamp" in source_lower and "require" in source_lower:
                return True
            
            # Look for specific time patterns
            if "starttime" in source_lower or "endtime" in source_lower:
                return True
        
        # Check for time parameters in functions
        for func in whitelist_functions:
            inputs = func.get("inputs", [])
            
            # Check for uint inputs with time-related names
            time_inputs = [
                inp for inp in inputs 
                if inp.get("type", "").startswith("uint") and 
                any(indicator in inp.get("name", "").lower() for indicator in time_indicators)
            ]
            
            if time_inputs:
                return True
        
        return False
    
    def _check_transferable(self, function_names: List[str], source_code: Optional[str]) -> bool:
        """Check if whitelist spots are transferable.
        
        Args:
            function_names: Function names
            source_code: Contract source code if available
            
        Returns:
            Whether whitelist spots appear to be transferable
        """
        # Look for transfer indicators in function names
        transfer_indicators = ["transfer", "delegate", "assign", "grant"]
        
        if any(indicator in ' '.join(function_names) for indicator in transfer_indicators):
            return True
        
        # Check source code if available
        if source_code:
            source_lower = source_code.lower()
            
            # Look for transfer function patterns
            for indicator in transfer_indicators:
                if indicator in source_lower and "address" in source_lower:
                    pattern = rf'function\s+{indicator}\w*\s*\(\s*address\s+'
                    if re.search(pattern, source_lower):
                        return True
        
        return False
    
    def _extract_additional_properties(self, source_code: str) -> Dict[str, Any]:
        """Extract additional whitelist properties from source code.
        
        Args:
            source_code: Contract source code
            
        Returns:
            Additional properties
        """
        properties = {}
        
        # Extract storage mechanism
        if "mapping(address => bool)" in source_code.lower():
            properties["data_storage"] = "onchain"
        elif "merkle" in source_code.lower():
            properties["data_storage"] = "merkle"
        
        # Extract access control mechanism
        if "onlyowner" in source_code.lower():
            properties["access_control"] = "ownership"
        elif "onlyrole" in source_code.lower():
            properties["access_control"] = "role-based"
        elif "require(msg.sender" in source_code.lower():
            properties["access_control"] = "simple-auth"
        
        return properties
    
    def extract_whitelist_details_from_source(self, source_code: str) -> Dict[str, Any]:
        """Extract detailed whitelist information from source code.
        
        Args:
            source_code: Contract source code
            
        Returns:
            Detailed whitelist information
        """
        details = {
            "variables": [],
            "modifiers": [],
            "events": []
        }
        
        # Extract whitelist-related variables
        var_pattern = r'(mapping\s*\(\s*address\s*=>\s*\w+\s*\)|bytes32)\s+(?:public\s+|private\s+|internal\s+)?\s*(\w+(?:whitelist|allowlist|merkle|eligible)\w*)\s*;'
        var_matches = re.findall(var_pattern, source_code, re.IGNORECASE)
        
        for var_type, var_name in var_matches:
            details["variables"].append({
                "name": var_name,
                "type": var_type.strip()
            })
        
        # Extract whitelist-related modifiers
        modifier_pattern = r'modifier\s+(\w*(?:whitelist|allowlist|eligible|member)\w*)\s*\('
        modifier_matches = re.findall(modifier_pattern, source_code, re.IGNORECASE)
        
        for modifier_name in modifier_matches:
            details["modifiers"].append({
                "name": modifier_name
            })
        
        # Extract whitelist-related events
        event_pattern = r'event\s+(\w*(?:whitelist|allowlist|eligible|member)\w*)\s*\('
        event_matches = re.findall(event_pattern, source_code, re.IGNORECASE)
        
        for event_name in event_matches:
            details["events"].append({
                "name": event_name
            })
        
        return details
