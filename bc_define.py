import hashlib
from datetime import datetime

from ecdsa import VerifyingKey

from TxOut import TxOut
from Transaction import Transaction
from Block import Block
from TxIn import TxIn
from UTXOs import UTXOs

import MerkleTree

# blockchain pre define info
diffInterval = 2


# blockchain class is a list to append the block one by one.
class Blockchain:
    def __init__(self):
        self.blocks = []
        self.target_hash = 0

        # when a new blockchain class was created, the genesis block will be created as first block
        genesis_block = genGenesisBlock()
        self.blocks.append(genesis_block)


def NewBlockchain():
    new_blockchain = Blockchain()
    return new_blockchain


def genGenesisBlock():
    # gen genesis block tx out
    genesisTxOutList = []
    genesisTxOutList.append(TxOut("", 1000))
    genesisTxInList = []

    # gen genesis  tx list
    genesisTXList = []
    genesisTX = Transaction(genesisTxInList, genesisTxOutList)
    genesisTX.TxId = "00000000"
    genesisTXList.append(genesisTX)

    # gen genesis block
    genesisBlock = Block(0, 'bf8ffdf71974a51a0862e6d618650bc0', 'bf8ffdf71974a51a0862e6d618650bc0',
                         'bf8ffdf71974a51a0862e6d618650bc0', 123, '123456')
    genesisBlock.setTransactions(genesisTXList)

    # add genesis block to blockchain
    return genesisBlock


def setCoinBaseTx(address):
    # initiate coinbase tx
    coinbaseTxInList = []
    coinbaseTxOutList = []
    coinbaseTxOutList.append(TxOut(address, 50))

    coinbaseTx = Transaction(coinbaseTxInList, coinbaseTxOutList)

    # add coinbase tx to tx list
    return coinbaseTx


def genNewBlock(blocks, tx_list, index, previousHash, nonce):
    # initiate block parameters
    # nonce = 0
    timestamp = getTimestamp()

    # start solving puzzle
    # check whether the miner has synchronized the blockchain
    if index < len(blocks):
        return None

    # gen transactions' merkle root (rootHash)
    rootHash = genRootHash(tx_list)

    # calculate block hash value
    hashValue = calculateHash(index, timestamp, previousHash, rootHash, nonce)
    hash_code = "New block's hash is" + str(hashValue)

    return hash_code, Block(index, hashValue, previousHash, rootHash, nonce, timestamp)


def calculateHash(index, timestamp, previousHash, rootHash, nonce):
    rawString = str(index) + str(timestamp) + str(previousHash) + str(rootHash) + str(nonce)

    # print("raw string",rawString)
    # apply sha256 twice
    hash = hashlib.sha256(rawString.encode("utf-8")).hexdigest()
    hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
    # print('hash result:',hash_result)
    return hash_result


def genRootHash(tx_list):
    txStringList = []
    for tx in tx_list:
        txStringList.append(tx.genTxString())

    return MerkleTree.genMerkleRoot(txStringList)


def getTimestamp():
    timestamp = datetime.now().timestamp()
    date_time = datetime.fromtimestamp(timestamp)
    # print(t)
    str_date_time = date_time.strftime("%Y%m%d%H%M%S")
    return str_date_time


def genUTXOs(blocks):
    print(blocks)

    txOutDict = {}
    txInList = []
    for block in blocks:

        for tx in block.transactionList:

            txInofTx = tx.TxInList
            txOutofTx = tx.TxOutList

            # get all txIn
            for i in range(len(txInofTx)):
                txInList.append(txInofTx[i].TxOutId + "[" + str(txInofTx[i].TxOutIndex) + "]")

            # get all txOut
            for i in range(len(txOutofTx)):
                key = str(tx.TxId + "[" + str(i) + "]")
                txOutDict[key] = txOutofTx[i]

    # remove the txOut that appears in txIn
    for usedTxIn in txInList:
        if usedTxIn in txOutDict.keys():
            txOutDict.pop(usedTxIn)

    return UTXOs(txOutDict)


def isValidBlock(blockchain, block):
    prevBlock = blockchain[-1]
    if prevBlock.index != block.index - 1:
        return False

    if prevBlock.hash != block.prevBlockHash:
        return False

    hash = hashlib.sha256(block.genBlockString().encode("utf-8")).hexdigest()
    hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
    if block.hash != hash_result:
        return False

    genUTXOs(blockchain)

    return True


def saveBlocktoDB(mycol, block):
    b_dict = block2Dict(block)
    mydict = {"_id": block.index, "block info": b_dict}

    x = mycol.insert_one(mydict)


def getBlockchainFromDB(mycol, blockchain):
    # db_blockchain = []
    for x in mycol.find():
        db_block = dict2Block(x['block info'])
        # db_blockchain.append(db_block)
        blockchain.append(db_block)

    # return db_blockchain


def getBlockFromDB(mycol, blockIndex):
    myquery = {"_id": blockIndex}

    mydoc = mycol.find(myquery)
    block = None

    for x in mydoc:
        block = dict2Block(x['block info'])

    return block


def msg2txList(msgtxList):
    txList = []

    for msgtx in msgtxList:
        txInList = []
        txOutList = []

        for msgTxIn in msgtx.TxInList:
            txIn = TxIn(msgTxIn.TxOutId, msgTxIn.TxOutIndex, msgTxIn.signature)
            txInList.append(txIn)

        for msgTxOut in msgtx.TxOutList:
            addr = VerifyingKey.from_pem(msgTxOut.address.encode())
            txOut = TxOut(addr, msgTxOut.amount)
            txOutList.append(txOut)

        tx = Transaction(txInList, txOutList)
        # print("old", tx.TxId)
        tx.setTxID(msgtx.TxId)
        # print("new set tx id", tx.TxId)
        # print()
        txList.append(tx)

    return txList


def block2Dict(block):
    b_dict = {}
    b_dict['index'] = block.index
    b_dict['hash'] = block.hash
    b_dict['prevBlockHash'] = block.prevBlockHash
    b_dict['rootHash'] = block.rootHash
    b_dict['nonce'] = block.nonce
    b_dict['timestamp'] = block.timestamp

    txList2dict = []
    for tx in block.transactionList:
        txList2dict.append(tx2dict(tx))

    b_dict['transactionList'] = txList2dict

    return b_dict


def tx2dict(tx):
    tx_dict = {}
    tx_dict['TxId'] = tx.TxId
    txIn_list = []
    txOut_list = []
    for txIn in tx.TxInList:
        txIn_list.append(txIn2Dict(txIn))

    for txOut in tx.TxOutList:
        txOut_list.append(txOut2Dict(txOut))

    tx_dict['TxInList'] = txIn_list
    tx_dict['TxOutList'] = txOut_list

    return tx_dict


def txIn2Dict(txIn):
    txIn_dict = {'TxOutId': txIn.TxOutId, 'TxOutIndex': txIn.TxOutIndex, 'signature': txIn.signature}
    return txIn_dict


def txOut2Dict(txOut):
    if not isinstance(txOut.address, str):
        addr = txOut.address.to_pem().decode()
    else:
        addr = txOut.address
    txOut_dict = {'address': addr, 'amount': txOut.amount}
    return txOut_dict


def dict2Block(b_dict):
    index = b_dict['index']
    hash = b_dict['hash']
    prevBlockHash = b_dict['prevBlockHash']
    rootHash = b_dict['rootHash']
    nonce = b_dict['nonce']
    timestamp = b_dict['timestamp']

    block = Block(index, hash, prevBlockHash, rootHash, nonce, timestamp)
    txList = []
    for tx_dict in b_dict['transactionList']:
        txList.append(dict2Tx(tx_dict))

    block.setTransactions(txList)

    return block


def dict2Tx(tx_dict):
    TxId = tx_dict['TxId']
    TxInList = tx_dict['TxInList']
    TxOutList = tx_dict['TxOutList']

    tx = Transaction(dict2TxIn(TxInList), dict2TxOut(TxOutList))
    tx.setTxID(TxId)

    return tx


def dict2TxIn(txInList_dict):
    TxInList = []

    for txIn in txInList_dict:
        TxOutId = txIn['TxOutId']
        TxOutIndex = txIn['TxOutIndex']
        signature = txIn['signature']

        newtxIn = TxIn(TxOutId, TxOutIndex, signature)
        TxInList.append(newtxIn)
    return TxInList


def dict2TxOut(txOutList_dict):
    TxOutList = []

    for txOut in txOutList_dict:
        address = str(txOut['address'])
        # print("new addr",type(address))
        # print(address.encode())
        vk = VerifyingKey.from_pem(address.encode())
        # print("addr", vk)

        amount = txOut['amount']

        newtxOut = TxOut(vk, amount)
        TxOutList.append(newtxOut)
    return TxOutList
