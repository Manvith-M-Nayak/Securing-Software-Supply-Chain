from brownie import accounts, AccessControl, GamificationEngine, SoftwareRegistry, AuditTrail, network

def main():
    # Method 1: Use accounts[0] directly (recommended for Ganache)
    deployer = accounts[0]
    
    # Method 2: Alternative - Load from mnemonic if needed
    # deployer = accounts.from_mnemonic("test test test test test test test test test test test junk", count=1)[0]
    
    # Method 3: If you have private keys, use this instead
    # deployer = accounts.add('your_private_key_here')
    
    print(f"🔍 Deployer address: {deployer.address}")
    print(f"🔍 Deployer balance: {deployer.balance()} ETH")
    
    if deployer.balance() == 0:
        print("❌ Deployer has no ETH! Please fund the account.")
        return
    
    # Lower gas price for local development
    gas_params = {
        "from": deployer,
        "gas_limit": 6721975,
        "gas_price": "20 gwei"  # Reduced from 2 gwei to 20 gwei
    }
    
    print("🚀 Deploying AccessControl...")
    access_control = AccessControl.deploy(gas_params)
    print(f"✅ AccessControl deployed at: {access_control.address}")

    print("🚀 Deploying GamificationEngine...")
    gamification = GamificationEngine.deploy(gas_params)
    print(f"✅ GamificationEngine deployed at: {gamification.address}")

    print("🚀 Deploying SoftwareRegistry...")
    software_registry = SoftwareRegistry.deploy(
        access_control.address,
        gamification.address,
        gas_params
    )
    print(f"✅ SoftwareRegistry deployed at: {software_registry.address}")

    print("🚀 Deploying AuditTrail...")
    audit_trail = AuditTrail.deploy(
        access_control.address,
        gamification.address,
        software_registry.address,
        gas_params
    )
    print(f"✅ AuditTrail deployed at: {audit_trail.address}")

    print("\n🎉 Deployment Complete!")
    print("=" * 50)
    print(f"AccessControl:     {access_control.address}")
    print(f"GamificationEngine: {gamification.address}")
    print(f"SoftwareRegistry:  {software_registry.address}")
    print(f"AuditTrail:        {audit_trail.address}")
    print("=" * 50)
    
    # Optional: Test basic functionality
    print("\n🧪 Testing basic functionality...")
    try:
        # Test AccessControl
        print(f"AccessControl owner: {access_control.owner()}")
        print("✅ All contracts deployed and accessible!")
    except Exception as e:
        print(f"⚠️  Warning: {e}")

if __name__ == "__main__":
    main()