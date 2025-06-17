// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract GamificationEngine {
    enum ActionType {
        UploadComponent,      // 0
        SubmitAudit,          // 1
        FindVulnerability,    // 2
        ResolveIssue,         // 3
        SecureRelease,        // 4
        PatchDependency       // 5
    }

    struct UserStats {
        uint256 points;
        uint256 streak;
        string[] badges;
        mapping(ActionType => uint256) actionCounts;
    }

    mapping(address => UserStats) private users;

    event ActionPerformed(address indexed user, ActionType action, uint256 pointsAwarded);
    event BadgeEarned(address indexed user, string badge);
    event StreakUpdated(address indexed user, uint256 newStreak);

    modifier validAction(uint8 actionIndex) {
        require(actionIndex <= uint8(ActionType.PatchDependency), "Invalid action type");
        _;
    }

    function performAction(ActionType action) external validAction(uint8(action)) {
        uint256 points = _getPointsForAction(action);
        UserStats storage stats = users[msg.sender];

        stats.points += points;
        stats.actionCounts[action]++;
        stats.streak++;

        emit ActionPerformed(msg.sender, action, points);
        emit StreakUpdated(msg.sender, stats.streak);

        _checkForBadges(msg.sender);
    }

    function _getPointsForAction(ActionType action) internal pure returns (uint256) {
        if (action == ActionType.UploadComponent) return 10;
        if (action == ActionType.SubmitAudit) return 15;
        if (action == ActionType.FindVulnerability) return 25;
        if (action == ActionType.ResolveIssue) return 20;
        if (action == ActionType.SecureRelease) return 30;
        if (action == ActionType.PatchDependency) return 15;
        return 0;
    }

    function _checkForBadges(address user) internal {
        UserStats storage stats = users[user];

        if (stats.points >= 100 && !_hasBadge(user, "Rising Star")) {
            stats.badges.push("Rising Star");
            emit BadgeEarned(user, "Rising Star");
        }

        if (stats.streak >= 5 && !_hasBadge(user, "Consistent Contributor")) {
            stats.badges.push("Consistent Contributor");
            emit BadgeEarned(user, "Consistent Contributor");
        }

        if (stats.actionCounts[ActionType.FindVulnerability] >= 3 && !_hasBadge(user, "Bug Hunter")) {
            stats.badges.push("Bug Hunter");
            emit BadgeEarned(user, "Bug Hunter");
        }

        if (stats.actionCounts[ActionType.SecureRelease] >= 2 && !_hasBadge(user, "Security Champion")) {
            stats.badges.push("Security Champion");
            emit BadgeEarned(user, "Security Champion");
        }
    }

    function _hasBadge(address user, string memory badge) internal view returns (bool) {
        string[] memory userBadges = users[user].badges;
        for (uint i = 0; i < userBadges.length; i++) {
            if (keccak256(bytes(userBadges[i])) == keccak256(bytes(badge))) {
                return true;
            }
        }
        return false;
    }

    // External view functions for frontends/APIs
    function getUserStats(address user) external view returns (uint256 points, uint256 streak, string[] memory badges) {
        UserStats storage stats = users[user];
        return (stats.points, stats.streak, stats.badges);
    }

    function getActionCount(address user, ActionType action) external view returns (uint256) {
        return users[user].actionCounts[action];
    }

    function pointsOf(address user) external view returns (uint256) {
        return users[user].points;
    }

    function streaks(address user) external view returns (uint256) {
        return users[user].streak;
    }

    function getBadges(address user) external view returns (string[] memory) {
        return users[user].badges;
    }
}