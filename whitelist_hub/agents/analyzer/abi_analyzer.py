"""ABI analysis component."""

import logging
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)


class ABIAnalyzer:
    """Component for analyzing contract ABIs."""
    
    def analyze_structure(self, abi_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ABI structure to extract key metrics and patterns.
        
        Args:
            abi_json: Contract ABI
            
        Returns:
            ABI structure analysis
        """
        structure = {
            "function_count": 0,
            "event_count": 0,
            "read_functions": 0,
            "write_functions": 0,
            "payable_functions": 0,
            "function_categories": {
                "admin": [],
                "user": [],
                "internal": [],
                "view": []
            }
        }
        
        admin_patterns = [
            "admin", "owner", "pause", "unpause", "upgrade", "withdraw",
            "set", "add", "remove", "blacklist", "authorize", "grant"
        ]
        
        for item in abi_json:
            item_type = item.get("type")
            
            if item_type == "function":
                structure["function_count"] += 1
                
                # Analyze state mutability
                state_mutability = item.get("stateMutability", "")
                if state_mutability in ["view", "pure"]:
                    structure["read_functions"] += 1
                    structure["function_categories"]["view"].append(item.get("name"))
                else:
                    structure["write_functions"] += 1
                
                if state_mutability == "payable":
                    structure["payable_functions"] += 1
                
                # Categorize by naming patterns
                function_name = item.get("name", "").lower()
                if any(pattern in function_name for pattern in admin_patterns):
                    structure["function_categories"]["admin"].append(item.get("name"))
                elif function_name.startswith("_"):
                    structure["function_categories"]["internal"].append(item.get("name"))
                else:
                    structure["function_categories"]["user"].append(item.get("name"))
                    
            elif item_type == "event":
                structure["event_count"] += 1
        
        return structure
    
    def identify_standard_interfaces(self, abi_json: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify standard interfaces implemented by the contract.
        
        Args:
            abi_json: Contract ABI
            
        Returns:
            Standard interfaces identification
        """
        # Map of interface -> required function signatures
        standard_interfaces = {
            "ERC20": {
                "functions": [
                    "totalSupply()",
                    "balanceOf(address)",
                    "transfer(address,uint256)",
                    "allowance(address,address)",
                    "approve(address,uint256)",
                    "transferFrom(address,address,uint256)"
                ],
                "events": [
                    "Transfer(address,address,uint256)",
                    "Approval(address,address,uint256)"
                ]
            },
            "ERC721": {
                "functions": [
                    "balanceOf(address)",
                    "ownerOf(uint256)",
                    "safeTransferFrom(address,address,uint256)",
                    "transferFrom(address,address,uint256)",
                    "approve(address,uint256)",
                    "getApproved(uint256)",
                    "setApprovalForAll(address,bool)",
                    "isApprovedForAll(address,address)"
                ],
                "events": [
                    "Transfer(address,address,uint256)",
                    "Approval(address,address,uint256)",
                    "ApprovalForAll(address,address,bool)"
                ]
            },
            "AccessControl": {
                "functions": [
                    "hasRole(bytes32,address)",
                    "getRoleAdmin(bytes32)",
                    "grantRole(bytes32,address)",
                    "revokeRole(bytes32,address)",
                    "renounceRole(bytes32,address)"
                ],
                "events": [
                    "RoleGranted(bytes32,address,address)",
                    "RoleRevoked(bytes32,address,address)",
                    "RoleAdminChanged(bytes32,bytes32,bytes32)"
                ]
            },
            "Ownable": {
                "functions": [
                    "owner()",
                    "transferOwnership(address)"
                ],
                "events": [
                    "OwnershipTransferred(address,address)"
                ]
            }
        }
        
        # Helper function to get function signature
        def get_function_signature(func):
            name = func.get("name", "")
            inputs = func.get("inputs", [])
            input_types = [inp.get("type", "") for inp in inputs]
            return f"{name}({','.join(input_types)})"
        
        # Helper function to get event signature
        def get_event_signature(event):
            name = event.get("name", "")
            inputs = event.get("inputs", [])
            input_types = [f"{inp.get('type', '')}" for inp in inputs]
            return f"{name}({','.join(input_types)})"
        
        # Extract function and event signatures from ABI
        contract_functions = set()
        contract_events = set()
        
        for item in abi_json:
            if item.get("type") == "function":
                contract_functions.add(get_function_signature(item))
            elif item.get("type") == "event":
                contract_events.add(get_event_signature(item))
        
        # Check each interface
        implemented_interfaces = {}
        
        for interface, required in standard_interfaces.items():
            required_functions = set(required.get("functions", []))
            required_events = set(required.get("events", []))
            
            matched_functions = required_functions.intersection(contract_functions)
            matched_events = required_events.intersection(contract_events)
            
            # Calculate implementation percentage
            total_required = len(required_functions) + len(required_events)
            total_matched = len(matched_functions) + len(matched_events)
            
            implementation_percentage = (total_matched / total_required * 100) if total_required else 0
            
            if implementation_percentage >= 95:
                implemented_interfaces[interface] = {
                    "fully_implemented": True,
                    "implementation_percentage": 100,
                    "missing_items": []
                }
            elif implementation_percentage >= 50:
                missing_functions = required_functions - contract_functions
                missing_events = required_events - contract_events
                missing_items = list(missing_functions) + list(missing_events)
                
                implemented_interfaces[interface] = {
                    "fully_implemented": False,
                    "implementation_percentage": implementation_percentage,
                    "missing_items": missing_items
                }
        
        return implemented_interfaces
    
    def classify_functions(self, abi: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify contract functions by purpose.
        
        Args:
            abi: Contract ABI
            
        Returns:
            Classified functions by category
        """
        categories = {
            "whitelist": [],
            "token_sale": [],
            "staking": [],
            "governance": [],
            "utility": [],
            "security": [],
            "upgrade": [],
            "admin": [],
            "uncategorized": []
        }
        
        # Function classification patterns
        patterns = {
            "whitelist": [
                "whitelist", "allowlist", "isWhitelisted", "merkle", "proof",
                "eligib", "allowed", "permit", "canParticipate"
            ],
            "token_sale": [
                "buy", "purchase", "contribute", "sale", "deposit", "presale",
                "claim", "allocation", "refund", "withdraw", "distribute"
            ],
            "staking": [
                "stake", "unstake", "reward", "farm", "yield", "harvest",
                "interest", "apy", "apr", "compound", "lock", "unlock"
            ],
            "governance": [
                "vote", "propose", "proposal", "delegate", "governance", "dao",
                "quorum", "ballot", "motion", "execute"
            ],
            "security": [
                "pause", "unpause", "emergency", "stop", "auth", "access",
                "guard", "protect", "secure", "verify"
            ],
            "upgrade": [
                "upgrade", "implementation", "initialize", "proxy", "logic",
                "update", "version", "migrate"
            ],
            "admin": [
                "admin", "owner", "manage", "control", "set", "add", "remove",
                "grant", "revoke", "role"
            ]
        }
        
        for func in abi:
            if func.get("type") != "function":
                continue
                
            name = func.get("name", "").lower()
            if not name:  # Skip fallback/receive functions
                continue
                
            # Create function item
            inputs = func.get("inputs", [])
            outputs = func.get("outputs", [])
            state_mutability = func.get("stateMutability", "")
            
            function_item = {
                "name": func.get("name"),
                "signature": self._get_function_signature(func),
                "inputs": inputs,
                "outputs": outputs,
                "state_mutability": state_mutability,
                "is_entry_point": not name.startswith("_") and state_mutability != "view" and state_mutability != "pure",
                "requires_auth": self._check_requires_auth(name, inputs),
                "user_accessible": not name.startswith("_") and not self._check_requires_auth(name, inputs)
            }
            
            # Check each category
            categorized = False
            
            for category, keywords in patterns.items():
                if any(keyword in name for keyword in keywords):
                    categories[category].append(function_item)
                    categorized = True
                    break
            
            # If still not categorized, check if it's a utility function
            if not categorized:
                if state_mutability in ["view", "pure"]:
                    categories["utility"].append(function_item)
                else:
                    categories["uncategorized"].append(function_item)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def verify_interface_implementation(self, abi: List[Dict[str, Any]], interface_name: str) -> Dict[str, Any]:
        """Verify if contract implements a specific interface.
        
        Args:
            abi: Contract ABI
            interface_name: Name of interface to check
            
        Returns:
            Verification result
        """
        standard_interfaces = self.identify_standard_interfaces(abi)
        
        if interface_name in standard_interfaces:
            return {
                "implements": True,
                "implementation_details": standard_interfaces[interface_name]
            }
        
        return {
            "implements": False,
            "message": f"Contract does not implement {interface_name} interface"
        }
    
    def _get_function_signature(self, func: Dict[str, Any]) -> str:
        """Get function signature string.
        
        Args:
            func: Function data
            
        Returns:
            Function signature
        """
        name = func.get("name", "")
        inputs = func.get("inputs", [])
        input_types = [inp.get("type", "") for inp in inputs]
        
        return f"{name}({','.join(input_types)})"
    
    def _check_requires_auth(self, name: str, inputs: List[Dict[str, Any]]) -> bool:
        """Check if function likely requires authentication.
        
        Args:
            name: Function name
            inputs: Function inputs
            
        Returns:
            Whether function likely requires auth
        """
        admin_patterns = [
            "admin", "owner", "manage", "set", "add", "remove", "grant",
            "revoke", "change", "create", "delete", "pause", "unpause"
        ]
        
        # Check name for admin patterns
        if any(pattern in name.lower() for pattern in admin_patterns):
            return True
        
        # Check for onlyX modifiers in name
        if name.startswith("only") or "_only" in name:
            return True
        
        # Check for role/admin inputs
        for inp in inputs:
            inp_name = inp.get("name", "").lower()
            inp_type = inp.get("type", "").lower()
            
            if "role" in inp_name or "admin" in inp_name:
                return True
            
            # Check for bytes32 type which often represents roles
            if inp_type == "bytes32" and ("role" in inp_name or "admin" in inp_name):
                return True
        
        return False
