from brownie import accounts, AccessControl, GamificationEngine, SoftwareRegistry, AuditTrail

def main():
     # This loads the same accounts used in Ganache GUI
    deployer = accounts.from_mnemonic("test test test test test test test test test test test junk", count=10)[0]
        
    if len(accounts) == 0:
        print("No accounts available. Please connect to a network with accounts.")
        return

    print("🚀 Deploying AccessControl...")
    access_control = AccessControl.deploy({"from": deployer,"gas_limit": 6000000,
            "gas_price": "2 gwei"})

    print("🚀 Deploying GamificationEngine...")
    gamification = GamificationEngine.deploy({"from": deployer,"gas_limit": 6000000,
            "gas_price": "2 gwei"})

    print("🚀 Deploying SoftwareRegistry...")
    software_registry = SoftwareRegistry.deploy(
        access_control.address,
        gamification.address,
        {"from": deployer,"gas_limit": 6000000,
            "gas_price": "2 gwei"}
    )

    print("🚀 Deploying AuditTrail...")
    audit_trail = AuditTrail.deploy(
        access_control.address,
        gamification.address,
        software_registry.address,  # ✅ FIXED: third constructor argument added
        {"from": deployer,"gas_limit": 6000000,
            "gas_price": "2 gwei"}
    )

    print("\n✅ Deployment Complete:")
    print("AccessControl:", access_control.address)
    print("GamificationEngine:", gamification.address)
    print("SoftwareRegistry:", software_registry.address)
    print("AuditTrail:", audit_trail.address)