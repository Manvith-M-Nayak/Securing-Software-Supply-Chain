import json
import os
from pathlib import Path

from brownie import SoftwareRegistry, AccessControl, AuditTrail, GamificationEngine

def main():
    print("Syncing frontend with latest ABIs and contract addresses...")

    # Define paths
    build_path = Path("build/contracts")
    frontend_abi_path = Path("../../frontend/src/abis")
    frontend_contracts_path = Path("../../frontend/src/contracts")

    # Ensure target directories exist
    os.makedirs(frontend_abi_path, exist_ok=True)
    os.makedirs(frontend_contracts_path, exist_ok=True)

    # Save ABIs
    contracts = {
        "SoftwareRegistry": SoftwareRegistry,
        "AccessControl": AccessControl,
        "AuditTrail": AuditTrail,
        "GamificationEngine": GamificationEngine,
    }

    addresses = {}

    for name, contract in contracts.items():
        # Save ABI
        abi_source = build_path / f"{name}.json"
        with open(abi_source, "r") as f:
            contract_data = json.load(f)

        abi_dest = frontend_abi_path / f"{name}.json"
        with open(abi_dest, "w") as f:
            json.dump(contract_data, f, indent=2)

        # Save address
        addresses[name] = contract[-1].address

    # Write addresses.json
    address_file = frontend_contracts_path / "addresses.json"
    with open(address_file, "w") as f:
        json.dump(addresses, f, indent=2)

    print("✅ Synced frontend with latest ABIs and contract addresses.")
