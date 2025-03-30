"""Interaction flow generation component."""

import logging
import re
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)


class InteractionFlowGenerator:
    """Component for generating user interaction flows for contracts."""
    
    def extract_patterns(
        self,
        transactions: List[Dict[str, Any]],
        abi: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract interaction patterns from transactions.
        
        Args:
            transactions: Transaction data
            abi: Contract ABI
            
        Returns:
            Extracted interaction patterns
        """
        patterns = {
            "common_functions": {},
            "sequences": [],
            "parameter_patterns": {}
        }
        
        # Decode transactions
        decoded_txs = []
        
        for tx in transactions:
            tx_input = tx.get("input", "0x")
            if tx_input == "0x":
                # Simple ETH transfer
                decoded_txs.append({
                    "tx_hash": tx.get("hash"),
                    "function_name": "ETH Transfer",
                    "function_selector": None,
                    "decoded_params": {},
                    "value": tx.get("value", "0x0")
                })
                continue
            
            # Try to decode function call
            if not tx_input.startswith("0x"):
                tx_input = "0x" + tx_input
                
            function_selector = tx_input[:10]  # First 4 bytes after "0x"
            matched_func = self._find_function_by_selector(function_selector, abi)
            
            if matched_func:
                decoded_txs.append({
                    "tx_hash": tx.get("hash"),
                    "function_name": matched_func.get("name"),
                    "function_selector": function_selector,
                    "decoded_params": self._decode_parameters(tx_input[10:], matched_func.get("inputs", [])),
                    "value": tx.get("value", "0x0")
                })
            else:
                # Unknown function
                decoded_txs.append({
                    "tx_hash": tx.get("hash"),
                    "function_name": "Unknown",
                    "function_selector": function_selector,
                    "decoded_params": {},
                    "value": tx.get("value", "0x0")
                })
        
        # Analyze function frequency
        for tx in decoded_txs:
            func_name = tx.get("function_name")
            patterns["common_functions"][func_name] = patterns["common_functions"].get(func_name, 0) + 1
        
        # Sort common functions by frequency
        patterns["common_functions"] = dict(
            sorted(
                patterns["common_functions"].items(), 
                key=lambda item: item[1], 
                reverse=True
            )
        )
        
        # Find sequences (simplistic approach)
        sequences = []
        if len(decoded_txs) >= 2:
            for i in range(len(decoded_txs) - 1):
                current = decoded_txs[i]
                next_tx = decoded_txs[i + 1]
                
                if current.get("function_name") != "Unknown" and next_tx.get("function_name") != "Unknown":
                    sequence = {
                        "first": current.get("function_name"),
                        "second": next_tx.get("function_name"),
                        "sender_same": transactions[i].get("from") == transactions[i + 1].get("from")
                    }
                    sequences.append(sequence)
        
        # Group sequences by frequency
        sequence_counts = {}
        for seq in sequences:
            key = f"{seq['first']} -> {seq['second']}"
            sequence_counts[key] = sequence_counts.get(key, 0) + 1
        
        # Sort sequences by frequency
        patterns["sequences"] = [
            {"sequence": key, "count": value}
            for key, value in sorted(sequence_counts.items(), key=lambda item: item[1], reverse=True)
        ][:5]  # Top 5 sequences
        
        # Analyze parameter patterns
        param_patterns = {}
        for tx in decoded_txs:
            func_name = tx.get("function_name")
            if func_name == "Unknown" or func_name == "ETH Transfer":
                continue
                
            params = tx.get("decoded_params", {})
            
            if func_name not in param_patterns:
                param_patterns[func_name] = {}
            
            for param_name, param_value in params.items():
                if param_name not in param_patterns[func_name]:
                    param_patterns[func_name][param_name] = []
                
                # Store unique values (up to 5 for brevity)
                if param_value not in param_patterns[func_name][param_name] and len(param_patterns[func_name][param_name]) < 5:
                    param_patterns[func_name][param_name].append(param_value)
        
        patterns["parameter_patterns"] = param_patterns
        
        return patterns
    
    def generate_flow(self, contract_data: Dict[str, Any], flow_type: str = None) -> Dict[str, Any]:
        """Generate user interaction flow for a contract.
        
        Args:
            contract_data: Contract data
            flow_type: Type of flow to generate (whitelist, token_sale, etc.)
            
        Returns:
            Generated interaction flow
        """
        if not flow_type:
            # Try to determine most appropriate flow type
            categories = contract_data.get("function_categories", {})
            
            if "whitelist" in categories:
                flow_type = "whitelist"
            elif "token_sale" in categories:
                flow_type = "token_sale"
            elif "staking" in categories:
                flow_type = "staking"
            else:
                flow_type = "general"
        
        # Generate flow based on type
        if flow_type == "whitelist":
            return self._generate_whitelist_flow(contract_data)
        elif flow_type == "token_sale":
            return self._generate_token_sale_flow(contract_data)
        elif flow_type == "staking":
            return self._generate_staking_flow(contract_data)
        else:
            return self._generate_general_flow(contract_data)
    
    def _generate_whitelist_flow(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate whitelist interaction flow.
        
        Args:
            contract_data: Contract data
            
        Returns:
            Whitelist interaction flow
        """
        # Get whitelist-related functions
        whitelist_functions = contract_data.get("function_categories", {}).get("whitelist", [])
        
        if not whitelist_functions:
            return {
                "name": "Whitelist Interaction",
                "description": "No whitelist functions found in contract",
                "tags": ["whitelist"],
                "category": "whitelist",
                "steps": []
            }
        
        # Check function purposes to determine flow
        check_funcs = [f for f in whitelist_functions if any(kw in f.get("name", "").lower() for kw in ["check", "is", "verify"])]
        add_funcs = [f for f in whitelist_functions if any(kw in f.get("name", "").lower() for kw in ["add", "set", "register"])]
        
        steps = []
        step_counter = 1
        
        # Add configuration steps if available
        admin_funcs = contract_data.get("function_categories", {}).get("admin", [])
        config_funcs = [f for f in admin_funcs if "whitelist" in f.get("name", "").lower() or "merkle" in f.get("name", "").lower()]
        
        for func in config_funcs:
            steps.append({
                "step": step_counter,
                "description": f"Admin configures whitelist settings using {func.get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": func.get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in func.get("inputs", [])],
                "expected_outcome": "Whitelist configuration is updated",
                "error_cases": [
                    {"condition": "Caller is not admin", "error_message": "Not authorized", "mitigation": "Use admin account"}
                ]
            })
            step_counter += 1
        
        # Add registration step if available
        if add_funcs:
            steps.append({
                "step": step_counter,
                "description": f"Admin adds users to whitelist using {add_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": add_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in add_funcs[0].get("inputs", [])],
                "expected_outcome": "User is added to whitelist",
                "error_cases": [
                    {"condition": "Caller is not admin", "error_message": "Not authorized", "mitigation": "Use admin account"},
                    {"condition": "User already whitelisted", "error_message": "Already whitelisted", "mitigation": "Skip already whitelisted users"}
                ]
            })
            step_counter += 1
        
        # Add check step if available
        if check_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User checks whitelist status using {check_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": check_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in check_funcs[0].get("inputs", [])],
                "expected_outcome": "Returns true if user is whitelisted, false otherwise",
                "error_cases": []
            })
            step_counter += 1
        
        # Look for functions that might use the whitelist
        all_functions = []
        for category, funcs in contract_data.get("function_categories", {}).items():
            all_functions.extend(funcs)
        
        # Find functions that might use whitelist for access control
        restricted_funcs = []
        for func in all_functions:
            if func.get("requires_auth") and func.get("user_accessible"):
                restricted_funcs.append(func)
        
        # Add restricted function step if available
        if restricted_funcs:
            steps.append({
                "step": step_counter,
                "description": f"Whitelisted user calls restricted function {restricted_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": restricted_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in restricted_funcs[0].get("inputs", [])],
                "expected_outcome": "Function executes successfully for whitelisted users",
                "error_cases": [
                    {"condition": "User not whitelisted", "error_message": "Not whitelisted", "mitigation": "Ensure user is whitelisted first"}
                ]
            })
        
        return {
            "name": "Whitelist Interaction Flow",
            "description": "Process for configuring and using the whitelist functionality",
            "tags": ["whitelist", "access control"],
            "category": "whitelist",
            "steps": steps,
            "prerequisites": ["Admin access for configuration steps"],
            "user_level": "intermediate"
        }
    
    def _generate_token_sale_flow(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate token sale interaction flow.
        
        Args:
            contract_data: Contract data
            
        Returns:
            Token sale interaction flow
        """
        # Get token sale functions
        sale_functions = contract_data.get("function_categories", {}).get("token_sale", [])
        
        if not sale_functions:
            return {
                "name": "Token Sale Interaction",
                "description": "No token sale functions found in contract",
                "tags": ["token sale"],
                "category": "token_sale",
                "steps": []
            }
        
        # Categorize functions
        buy_funcs = [f for f in sale_functions if any(kw in f.get("name", "").lower() for kw in ["buy", "purchase", "contribute"])]
        claim_funcs = [f for f in sale_functions if any(kw in f.get("name", "").lower() for kw in ["claim", "withdraw", "redeem"])]
        config_funcs = [f for f in sale_functions if any(kw in f.get("name", "").lower() for kw in ["set", "configure", "start", "end"])]
        
        steps = []
        step_counter = 1
        
        # Add configuration steps
        if config_funcs:
            steps.append({
                "step": step_counter,
                "description": f"Admin configures token sale using {config_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": config_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in config_funcs[0].get("inputs", [])],
                "expected_outcome": "Token sale parameters are set",
                "error_cases": [
                    {"condition": "Caller is not admin", "error_message": "Not authorized", "mitigation": "Use admin account"}
                ]
            })
            step_counter += 1
        
        # Add whitelist check if relevant
        whitelist_funcs = contract_data.get("function_categories", {}).get("whitelist", [])
        if whitelist_funcs:
            check_funcs = [f for f in whitelist_funcs if any(kw in f.get("name", "").lower() for kw in ["check", "is", "verify"])]
            if check_funcs:
                steps.append({
                    "step": step_counter,
                    "description": f"User checks whitelist status using {check_funcs[0].get('name')}",
                    "contract_address": contract_data.get("address", ""),
                    "function_name": check_funcs[0].get("name", ""),
                    "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in check_funcs[0].get("inputs", [])],
                    "expected_outcome": "Returns true if user is whitelisted, false otherwise",
                    "error_cases": []
                })
                step_counter += 1
        
        # Add buy step
        if buy_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User purchases tokens using {buy_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": buy_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in buy_funcs[0].get("inputs", [])],
                "expected_outcome": "User's contribution is recorded and tokens are allocated",
                "error_cases": [
                    {"condition": "User not whitelisted", "error_message": "Not whitelisted", "mitigation": "Ensure user is whitelisted first"},
                    {"condition": "Sale not active", "error_message": "Sale not active", "mitigation": "Check sale status before contributing"},
                    {"condition": "Contribution below minimum", "error_message": "Below minimum", "mitigation": "Contribute at least the minimum amount"}
                ]
            })
            step_counter += 1
        
        # Add claim step
        if claim_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User claims tokens using {claim_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": claim_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in claim_funcs[0].get("inputs", [])],
                "expected_outcome": "User receives purchased tokens",
                "error_cases": [
                    {"condition": "No allocation", "error_message": "No allocation", "mitigation": "Ensure user has contributed first"},
                    {"condition": "Already claimed", "error_message": "Already claimed", "mitigation": "Check if tokens were already claimed"}
                ]
            })
        
        return {
            "name": "Token Sale Interaction Flow",
            "description": "Process for participating in the token sale",
            "tags": ["token sale", "purchase", "claim"],
            "category": "token_sale",
            "steps": steps,
            "prerequisites": ["ETH/native tokens for purchase", "Whitelist status (if required)"],
            "user_level": "beginner"
        }
    
    def _generate_staking_flow(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate staking interaction flow.
        
        Args:
            contract_data: Contract data
            
        Returns:
            Staking interaction flow
        """
        # Get staking functions
        staking_functions = contract_data.get("function_categories", {}).get("staking", [])
        
        if not staking_functions:
            return {
                "name": "Staking Interaction",
                "description": "No staking functions found in contract",
                "tags": ["staking"],
                "category": "staking",
                "steps": []
            }
        
        # Categorize functions
        stake_funcs = [f for f in staking_functions if any(kw in f.get("name", "").lower() for kw in ["stake", "deposit", "lock"])]
        unstake_funcs = [f for f in staking_functions if any(kw in f.get("name", "").lower() for kw in ["unstake", "withdraw", "exit"])]
        reward_funcs = [f for f in staking_functions if any(kw in f.get("name", "").lower() for kw in ["reward", "claim", "harvest", "get"])]
        
        steps = []
        step_counter = 1
        
        # Add approval step if likely needed
        utility_funcs = contract_data.get("function_categories", {}).get("utility", [])
        if utility_funcs:
            approve_funcs = [f for f in utility_funcs if "approve" in f.get("name", "").lower()]
            if approve_funcs:
                steps.append({
                    "step": step_counter,
                    "description": "User approves token spending",
                    "contract_address": "Token Contract Address",  # Placeholder
                    "function_name": "approve",
                    "inputs": [
                        {"name": "spender", "type": "address", "value": contract_data.get("address", "")},
                        {"name": "amount", "type": "uint256", "value": "amount to stake"}
                    ],
                    "expected_outcome": "Approval granted to staking contract",
                    "error_cases": [
                        {"condition": "Insufficient balance", "error_message": "Insufficient balance", "mitigation": "Ensure sufficient token balance"}
                    ]
                })
                step_counter += 1
        
        # Add stake step
        if stake_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User stakes tokens using {stake_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": stake_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in stake_funcs[0].get("inputs", [])],
                "expected_outcome": "Tokens staked successfully",
                "error_cases": [
                    {"condition": "Amount is zero", "error_message": "Amount cannot be zero", "mitigation": "Stake a positive amount"},
                    {"condition": "Not approved", "error_message": "Not approved", "mitigation": "Approve tokens first"}
                ]
            })
            step_counter += 1
        
        # Add reward claim step
        if reward_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User claims rewards using {reward_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": reward_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in reward_funcs[0].get("inputs", [])],
                "expected_outcome": "Rewards claimed successfully",
                "error_cases": [
                    {"condition": "No rewards", "error_message": "No rewards", "mitigation": "Stake longer or check if rewards are available"}
                ]
            })
            step_counter += 1
        
        # Add unstake step
        if unstake_funcs:
            steps.append({
                "step": step_counter,
                "description": f"User unstakes tokens using {unstake_funcs[0].get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": unstake_funcs[0].get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in unstake_funcs[0].get("inputs", [])],
                "expected_outcome": "Tokens unstaked successfully",
                "error_cases": [
                    {"condition": "Nothing staked", "error_message": "Nothing staked", "mitigation": "Stake tokens first"},
                    {"condition": "Lock period", "error_message": "Still locked", "mitigation": "Wait until lock period ends"}
                ]
            })
        
        return {
            "name": "Staking Interaction Flow",
            "description": "Process for staking tokens, claiming rewards, and unstaking",
            "tags": ["staking", "rewards", "yield"],
            "category": "staking",
            "steps": steps,
            "prerequisites": ["Token balance for staking"],
            "user_level": "beginner"
        }
    
    def _generate_general_flow(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate general interaction flow.
        
        Args:
            contract_data: Contract data
            
        Returns:
            General interaction flow
        """
        # Get user-accessible functions
        user_functions = []
        for category, funcs in contract_data.get("function_categories", {}).items():
            for func in funcs:
                if func.get("user_accessible") and func.get("is_entry_point"):
                    user_functions.append(func)
        
        if not user_functions:
            return {
                "name": "Contract Interaction",
                "description": "No user-accessible functions found in contract",
                "tags": ["general"],
                "category": "general",
                "steps": []
            }
        
        # Sort functions by name for consistent order
        user_functions.sort(key=lambda f: f.get("name", ""))
        
        steps = []
        step_counter = 1
        
        # Add steps for each user function
        for func in user_functions[:5]:  # Limit to 5 functions for brevity
            steps.append({
                "step": step_counter,
                "description": f"User calls {func.get('name')}",
                "contract_address": contract_data.get("address", ""),
                "function_name": func.get("name", ""),
                "inputs": [{"name": inp.get("name"), "type": inp.get("type")} for inp in func.get("inputs", [])],
                "expected_outcome": "Function executes successfully",
                "error_cases": []
            })
            step_counter += 1
        
        return {
            "name": "General Contract Interaction Flow",
            "description": "Basic interaction with contract functions",
            "tags": ["general"],
            "category": "general",
            "steps": steps,
            "prerequisites": [],
            "user_level": "intermediate"
        }
    
    def _find_function_by_selector(self, selector: str, abi: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find function in ABI by selector.
        
        Args:
            selector: Function selector
            abi: Contract ABI
            
        Returns:
            Function if found, None otherwise
        """
        # Note: In a real implementation, this would compute the selector from the signature
        # This is a simplified implementation that just looks for matching name patterns
        
        if not selector or selector == "0x":
            return None
        
        # Common function selectors (hardcoded for demonstration)
        known_selectors = {
            "0xa9059cbb": {"name": "transfer", "signature": "transfer(address,uint256)"},
            "0x095ea7b3": {"name": "approve", "signature": "approve(address,uint256)"},
            "0x23b872dd": {"name": "transferFrom", "signature": "transferFrom(address,address,uint256)"},
            "0x70a08231": {"name": "balanceOf", "signature": "balanceOf(address)"},
            "0x18160ddd": {"name": "totalSupply", "signature": "totalSupply()"},
            "0x6352211e": {"name": "ownerOf", "signature": "ownerOf(uint256)"}
        }
        
        if selector in known_selectors:
            # Find the function in ABI by name
            known_name = known_selectors[selector]["name"]
            for func in abi:
                if func.get("type") == "function" and func.get("name") == known_name:
                    return func
        
        # If not found in known selectors, try to match by name pattern
        # Note: This is a heuristic and not reliable
        last_bytes = selector[-6:]  # Last 3 bytes of selector
        
        for func in abi:
            if func.get("type") != "function":
                continue
                
            # Hash the function name and check if last bytes match
            # Note: This is not how actual selectors work, just a demo
            name_hash = hash(func.get("name", "")) & 0xFFFFFF  # Last 3 bytes
            if format(name_hash, "06x") == last_bytes:
                return func
        
        return None
    
    def _decode_parameters(self, hex_data: str, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Decode parameters from hex data.
        
        Args:
            hex_data: Hex data to decode
            inputs: Function input types
            
        Returns:
            Decoded parameters
        """
        # Note: In a real implementation, this would use proper ABI decoding
        # This is a simplified implementation that returns placeholder values
        
        params = {}
        
        for i, inp in enumerate(inputs):
            name = inp.get("name", f"param{i}")
            type_str = inp.get("type", "")
            
            # Provide placeholder values based on type
            if type_str == "address":
                params[name] = "0x0000000000000000000000000000000000000000"
            elif type_str.startswith("uint"):
                params[name] = "0"
            elif type_str == "bool":
                params[name] = "false"
            elif type_str == "string":
                params[name] = ""
            elif type_str.endswith("[]"):
                params[name] = []
            else:
                params[name] = "0x"
        
        return params
