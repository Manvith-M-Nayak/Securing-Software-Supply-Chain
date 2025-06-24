// frontend/src/pages/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import Web3 from 'web3';

// ABI and deployed address import
import SoftwareRegistryABI from '../abis/SoftwareRegistry.json';
import contractAddresses from '../contracts/addresses.json';

// ⚠️ NEVER expose private keys in production. For local Ganache only!
const PRIVATE_KEY = process.env.REACT_APP_PRIVATE_KEY;

// Ensure the .env file contains:
// REACT_APP_GANACHE_RPC_URL=http://127.0.0.1:8545
const GANACHE_RPC_URL = process.env.REACT_APP_GANACHE_RPC_URL;

// Retrieve contract address from addresses.json
const CONTRACT_ADDRESS = contractAddresses.SoftwareRegistry;

function Dashboard({ user }) {
  const [form, setForm] = useState({
    name: '',
    version: '',
    hash: '',
    commitHash: ''
  });

  const [status, setStatus] = useState('');
  const [contract, setContract] = useState(null);
  const [walletAddress, setWalletAddress] = useState('');

  // Initialize contract instance
  useEffect(() => {
    if (!GANACHE_RPC_URL) {
      console.error('❌ GANACHE_RPC_URL not found in environment variables');
      setStatus('Environment config missing. Check .env file.');
      return;
    }

    if (!CONTRACT_ADDRESS) {
      console.error('❌ CONTRACT_ADDRESS not found in addresses.json');
      setStatus('Smart contract address not configured.');
      return;
    }

    try {
      const provider = new ethers.JsonRpcProvider(GANACHE_RPC_URL);
      const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
      setWalletAddress(wallet.address);
      const contractInstance = new ethers.Contract(CONTRACT_ADDRESS, SoftwareRegistryABI, wallet);
      setContract(contractInstance);
    } catch (err) {
      console.error('❌ Failed to initialize contract:', err);
      setStatus('Contract setup failed.');
    }
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const verifyWithML = async () => {
    // Simulated ML verification
    await new Promise(resolve => setTimeout(resolve, 1000));
    return true;
  };

  const submitComponent = async () => {
    if (!contract) {
      setStatus('Smart contract not ready.');
      return;
    }

    const { name, version, hash, commitHash } = form;

    // Basic input validation
    if (!name || !version || !hash || !commitHash) {
      setStatus('❌ All fields are required.');
      return;
    }

    const verified = await verifyWithML();
    if (!verified) {
      setStatus('❌ ML verification failed.');
      return;
    }

    try {
      setStatus('⏳ Preparing blockchain transaction...');

      // Log all values for debug
      console.log("Form data:", { name, version, hash, commitHash });
      console.log("Contract Address:", CONTRACT_ADDRESS);
      console.log("Wallet Address:", walletAddress);

      // Call registerComponent
      const tx = await contract.registerComponent(name, version, hash, commitHash);
      setStatus('📤 Transaction submitted. Waiting for confirmation...');
      await tx.wait();
      const web3 = new Web3(process.env.REACT_APP_GANACHE_RPC_URL); // Ganache RPC
      const txHash = '0x6be82a6765e2cdac41a710df03152c912b7e4c685d5ddf268e4d5fb7d5116ef1';
      // Get transaction details
      const tx1 = await web3.eth.getTransaction(txHash);
      console.log('Input data:', tx1.input);
      setStatus('✅ Component successfully registered on blockchain.');
    } catch (error) {
      console.error('❌ Blockchain transaction error:', error);

      // Extract ethers error message if available
      if (error?.code === 'CALL_EXCEPTION') {
        setStatus('❌ Call reverted. Are you authorized as a Developer?');
      } else if (error?.code === 'UNSUPPORTED_OPERATION') {
        setStatus('❌ Check your RPC URL or contract setup.');
      } else {
        setStatus('❌ Blockchain transaction failed.');
      }
    }
  };

  return (
    <div style={{ padding: '1rem', fontFamily: 'Arial' }}>
      <h2>Welcome, {user?.username || 'Developer'}</h2>
      <h3>Register a Software Component</h3>

      <input
        name="name"
        placeholder="Component Name"
        value={form.name}
        onChange={handleChange}
        style={{ display: 'block', margin: '8px 0', width: '300px' }}
      />
      <input
        name="version"
        placeholder="Version"
        value={form.version}
        onChange={handleChange}
        style={{ display: 'block', margin: '8px 0', width: '300px' }}
      />
      <input
        name="hash"
        placeholder="Hash (IPFS or SHA256)"
        value={form.hash}
        onChange={handleChange}
        style={{ display: 'block', margin: '8px 0', width: '300px' }}
      />
      <input
        name="commitHash"
        placeholder="Commit Hash"
        value={form.commitHash}
        onChange={handleChange}
        style={{ display: 'block', margin: '8px 0', width: '300px' }}
      />

      <button onClick={submitComponent} style={{ padding: '0.5rem 1rem', marginTop: '12px' }}>
        Submit to Blockchain
      </button>

      <p style={{ marginTop: '16px', color: status.includes('❌') ? 'red' : 'green' }}>
        {status}
      </p>
    </div>
  );
}

export default Dashboard;
