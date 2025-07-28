import json
import os
from web3 import Web3
from web3.middleware import geth_poa_middleware
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Connect to the local Ethereum node
web3 = Web3(Web3.HTTPProvider("http://172.29.240.1:8545"))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
if not web3.is_connected():
    logger.error("Failed to connect to Ethereum node at http://172.29.240.1:8545")
    raise Exception("Failed to connect to Ethereum node")

# Load the ABI from the backend directory
abi_path = os.path.join(os.path.dirname(__file__), 'backend', 'abis', 'PullRequests.json')
try:
    with open(abi_path, 'r') as f:
        abi = json.load(f)['abi']
except FileNotFoundError:
    logger.error(f"ABI file not found at {abi_path}")
    raise Exception(f"ABI file not found at {abi_path}")
except json.JSONDecodeError:
    logger.error(f"Invalid JSON in ABI file at {abi_path}")
    raise Exception(f"Invalid JSON in ABI file")

# Contract address
contract_address = "0xc4a28C2308822811d2e08558FA25E1d035792d73"

# Create contract instance
try:
    contract = web3.eth.contract(address=contract_address, abi=abi)
except Exception as e:
    logger.error(f"Failed to initialize contract at {contract_address}: {str(e)}")
    raise Exception(f"Failed to initialize contract: {str(e)}")

# Your Ethereum account details (replace with actual values)
account_address = "0xa6Ec1baB487a3dD34FEe313807B5Af84d02F0317"  # e.g., '0x1234...'
private_key = "0xd59cef127aa78e055eb5f1db001ea21fb09c49a0c2339f6d1a5a43f072109cd6"  # e.g., '0x...'

# Ensure the account has the private key
try:
    web3.eth.account.from_key(private_key)
except ValueError as e:
    logger.error(f"Invalid private key: {str(e)}")
    raise Exception(f"Invalid private key")

# Function to log a pull request
def log_pull_request():
    try:
        # Sample pull request data
        pull_request_id = 1
        project_name = "test"
        timestamp = "2025-07-26T14:35:00Z"  # Current time + 1 minute from 02:35 PM IST
        status = "pending"

        # Estimate gas required
        logger.info("Estimating gas requirement...")
        gas_estimate = contract.functions.logPullRequest(
            pull_request_id,
            project_name,
            timestamp,
            status
        ).estimate_gas({'from': account_address})

        # Use estimated gas with a 20% buffer
        gas_limit = int(gas_estimate * 1.2)
        logger.info(f"Estimated gas: {gas_estimate}, Using gas limit: {gas_limit}")

        # Build the transaction
        nonce = web3.eth.get_transaction_count(account_address)
        tx = contract.functions.logPullRequest(
            pull_request_id,
            project_name,
            timestamp,
            status
        ).build_transaction({
            'from': account_address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': web3.to_wei('50', 'gwei'),
        })

        # Sign and send the transaction
        logger.info("Signing and sending transaction...")
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for transaction receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        logger.info(f"Pull request logged successfully. Transaction hash: {web3.to_hex(tx_hash)}")
        logger.info(f"Block number: {receipt.blockNumber}")
        return tx_hash

    except ValueError as e:
        logger.error(f"Transaction failed: {str(e)}")
        if 'out of gas' in str(e).lower():
            logger.error("Gas limit too low. Try increasing the gas limit manually.")
        raise
    except Exception as e:
        logger.error(f"Error logging pull request: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        log_pull_request()
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")