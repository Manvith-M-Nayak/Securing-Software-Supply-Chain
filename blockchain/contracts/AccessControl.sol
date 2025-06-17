// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract AccessControl {
    enum Role { None, User, Developer, Auditor, Admin }

    mapping(address => Role) public roles;
    address public owner;

    event RoleAssigned(address indexed account, Role role);
    event RoleRevoked(address indexed account);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    modifier onlyAdmin() {
        require(roles[msg.sender] == Role.Admin || msg.sender == owner, "Not admin");
        _;
    }

    modifier onlyRole(Role r) {
        require(roles[msg.sender] == r, "Incorrect role");
        _;
    }

    constructor() {
        owner = msg.sender;
        roles[msg.sender] = Role.Admin;
        emit RoleAssigned(msg.sender, Role.Admin);
    }

    function assignRole(address user, Role role) public onlyAdmin {
        roles[user] = role;
        emit RoleAssigned(user, role);
    }

    function revokeRole(address user) public onlyAdmin {
        roles[user] = Role.None;
        emit RoleRevoked(user);
    }

    function getRole(address user) public view returns (Role) {
        return roles[user];
    }

    function isAuthorized(address user, Role role) public view returns (bool) {
        return roles[user] == role;
    }
}