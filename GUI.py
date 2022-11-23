import json
from tkinter import *
from Starter import *


class MainPage(object):
    def __init__(self, master=None):
        self.root = master
        self.root.geometry('%dx%d' % (800, 800))
        self.createPage()

    def createPage(self):
        self.page = Frame(self.root)  # 创建Frame
        self.page.pack()

        Button(self.page, text="PolyU Go", font=10, width=15, height=3,
               command=self.goGamePage).pack(
            fill=X,
            pady=60,
            padx=10)
        Button(self.page, text='Show UTXOs', font=30, width=15, height=3, command=self.goShowUTXOsPage).pack(fill=X,
                                                                                                             pady=40,
                                                                                                             padx=10)
        Button(self.page, text='Show Block Info', font=30, width=15, height=3, command=self.goShowBlockPage).pack(
            fill=X,
            pady=40,
            padx=10)

    def goGamePage(self):
        self.page.destroy()
        gamePage(self.root)
        self.root.title(f"PolyU Go [{starter1.minerIndex}]")

    def goShowUTXOsPage(self):
        self.page.destroy()
        showUTXOsPage(self.root)
        self.root.title('Show UTXOs')

    def goShowBlockPage(self):
        self.page.destroy()
        showBlockPage(self.root)
        self.root.title('Show Block Info')


class gamePage(object):
    def __init__(self, master=None):
        self.root = master
        # self.root.geometry('%dx%d' % (500, 500))
        self.efforts = StringVar()
        self.guess = StringVar()
        self.result = StringVar()
        self.opportunities = StringVar()
        self.createPage()

    def createPage(self):
        self.page = Frame(self.root)
        self.page.pack()

        Label(self.page).grid(row=0, stick=W)
        Label(self.page, text='Daily efforts: ').grid(row=1, stick=W, pady=10, column=0)
        Entry(self.page, textvariable=self.efforts).grid(row=2, stick=W, pady=10, ipadx=20)
        Button(self.page, text='Redeem', command=self.reedemEffort).grid(row=3, stick=W, pady=10)
        Label(self.page, text='Remaining opportunities: ').grid(row=4, stick=W, pady=10)
        Label(self.page, bg="white", textvariable=self.opportunities, anchor=NW, justify='left', width=21).grid(row=5,
                                                                                                                stick=W,
                                                                                                                pady=10)

        Label(self.page, text='Guess position: ').grid(row=6, stick=W, pady=10, column=0)
        Entry(self.page, textvariable=self.guess).grid(row=7, stick=W, pady=10, ipadx=20)
        Button(self.page, text='Go', command=self.checkResult).grid(row=8, stick=W, pady=10)
        Label(self.page, text='Result: ').grid(row=9, stick=W, pady=10)
        Label(self.page, bg="white", textvariable=self.result, anchor=NW, justify='left', width=21).grid(row=10,
                                                                                                         stick=W,
                                                                                                         pady=10,
                                                                                                         ipadx=200,
                                                                                                         ipady=100)

        Button(self.page, text='Update Map', command=self.clean).grid(row=11, stick=W, pady=10)
        Button(self.page, text='Back', command=self.goMainPage).grid(row=12, stick=W, pady=10)

    def reedemEffort(self):
        efforts = self.efforts.get()
        self.opportunities.set(efforts)

    def checkResult(self):
        remainingTimes = int(self.opportunities.get())
        if remainingTimes > 0:
            guess = self.guess.get()
            # call mining function TODO
            result = Owner.checkResult(guess)
            if result.startswith("Failed"):
                self.result.set(result)
            else:
                # find a new block
                blockHash = result
                feedback = f"Find a new block at position[{guess}]!\nThe block hash is {blockHash}"
                self.result.set(feedback)
            self.opportunities.set(str(remainingTimes - 1))
        else:
            feedback = "You have run out of opportunities\n" + "Go to work!!"
            self.result.set(feedback)

    def clean(self):
        self.efforts.set("")
        self.guess.set("")
        self.result.set("")
        self.opportunities.set("")
        Owner.refreshMap()

    def goMainPage(self):
        self.page.destroy()
        MainPage(self.root)
        self.root.title(f"Miner {starter1.minerIndex}")


class showUTXOsPage(object):
    def __init__(self, master=None):
        self.root = master
        # self.root.geometry('%dx%d' % (500, 500))
        self.UTXOs = StringVar()
        self.createPage()
        self.ListBox = None

    def createPage(self):
        self.page = Frame(self.root)

        Label(self.page).grid(row=0, stick=W)

        Label(self.page, text='UTXOs: ').grid(row=5, stick=W, pady=10)

        s = Scrollbar(self.page, orient=VERTICAL)
        s2 = Scrollbar(self.page, orient=HORIZONTAL)
        self.ListBox = Listbox(self.page, width=50, yscrollcommand=s.set, xscrollcommand=s2.set)

        s.config(command=self.ListBox.yview())
        s2.config(command=self.ListBox.xview())

        self.ListBox.grid(row=6, stick=W,
                          pady=10,
                          ipadx=50,
                          ipady=200)

        global starter1

        result = starter1.miner.getUTXOs()

        keys = result.utxos.key
        amounts = result.utxos.amount
        owner = result.utxos.owner

        for i in range(len(keys)):
            desplay_result = keys[i] + f" Amount: {amounts[i]} Owner: {owner[i]}"

            self.ListBox.insert(END, desplay_result)
            self.ListBox.insert(END, "\n")

        Button(self.page, text='Back', command=self.goMainPage).grid(row=7, stick=W, pady=10)
        self.page.pack()

    def getUTXOs(self):
        # getUTXOs() TODO
        global starter1
        # genUTXOs(starter1.bc_Miner.minerIndex)

        result = starter1.miner.getUTXOs()

        keys = result.utxos.key
        amounts = result.utxos.amount
        owner = result.utxos.owner

        desplay_result = ""
        for i in range(len(keys)):
            desplay_result += keys[i] + f"\nAmount: {amounts[i]}\nOwner: {owner[i]} \n\n"

    def goMainPage(self):
        self.page.destroy()
        MainPage(self.root)
        self.root.title(f"Miner {starter1.minerIndex}")


class showBlockPage(object):
    def __init__(self, master=None):
        self.root = master
        # self.root.geometry('%dx%d' % (500, 500))
        self.blockIndex = StringVar()
        self.blockInfo = StringVar()
        self.createPage()

    def createPage(self):
        self.page = Frame(self.root)
        self.page.pack()
        # self.page

        Label(self.page).grid(row=0, stick=W)
        Label(self.page, text='Block Index: ').grid(row=1, stick=W, pady=10, column=0)
        Entry(self.page, textvariable=self.blockIndex).grid(row=2, stick=W, pady=10, ipadx=20)
        Label(self.page, text='Block Info: ').grid(row=3, stick=W, pady=10)
        Label(self.page, bg="white", textvariable=self.blockInfo, anchor=NW, justify='left', width=21).grid(row=4,
                                                                                                            stick=W,
                                                                                                            pady=10,
                                                                                                            ipadx=200,
                                                                                                            ipady=100)
        Button(self.page, text='Get Block', command=self.getBlock).grid(row=5, stick=W, pady=10)
        Button(self.page, text='Back', command=self.goMainPage).grid(row=7, stick=W, pady=10)

    def getBlock(self):
        index = self.blockIndex.get()

        # get Block Info TODO
        block = starter1.miner.getBlockInfo(int(index)).newBlock

        for tx in block.transactionList:

            for txOut in tx.TxOutList:
                hash = hashlib.sha256((txOut.address).encode("utf-8")).hexdigest()
                hash_result = hashlib.sha256(hash.encode("utf-8")).hexdigest()
                txOut.address = hash_result

        self.blockInfo.set(block)

    def goMainPage(self):
        self.page.destroy()
        MainPage(self.root)
        self.root.title(f"Miner {starter1.minerIndex}")


starter1 = None
Owner = None


class runGUI:
    def __init__(self, starter):
        global starter1
        global Owner
        starter1 = starter
        Owner = starter.miner

    def run(self):
        print("GUI go")

        root = Tk()
        root.title(f"Miner {starter1.minerIndex}")
        MainPage(root)
        root.mainloop()


if __name__ == "__main__":
    runGUI(0).run()
