import React, { useState, useEffect } from "react";
import { ethers } from "ethers";
import axios from "axios";

// Import ABI and deployed contract address
import ABI from "../abis/SoftwareRegistry.json";
import deployed from "../contracts/deployed_addresses.json";

// Load environment variables
const GANACHE_RPC_URL = process.env.REACT_APP_GANACHE_RPC_URL || "http://127.0.0.1:8545";
const PRIVATE_KEY = process.env.REACT_APP_PRIVATE_KEY;
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5001";

if (!PRIVATE_KEY) throw new Error("❌ Missing REACT_APP_PRIVATE_KEY in .env file.");

function DeveloperDashboard() {
  const [contract, setContract] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [account, setAccount] = useState("");
  const [commits, setCommits] = useState([]);
  const [status, setStatus] = useState("Loading...");
  const [justStoredIds, setJustStoredIds] = useState([]);
  const [user, setUser] = useState(null);

  // Setup contract and wallet
  useEffect(() => {
    try {
      const provider = new ethers.JsonRpcProvider(GANACHE_RPC_URL);
      const signer = new ethers.Wallet(PRIVATE_KEY, provider);
      const instance = new ethers.Contract(deployed.SoftwareRegistry, ABI, signer);

      setContract(instance);
      setWallet(signer);
      setAccount(signer.address);
    } catch (err) {
      console.error("❌ Contract or wallet setup failed", err);
      setStatus("Failed to connect to the blockchain.");
    }
  }, []);

  // Load user from localStorage
  useEffect(() => {
    try {
      const u = JSON.parse(localStorage.getItem("user"));
      if (u) {
        setUser(u);
      } else {
        setStatus("⚠️ No user info found.");
      }
    } catch (err) {
      console.error("⚠️ Invalid user data in localStorage");
    }
  }, []);

  // Fetch commits from backend
  useEffect(() => {
    if (!user) return;

    const fetchCommits = async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/api/commits`);
        setCommits(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("❌ Failed to fetch commits", err);
      }
    };

    fetchCommits();
    const interval = setInterval(fetchCommits, 30000);
    return () => clearInterval(interval);
  }, [user]);

  // Helper: filter commits belonging to the user
  const userCommits = commits.filter((commit) => {
    const name = user?.githubUsername?.toLowerCase() || user?.username?.toLowerCase();
    const email = user?.email?.toLowerCase();
    const aName = commit.author?.toLowerCase() || "";
    const aEmail = commit.authorEmail?.toLowerCase() || "";
    return aName === name || aEmail.includes(email);
  });

  // Automatically push unstored commits to blockchain
  useEffect(() => {
    if (!contract || !wallet || !account) return;

    const pushCommit = async (commit) => {
      try {
        const { projectName, commitHash, message, author, timestamp, filesChanged, id } = commit;

        const payload = JSON.stringify({
          message: message || "",
          author: author || "",
          timestamp: timestamp || Date.now(),
          filesChanged: Array.isArray(filesChanged) ? filesChanged : [],
        });

        const tx = await contract.storeCommit(projectName, ethers.id(commitHash), payload, account);
        setStatus("📤 Transaction sent... waiting");
        const receipt = await tx.wait();

        await axios.patch(`${API_BASE_URL}/api/commits/${id}/mark-onchain`, {
          txHash: receipt.transactionHash,
        });

        setCommits((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, isOnBlockchain: true, blockchainTxHash: receipt.transactionHash } : c
          )
        );

        setJustStoredIds((prev) => [...prev, id]);
        setTimeout(() => {
          setJustStoredIds((prev) => prev.filter((x) => x !== id));
        }, 5000);
      } catch (err) {
        console.error("❌ Blockchain transaction error", err);
        setStatus("❌ Transaction failed");
      }
    };

    (async () => {
      for (const c of userCommits) {
        if (!c.isOnBlockchain && c.projectName) {
          await pushCommit(c);
        }
      }
    })();
  }, [contract, wallet, account, userCommits]);

  const fmt = (t) => new Date(t).toLocaleString();

  return (
    <div className="min-h-screen bg-gray-100 p-6 font-sans">
      <header className="bg-white shadow p-4 rounded mb-6 flex justify-between">
        <div>
          <h1 className="text-2xl font-bold">Developer Dashboard</h1>
          <p className="text-gray-600">Logged in as: {user?.username || "..."}</p>
        </div>
        <button
          onClick={() => {
            localStorage.clear();
            window.location.href = "/login";
          }}
          className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
        >
          Logout
        </button>
      </header>

      <main className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-4">Your Commits</h2>
        {userCommits.map((c) => (
          <div
            key={c.id}
            className="border p-4 rounded mb-4 bg-gray-50 hover:shadow transition"
          >
            <div className="flex justify-between mb-2">
              <strong>{c.message}</strong>
              {c.isOnBlockchain ? (
                <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded">
                  On Chain
                </span>
              ) : (
                <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-1 rounded">
                  Pending…
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700">
              {c.projectName} • {c.commitHash} • {fmt(c.timestamp)}
            </p>
            {c.blockchainTxHash && (
              <p className="text-xs text-gray-600 break-all mt-1">
                TX: {c.blockchainTxHash}
              </p>
            )}
            {justStoredIds.includes(c.id) && (
              <p className="text-green-700 text-xs mt-2">
                ✅ Successfully stored on blockchain!
              </p>
            )}
            <div className="mt-2 bg-white rounded p-2">
              <h4 className="font-semibold text-sm mb-1">Files Changed</h4>
              {Array.isArray(c.filesChanged) ? (
                c.filesChanged.map((f, i) => (
                  <div key={i} className="text-xs text-gray-800">
                    {f.filename} +{f.additions} -{f.deletions}
                  </div>
                ))
              ) : (
                <p className="text-xs text-gray-500">No file data</p>
              )}
            </div>
          </div>
        ))}

        {userCommits.length === 0 && (
          <p className="text-gray-500 text-center py-8">No commits found.</p>
        )}
        <p className="mt-6 text-sm">{status}</p>
      </main>
    </div>
  );
}

export default DeveloperDashboard;