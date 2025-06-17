// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AccessControl.sol";
import "./SoftwareRegistry.sol"; // For verifying commitHash existence

contract AuditTrail {
    AccessControl public accessControl;
    IGamification public gamification;
    SoftwareRegistry public softwareRegistry;

    constructor(address _accessControl, address _gamification, address _softwareRegistry) {
        accessControl = AccessControl(_accessControl);
        gamification = IGamification(_gamification);
        softwareRegistry = SoftwareRegistry(_softwareRegistry);
    }

    struct AuditRecord {
        uint256 auditId;
        uint256 componentId;
        address auditor;
        string mlVerdict;
        string reportHash;
        string commitHash;
        uint256 timestamp;
    }

    uint256 public nextAuditId = 0;
    mapping(uint256 => AuditRecord[]) private audits;

    event AuditLogged(
        uint256 indexed auditId,
        uint256 indexed componentId,
        address indexed auditor,
        string mlVerdict,
        string reportHash,
        string commitHash,
        uint256 timestamp
    );

    function logAudit(
        uint256 componentId,
        string calldata mlVerdict,
        string calldata reportHash,
        string calldata commitHash
    ) external {
        require(
            accessControl.isAuthorized(msg.sender, AccessControl.Role.Auditor),
            "Not authorized"
        );

        // ✅ Validate commitHash exists for the component
        bool valid = false;
        SoftwareRegistry.Version[] memory versions = softwareRegistry.getVersions(componentId);

        for (uint i = 0; i < versions.length; i++) {
            if (keccak256(abi.encodePacked(versions[i].commitHash)) == keccak256(abi.encodePacked(commitHash))) {
                valid = true;
                break;
            }
        }

        require(valid, "Invalid commitHash for this component");

        audits[componentId].push(
            AuditRecord(
                nextAuditId,
                componentId,
                msg.sender,
                mlVerdict,
                reportHash,
                commitHash,
                block.timestamp
            )
        );

        emit AuditLogged(nextAuditId, componentId, msg.sender, mlVerdict, reportHash, commitHash, block.timestamp);
        nextAuditId++;

        gamification.performAction(1); // ActionType.UploadAudit
    }

    function getAuditCount(uint256 componentId) external view returns (uint256) {
        return audits[componentId].length;
    }

    function getAuditByIndex(uint256 componentId, uint256 index) external view returns (
        uint256 auditId,
        address auditor,
        string memory mlVerdict,
        string memory reportHash,
        string memory commitHash,
        uint256 timestamp
    ) {
        require(index < audits[componentId].length, "Invalid index");
        AuditRecord storage a = audits[componentId][index];
        return (a.auditId, a.auditor, a.mlVerdict, a.reportHash, a.commitHash, a.timestamp);
    }
}