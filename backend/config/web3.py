from web3 import Web3
import os
import json
from dotenv import load_dotenv
from web3.middleware import geth_poa_middleware

# Load variables from .env into the environment
load_dotenv()

# Function to return a connected Web3 instance
def get_web3():
    # Load RPC endpoint from .env file
    ganache_rpc = os.environ.get("GANACHE_RPC")
    if not ganache_rpc:
        raise Exception("GANACHE_RPC not set in .env")

    # Initialize Web3 with the HTTP Provider
    w3 = Web3(Web3.HTTPProvider(ganache_rpc))

    # Inject POA middleware if it hasn’t already been injected
    if geth_poa_middleware not in w3.middleware_onion:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    # Verify connection
    if not w3.is_connected():
        raise ConnectionError("Web3 is not connected to the RPC provider.")

    return w3

# Function to retrieve the deployed contract instance
def get_contract(w3):
    # Load contract address from .env
    contract_address = os.environ.get("REGISTRY_ADDRESS")
    if not contract_address:
        raise Exception("REGISTRY_ADDRESS not set in .env")

    # Build the ABI path (assuming ABI is a raw list or full artifact)
    abi_path = "../frontend/src/abis/SoftwareRegistry.json"
    if not os.path.exists(abi_path):
        raise FileNotFoundError(f"ABI file not found at {abi_path}")

    # Load and parse the ABI file
    with open(abi_path, "r") as file:
        abi_json = json.load(file)

        # Handle two ABI formats: raw list and full artifact
        if isinstance(abi_json, list):
            abi = abi_json
        elif isinstance(abi_json, dict) and "abi" in abi_json:
            abi = abi_json["abi"]
        else:
            raise ValueError("Invalid ABI format: Expected a list or a dict with 'abi' key.")

    # Return the contract instance using checksum address
    return w3.eth.contract(address=w3.to_checksum_address(contract_address), abi=abi)
