// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PullRequests {
    uint256 public pullRequestCount;

    struct PullRequest {
        uint256 pullRequestId;
        string projectName;
        string developer;
        string timestamp;
        string status;
        bool isLogged;
    }

    mapping(uint256 => PullRequest[]) public pullRequests;
    mapping(string => mapping(string => uint256[])) public developerPullRequests;

    event PullRequestLogged(
        uint256 indexed pullRequestId,
        string projectName,
        string developer,
        string timestamp,
        string status
    );

    event PullRequestStatusUpdated(
        uint256 indexed pullRequestId,
        string projectName,
        string developer,
        string timestamp,
        string newStatus
    );

    function logPullRequest(
        uint256 _pullRequestId,
        string memory _projectName,
        string memory _developer,
        string memory _timestamp,
        string memory _status
    ) public {
        // Validate status
        require(
            keccak256(abi.encodePacked(_status)) == keccak256(abi.encodePacked("pending")) ||
            keccak256(abi.encodePacked(_status)) == keccak256(abi.encodePacked("approved")) ||
            keccak256(abi.encodePacked(_status)) == keccak256(abi.encodePacked("rejected")),
            "Invalid status"
        );

        // Check for duplicate IDs
        if (pullRequests[_pullRequestId].length > 0) {
            require(!pullRequests[_pullRequestId][0].isLogged, "Pull request already logged");
        }

        PullRequest memory newPullRequest = PullRequest({
            pullRequestId: _pullRequestId,
            projectName: _projectName,
            developer: _developer,
            timestamp: _timestamp,
            status: _status,
            isLogged: true
        });

        pullRequests[_pullRequestId].push(newPullRequest);
        developerPullRequests[_developer][_projectName].push(_pullRequestId);
        pullRequestCount++;

        emit PullRequestLogged(_pullRequestId, _projectName, _developer, _timestamp, _status);
    }

    function updatePullRequestStatus(
        uint256 _pullRequestId,
        string memory _projectName,
        string memory _newStatus,
        string memory _timestamp
    ) public {
        require(pullRequests[_pullRequestId].length > 0, "Pull request does not exist");
        require(pullRequests[_pullRequestId][0].isLogged, "Pull request not logged");
        require(
            keccak256(abi.encodePacked(pullRequests[_pullRequestId][pullRequests[_pullRequestId].length - 1].status)) 
            != keccak256(abi.encodePacked(_newStatus)), 
            "Status unchanged"
        );
        require(
            keccak256(abi.encodePacked(_newStatus)) == keccak256(abi.encodePacked("pending")) ||
            keccak256(abi.encodePacked(_newStatus)) == keccak256(abi.encodePacked("approved")) ||
            keccak256(abi.encodePacked(_newStatus)) == keccak256(abi.encodePacked("rejected")),
            "Invalid status"
        );

        PullRequest memory updatedPullRequest = PullRequest({
            pullRequestId: _pullRequestId,
            projectName: _projectName,
            developer: pullRequests[_pullRequestId][0].developer,
            timestamp: _timestamp,
            status: _newStatus,
            isLogged: true
        });

        pullRequests[_pullRequestId].push(updatedPullRequest);
        developerPullRequests[pullRequests[_pullRequestId][0].developer][_projectName].push(_pullRequestId);
        pullRequestCount++;

        emit PullRequestStatusUpdated(_pullRequestId, _projectName, pullRequests[_pullRequestId][0].developer, _timestamp, _newStatus);
    }

    function getPullRequestsByDeveloper(string memory _developer, string memory _projectName)
        public
        view
        returns (uint256[] memory)
    {
        return developerPullRequests[_developer][_projectName];
    }

    function getPullRequest(uint256 _pullRequestId)
        public
        view
        returns (
            uint256 pullRequestId,
            string memory projectName,
            string memory developer,
            string memory timestamp,
            string memory status,
            bool isLogged
        )
    {
        if (pullRequests[_pullRequestId].length == 0) {
            return (0, "", "", "", "", false);
        }
        PullRequest memory pr = pullRequests[_pullRequestId][pullRequests[_pullRequestId].length - 1];
        return (
            pr.pullRequestId,
            pr.projectName,
            pr.developer,
            pr.timestamp,
            pr.status,
            pr.isLogged
        );
    }

    function getPullRequestHistory(uint256 _pullRequestId)
        public
        view
        returns (PullRequest[] memory)
    {
        return pullRequests[_pullRequestId];
    }

    function getPullRequestCount() public view returns (uint256) {
        return pullRequestCount;
    }
}