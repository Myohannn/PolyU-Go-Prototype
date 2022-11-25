import time
from concurrent import futures
import logging
import grpc
import grpc_utils.blockchain_pb2 as blockchain_pb2
import grpc_utils.blockchain_pb2_grpc as blockchain_pb2_grpc
from bc_define import *
from ECDSA import *
import pymongo


# We implement the function at server class
class BlockchainServer(blockchain_pb2_grpc.BlockChainServicer):
    # When the server created, a new blockchain will be created too
    def __init__(self):
        self.blockchain = NewBlockchain()
        self.localTxList = []
        self.clientIndex = '-1'

        self.publicKey = ''
        self.privatekey = ''
        self.publicKey_list = []

        myClient = pymongo.MongoClient("mongodb://localhost:27017/")
        self.mydb = myClient["BlockchainDB"]
        self.col = None

        self.map = []

    def initTxList(self, request, context):
        self.localTxList = []
        coinbaseTx = setCoinBaseTx(self.publicKey)
        self.localTxList.append(coinbaseTx)
        response = blockchain_pb2.InitTxListResponse(message="Tx list init")
        return response

    def receiveBlock(self, request, context):
        print(request.message)
        msgBlock = request.newBlock
        block = Block(msgBlock.index, msgBlock.hash, msgBlock.prevBlockHash, msgBlock.rootHash,
                      msgBlock.nonce, msgBlock.timestamp)
        msgTxList = msgBlock.transactionList
        block.setTransactions(msg2txList(msgTxList))
        # print("received block txlist", msgTxList)
        # block = NewBlock(request.newBlock.transaction, request.newBlock.prevBlockHash)
        if isValidBlock(self.blockchain.blocks, block) or len(self.blockchain.blocks) == 1:
            print("Valid block")
            # print("valid block's tx list", block.transactionList)
            self.blockchain.blocks.append(block)
            saveBlocktoDB(self.col, block)

            self.map = initMap(self.blockchain.blocks)
            print("Update map:", self.map)

            print("Blockchain updated: ")
            for i in range(len(self.blockchain.blocks)):
                print("block " + str(i) + ":")
                print('block hash = ' + self.blockchain.blocks[i].hash)
                # print('block transaction = ' + self.blockchain.blocks[i].transactionList)
            print()

            response = blockchain_pb2.ReceiveBlockResponse(message="OK")

        else:
            response = blockchain_pb2.ReceiveBlockResponse(message="Invalid Block!!!")

        return response

    def receiveMessage(self, request, context):
        req = request.message
        # print("server MSG: ", req)
        if req == "Highest Index" or req == "Local index":
            response = blockchain_pb2.receiveMessageResponse(message=str(len(self.blockchain.blocks)))
            return response
        if req.startswith("Get Block"):
            block_idx = int(req.split(":")[-1])
            print("some one is getting block", block_idx)

            block = self.blockchain.blocks[block_idx]

            pb2_block = blockchain_pb2.Block(index=block.index, hash=block.hash, prevBlockHash=block.prevBlockHash,
                                             rootHash=block.rootHash, nonce=block.nonce,
                                             timestamp=block.timestamp,
                                             transactionList=txList2msg(block.transactionList))
            # print("needed block:", pb2_block)
            msg = f"Here is block {block_idx}"
            response = blockchain_pb2.receiveMessageResponse(message=msg, newBlock=pb2_block)
            return response
        if req.startswith("Gen Block"):
            target = int(req.split(":")[-1])
            print(f"{self.clientIndex} found a new target at", target)
            current_blockIndex = len(self.blockchain.blocks)
            previousBlockHash = self.blockchain.blocks[current_blockIndex - 1].hash
            hash_code, block = genNewBlock(self.blockchain.blocks, self.localTxList, current_blockIndex,
                                           previousBlockHash,
                                           target)
            block.setTransactions(self.localTxList)
            self.blockchain.blocks.append(block)
            saveBlocktoDB(self.col, block)
            print(f"Block {block.index} saved in to storage!")
            # time.sleep(5)

            self.map = initMap(self.blockchain.blocks)
            print("Update map:", self.map)

            print("Blockchain updated: ")
            for i in range(len(self.blockchain.blocks)):
                print("block " + str(i) + ":")
                print('block hash = ' + self.blockchain.blocks[i].hash)
            print()

            pb2_block = blockchain_pb2.Block(index=block.index, hash=block.hash, prevBlockHash=block.prevBlockHash,
                                             rootHash=block.rootHash, nonce=block.nonce,
                                             timestamp=block.timestamp,
                                             transactionList=txList2msg(block.transactionList))

            addr = self.publicKey.to_pem().decode()
            hash = hashlib.sha256((addr).encode("utf-8")).hexdigest()
            hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()

            response = blockchain_pb2.receiveMessageResponse(message=hash_result, newBlock=pb2_block)
            return response

        if req.startswith("Update map"):
            pKey = req.split(":")[-1]
            target = int(req.split(":")[-2])
            self.map[int(target)] = pKey
            print("Update map:", self.map)
            response = blockchain_pb2.receiveMessageResponse(message="ok")
            return response

        if req.startswith("Refresh map"):
            self.map = updateMap(self.map, 10)
            response = blockchain_pb2.receiveMessageResponse(map=self.map)
            return response

        if req.startswith("New map"):
            newMap = request.map
            self.map = newMap
            print("New map:", self.map)
            response = blockchain_pb2.receiveMessageResponse(message="ok")
            return response

        if req.startswith("Guess"):
            guess = int(req.split(":")[-1])
            if self.map[guess] == "1":
                addr = self.publicKey.to_pem().decode()
                hash = hashlib.sha256((addr).encode("utf-8")).hexdigest()
                hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
                self.map[guess] = hash_result
                print("Update map:", self.map)

                result = "True"
            else:
                result = "False"
            print("guess result:", result)
            response = blockchain_pb2.receiveMessageResponse(message=result)
            return response

    # check channel aliveness
    def getState(self, request, context):
        if self.clientIndex == '-1':
            self.clientIndex = request.message
            sk, vk = loadKey(self.clientIndex)
            self.privatekey = sk
            self.publicKey = vk
            # get public key pair list
            for i in range(4):
                self.publicKey_list.append(loadKey(i))
            col_name = f'miner{self.clientIndex}'
            self.col = self.mydb[col_name]

            # initiate map
            length = 100
            self.map = ["1", "1", "1", "1", "1"]
            for i in range(length - 5):
                self.map.append("0")

        message = f'Miner {self.clientIndex} alive!'
        response = blockchain_pb2.getStateResponse(message=message)
        return response

    def getUTXOs(self, request, context):
        utxos = genUTXOs(self.blockchain.blocks).utxos
        print("UTXOS:::::", utxos)
        msgUTXOs = UTXOs2msg(utxos)
        response = blockchain_pb2.getUTXOsResponse(utxos=msgUTXOs)
        return response

    def QueryDB(self, request, context):
        print("Query DB request:", request.message)
        db_blockchain = getBlockchainFromDB(self.col, self.blockchain.blocks)

        print("Blockchain from DB: ")
        for i in range(len(self.blockchain.blocks)):
            print("block " + str(i) + ":")
            print('block hash = ' + self.blockchain.blocks[i].hash)
        print()

        return blockchain_pb2.QueryDBResponse(message='Blockchain reading complete!')


def initMap(blocks):
    # initiate map
    length = 100
    map = ["1", "1", "1", "1", "1"]
    for i in range(length - 5):
        map.append("0")

    target_list = []
    addr_list = []

    for b in range(1, len(blocks)):
        target_list.append(blocks[b].nonce)

        coinTX = blocks[b].transactionList[0]
        addr = coinTX.TxOutList[0].address
        hash = hashlib.sha256((addr.to_pem().decode()).encode("utf-8")).hexdigest()
        hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
        addr_list.append(hash_result)

    print("target_list:", target_list)
    print("addr_list:", addr_list)
    for i in range(len(target_list)):
        map[int(target_list[i])] = addr_list[i]

    return map


# server setting
def serve(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    blockchain_pb2_grpc.add_BlockChainServicer_to_server(BlockchainServer(), server)
    server.add_insecure_port('127.0.0.1:' + port)
    server.start()
    print("blockchain-demo started, listening on " + port)
    server.wait_for_termination()


def txList2msg(tx_list):
    msgTxList = []
    # msgTxList = ''
    for tx in tx_list:
        msgTxInList = []
        msgTxOutList = []

        for txIn in tx.TxInList:
            msgTxIn = blockchain_pb2.TxIn(TxOut=txIn.TxOutId, TxOutIndex=txIn.TxOutIndex, signature=txIn.signature)
            msgTxInList.append(msgTxIn)

        for txOut in tx.TxOutList:
            # TODO
            if not isinstance(txOut.address, str):
                addr = txOut.address.to_pem().decode()
                # print(addr)
            else:
                addr = txOut.address
            msgTxOut = blockchain_pb2.TxOut(address=addr, amount=txOut.amount)
            msgTxOutList.append(msgTxOut)

        msgTx = blockchain_pb2.Transaction(TxId=tx.TxId, TxInList=msgTxInList, TxOutList=msgTxOutList)
        msgTxList.append(msgTx)

    return msgTxList


def UTXOs2msg(UTXOs):
    msgkey_list = []
    msgOwner_list = []
    msgAmount_list = []
    for k, v in UTXOs.items():
        msgkey_list.append(k)

        msgAmount_list.append(v.amount)

        if not isinstance(v.address, str):
            addr = v.address.to_pem().decode()
            # print(addr)
        else:
            addr = v.address
        hash = hashlib.sha256((addr).encode("utf-8")).hexdigest()
        hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
        msgOwner_list.append(hash_result)

    msgUTXOs = blockchain_pb2.UTXOs(key=msgkey_list, amount=msgAmount_list, owner=msgOwner_list)

    return msgUTXOs


def updateMap(map, numOfTarget):
    # delete previous block
    for i in range(5, 99):
        if map[i] == '1':
            map[i] = '0'
    import random

    # generate target list and update map
    targetIndexList = []

    for i in range(numOfTarget):
        idx = random.randint(0, 99)
        # check whether the position has been mined
        while map[idx] != '0':
            idx = random.randint(0, 99)
        targetIndexList.append(idx)

    for target in targetIndexList:
        map[target] = '1'

    print("New Map:", map)
    return map


# run the server
if __name__ == '__main__':
    logging.basicConfig()
    port = "50051"
    serve(port)
