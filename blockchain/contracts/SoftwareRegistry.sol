// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./AccessControl.sol";

interface IGamification {
    function performAction(uint8 action) external;
}

contract SoftwareRegistry {
    struct Version {
        string version;
        string hash;
        string commitHash; 
        uint256 timestamp;
    }

    struct Component {
        string name;
        address creator;
        Version[] versions;
        uint256[] dependencies;
        bool exists;
    }

    mapping(uint256 => Component) public components;
    uint256 public componentCount;

    AccessControl public accessControl;
    IGamification public gamification;

    event ComponentRegistered(
        uint256 indexed componentId,
        string name,
        string version,
        string hash,
        string commitHash
    );

    event VersionAdded(
        uint256 indexed componentId,
        string version,
        string hash,
        string commitHash
    );

    event DependencyAdded(
        uint256 indexed fromComponentId,
        uint256 toComponentId
    );

    constructor(address _accessControl, address _gamification) {
        accessControl = AccessControl(_accessControl);
        gamification = IGamification(_gamification);
    }

    function registerComponent(
        string memory name,                 // These are the parameters for the function
        string memory version,
        string memory hash,
        string memory commitHash
    ) public {
        require(
            accessControl.isAuthorized(msg.sender, AccessControl.Role.Developer), //Checking whether the user is a dev
            "Not a developer"
        );

        uint256 id = componentCount;
        Component storage c = components[id];
        c.name = name;
        c.creator = msg.sender;
        c.exists = true;
        c.versions.push(Version(version, hash, commitHash, block.timestamp));
        componentCount++;

        emit ComponentRegistered(id, name, version, hash, commitHash);

        gamification.performAction(uint8(0)); // ActionType.UploadComponent
    }

    function addVersion(
        uint256 componentId,
        string memory version,
        string memory hash,
        string memory commitHash
    ) public {
        require(components[componentId].exists, "Component does not exist");
        require(components[componentId].creator == msg.sender, "Only creator can add version");

        components[componentId].versions.push(
            Version(version, hash, commitHash, block.timestamp)
        );

        emit VersionAdded(componentId, version, hash, commitHash);
    }

    function addDependency(uint256 fromComponentId, uint256 toComponentId) public {
        require(components[fromComponentId].exists && components[toComponentId].exists, "Component does not exist");
        require(components[fromComponentId].creator == msg.sender, "Only creator can add dependency");

        components[fromComponentId].dependencies.push(toComponentId);
        emit DependencyAdded(fromComponentId, toComponentId);
    }

    function getVersions(uint256 componentId) public view returns (Version[] memory) {
        return components[componentId].versions;
    }

    function getDependencies(uint256 componentId) public view returns (uint256[] memory) {
        return components[componentId].dependencies;
    }

    function getComponent(uint256 componentId) public view returns (
        string memory name,
        address creator,
        bool exists
    ) {
        Component storage c = components[componentId];
        return (c.name, c.creator, c.exists);
    }
}