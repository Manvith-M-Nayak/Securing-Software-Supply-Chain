import json
import os
from pathlib import Path
from brownie import accounts, PullRequests, network

def main():
    # Method 1: Use accounts[0] directly (recommended for Ganache)
    deployer = accounts[0]
    
    print(f"🔍 Deployer address: {deployer.address}")
    print(f"🔍 Deployer balance: {deployer.balance()} ETH")
    
    if deployer.balance() == 0:
        print("❌ Deployer has no ETH! Please fund the account.")
        return
    
    # Lower gas price for local development
    gas_params = {
        "from": deployer,
        "gas_limit": 6721975,
        "gas_price": "20 gwei"
    }
    
    print("🚀 Deploying PullRequests...")
    pull_requests = PullRequests.deploy(gas_params)
    print(f"✅ PullRequests deployed at: {pull_requests.address}")

    print("\n🎉 Deployment Complete!")
    print("=" * 50)
    print(f"PullRequests:  {pull_requests.address}")
    print("=" * 50)

    # Define paths for frontend and backend
    frontend_abi_path = Path("../../frontend/src/abis")
    frontend_contracts_path = Path("../../frontend/src/contracts")

    backend_abi_path = Path("../../backend/abis")
    backend_contracts_path = Path("../../backend/contracts")

    # Ensure all target directories exist
    os.makedirs(frontend_abi_path, exist_ok=True)
    os.makedirs(frontend_contracts_path, exist_ok=True)
    os.makedirs(backend_abi_path, exist_ok=True)
    os.makedirs(backend_contracts_path, exist_ok=True)

    # Define contract
    contracts = {
        "PullRequests": PullRequests
    }

    # Dictionary to store deployed address
    addresses = {}

    for name, contract in contracts.items():
        # Get the latest deployed instance
        instance = contract[-1]

        # Extract and write only the ABI
        abi = instance.abi
        abi_json = json.dumps({"abi": abi}, indent=2)

        # Write ABI to frontend
        with open(frontend_abi_path / f"{name}.json", "w") as f:
            f.write(abi_json)

        # Write ABI to backend
        with open(backend_abi_path / f"{name}.json", "w") as f:
            f.write(abi_json)

        # Store address
        addresses[name] = instance.address

    # Write addresses to frontend
    with open(frontend_contracts_path / "addresses.json", "w") as f:
        json.dump(addresses, f, indent=2)

    # Write addresses to backend
    with open(backend_contracts_path / "addresses.json", "w") as f:
        json.dump(addresses, f, indent=2)

    print("✅ Synced ABI and address for PullRequests to both frontend and backend")

if __name__ == "__main__":
    main()