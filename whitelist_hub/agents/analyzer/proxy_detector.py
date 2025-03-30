"""Proxy pattern detection component."""

import logging
from typing import Dict, List, Any, Optional

from ...utils.blockchain_client import BlockchainClient

logger = logging.getLogger(__name__)


class ProxyDetector:
    """Component for detecting proxy patterns in contracts."""
    
    def __init__(self, blockchain_client: BlockchainClient):
        """Initialize proxy detector.
        
        Args:
            blockchain_client: Client for blockchain interactions
        """
        self.blockchain_client = blockchain_client
    
    def analyze_bytecode(self, bytecode: str) -> Dict[str, Any]:
        """Analyze contract bytecode for proxy patterns.
        
        Args:
            bytecode: Contract bytecode
            
        Returns:
            Bytecode analysis for proxy patterns
        """
        analysis = {
            "delegatecall_present": False,
            "bytecode_length": len(bytecode),
            "is_minimal_proxy": False,
            "possible_storage_slots": [],
            "proxy_likelihood": 0
        }
        
        # Check for DELEGATECALL opcode (simplified)
        if "0x39" in bytecode:  # DELEGATECALL opcode
            analysis["delegatecall_present"] = True
        
        # Check for minimal proxy pattern (EIP-1167)
        if bytecode.startswith("0x363d3d373d3d3d363d73"):
            analysis["is_minimal_proxy"] = True
        
        # Check for known implementation storage slots
        known_slots = [
            # EIP-1967 implementation slot
            "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
            # OpenZeppelin TransparentUpgradeableProxy admin slot
            "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
            # EIP-1822 UUPS implementation slot
            "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
        ]
        
        for slot in known_slots:
            if slot[2:] in bytecode:  # Remove "0x" prefix
                analysis["possible_storage_slots"].append(slot)
        
        # Calculate likelihood based on findings
        likelihood = 0
        if analysis["delegatecall_present"]:
            likelihood += 0.4
        if analysis["is_minimal_proxy"]:
            likelihood += 0.5
        if analysis["possible_storage_slots"]:
            likelihood += 0.3 * len(analysis["possible_storage_slots"])
        if analysis["bytecode_length"] < 1000:  # Small bytecode is indicative of proxies
            likelihood += 0.2
        
        analysis["proxy_likelihood"] = min(likelihood, 1.0)
        
        return analysis
    
    def analyze_abi(self, abi: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ABI for proxy-related functions.
        
        Args:
            abi: Contract ABI
            
        Returns:
            ABI analysis for proxy functions
        """
        analysis = {
            "proxy_functions": [],
            "admin_functions": [],
            "upgrade_functions": [],
            "proxy_likelihood": 0
        }
        
        # Proxy-related function keywords
        proxy_keywords = ["implementation", "delegate", "logic", "proxy"]
        admin_keywords = ["admin", "owner", "authority"]
        upgrade_keywords = ["upgrade", "update", "set", "change"]
        
        for func in abi:
            if func.get("type") != "function":
                continue
                
            name = func.get("name", "").lower()
            
            # Check for proxy functions
            if any(keyword in name for keyword in proxy_keywords):
                analysis["proxy_functions"].append({
                    "name": func.get("name"),
                    "inputs": func.get("inputs", []),
                    "outputs": func.get("outputs", [])
                })
            
            # Check for admin functions
            if any(keyword in name for keyword in admin_keywords):
                analysis["admin_functions"].append({
                    "name": func.get("name"),
                    "inputs": func.get("inputs", []),
                    "outputs": func.get("outputs", [])
                })
            
            # Check for upgrade functions
            if any(keyword in name for keyword in upgrade_keywords):
                if "implementation" in name or "logic" in name:
                    analysis["upgrade_functions"].append({
                        "name": func.get("name"),
                        "inputs": func.get("inputs", []),
                        "outputs": func.get("outputs", [])
                    })
        
        # Calculate proxy likelihood based on ABI
        likelihood = 0
        
        if analysis["proxy_functions"]:
            likelihood += 0.4
        
        if analysis["upgrade_functions"]:
            likelihood += 0.3
        
        if analysis["admin_functions"]:
            likelihood += 0.1
        
        # Check for fallback function (common in proxies)
        if any(func.get("name") == "" for func in abi):
            likelihood += 0.2
        
        analysis["proxy_likelihood"] = min(likelihood, 1.0)
        
        return analysis
    
    def analyze_transaction_patterns(
        self, 
        recent_transactions: List[Dict[str, Any]],
        creation_transaction: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze transaction patterns for proxy indicators.
        
        Args:
            recent_transactions: Recent contract transactions
            creation_transaction: Contract creation transaction
            
        Returns:
            Transaction pattern analysis
        """
        analysis = {
            "upgrade_transactions": [],
            "proxy_initialization": False,
            "proxy_likelihood": 0
        }
        
        # Upgrade-related function signatures
        upgrade_signatures = [
            "0x3659cfe6",  # upgradeTo(address)
            "0x4f1ef286",  # upgradeToAndCall(address,bytes)
            "0x55241077",  # setImplementation(address)
            "0x88a7ca5c",  # updateImplementation(address)
            "0xbecde124"   # setLogic(address)
        ]
        
        # Check recent transactions for upgrade calls
        for tx in recent_transactions:
            input_data = tx.get("input", "0x")
            
            if input_data.startswith("0x"):
                function_selector = input_data[:10]  # First 4 bytes after "0x"
                
                if function_selector in upgrade_signatures:
                    analysis["upgrade_transactions"].append({
                        "tx_hash": tx.get("hash"),
                        "function_selector": function_selector,
                        "block_number": tx.get("blockNumber")
                    })
        
        # Check creation transaction for proxy initialization patterns
        if creation_transaction:
            input_data = creation_transaction.get("input", "0x")
            
            # Check for constructor with address parameter (potential implementation address)
            if len(input_data) > 74 and "0000000000000000000000" in input_data:
                analysis["proxy_initialization"] = True
        
        # Calculate proxy likelihood based on transaction patterns
        likelihood = 0
        
        if analysis["upgrade_transactions"]:
            likelihood += 0.6
        
        if analysis["proxy_initialization"]:
            likelihood += 0.4
        
        analysis["proxy_likelihood"] = min(likelihood, 1.0)
        
        return analysis
    
    async def detect_implementation(
        self, 
        contract_address: str, 
        blockchain: str,
        storage_slots: List[str]
    ) -> Dict[str, Any]:
        """Detect proxy implementation address.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            storage_slots: Potential implementation storage slots
            
        Returns:
            Proxy detection result
        """
        # Use default slots if none provided
        if not storage_slots:
            storage_slots = [
                # EIP-1967 implementation slot
                "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
                # OpenZeppelin TransparentUpgradeableProxy admin slot
                "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
                # EIP-1822 UUPS implementation slot
                "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7"
            ]
        
        implementation_addresses = []
        current_block = await self.blockchain_client.get_current_block(blockchain)
        
        for slot in storage_slots:
            try:
                slot_value = await self.blockchain_client.read_storage_at_block(
                    contract_address,
                    slot,
                    current_block,
                    blockchain
                )
                
                if slot_value and slot_value != "0x0000000000000000000000000000000000000000000000000000000000000000":
                    # Extract address from storage value
                    impl_address = "0x" + slot_value[-40:]
                    
                    # Verify it's a contract
                    impl_bytecode = await self.blockchain_client.fetch_contract_bytecode(
                        impl_address,
                        blockchain
                    )
                    
                    if impl_bytecode and impl_bytecode != "0x":
                        implementation_addresses.append({
                            "address": impl_address,
                            "storage_slot": slot,
                            "bytecode_length": len(impl_bytecode) // 2
                        })
            except Exception as e:
                logger.error(f"Error reading storage slot {slot}: {e}")
        
        return {
            "is_proxy": bool(implementation_addresses),
            "implementation_addresses": implementation_addresses,
            "detection_method": "storage_slots"
        }
    
    async def analyze_implementation_history(
        self, 
        contract_address: str, 
        blockchain: str, 
        storage_slots: List[str]
    ) -> Dict[str, Any]:
        """Analyze history of implementation changes for a proxy contract.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            storage_slots: Storage slots to check
            
        Returns:
            Implementation history analysis
        """
        if not storage_slots:
            # Use EIP-1967 slot as default
            storage_slots = ["0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"]
        
        # Get current block and creation block
        current_block = await self.blockchain_client.get_current_block(blockchain)
        creation_block = await self.blockchain_client.get_contract_creation_block(contract_address, blockchain)
        
        # Create sampling points throughout contract history
        block_interval = max(1000, (current_block - creation_block) // 10)
        sample_blocks = list(range(creation_block, current_block, block_interval))
        sample_blocks.append(current_block)  # Include current state
        
        implementation_history = []
        
        for block in sample_blocks:
            block_implementations = {}
            
            for slot in storage_slots:
                try:
                    # Read storage at this block
                    slot_value = await self.blockchain_client.read_storage_at_block(
                        contract_address,
                        slot,
                        block,
                        blockchain
                    )
                    
                    if slot_value and slot_value != "0x0000000000000000000000000000000000000000000000000000000000000000":
                        # Extract address from storage value
                        impl_address = "0x" + slot_value[-40:]
                        block_implementations[slot] = impl_address
                except Exception as e:
                    logger.error(f"Error reading storage at block {block}: {e}")
                    continue
            
            if block_implementations:
                implementation_history.append({
                    "block_number": block,
                    "implementations": block_implementations
                })
        
        # Analyze upgrade frequency and patterns
        upgrades = []
        previous_impls = {}
        
        for i, checkpoint in enumerate(implementation_history):
            if i == 0:
                previous_impls = checkpoint["implementations"]
                continue
                
            for slot, impl in checkpoint["implementations"].items():
                if slot in previous_impls and previous_impls[slot] != impl:
                    upgrades.append({
                        "from_block": implementation_history[i-1]["block_number"],
                        "to_block": checkpoint["block_number"],
                        "old_implementation": previous_impls[slot],
                        "new_implementation": impl,
                        "storage_slot": slot
                    })
                    
            previous_impls = checkpoint["implementations"]
        
        return {
            "implementation_history": implementation_history,
            "upgrade_count": len(upgrades),
            "upgrades": upgrades,
            "current_implementations": implementation_history[-1]["implementations"] if implementation_history else {}
        }
