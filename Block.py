class Block:
    def __init__(self, index, hash, prevBlockHash, rootHash, nonce, timestamp):
        # block's current index
        self.index = index
        # block's hash
        self.hash = hash
        # previous block's hash
        self.prevBlockHash = prevBlockHash
        # block's merkle root hash
        self.rootHash = rootHash
        # block's nonce
        self.nonce = nonce
        # block's timestamp
        self.timestamp = timestamp

        # block's saved transactions
        self.transactionList = []

    def setTransactions(self, transactionList):
        self.transactionList = transactionList

    def genBlockString(self):
        return str(self.index) + self.timestamp + self.prevBlockHash + self.rootHash + str(self.nonce)
