import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

### Buiding a blockchain

class Blockchain:

    #initializes blockchain and appends genesis block to chain
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(proof=1, previous_hash='0')
        self.nodes = set()


    #creates a block and appends it to the chain
    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain)+1, 
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions
                 }

        self.transactions = []
        self.chain.append(block)
        return block


    #returns last block on the chain
    def get_last_block(self):
        return self.chain[-1]


    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1

        return new_proof


    #returns hash of a block
    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()


    #returns bool value of chain validity
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False

            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False

            previous_block = block
            block_index += 1

        return True

    #add transaction to block
    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender':sender,
                                  'receiver':receiver,
                                  'amount':amount
                                  })

        previous_block = self.get_last_block()
        return previous_block['index'] + 1

    #adds node to blockchain
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)


    #replaces chain in node for biggest chain in blockchain
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)

        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain

        if longest_chain:
            self.chain = longest_chain
            return True

        return False



### Flask web app for rest requests
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False


# Creating blockchain instance
blockchain = Blockchain()

# Creating an address for the node on port 5003
node_address = str(uuid4()).replace('-','')

### Mining a new block

@app.route('/mine_block', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_last_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transaction(node_address, 'miner', 1)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message':'You mined a block', 
                'index':block['index'],
                'timestamp':block['timestamp'],
                'proof':block['proof'],
                'previous_hash':block['previous_hash'],
                'transactions':block['transactions']
                }
    return jsonify(response), 200

# GET for entire blockchain
@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain':blockchain.chain,
                'length':len(blockchain.chain)
                }
    return jsonify(response), 200

# Check if blockchain is valid
@app.route('/is_valid', methods=['GET'])
def is_valid():
    is_val = blockchain.is_chain_valid(blockchain.chain)
    if is_val:
        response = {'message': 'Blockchain is valid'}
    else:
        response = {'message': 'Blockchain is not valid'}
    return jsonify(response), 200


# Adding new transaction to blockchain
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    jsonf = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all (key in jsonf for key in transaction_keys):
        return 'Some elements of transaction are missing', 400

    index = blockchain.add_transaction(jsonf['sender'], jsonf['receiver'], jsonf['amount'])
    response = {'message':f'Transaction will be added to block {index}'}
    return jsonify(response), 201


### Decentralizing the blockchain

# Connecting new nodes
@app.route('/connect_node', methods=['POST'])
def connect_node():
    jsonf = request.get_json()
    nodes = jsonf.get('nodes')
    if nodes is None:
        return "No nodes found", 400
    
    for node in nodes:
        blockchain.add_node(node)

    response = {'message':'All the nodes are now connected. Blockchain contains the following nodes:',
                'total_nodes': list(blockchain.nodes)
                }
    return jsonify(response), 201


# Replacing chain by longest chain if needed
@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message':'Chain was replaced by longest one.',
                    'new_chain':blockchain.chain
                    }
    else:
        response = {'message':'Chain does not need to be replaced.',
                    'actual_chain':blockchain.chain
                    }

    return jsonify(response), 200



app.run(host='0.0.0.0',port=5003)