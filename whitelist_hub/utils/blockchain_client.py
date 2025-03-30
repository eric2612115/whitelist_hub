"""Blockchain interaction client."""

import logging
import json
from typing import Dict, List, Optional, Any, Union
import aiohttp
from web3 import Web3
import asyncio
from functools import partial

from ..core.config import settings

logger = logging.getLogger(__name__)


class BlockchainClient:
    """Client for interacting with blockchain nodes and explorers."""
    
    def __init__(self):
        """Initialize blockchain client."""
        self.rpc_urls = {
            "ethereum": settings.ETHEREUM_RPC_URL,
            "bsc": settings.BSC_RPC_URL,
            "polygon": settings.POLYGON_RPC_URL,
            "arbitrum": settings.ARBITRUM_RPC_URL,
            "optimism": settings.OPTIMISM_RPC_URL
        }
        
        self.explorer_apis = {
            "ethereum": "https://api.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "polygon": "https://api.polygonscan.com/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api"
        }
        
        self.explorer_api_keys = {
            "ethereum": settings.ETHERSCAN_API_KEY,
            "bsc": settings.BSCSCAN_API_KEY,
            "polygon": settings.POLYGONSCAN_API_KEY,
            "arbitrum": settings.ARBISCAN_API_KEY,
            "optimism": settings.OPTIMISTICSCAN_API_KEY
        }
        
        # Initialize Web3 providers
        self.web3_providers = {}
        for chain, url in self.rpc_urls.items():
            if url:
                self.web3_providers[chain] = Web3(Web3.HTTPProvider(url))
    
    def get_web3(self, blockchain: str) -> Web3:
        """Get Web3 instance for specified blockchain.
        
        Args:
            blockchain: Blockchain name
            
        Returns:
            Web3 instance
        
        Raises:
            ValueError: If blockchain is not supported or configured
        """
        if blockchain in self.web3_providers:
            return self.web3_providers[blockchain]
        
        raise ValueError(f"No Web3 provider configured for {blockchain}")
    
    async def _async_wrapper(self, func, *args, **kwargs):
        """Wrap synchronous Web3 methods to run in thread pool.
        
        Args:
            func: Web3 function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, partial(func, *args, **kwargs)
        )
    
    async def fetch_contract_bytecode(self, address: str, blockchain: str) -> str:
        """Fetch contract bytecode.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Contract bytecode as hex string
        """
        try:
            w3 = self.get_web3(blockchain)
            bytecode = await self._async_wrapper(
                w3.eth.get_code, 
                Web3.to_checksum_address(address)
            )
            return bytecode.hex()
        except Exception as e:
            logger.error(f"Error fetching bytecode for {address} on {blockchain}: {e}")
            
            # Fallback to explorer API
            try:
                params = {
                    "module": "proxy",
                    "action": "eth_getCode",
                    "address": address,
                    "tag": "latest"
                }
                
                if self.explorer_api_keys.get(blockchain):
                    params["apikey"] = self.explorer_api_keys[blockchain]
                
                result = await self._make_explorer_api_request(blockchain, params)
                return result.get("result", "0x")
            except Exception as e2:
                logger.error(f"Explorer API fallback failed: {e2}")
                raise
    
    async def fetch_contract_abi(self, address: str, blockchain: str) -> List[Dict[str, Any]]:
        """Fetch contract ABI from blockchain explorer.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Contract ABI as JSON
        """
        params = {
            "module": "contract",
            "action": "getabi",
            "address": address
        }
        
        if self.explorer_api_keys.get(blockchain):
            params["apikey"] = self.explorer_api_keys[blockchain]
        
        try:
            result = await self._make_explorer_api_request(blockchain, params)
            
            if result.get("status") == "1" and result.get("result"):
                return json.loads(result["result"])
            else:
                logger.warning(f"No ABI found for {address} on {blockchain}: {result.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            logger.error(f"Error fetching ABI for {address} on {blockchain}: {e}")
            return []
    
    async def fetch_contract_source_code(self, address: str, blockchain: str) -> Optional[str]:
        """Fetch contract source code from blockchain explorer.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Contract source code or None if not available
        """
        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address
        }
        
        if self.explorer_api_keys.get(blockchain):
            params["apikey"] = self.explorer_api_keys[blockchain]
        
        try:
            result = await self._make_explorer_api_request(blockchain, params)
            
            if result.get("status") == "1" and result.get("result"):
                source_code_result = result["result"][0]
                
                if source_code_result.get("SourceCode"):
                    return source_code_result["SourceCode"]
                else:
                    logger.warning(f"No source code found for {address} on {blockchain}")
                    return None
            else:
                logger.warning(f"Failed to fetch source code for {address} on {blockchain}: {result.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"Error fetching source code for {address} on {blockchain}: {e}")
            return None
    
    async def fetch_recent_transactions(self, address: str, blockchain: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent transactions for a contract.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": limit,
            "sort": "desc"
        }
        
        if self.explorer_api_keys.get(blockchain):
            params["apikey"] = self.explorer_api_keys[blockchain]
        
        try:
            result = await self._make_explorer_api_request(blockchain, params)
            
            if result.get("status") == "1" and result.get("result"):
                return result["result"]
            else:
                logger.warning(f"No transactions found for {address} on {blockchain}: {result.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            logger.error(f"Error fetching transactions for {address} on {blockchain}: {e}")
            return []
    
    async def fetch_function_transactions(
        self, 
        address: str, 
        function_signatures: List[str], 
        blockchain: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch transactions that called specific functions.
        
        Args:
            address: Contract address
            function_signatures: List of function signatures (4-byte selectors)
            blockchain: Blockchain name
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions
        """
        txs = await self.fetch_recent_transactions(address, blockchain, limit * 2)
        
        # Filter transactions by function signature
        filtered_txs = []
        for tx in txs:
            input_data = tx.get("input", "0x")
            
            # Check if this transaction calls any of the target functions
            if any(input_data.startswith("0x" + sig[2:]) for sig in function_signatures):
                filtered_txs.append(tx)
            
            if len(filtered_txs) >= limit:
                break
        
        return filtered_txs
    
    async def fetch_successful_transactions(
        self, 
        address: str, 
        blockchain: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetch successful transactions for a contract.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            limit: Maximum number of transactions to return
            
        Returns:
            List of successful transactions
        """
        txs = await self.fetch_recent_transactions(address, blockchain, limit * 2)
        
        # Filter for successful transactions
        successful_txs = [tx for tx in txs if tx.get("isError") == "0"][:limit]
        
        return successful_txs
    
    async def fetch_contract_creation(self, address: str, blockchain: str) -> Optional[Dict[str, Any]]:
        """Fetch contract creation transaction.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Contract creation transaction or None if not found
        """
        # First try to get transaction hash from explorer API
        try:
            w3 = self.get_web3(blockchain)
            
            # Get contract transaction count
            tx_count = await self._async_wrapper(
                w3.eth.get_transaction_count, 
                Web3.to_checksum_address(address)
            )
            
            # If no transactions, this might not be a contract
            if tx_count == 0:
                logger.warning(f"No transactions found for {address} on {blockchain}")
                return None
            
            # Try to get contract creation info from explorer API
            params = {
                "module": "contract",
                "action": "getcontractcreation",
                "contractaddresses": address
            }
            
            if self.explorer_api_keys.get(blockchain):
                params["apikey"] = self.explorer_api_keys[blockchain]
            
            result = await self._make_explorer_api_request(blockchain, params)
            
            if result.get("status") == "1" and result.get("result"):
                creation_info = result["result"][0]
                tx_hash = creation_info.get("txHash")
                
                if tx_hash:
                    # Get full transaction details
                    tx = await self._async_wrapper(
                        w3.eth.get_transaction,
                        tx_hash
                    )
                    
                    tx_receipt = await self._async_wrapper(
                        w3.eth.get_transaction_receipt,
                        tx_hash
                    )
                    
                    # Combine transaction and receipt data
                    return {
                        "hash": tx_hash,
                        "block_number": tx_receipt.get("blockNumber"),
                        "from": tx.get("from"),
                        "gas_used": tx_receipt.get("gasUsed"),
                        "contract_address": tx_receipt.get("contractAddress"),
                        "timestamp": await self._get_block_timestamp(blockchain, tx_receipt.get("blockNumber"))
                    }
                
                return {
                    "hash": creation_info.get("txHash"),
                    "from": creation_info.get("contractCreator")
                }
            
            logger.warning(f"Contract creation not found for {address} on {blockchain}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching contract creation for {address} on {blockchain}: {e}")
            return None
    
    async def read_storage_at_block(
        self, 
        address: str, 
        storage_slot: str, 
        block_number: int, 
        blockchain: str
    ) -> str:
        """Read contract storage at specific block.
        
        Args:
            address: Contract address
            storage_slot: Storage slot to read
            block_number: Block number
            blockchain: Blockchain name
            
        Returns:
            Storage value as hex string
        """
        try:
            w3 = self.get_web3(blockchain)
            
            # Convert address and slot to checksum format
            checksum_address = Web3.to_checksum_address(address)
            
            # Convert slot to proper format if needed
            if not storage_slot.startswith("0x"):
                storage_slot = "0x" + storage_slot
            
            # Read storage using getStorageAt
            value = await self._async_wrapper(
                w3.eth.get_storage_at,
                checksum_address,
                int(storage_slot, 16),
                block_number
            )
            
            return "0x" + value.hex()
        except Exception as e:
            logger.error(f"Error reading storage at {storage_slot} for {address} on {blockchain} at block {block_number}: {e}")
            
            # Fallback to explorer API
            try:
                params = {
                    "module": "proxy",
                    "action": "eth_getStorageAt",
                    "address": address,
                    "position": storage_slot,
                    "tag": hex(block_number)
                }
                
                if self.explorer_api_keys.get(blockchain):
                    params["apikey"] = self.explorer_api_keys[blockchain]
                
                result = await self._make_explorer_api_request(blockchain, params)
                return result.get("result", "0x0")
            except Exception as e2:
                logger.error(f"Explorer API fallback failed: {e2}")
                raise
    
    async def get_current_block(self, blockchain: str) -> int:
        """Get current block number.
        
        Args:
            blockchain: Blockchain name
            
        Returns:
            Current block number
        """
        try:
            w3 = self.get_web3(blockchain)
            block_number = await self._async_wrapper(w3.eth.block_number)
            return block_number
        except Exception as e:
            logger.error(f"Error fetching current block for {blockchain}: {e}")
            
            # Fallback to explorer API
            try:
                params = {
                    "module": "proxy",
                    "action": "eth_blockNumber"
                }
                
                if self.explorer_api_keys.get(blockchain):
                    params["apikey"] = self.explorer_api_keys[blockchain]
                
                result = await self._make_explorer_api_request(blockchain, params)
                return int(result.get("result", "0x0"), 16)
            except Exception as e2:
                logger.error(f"Explorer API fallback failed: {e2}")
                raise
    
    async def get_contract_creation_block(self, address: str, blockchain: str) -> int:
        """Get contract creation block number.
        
        Args:
            address: Contract address
            blockchain: Blockchain name
            
        Returns:
            Creation block number
        """
        creation_tx = await self.fetch_contract_creation(address, blockchain)
        
        if creation_tx and "block_number" in creation_tx:
            return creation_tx["block_number"]
        
        # If we couldn't get the creation block, return 0
        return 0
    
    async def _get_block_timestamp(self, blockchain: str, block_number: int) -> int:
        """Get block timestamp.
        
        Args:
            blockchain: Blockchain name
            block_number: Block number
            
        Returns:
            Block timestamp in seconds
        """
        try:
            w3 = self.get_web3(blockchain)
            block = await self._async_wrapper(w3.eth.get_block, block_number)
            return block.timestamp
        except Exception as e:
            logger.warning(f"Error fetching block timestamp for {blockchain} block {block_number}: {e}")
            
            # Fallback to explorer API
            try:
                params = {
                    "module": "block",
                    "action": "getblockreward",
                    "blockno": block_number
                }
                
                if self.explorer_api_keys.get(blockchain):
                    params["apikey"] = self.explorer_api_keys[blockchain]
                
                result = await self._make_explorer_api_request(blockchain, params)
                
                if result.get("status") == "1" and result.get("result"):
                    # Extract timestamp from response
                    timestamp = int(result.get("result", {}).get("timeStamp", 0))
                    return timestamp
                else:
                    logger.error(f"Failed to get block timestamp from explorer: {result.get('message', 'Unknown error')}")
                    return 0
            except Exception as e2:
                logger.error(f"Explorer API fallback failed for timestamp: {e2}")
                return 0
    
    async def _make_explorer_api_request(self, blockchain: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to blockchain explorer API.
        
        Args:
            blockchain: Blockchain name
            params: Request parameters
            
        Returns:
            API response
            
        Raises:
            ValueError: If blockchain is not supported
            RuntimeError: If API request fails
        """
        if blockchain not in self.explorer_apis:
            raise ValueError(f"Unsupported blockchain: {blockchain}")
        
        url = self.explorer_apis[blockchain]
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise RuntimeError(f"Explorer API request failed: {response.status}")
                
                return await response.json()
    
    async def call_contract_function(
        self,
        address: str,
        function_selector: str,
        params: List[Any],
        blockchain: str
    ) -> Any:
        """Call read-only contract function.
        
        Args:
            address: Contract address
            function_selector: Function selector
            params: Function parameters
            blockchain: Blockchain name
            
        Returns:
            Function result
            
        Raises:
            ValueError: If blockchain is not supported
            RuntimeError: If function call fails
        """
        try:
            w3 = self.get_web3(blockchain)
            
            # Prepare call data
            call_data = function_selector + self._encode_params(params)
            
            # Make call
            result = await self._async_wrapper(
                w3.eth.call,
                {
                    "to": Web3.to_checksum_address(address),
                    "data": call_data
                }
            )
            
            return result.hex()
        except Exception as e:
            logger.error(f"Error calling contract function: {e}")
            
            # Fallback to explorer API
            try:
                params = {
                    "module": "proxy",
                    "action": "eth_call",
                    "to": address,
                    "data": call_data,
                    "tag": "latest"
                }
                
                if self.explorer_api_keys.get(blockchain):
                    params["apikey"] = self.explorer_api_keys[blockchain]
                
                result = await self._make_explorer_api_request(blockchain, params)
                return result.get("result", "0x")
            except Exception as e2:
                logger.error(f"Explorer API fallback failed: {e2}")
                raise
    
    def _encode_params(self, params: List[Any]) -> str:
        """Encode function parameters for contract call.
        
        Args:
            params: Function parameters
            
        Returns:
            Encoded parameters as hex string
            
        Note:
            This is a simplified implementation. In a real system,
            you would use web3.py's contract functionality for this.
        """
        # For simplicity, return empty string
        # In a real implementation, this would properly encode parameters using ABI
        return ""
