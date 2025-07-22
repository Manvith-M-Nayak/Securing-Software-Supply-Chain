from flask import Blueprint, request, jsonify
from config.db import connect_db
from config.web3 import get_web3, get_contract
from models.commit_model import commit_exists, save_commit_to_db
from eth_account import Account  # For signing transactions (required in web3.py v6+)
import os

# ------------------- Blueprint Setup -------------------
webhook_bp = Blueprint("webhook", __name__)
db = connect_db()

# Initialize Web3 connection
w3 = get_web3()

# Get the deployed smart contract
contract = get_contract(w3)

# Load environment-based credentials
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
DEPLOYER_ADDRESS = w3.to_checksum_address(os.environ.get("DEPLOYER_ADDRESS"))

# ------------------- Webhook Endpoint -------------------
@webhook_bp.route("/webhook", methods=["POST"])
def receive_commit():
    data = request.get_json()

    # Extract values from JSON payload
    commit_hash = data.get("commitHash")
    component_name = data.get("componentName")
    version = data.get("version")
    developer = data.get("developer")
    timestamp = data.get("timestamp")

    # Basic input validation
    if not all([commit_hash, component_name, version, developer, timestamp]):
        return jsonify({"error": "Missing fields"}), 400

    # Check if commit already exists in MongoDB
    if commit_exists(db, commit_hash):
        return jsonify({"message": "Commit already exists"}), 200

    # Save commit to MongoDB
    commit_data = {
        "commitHash": commit_hash,
        "componentName": component_name,
        "version": version,
        "developer": developer,
        "timestamp": timestamp
    }
    save_commit_to_db(db, commit_data)

    # Store commit to the blockchain
    try:
        # Get the current nonce for the sender
        nonce = w3.eth.get_transaction_count(DEPLOYER_ADDRESS)

        # Build the transaction for the smart contract method `storeCommit`
        tx = contract.functions.storeCommit(
            component_name,
            version,
            commit_hash,
            developer
        ).build_transaction({
            'from': DEPLOYER_ADDRESS,
            'nonce': nonce,
            'gas': 3000000,
            'gasPrice': w3.to_wei('10', 'gwei')  # gasPrice must be set for Ganache or real networks
        })

        # Sign the transaction with the private key
        signed_tx = Account.sign_transaction(tx, private_key=PRIVATE_KEY)

        # Broadcast the transaction to the blockchain
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        # Wait for the transaction to be mined
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return jsonify({
            "message": "Commit stored successfully",
            "txHash": tx_hash.hex()
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
