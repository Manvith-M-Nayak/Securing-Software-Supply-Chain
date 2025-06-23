from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-secret')
jwt = JWTManager(app)

web3 = Web3(Web3.HTTPProvider('http://172.29.240.1:8545'))

with open('../blockchain/deployed_addresses.json') as f:
    data = json.load(f)

with open('../blockchain/build/contracts/GamificationEngine.json') as f:
    abi = json.load(f)['abi']

contract = web3.eth.contract(address=Web3.to_checksum_address(data['GamificationEngine']), abi=abi)
default_account = web3.eth.accounts[0]

users = {'alice': 'password123'}

@app.route('/login', methods=['POST'])
def login():
    req = request.json
    print("Received login request:", req)  # Debug log

    username = req.get('username')
    password = req.get('password')

    if users.get(username) == password:
        print("Login successful")  # Debug log
        token = create_access_token(identity=username)
        return jsonify(token=token)

    print("Login failed")  # Debug log
    return jsonify(msg='Invalid'), 401


@app.route('/get-score', methods=['GET'])
@jwt_required()
def get_score():
    score = contract.functions.getScore().call()
    return jsonify(score=score)

@app.route('/increment-score', methods=['POST'])
@jwt_required()
def increment_score():
    tx = contract.functions.incrementScore().transact({'from': default_account})
    web3.eth.wait_for_transaction_receipt(tx)
    return jsonify(msg='Score increased')

if __name__ == '__main__':
    app.run(debug=True)