const Web3 = require('web3');
const fs = require('fs');

// Connect to the local Ethereum node
const web3 = new Web3('http://172.29.240.1:8545');

// Load the ABI from the backend directory
const abi = JSON.parse(fs.readFileSync('backend/abis/PullRequests.json', 'utf8')).abi;

// Contract address
const contractAddress = '0xc4a28C2308822811d2e08558FA25E1d035792d73';

// Create contract instance
const contract = new web3.eth.Contract(abi, contractAddress);

// Your Ethereum account details (replace with actual values)
const account = '0xa6Ec1baB487a3dD34FEe313807B5Af84d02F0317'; // e.g., '0x1234...'
const privateKey = '0xd59cef127aa78e055eb5f1db001ea21fb09c49a0c2339f6d1a5a43f072109cd6'; // e.g., '0x...'

// Function to log a pull request
async function logPullRequest() {
  const tx = await contract.methods.logPullRequest(
    1,              // pullRequestId
    'test',         // projectName
    '2025-07-26T14:00:00Z', // timestamp (current time or earlier)
    'pending'       // status
  ).send({
    from: account,
    gas: 200000,
  });

  console.log('Pull request logged. Transaction hash:', tx.transactionHash);
}

// Execute the function
logPullRequest().catch(console.error);