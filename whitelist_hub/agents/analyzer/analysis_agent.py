"""Main Analysis Agent implementation."""

import logging
from typing import Dict, List, Any, Optional, Tuple

from ..base_agent import BaseAgent
from ...models.analysis_log import AnalysisLog
from ...utils.blockchain_client import BlockchainClient
from .abi_analyzer import ABIAnalyzer
from .proxy_detector import ProxyDetector
from .whitelist_analyzer import WhitelistAnalyzer
from .interaction_flow_generator import InteractionFlowGenerator

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Analysis Agent for analyzing smart contracts."""
    
    def __init__(self, blockchain_client=None, *args, **kwargs):
        """Initialize Analysis Agent.
        
        Args:
            blockchain_client: Client for blockchain interactions
        """
        super().__init__(agent_type="analyzer", *args, **kwargs)
        self.blockchain_client = blockchain_client or BlockchainClient()
        
        # Initialize components
        self.abi_analyzer = ABIAnalyzer()
        self.proxy_detector = ProxyDetector(self.blockchain_client)
        self.whitelist_analyzer = WhitelistAnalyzer()
        self.interaction_flow_generator = InteractionFlowGenerator()
    
    async def analyze_contract_abi(
        self, 
        contract_address: str,
        blockchain: str,
        abi_json: List[Dict[str, Any]],
        blockchain_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Analyze contract ABI to understand functionality.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            abi_json: Contract ABI as JSON
            blockchain_context: Optional additional context
            
        Returns:
            Tuple of (analysis result, analysis log)
        """
        context = {
            "contract_address": contract_address,
            "blockchain": blockchain,
            "abi": abi_json,
            "blockchain_context": blockchain_context or {}
        }
        
        # Add ABI structure analysis
        abi_structure = self.abi_analyzer.analyze_structure(abi_json)
        context["abi_structure"] = abi_structure
        
        # Identify standard interfaces
        standard_interfaces = self.abi_analyzer.identify_standard_interfaces(abi_json)
        context["standard_interfaces"] = standard_interfaces
        
        return await self.run(
            task="Analyze the contract ABI to classify functions and understand functionality",
            context=context,
            initial_state="abi_analysis"
        )
    
    async def detect_proxy_pattern(
        self,
        contract_address: str,
        blockchain: str,
        deep_analysis: bool = True
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Detect if contract is a proxy and identify implementation.
        
        Args:
            contract_address: Contract address
            blockchain: Blockchain name
            deep_analysis: Whether to perform deep analysis with historical data
            
        Returns:
            Tuple of (detection result, analysis log)
        """
        # Gather contract data
        bytecode = await self.blockchain_client.fetch_contract_bytecode(
            contract_address, blockchain
        )
        
        abi = await self.blockchain_client.fetch_contract_abi(
            contract_address, blockchain
        )
        
        recent_transactions = await self.blockchain_client.fetch_recent_transactions(
            contract_address, blockchain, limit=50
        )
        
        creation_transaction = await self.blockchain_client.fetch_contract_creation(
            contract_address, blockchain
        )
        
        # Prepare context
        context = {
            "contract_address": contract_address,
            "blockchain": blockchain,
            "bytecode": bytecode,
            "abi": abi,
            "recent_transactions": recent_transactions,
            "creation_transaction": creation_transaction,
            "deep_analysis": deep_analysis
        }
        
        # Add bytecode analysis
        bytecode_analysis = self.proxy_detector.analyze_bytecode(bytecode)
        context["bytecode_analysis"] = bytecode_analysis
        
        # Add ABI analysis
        abi_analysis = self.proxy_detector.analyze_abi(abi) if abi else {"proxy_likelihood": 0}
        context["abi_analysis"] = abi_analysis
        
        # Add transaction pattern analysis
        tx_analysis = self.proxy_detector.analyze_transaction_patterns(recent_transactions, creation_transaction)
        context["transaction_analysis"] = tx_analysis
        
        return await self.run(
            task="Determine if the contract is a proxy/router and identify its implementation",
            context=context,
            initial_state="proxy_detection"
        )
    
    async def analyze_whitelist_mechanism(
        self,
        contract_address: str,
        contract_data: Dict[str, Any],
        blockchain: str = "ethereum"
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Analyze whitelist mechanism in a contract.
        
        Args:
            contract_address: Contract address
            contract_data: Existing contract data
            blockchain: Blockchain name
            
        Returns:
            Tuple of (whitelist analysis, analysis log)
        """
        # Extract whitelist-related functions
        whitelist_functions = contract_data.get("function_categories", {}).get("whitelist", [])
        
        # Get source code if available
        source_code = await self.blockchain_client.fetch_contract_source_code(contract_address, blockchain)
        
        # Prepare context
        context = {
            "contract_address": contract_address,
            "contract_data": contract_data,
            "whitelist_functions": whitelist_functions,
            "source_code": source_code,
            "blockchain": blockchain
        }
        
        # Get historical interaction patterns with the contract
        if whitelist_functions:
            # Find transactions that called these functions
            whitelist_transactions = await self.blockchain_client.fetch_function_transactions(
                contract_address,
                [func.get("signature", "") for func in whitelist_functions],
                blockchain,
                limit=100
            )
            context["whitelist_transactions"] = whitelist_transactions
        
        return await self.run(
            task="Analyze and classify the whitelist mechanism in this contract",
            context=context,
            initial_state="whitelist_mechanism"
        )
    
    async def generate_user_interaction_flows(
        self,
        contract_address: str,
        contract_data: Dict[str, Any],
        blockchain: str = "ethereum"
    ) -> Tuple[Dict[str, Any], AnalysisLog]:
        """Generate user interaction flows for a contract.
        
        Args:
            contract_address: Contract address
            contract_data: Existing contract data
            blockchain: Blockchain name
            
        Returns:
            Tuple of (interaction flows, analysis log)
        """
        # Add transaction data for more context
        sample_successful_txs = await self.blockchain_client.fetch_successful_transactions(
            contract_address, 
            blockchain, 
            limit=20
        )
        
        # Prepare context
        context = {
            "contract_address": contract_address,
            "contract_data": contract_data,
            "blockchain": blockchain,
            "sample_transactions": sample_successful_txs
        }
        
        # Identify common interaction patterns from transactions
        if sample_successful_txs:
            interaction_patterns = self.interaction_flow_generator.extract_patterns(
                sample_successful_txs,
                contract_data.get("abi", [])
            )
            context["interaction_patterns"] = interaction_patterns
        
        return await self.run(
            task="Generate user interaction flows for the contract",
            context=context,
            initial_state="user_flow_analysis"
        )
    
    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analyzer-specific actions.
        
        Args:
            action: Action to execute
            
        Returns:
            Result of action execution
        """
        action_type = action.get("type", "").lower()
        params = action.get("params", {})
        
        if action_type == "classify_functions":
            # Classify contract functions
            abi = params.get("abi") or self.context.get("abi", [])
            result = self.abi_analyzer.classify_functions(abi)
            return {"function_classifications": result}
            
        elif action_type == "detect_proxy_implementation":
            # Detect proxy implementation address
            contract_address = params.get("contract_address") or self.context.get("contract_address")
            blockchain = params.get("blockchain") or self.context.get("blockchain")
            storage_slots = params.get("storage_slots", [])
            result = await self.proxy_detector.detect_implementation(contract_address, blockchain, storage_slots)
            return {"proxy_detection": result}
            
        elif action_type == "analyze_whitelist_pattern":
            # Analyze whitelist pattern
            functions = params.get("functions") or self.context.get("whitelist_functions", [])
            source_code = params.get("source_code") or self.context.get("source_code")
            result = self.whitelist_analyzer.analyze_pattern(functions, source_code)
            return {"whitelist_analysis": result}
            
        elif action_type == "generate_interaction_flow":
            # Generate user interaction flow
            contract_data = params.get("contract_data") or self.context.get("contract_data", {})
            flow_type = params.get("flow_type")
            result = self.interaction_flow_generator.generate_flow(contract_data, flow_type)
            return {"interaction_flow": result}
            
        elif action_type == "verify_interface_implementation":
            # Verify interface implementation
            abi = params.get("abi") or self.context.get("abi", [])
            interface_name = params.get("interface")
            result = self.abi_analyzer.verify_interface_implementation(abi, interface_name)
            return {"interface_verification": result}
            
        else:
            # Fall back to base implementation
            return await super()._execute_action(action)
