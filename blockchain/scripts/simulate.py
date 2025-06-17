from brownie import accounts, AccessControl, GamificationEngine, SoftwareRegistry, AuditTrail

def main():
    admin = accounts[0]
    developer = accounts[1]
    auditor = accounts[2]

    # Use latest deployed contract instances
    access_control = AccessControl[-1]
    gamification = GamificationEngine[-1]
    software_registry = SoftwareRegistry[-1]
    audit_trail = AuditTrail[-1]

    print("🎓 Assigning roles...")
    access_control.assignRole(developer, 1, {"from": admin})  # Role.Developer = 1
    access_control.assignRole(auditor, 2, {"from": admin})    # Role.Auditor = 2

    print("🛠 Developer registering a component...")
    tx1 = software_registry.registerComponent(
    "ComponentX", "1.0.0", "QmComponentHash123", "pass", {"from": developer}
    )

    print("✅ Component registered")

    print("🔍 Auditor logging an audit...")
    tx2 = audit_trail.logAudit(
        0,                # componentId (only one so far)
        "pass",           # auditResult
        "QmAuditReportHash456",  # auditHash
        "pass",           # ML Verdict (add this if required by your constructor)
        {"from": auditor}
    )
    print("✅ Audit logged")

    print("🎮 Checking gamification stats...")
    points = gamification.pointsOf(developer)
    print(f"🎯 Developer Points: {points}")

    streak = gamification.streaks(developer)
    print(f"🔥 Developer Streak: {streak}")

    badges = gamification.getBadges(developer)
    print(f"🏅 Developer Badges: {badges}")

    