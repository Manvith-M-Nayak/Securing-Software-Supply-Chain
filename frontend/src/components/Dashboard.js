// src/pages/Dashboard.jsx
import React, { useState } from 'react';
import { ethers } from 'ethers';
import SoftwareRegistryABI from '../abis/SoftwareRegistry.json';

const PRIVATE_KEY = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'; // Copy from Ganache's GUI
const CONTRACT_ADDRESS = 'YOUR_CONTRACT_ADDRESS'; // Deployed contract address

function Dashboard({ user }) {
  const [form, setForm] = useState({
    name: '',
    version: '',
    hash: '',
    commitHash: ''
  });

  const [status, setStatus] = useState('');

  const verifyWithML = async () => {
    await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
    return true; // Accept all for now
  };

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const submitComponent = async () => {
    const verified = await verifyWithML();
    if (!verified) {
      setStatus('Verification failed.');
      return;
    }

    try {
      setStatus('Preparing blockchain submission...');

      const provider = new ethers.JsonRpcProvider(GANACHE_RPC_URL);
      const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

      const contract = new ethers.Contract(CONTRACT_ADDRESS, SoftwareRegistryABI, wallet);

      const tx = await contract.registerComponent(
        form.name,
        form.version,
        form.hash,
        form.commitHash
      );

      setStatus('Transaction submitted. Waiting...');
      await tx.wait();
      setStatus('Component successfully added to blockchain.');

    } catch (err) {
      console.error(err);
      setStatus('Blockchain transaction failed.');
    }
  };

  return (
    <div>
      <h2>Welcome {user.username}</h2>
      <h3>Register a Software Component</h3>
      <input name="name" placeholder="Component Name" value={form.name} onChange={handleChange} />
      <input name="version" placeholder="Version" value={form.version} onChange={handleChange} />
      <input name="hash" placeholder="Hash (IPFS / file)" value={form.hash} onChange={handleChange} />
      <input name="commitHash" placeholder="Commit Hash" value={form.commitHash} onChange={handleChange} />
      <button onClick={submitComponent}>Submit to Blockchain</button>
      <p>{status}</p>
    </div>
  );
}

export default Dashboard;
