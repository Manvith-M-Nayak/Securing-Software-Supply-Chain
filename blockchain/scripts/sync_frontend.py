import json
import os
from pathlib import Path
from brownie import SoftwareRegistry, AccessControl, AuditTrail, GamificationEngine

def main():
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

    # Define contracts
    contracts = {
        "SoftwareRegistry": SoftwareRegistry,
        "AccessControl": AccessControl,
        "AuditTrail": AuditTrail,
        "GamificationEngine": GamificationEngine,
    }

    # Dictionary to store deployed addresses
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

    print("✅ Synced ABIs and addresses to both frontend and backend")
