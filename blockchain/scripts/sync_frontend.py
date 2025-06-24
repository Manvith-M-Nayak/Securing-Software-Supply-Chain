import json
import os
from pathlib import Path

from brownie import SoftwareRegistry, AccessControl, AuditTrail, GamificationEngine

def main():
    # Paths relative to blockchain/scripts/sync.py
    frontend_abi_path = Path("../../frontend/src/abis")
    frontend_contracts_path = Path("../../frontend/src/contracts")

    # Ensure target directories exist
    os.makedirs(frontend_abi_path, exist_ok=True)
    os.makedirs(frontend_contracts_path, exist_ok=True)

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
        abi_dest = frontend_abi_path / f"{name}.json"

        with open(abi_dest, "w") as f:
            json.dump(abi, f, indent=2)

        # Store address
        addresses[name] = instance.address

    # Write addresses to addresses.json
    address_file = frontend_contracts_path / "addresses.json"
    with open(address_file, "w") as f:
        json.dump(addresses, f, indent=2)

    print("Synced frontend with latest ABIs and contract addresses.")
