from __future__ import print_function

import logging
import grpc

import grpc_utils.blockchain_pb2 as blockchain_pb2
import grpc_utils.blockchain_pb2_grpc as blockchain_pb2_grpc


class bc_Miner:
    def __init__(self, minerIndex):

        self.port_list = []
        self.miner_index = minerIndex
        self.localport = ''
        self.latestBlockIndex = 1
        self.localBlockIndex = 0

        # self.initMiner()

    def run(self):
        self.initMiner()
        self.QueryDB()

        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        resposne = self.sendMessage(local_channel, 'Local index')
        self.localBlockIndex = int(resposne.message)
        self.latestBlockIndex = self.localBlockIndex

    def initMiner(self):
        f = open("portList.txt")
        line = f.readline()
        while line:
            self.port_list.append(line.replace('\n', ''))
            line = f.readline()
        f.close()

        # get key pair

        # update server side miner_index
        local_port = self.port_list[self.miner_index]
        local_channel = grpc.insecure_channel('localhost:' + local_port)
        stub = blockchain_pb2_grpc.BlockChainStub(local_channel)
        response = stub.getState(blockchain_pb2.getStateRequest(message=self.miner_index))
        print(response)

        self.localport = self.port_list[self.miner_index]

        initTX = stub.initTxList(blockchain_pb2.InitTxListRequest(message="init transaction"))

        # self.mining()

    def QueryDB(self):
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        stub = blockchain_pb2_grpc.BlockChainStub(local_channel)
        response = stub.QueryDB(blockchain_pb2.QueryDBRequest(message='Read blockchain from DB'))
        print("Query DB result:", response)

    def getLatestBlockIdx(self):
        index_list = self.broadcastMsg("Highest Index")

        # print("Live miner's latest block index", index_list)
        for idx in index_list:
            if int(idx.message) <= self.latestBlockIndex:
                # self.latestBlockIndex = self.localBlockIndex
                continue
            else:
                self.latestBlockIndex = int(idx.message)
                print("The highest index is:", idx.message)

    def broadcastMsg(self, message):
        channel_list = self.getAliveChannel(self.port_list)
        response_list = []

        for c in channel_list:
            try:
                response = self.sendMessage(c, message)
                response_list.append(response)
            except Exception as e:
                print("broadcastMsg err", e)
        return response_list

    def checkResult(self, guess):
        msg = f"Guess:{guess}"

        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        response = self.sendMessage(local_channel, msg)

        if response.message == "True":
            return self.mineABlock(guess)
        else:
            return f"Failed to find a block at position[{guess}]..."

    def mineABlock(self, target):
        # check whether it is synchronized
        while 1:
            if self.isMining():
                break

            print(f"Getting block {self.localBlockIndex}")
            self.getBlock(self.localBlockIndex)
            self.getLatestBlockIdx()
            # query next block

        # generate new block
        blockHash = self.genNewBlock(target)

        return blockHash

    def genNewBlock(self, target):
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        stub = blockchain_pb2_grpc.BlockChainStub(local_channel)

        # generate a block
        response = self.sendMessage(local_channel, f'Gen Block:{target}')
        minerKey = response.message
        print("Add the block successfully.")

        # initiate coinbase transaction
        initTX = stub.initTxList(blockchain_pb2.InitTxListRequest(message="init transaction"))
        print(initTX.message)

        # broadcast the new block
        self.broadcastBlock(response.newBlock)
        blockHash = response.newBlock.hash

        # update the map
        msg = f"Update map:{target}:{minerKey}"
        response_list = self.broadcastMsg(msg)
        return blockHash

    def refreshMap(self):
        # get local map
        msg = f"Refresh map"
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        response = self.sendMessage(local_channel, msg)
        self.broadcastMap(response.map)

    def broadcastMap(self, map):
        channel_list = self.getAliveChannel(self.port_list)

        for c in channel_list:
            try:
                stub = blockchain_pb2_grpc.BlockChainStub(c)
                tran_msg = f"New map"
                response = stub.receiveMessage(blockchain_pb2.receiveMessageRequest(message=tran_msg, map=map))

            except Exception as e:
                print("broadcastMap err: ", e)

    def isMining(self):
        # check whether the mining should start mining
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        resposne = self.sendMessage(local_channel, 'Local index')
        self.localBlockIndex = int(resposne.message)
        self.getLatestBlockIdx()

        print("local:", self.localBlockIndex)
        print("latest:", self.latestBlockIndex)
        if self.localBlockIndex < self.latestBlockIndex:
            # query next block
            return False
        else:
            # start mining
            return True

    def sendMessage(self, channel, message):
        stub = blockchain_pb2_grpc.BlockChainStub(channel)

        # tran_msg = f"{self.miner_index} find a new Block!"
        response = stub.receiveMessage(blockchain_pb2.receiveMessageRequest(message=message))
        # print("client MSG:", response.message)
        return response

    def broadcastBlock(self, block):
        channel_list = self.getAliveChannel(self.port_list)

        for c in channel_list:
            try:
                self.sendBlock(c, block)
            except Exception as e:
                print("broadcastBlock err: ", e)

    def sendBlock(self, channel, block):
        stub = blockchain_pb2_grpc.BlockChainStub(channel)

        tran_msg = f"{self.miner_index} find a new Block!"
        response = stub.receiveBlock(blockchain_pb2.ReceiveBlockRequest(message=tran_msg, newBlock=block))
        print(response)

    def getAliveChannel(self, port_list):
        channel_list = []
        alive_miner = []
        for i, p in enumerate(port_list):
            if i == self.miner_index:
                continue
            channel = grpc.insecure_channel('localhost:' + p)

            try:
                grpc.channel_ready_future(channel).result(timeout=0.1)
            except:
                result = f"channel:{p} connect timeout"
            else:
                result = f"channel:{p} connect success"
                channel_list.append(channel)
                alive_miner.append(i)

        print(f"Miner {alive_miner} are alive")
        return channel_list

    def getUTXOs(self):
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        stub = blockchain_pb2_grpc.BlockChainStub(local_channel)
        response = stub.getUTXOs(blockchain_pb2.getUTXOsRequest(message="get UTXOs"))
        return response

    def getBlock(self, block_index):
        # get block message from other miner
        msg = f"Get Block:{block_index}"
        response_list = self.broadcastMsg(msg)
        # print("block response list", response_list)
        requeried_block = response_list[0].newBlock

        # add block into local blockchain
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        try:
            self.sendBlock(local_channel, requeried_block)
        except:
            print("Error get block")

    def getBlockInfo(self, block_index):
        msg = f"Get Block:{block_index}"
        local_channel = grpc.insecure_channel('localhost:' + self.localport)
        response = self.sendMessage(local_channel, msg)

        return response


if __name__ == '__main__':
    logging.basicConfig()

    miner = bc_Miner(0)
    miner.initMiner()
    # read from stroge and then start mining
    miner.mining()
