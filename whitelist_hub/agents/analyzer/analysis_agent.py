"""Analysis agent for contract analysis."""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime

from crewai import Agent, Task, Crew

from ...utils.ai_client import AIClient
from ...prompts.prompt_manager import PromptManager
from ...utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Analysis agent for smart contract analysis."""
    
    def __init__(
        self,
        ai_client: AIClient,
        prompt_manager: PromptManager,
        blockchain_client: BlockchainClient
    ):
        """Initialize analysis agent.
        
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
        name: str = "Analyzer",
        goal: str = "Analyze smart contracts to detect, classify, and explain whitelist mechanisms and other key functionalities",
        backstory: Optional[str] = None,
        verbose: bool = True
    ) -> Agent:
        """Create a CrewAI agent for contract analysis.
        
        Args:
            name: Agent name
            goal: Agent goal
            backstory: Agent backstory
            verbose: Whether to enable verbose logging
            
        Returns:
            CrewAI Agent instance
        """
        if not backstory:
            backstory = """You are a specialized smart contract analysis agent with deep expertise
            in blockchain technology, Solidity, and smart contract patterns. You have analyzed
            thousands of contracts across multiple chains and can quickly identify key functions,
            security considerations, and whitelist implementations. You excel at categorizing
            contract functions, detecting proxy patterns, and explaining complex blockchain mechanisms
            in clear terms. Your technical depth allows you to recognize even the most subtle
            whitelist implementations."""
        
        # Custom callback to use ai_client
        async def callback_function(message):
            response = await self.ai_client.get_completion(message, temperature=0.1, max_tokens=4000)
            return response["choices"][0]["message"]["content"]
        
        # Create the agent
        self._agent = Agent(
            name=name,
            role="Smart Contract Analyzer",
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=False,
            tools=[
                self.analyze_contract_abi,
                self.detect_proxy_pattern,
                self.analyze_whitelist_mechanism,
                self.categorize_contract_functions,
                self.analyze_security_patterns
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
    
    async def analyze_contract_abi(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        abi_json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze contract ABI.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            abi_json: ABI JSON if already fetched
            
        Returns:
            ABI analysis result
        """
        try:
            # Get ABI if not provided
            if not abi_json:
                abi_json = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
            
            # Check if ABI is available
            if not abi_json:
                return {
                    "contract_address": contract_address,
                    "blockchain": blockchain,
                    "error": "ABI not available",
                    "has_abi": False,
                    "function_count": 0,
                    "function_categories": {}
                }
            
            # Extract functions and events
            functions = []
            events = []
            for item in abi_json:
                if "type" not in item:
                    continue
                
                if item["type"] == "function":
                    function_info = {
                        "name": item.get("name", ""),
                        "inputs": self._format_parameters(item.get("inputs", [])),
                        "outputs": self._format_parameters(item.get("outputs", [])),
                        "state_mutability": item.get("stateMutability", "")
                    }
                    functions.append(function_info)
                elif item["type"] == "event":
                    event_info = {
                        "name": item.get("name", ""),
                        "inputs": self._format_parameters(item.get("inputs", [])),
                        "anonymous": item.get("anonymous", False)
                    }
                    events.append(event_info)
            
            # Analyze functions to categorize them
            function_categories = self._categorize_functions(functions)
            
            # Check if contract has whitelist functionality
            has_whitelist = self._has_whitelist_functionality(functions, events)
            
            # Check if contract has owner/admin functionality
            has_owner = self._has_owner_functionality(functions)
            
            # Combine all analyses
            result = {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "has_abi": True,
                "function_count": len(functions),
                "event_count": len(events),
                "functions": functions,
                "events": events,
                "function_categories": function_categories,
                "has_whitelist": has_whitelist,
                "has_owner": has_owner
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing contract ABI {contract_address}: {e}")
            return {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "error": str(e),
                "has_abi": False,
                "function_count": 0,
                "function_categories": {}
            }
    
    async def detect_proxy_pattern(
        self,
        contract_address: str,
        blockchain: str = "ethereum"
    ) -> Dict[str, Any]:
        """Detect if contract uses a proxy pattern.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Proxy detection result
        """
        try:
            # Get ABI
            abi_json = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
            
            # Check if ABI is available
            if not abi_json:
                return {
                    "contract_address": contract_address,
                    "blockchain": blockchain,
                    "is_proxy": False,
                    "proxy_type": "unknown",
                    "confidence": 0,
                    "implementation_address": None
                }
            
            # Look for proxy patterns in functions
            proxy_indicators = {
                "eip1967": 0,
                "eip897": 0,
                "gnosis": 0,
                "minimal": 0,
                "diamond": 0
            }
            
            implementation_address = None
            
            # Check for function names indicating proxy patterns
            for item in abi_json:
                if item.get("type") != "function":
                    continue
                
                function_name = item.get("name", "").lower()
                
                # EIP-1967 indicators
                if function_name in ["implementation", "getimplementation", "proxiablesuuid"]:
                    proxy_indicators["eip1967"] += 2
                
                # EIP-897 indicators
                if function_name in ["implementation", "isproxy"]:
                    proxy_indicators["eip897"] += 2
                
                # Gnosis Safe/MultiSig proxy indicators
                if function_name in ["mastercopy", "getmastercopy"]:
                    proxy_indicators["gnosis"] += 2
                
                # Diamond/Facet proxy pattern (EIP-2535)
                if function_name in ["diamondcut", "facets", "facetaddress", "facetfunctionselectors"]:
                    proxy_indicators["diamond"] += 2
                
                # Minimal proxy indicators
                if function_name in ["delegate", "delegatecall", "forwarded"]:
                    proxy_indicators["minimal"] += 1
                
                # Try to get implementation address if available directly
                if function_name in ["implementation", "getimplementation", "mastercopy", "getmastercopy"]:
                    try:
                        # Call the function to get implementation address
                        # This would typically use blockchain_client but simplified here
                        address = await self.blockchain_client.call_contract_function(
                            contract_address, blockchain, function_name, []
                        )
                        if address and isinstance(address, str) and address.startswith("0x"):
                            implementation_address = address
                    except Exception as e:
                        logger.debug(f"Error getting implementation address: {e}")
            
            # Look for fallback or receive functions (common in proxies)
            has_fallback = any(item.get("type") == "fallback" for item in abi_json)
            has_receive = any(item.get("type") == "receive" for item in abi_json)
            
            if has_fallback:
                proxy_indicators["minimal"] += 1
            
            # If no implementation found via function call, try to read storage slots
            if not implementation_address:
                # EIP-1967 implementation slot
                try:
                    slot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
                    address = await self.blockchain_client.read_contract_storage(
                        contract_address, blockchain, slot
                    )
                    if address and address.startswith("0x"):
                        implementation_address = address
                        proxy_indicators["eip1967"] += 3
                except Exception as e:
                    logger.debug(f"Error reading EIP-1967 slot: {e}")
                
                # Try legacy proxy slot (OpenZeppelin)
                if not implementation_address:
                    try:
                        slot = "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3"
                        address = await self.blockchain_client.read_contract_storage(
                            contract_address, blockchain, slot
                        )
                        if address and address.startswith("0x"):
                            implementation_address = address
                            proxy_indicators["eip897"] += 3
                    except Exception as e:
                        logger.debug(f"Error reading legacy proxy slot: {e}")
            
            # Determine if contract is a proxy
            max_indicator = max(proxy_indicators.values())
            is_proxy = max_indicator >= 2 or (has_fallback and max_indicator >= 1) or implementation_address is not None
            
            # Determine proxy type
            proxy_type = "unknown"
            if is_proxy:
                proxy_type = max(proxy_indicators.items(), key=lambda x: x[1])[0]
            
            # Calculate confidence
            confidence = 0
            if is_proxy:
                # Base confidence on the strength of indicators
                confidence = min(max_indicator / 4, 1.0)
                # Increase confidence if implementation address found
                if implementation_address:
                    confidence = min(confidence + 0.3, 1.0)
                # Increase confidence if fallback exists
                if has_fallback:
                    confidence = min(confidence + 0.1, 1.0)
            
            result = {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "is_proxy": is_proxy,
                "proxy_type": proxy_type,
                "confidence": confidence,
                "implementation_address": implementation_address,
                "has_fallback": has_fallback,
                "has_receive": has_receive,
                "proxy_indicators": proxy_indicators
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting proxy pattern for {contract_address}: {e}")
            return {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "error": str(e),
                "is_proxy": False,
                "proxy_type": "unknown",
                "confidence": 0,
                "implementation_address": None
            }
    
    async def analyze_whitelist_mechanism(
        self,
        contract_address: str,
        contract_data: Dict[str, Any],
        blockchain: str = "ethereum"
    ) -> Dict[str, Any]:
        """Analyze whitelist mechanism in a contract.
        
        Args:
            contract_address: Contract address
            contract_data: Contract data from previous analysis
            blockchain: Blockchain name
            
        Returns:
            Whitelist mechanism analysis
        """
        try:
            # Check if contract has whitelist functionality
            if not contract_data.get("has_whitelist", False):
                return {
                    "contract_address": contract_address,
                    "blockchain": blockchain,
                    "has_whitelist": False,
                    "mechanism_type": "none",
                    "whitelist_functions": [],
                    "description": "No whitelist functionality detected"
                }
            
            # Extract whitelist-related functions
            functions = contract_data.get("functions", [])
            whitelist_functions = []
            
            for function in functions:
                name = function.get("name", "").lower()
                
                # Check for whitelist-related function names
                if any(term in name for term in ["whitelist", "allowlist", "allowed", "permit"]):
                    whitelist_functions.append(function)
                
                # Check for access control function with address parameters
                elif any(term in name for term in ["access", "authorize", "permission", "role"]):
                    # Check if function has address parameter
                    inputs = function.get("inputs", [])
                    if any("address" in param.get("type", "") for param in inputs):
                        whitelist_functions.append(function)
            
            # Look for whitelist-related mappings in storage (simplified)
            # In a real implementation, this would analyze storage layout and state
            
            # Determine whitelist mechanism type
            mechanism_type = "unknown"
            is_merkle = False
            is_signature = False
            is_mapping = False
            is_tiered = False
            is_time_limited = False
            
            # Analyze function names and parameters for mechanism type
            for function in whitelist_functions:
                name = function.get("name", "").lower()
                inputs = function.get("inputs", [])
                
                # Check for Merkle proof mechanism
                if any(term in name for term in ["merkle", "proof", "verify"]):
                    is_merkle = True
                
                # Check for signature verification
                if any(term in name for term in ["signature", "verify", "sign"]):
                    is_signature = True
                
                # Check for tiered whitelist
                if any(term in name for term in ["tier", "level", "group", "role"]):
                    is_tiered = True
                
                # Check for time-limited whitelist
                if any(term in name for term in ["time", "expiry", "deadline", "valid"]):
                    is_time_limited = True
                
                # Check for simple mapping (address => bool)
                if any(term in name for term in ["add", "remove", "set", "update"]) and len(inputs) > 0:
                    if "address" in inputs[0].get("type", ""):
                        is_mapping = True
            
            # Determine the primary mechanism type
            if is_merkle:
                mechanism_type = "merkle_proof"
            elif is_signature:
                mechanism_type = "signature_based"
            elif is_mapping:
                mechanism_type = "mapping_based"
            elif is_tiered:
                mechanism_type = "tiered_access"
            else:
                mechanism_type = "basic"
            
            # Determine data storage approach
            data_storage = "unknown"
            if is_merkle:
                data_storage = "merkle"
            elif is_mapping:
                data_storage = "mapping"
            elif is_signature:
                data_storage = "offchain"
                
            # Generate description
            description = f"This contract implements a {mechanism_type} whitelist mechanism"
            if is_tiered:
                description += " with tiered access levels"
            if is_time_limited:
                description += " and time-limited validity"
            description += f". Whitelist data is stored using {data_storage} approach."
            
            result = {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "has_whitelist": True,
                "mechanism_type": mechanism_type,
                "whitelist_functions": whitelist_functions,
                "is_tiered": is_tiered,
                "is_time_limited": is_time_limited,
                "data_storage": data_storage,
                "description": description
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing whitelist mechanism for {contract_address}: {e}")
            return {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "error": str(e),
                "has_whitelist": False,
                "mechanism_type": "unknown",
                "whitelist_functions": []
            }
    
    async def categorize_contract_functions(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        functions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, List[str]]:
        """Categorize contract functions by purpose.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            functions: List of functions if already available
            
        Returns:
            Categories of functions
        """
        try:
            # Get functions if not provided
            if not functions:
                abi_json = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
                if not abi_json:
                    return {}
                
                functions = []
                for item in abi_json:
                    if item.get("type") == "function":
                        function_info = {
                            "name": item.get("name", ""),
                            "inputs": self._format_parameters(item.get("inputs", [])),
                            "outputs": self._format_parameters(item.get("outputs", [])),
                            "state_mutability": item.get("stateMutability", "")
                        }
                        functions.append(function_info)
            
            return self._categorize_functions(functions)
            
        except Exception as e:
            logger.error(f"Error categorizing functions for {contract_address}: {e}")
            return {}
    
    async def analyze_security_patterns(
        self,
        contract_address: str,
        blockchain: str = "ethereum",
        contract_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze contract security patterns.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            contract_data: Contract data from previous analysis
            
        Returns:
            Security pattern analysis
        """
        try:
            # Get contract data if not provided
            if not contract_data:
                abi_json = await self.blockchain_client.fetch_contract_abi(contract_address, blockchain)
                if not abi_json:
                    return {
                        "contract_address": contract_address,
                        "blockchain": blockchain,
                        "error": "ABI not available",
                        "patterns_detected": {},
                        "risk_level": "unknown"
                    }
                
                # Generate basic contract data
                functions = []
                for item in abi_json:
                    if item.get("type") == "function":
                        function_info = {
                            "name": item.get("name", ""),
                            "inputs": self._format_parameters(item.get("inputs", [])),
                            "outputs": self._format_parameters(item.get("outputs", [])),
                            "state_mutability": item.get("stateMutability", "")
                        }
                        functions.append(function_info)
                
                contract_data = {
                    "functions": functions
                }
            
            # Initialize patterns
            patterns_detected = {
                "reentrancy_protection": False,
                "access_control": False,
                "input_validation": False,
                "secure_transfers": False,
                "pausable": False,
                "upgradeable": False,
                "oracle_usage": False,
                "overflow_protection": False
            }
            
            functions = contract_data.get("functions", [])
            function_names = [f.get("name", "").lower() for f in functions]
            
            # Check for reentrancy protection
            for function in functions:
                modifiers = function.get("modifiers", [])
                if any(mod in modifiers for mod in ["nonReentrant", "reentrancyGuard"]):
                    patterns_detected["reentrancy_protection"] = True
                    break
            
            # Check for access control
            if any(name in function_names for name in ["onlyowner", "onlyadmin", "onlyrole", "require", "authorize"]):
                patterns_detected["access_control"] = True
            
            # Check for input validation
            if any(name in function_names for name in ["require", "validate", "check"]):
                patterns_detected["input_validation"] = True
            
            # Check for secure transfers
            if any(name in function_names for name in ["safetransferfrom", "safetransfer", "transfer"]):
                patterns_detected["secure_transfers"] = True
            
            # Check for pausable
            if any(name in function_names for name in ["pause", "unpause", "paused"]):
                patterns_detected["pausable"] = True
            
            # Check for upgradeable
            proxy_result = await self.detect_proxy_pattern(contract_address, blockchain)
            patterns_detected["upgradeable"] = proxy_result.get("is_proxy", False)
            
            # Check for oracle usage
            if any(name in function_names for name in ["oracle", "price", "feedvalue", "getprice", "getlatest"]):
                patterns_detected["oracle_usage"] = True
            
            # Check for overflow protection (all contracts after Solidity 0.8.0 have this by default)
            if any(name in function_names for name in ["safemul", "safemul", "safeadd", "safesub"]):
                patterns_detected["overflow_protection"] = True
            
            # Calculate risk level based on patterns
            risk_score = sum([
                2 if patterns_detected["reentrancy_protection"] else 0,
                2 if patterns_detected["access_control"] else 0,
                1 if patterns_detected["input_validation"] else 0,
                1 if patterns_detected["secure_transfers"] else 0,
                1 if patterns_detected["pausable"] else 0,
                2 if patterns_detected["upgradeable"] else 0,
                1 if patterns_detected["overflow_protection"] else 0
            ])
            
            # Determine risk level
            risk_level = "high"
            if risk_score >= 7:
                risk_level = "low"
            elif risk_score >= 4:
                risk_level = "medium"
            
            result = {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "patterns_detected": patterns_detected,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "findings": self._generate_security_findings(patterns_detected)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing security patterns for {contract_address}: {e}")
            return {
                "contract_address": contract_address,
                "blockchain": blockchain,
                "error": str(e),
                "patterns_detected": {},
                "risk_level": "unknown"
            }
    
    def _format_parameters(self, params: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format parameters from ABI format.
        
        Args:
            params: Parameters from ABI
            
        Returns:
            Formatted parameters
        """
        formatted = []
        for param in params:
            formatted.append({
                "name": param.get("name", ""),
                "type": param.get("type", "")
            })
        return formatted
    
    def _categorize_functions(self, functions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Categorize functions by purpose.
        
        Args:
            functions: List of functions
            
        Returns:
            Categories of functions
        """
        categories = {
            "admin": [],
            "user": [],
            "view": [],
            "whitelist": [],
            "token": [],
            "metadata": [],
            "utility": [],
            "security": [],
            "proxy": [],
            "unknown": []
        }
        
        for function in functions:
            name = function.get("name", "").lower()
            state_mutability = function.get("state_mutability", "")
            
            # Admin functions
            if any(term in name for term in ["owner", "admin", "set", "add", "remove", "grant", "revoke"]):
                categories["admin"].append(name)
                continue
                
            # Whitelist functions
            if any(term in name for term in ["whitelist", "allowlist", "allowed", "permit", "authorize"]):
                categories["whitelist"].append(name)
                continue
                
            # Token functions
            if any(term in name for term in ["transfer", "approve", "allowance", "balance", "mint", "burn"]):
                categories["token"].append(name)
                continue
                
            # Metadata functions
            if any(term in name for term in ["name", "symbol", "decimals", "uri", "metadata"]):
                categories["metadata"].append(name)
                continue
                
            # View functions (read-only)
            if state_mutability in ["view", "pure"]:
                categories["view"].append(name)
                continue
                
            # Security functions
            if any(term in name for term in ["pause", "unpause", "lock", "unlock", "emergency"]):
                categories["security"].append(name)
                continue
                
            # Proxy functions
            if any(term in name for term in ["implementation", "delegate", "proxy", "upgrade"]):
                categories["proxy"].append(name)
                continue
                
            # User-facing interaction functions
            if any(term in name for term in ["buy", "sell", "swap", "deposit", "withdraw", "claim", "stake"]):
                categories["user"].append(name)
                continue
                
            # Utility functions
            if any(term in name for term in ["calculate", "get", "convert", "check", "is", "has"]):
                categories["utility"].append(name)
                continue
                
            # Default to unknown
            categories["unknown"].append(name)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _has_whitelist_functionality(self, functions: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> bool:
        """Check if contract has whitelist functionality.
        
        Args:
            functions: List of functions
            events: List of events
            
        Returns:
            True if whitelist functionality detected, False otherwise
        """
        # Check function names
        function_names = [f.get("name", "").lower() for f in functions]
        if any(any(term in name for term in ["whitelist", "allowlist", "allowed", "permit"]) for name in function_names):
            return True
            
        # Check event names
        event_names = [e.get("name", "").lower() for e in events]
        if any(any(term in name for term in ["whitelist", "allowlist", "allowed", "permit"]) for name in event_names):
            return True
            
        # Check for mapping-like functions with address parameters
        for function in functions:
            name = function.get("name", "").lower()
            inputs = function.get("inputs", [])
            
            if any(term in name for term in ["add", "remove", "set", "is", "check"]):
                if any("address" in input.get("type", "") for input in inputs):
                    if any(term in name for term in ["authorized", "permission", "access", "role"]):
                        return True
        
        return False
    
    def _has_owner_functionality(self, functions: List[Dict[str, Any]]) -> bool:
        """Check if contract has owner functionality.
        
        Args:
            functions: List of functions
            
        Returns:
            True if owner functionality detected, False otherwise
        """
        function_names = [f.get("name", "").lower() for f in functions]
        return any(any(term in name for term in ["owner", "admin", "onlyowner", "onlyadmin"]) for name in function_names)
    
    def _generate_security_findings(self, patterns: Dict[str, bool]) -> List[Dict[str, str]]:
        """Generate security findings based on detected patterns.
        
        Args:
            patterns: Detected security patterns
            
        Returns:
            List of security findings
        """
        findings = []
        
        if not patterns.get("reentrancy_protection", False):
            findings.append({
                "severity": "high",
                "title": "Missing Reentrancy Protection",
                "description": "Contract does not implement explicit reentrancy protection. Consider using ReentrancyGuard."
            })
            
        if not patterns.get("access_control", False):
            findings.append({
                "severity": "high",
                "title": "Missing Access Control",
                "description": "Contract does not implement access control for privileged functions."
            })
            
        if not patterns.get("input_validation", False):
            findings.append({
                "severity": "medium",
                "title": "Lacking Input Validation",
                "description": "Contract may not properly validate inputs, leading to unexpected behavior."
            })
            
        if not patterns.get("pausable", False) and patterns.get("upgradeable", False):
            findings.append({
                "severity": "medium",
                "title": "Upgradeable Without Pause Mechanism",
                "description": "Upgradeable contract without pause functionality can lead to issues during upgrades."
            })
            
        if patterns.get("oracle_usage", False) and not patterns.get("input_validation", False):
            findings.append({
                "severity": "high",
                "title": "Unvalidated Oracle Data",
                "description": "Contract uses oracle data without proper validation, risking manipulation."
            })
            
        return findings
