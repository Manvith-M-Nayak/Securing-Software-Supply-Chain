// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*  ───────────────────────────────────────────────────────────────────────────
    SoftwareRegistry
    --------------------------------------------------------------------------
    CHANGES IN THIS VERSION
      1.  storeCommit now accepts *either* a 40‑character Git SHA‑1 string
          or a 66‑character 0x‑prefixed hex (bytes32) and validates both.
      2.  Authorisation logic is more forgiving:
            • If `committer == address(0)`  →  msg.sender is used.
            • If msg.sender OR committer is an authorised Developer, it passes.
      3.  Gamification hook wrapped in try/catch so a mis‑configured engine
          can never revert a user transaction.
      4.  Added convenience aliases recordCommit(...) and addCommit(...)
          which forward to storeCommit(...) so older ABIs remain functional.
      5.  Added detailed revert reasons to every require() for easier
          debugging from the frontend.
      6.  Solidity‑style natspec cleaned up and expanded.
    --------------------------------------------------------------------------
    NOTE:  No changes are required in your frontend code that calls
           storeCommit / recordCommit / addCommit.  All three work.
    ─────────────────────────────────────────────────────────────────────────*/

/* ───────────────────────────── dependencies ─────────────────────────────── */
import "./AccessControl.sol";

/* ─────────────────────── external gamification interface ────────────────── */
interface IGamification {
    function performAction(uint8 action) external;
}

/* ─────────────────────────── main contract ──────────────────────────────── */
contract SoftwareRegistry {
    /* ───────────────────────────── data types ───────────────────────────── */

    struct Version {
        string   version;        // semantic version tag  (v1.2.3)
        string   hash;           // content hash          (IPFS / SHA‑256)
        string   commitHash;     // 40‑byte Git commit SHA
        uint256  timestamp;      // added at block.time
    }

    struct Component {
        string     name;         // repository / package name
        address    creator;      // wallet that registered component
        Version[]  versions;     // chronological history
        uint256[]  dependencies; // componentIds it relies on
        bool       exists;       // guard flag
    }

    struct Commit {
        string   projectName;    // repository name
        string   commitHash;     // original Git commit SHA
        string   metadata;       // JSON blob from backend
        address  committer;      // credited wallet
        uint256  timestamp;      // on‑chain time
    }

    /* ───────────────────────── storage variables ────────────────────────── */

    mapping(uint256 => Component) public components;   // componentId → Component
    uint256 public componentCount;

    // commitHash is unique; keeping it as a string keeps ABI simple.
    mapping(string => Commit) private commits;         // commitHash → Commit

    AccessControl public accessControl;
    IGamification public gamification;

    /* ────────────────────────────── events ──────────────────────────────── */

    event ComponentRegistered(
        uint256 indexed componentId,
        string  name,
        string  version,
        string  hash,
        string  commitHash
    );

    event VersionAdded(
        uint256 indexed componentId,
        string  version,
        string  hash,
        string  commitHash
    );

    event DependencyAdded(
        uint256 indexed fromComponentId,
        uint256 toComponentId
    );

    event CommitStored(
        string  indexed projectName,
        string  indexed commitHash,
        address indexed committer
    );

    /* ─────────────────────────── constructor ───────────────────────────── */

    constructor(address _accessControl, address _gamification) {
        accessControl = AccessControl(_accessControl);
        gamification  = IGamification(_gamification);
    }

    /* ─────────────────── component‑level functionality ──────────────────── */

    /**
     * Register a brand‑new software component.
     * Caller must possess the Developer role inside AccessControl.
     */
    function registerComponent(
        string memory name,
        string memory version,
        string memory hash,
        string memory commitHash
    ) external {
        require(
            accessControl.isAuthorized(msg.sender, AccessControl.Role.Developer),
            "registerComponent: caller is not a developer"
        );

        uint256 id              = componentCount;
        Component storage c      = components[id];
        c.name                   = name;
        c.creator                = msg.sender;
        c.exists                 = true;
        c.versions.push(
            Version(version, hash, commitHash, block.timestamp)
        );
        componentCount++;

        emit ComponentRegistered(id, name, version, hash, commitHash);

        /* Gamification action type 0 = UploadComponent. Non‑critical. */
        _safeGamificationHook(uint8(0));
    }

    /**
     * Append a new semantic version to an existing component.
     */
    function addVersion(
        uint256 componentId,
        string memory version,
        string memory hash,
        string memory commitHash
    ) external {
        require(components[componentId].exists, "addVersion: component missing");
        require(
            components[componentId].creator == msg.sender,
            "addVersion: only creator"
        );

        components[componentId].versions.push(
            Version(version, hash, commitHash, block.timestamp)
        );

        emit VersionAdded(componentId, version, hash, commitHash);
    }

    /**
     * Declare that Component A depends on Component B.
     */
    function addDependency(
        uint256 fromComponentId,
        uint256 toComponentId
    ) external {
        require(
            components[fromComponentId].exists &&
            components[toComponentId].exists,
            "addDependency: component missing"
        );
        require(
            components[fromComponentId].creator == msg.sender,
            "addDependency: only creator"
        );

        components[fromComponentId].dependencies.push(toComponentId);
        emit DependencyAdded(fromComponentId, toComponentId);
    }

    /* ───────────────────── Git commit‑level functionality ───────────────── */

    /**
     * Primary commit‑storage entry point.
     *
     * Arguments match the call the backend already emits:
     *   projectName, commitHash, metadata, committer
     *
     * commitHash can be either:
     *   • 40‑char raw SHA‑1     (e.g.  a1b2c3…f9)
     *   • 66‑char 0x‑prefixed   (e.g.  0xa1b2…f9, 64 hex digits)
     *
     * Passing `committer = address(0)` auto‑fills it with msg.sender.
     */
    function storeCommit(
        string memory projectName,
        string memory commitHash,
        string memory metadata,
        address committer
    ) public {
        bytes memory hashBytes = bytes(commitHash);
        require(
            hashBytes.length == 40 || hashBytes.length == 66,
            "storeCommit: commitHash must be 40 or 66 chars"
        );

        /* Uniqueness check (case‑sensitive) */
        require(
            bytes(commits[commitHash].commitHash).length == 0,
            "storeCommit: commit already stored"
        );

        /* Resolve who gets author credit */
        address effectiveCommitter =
            committer == address(0) ? msg.sender : committer;

        /* Authorisation: either party can be a recognised Developer */
        require(
            accessControl.isAuthorized(effectiveCommitter, AccessControl.Role.Developer) ||
            accessControl.isAuthorized(msg.sender        , AccessControl.Role.Developer),
            "storeCommit: not authorised developer"
        );

        commits[commitHash] = Commit({
            projectName : projectName,
            commitHash  : commitHash,
            metadata    : metadata,
            committer   : effectiveCommitter,
            timestamp   : block.timestamp
        });

        emit CommitStored(projectName, commitHash, effectiveCommitter);

        /* Gamification action type 1 = StoreCommit. Non‑critical. */
        _safeGamificationHook(uint8(1));
    }

    /*  Legacy aliases so older ABIs never break.
        Both simply forward to storeCommit with identical semantics.       */

    function recordCommit(
        string memory projectName,
        string memory commitHash,
        string memory metadata,
        address committer
    ) external {
        storeCommit(projectName, commitHash, metadata, committer);
    }

    function addCommit(
        string memory projectName,
        string memory commitHash,
        string memory metadata,
        address committer
    ) external {
        storeCommit(projectName, commitHash, metadata, committer);
    }

    /* ───────────────────────────── view helpers ─────────────────────────── */

    function getCommit(
        string calldata commitHash
    ) external view returns (
        string memory projectName,
        string memory metadata,
        address committer,
        uint256 timestamp
    ) {
        Commit storage c = commits[commitHash];
        require(bytes(c.commitHash).length != 0, "getCommit: not found");
        return (c.projectName, c.metadata, c.committer, c.timestamp);
    }

    function getVersions(
        uint256 componentId
    ) external view returns (Version[] memory) {
        return components[componentId].versions;
    }

    function getDependencies(
        uint256 componentId
    ) external view returns (uint256[] memory) {
        return components[componentId].dependencies;
    }

    function getComponent(
        uint256 componentId
    ) external view returns (
        string memory name,
        address creator,
        bool exists
    ) {
        Component storage c = components[componentId];
        return (c.name, c.creator, c.exists);
    }

    /* ─────────────────────── internal helper functions ──────────────────── */

    /**
     * Calls gamification.performAction(action) but *never* reverts
     * the whole transaction if the call fails or the engine is unset.
     */
    function _safeGamificationHook(uint8 action) internal {
        if (address(gamification) == address(0)) return;
        /* External call safety wrapper */
        try gamification.performAction(action) { /**/ }
        catch { /** swallow all failures **/ }
    }
}
