# Securing Software Supply Chain

A novel framework for securing the software supply chain by integrating **Code Forensics**, **Blockchain**, and **Gamification**.

---

## Overview

As software projects grow in complexity, multiple developers collaborate through version control systems, making it critical to ensure every code change is secure and traceable. This platform automates security analysis of pull requests, logs every action immutably on a **blockchain**, and incentivizes secure coding through **gamification**.

---

## Features

- **Vulnerability Detection** — Automatically scans pull requests for buffer overflows, SQL injection, XSS, path traversal, and integer overflow/underflow.
- **Blockchain Audit Trail** — Every pull request, review decision, and metadata is immutably logged via smart contracts on a private blockchain.
- **Role-based Access Control** — Developers, Auditors, and Administrators each have tailored dashboards and permissions.
- **Code Forensics** — Full pull request history with transaction hashes, timestamps, and vulnerability details accessible from the admin panel.
- **Gamification** — Developers earn/lose points based on the security quality of their commits, incentivizing secure coding practices.

---

## Project Structure

```
Securing-Software-Supply-Chain/
│
├── backend/                    # Flask backend
│   ├── server.py               # Main server entry point
│   ├── requirements.txt
│   ├── abis/                   # Contract ABIs for backend Web3 calls
│   ├── bin/                    # Bearer token utilities
│   ├── config/
│   │   ├── db.py               # MongoDB connection
│   │   └── web3.py             # Web3/blockchain connection
│   ├── contracts/
│   │   └── addresses.json      # Deployed contract addresses
│   ├── models/                 # Mongoose-style Python models
│   │   ├── commit.py
│   │   ├── commit_model.py     # ML model integration
│   │   ├── project.py
│   │   └── user.py
│   └── routes/
│       ├── admin_routes.py
│       ├── auditor_routes.py
│       ├── auth_routes.py
│       ├── developer_routes.py
│       └── webhook_routes.py   # GitHub webhook handler
│
├── blockchain/                 # Brownie smart contract project
│   ├── contracts/
│   │   ├── AccessControl.sol
│   │   ├── AuditTrail.sol
│   │   ├── GamificationEngine.sol
│   │   ├── PullRequests.sol
│   │   └── SoftwareRegistry.sol
│   ├── scripts/
│   │   ├── deploy.py
│   │   ├── simulate.py
│   │   └── sync_frontend.py    # Syncs deployed ABIs to frontend
│   └── brownie-config.yaml
│
├── frontend/                   # React frontend
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── abis/               # Contract ABIs for frontend Web3 calls
│       ├── contracts/          # Deployed contract addresses
│       └── pages/
│           ├── Login.js
│           ├── Signup.js
│           ├── Dashboard.js
│           ├── AdminDashboard.js
│           ├── AdminCreateProject.js
│           ├── AdminCommitHistory.js
│           ├── AdminPullHistory.js
│           ├── AdminRoleManager.js
│           ├── AuditorDashboard.js
│           └── DeveloperDashboard.js
│
├── requirements.txt            # Root-level Python dependencies
├── package.json
├── test.py
└── test.js
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React.js |
| Backend | Python (Flask) |
| Database | MongoDB |
| Blockchain | Solidity Smart Contracts (Brownie) |
| GitHub Integration | GitHub Webhooks + GitHub API |
| Web3 | Web3.py |

---

## Prerequisites

- Python 3.8+
- Node.js 16+
- MongoDB (local or Atlas)
- Brownie (`pip install eth-brownie`)
- A local or test Ethereum network (e.g., Ganache)
- A GitHub account with webhook access

---

## Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Manvith-M-Nayak/Securing-Software-Supply-Chain.git
cd Securing-Software-Supply-Chain
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
```

Configure your environment variables (create a `.env` file in `/backend`):

```env
MONGO_URI=mongodb://localhost:27017/supplychain
SECRET_KEY=your_jwt_secret
GITHUB_TOKEN=your_github_personal_access_token
WEB3_PROVIDER=http://127.0.0.1:8545
```

Start the Flask server:

```bash
python server.py
```

### 3. Blockchain

```bash
cd blockchain
brownie compile
brownie run scripts/deploy.py --network development
brownie run scripts/sync_frontend.py   # Copies ABIs and addresses to frontend
```

### 4. Frontend

```bash
cd frontend
npm install
npm start
```

The React app will be available at `http://localhost:3000`.

---

## How It Works

1. **Admin** creates a project → a linked GitHub repository is set up and developers/auditors are assigned.
2. **Developer** opens a pull request → the GitHub webhook triggers the backend.
4. **Blockchain** logs the pull request metadata, verdict, and timestamps immutably.
5. **Auditor** reviews the vulnerability report on the dashboard and approves or rejects the PR.
6. **Gamification Engine** updates developer points based on the outcome.

---

## User Roles

| Role | Capabilities |
|---|---|
| **Developer** | Submit pull requests, view own PR history and points |
| **Auditor** | View ML scan results, approve or reject pull requests |
| **Administrator** | Create projects, assign roles, view full audit history |

---

## Smart Contracts

| Contract | Purpose |
|---|---|
| `PullRequests.sol` | Records PR submissions, statuses, and verdicts |
| `AuditTrail.sol` | Immutable log of all auditor actions |
| `GamificationEngine.sol` | Tracks and updates developer point scores |
| `AccessControl.sol` | Manages role-based permissions on-chain |
| `SoftwareRegistry.sol` | Registers projects and associated metadata |

---

## Running Tests

```bash
# Python tests
python test.py

# JavaScript tests
node test.js
```

---

