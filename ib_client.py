import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.order import *

class IBWrapper(EWrapper):
    def __init__(self, bot):
        self.bot = bot # assign the bot instance
        EWrapper.__init__(self)
    
    # Listen to real-time bars
    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
        try:
            self.bot.on_bar_update(reqId, time, open, high, low, close, volume, wap, count)
        except Exception as e:
            print(e)

    # Historical Data
    def historicalData(self, reqId, bar):
        try:
            self.bot.on_bar_update(reqId, bar, False)
        except Exception as e:
            print(e)
    # # On realtime bar after historical data finishes
    # def historicalDataUpdate(self, reqId: int, bar: BarData):
    #     try:
    #         bot.on_bar_update(reqId, bar, True)
    #     except Exception as e:
    #         print(e)
    # # On Historical Data End
    # def historicalDataEnd(self, reqId: int, start: str, end: str):
    #     print(reqId)
    # Get next order id we can use
    def nextValidId(self, nextOrderId: int):
        global orderId
        orderId = nextOrderId

# Client
class IBClient(EClient):
    def __init__(self, bot):
        wrapper = IBWrapper(bot)
        EClient.__init__(self, wrapper)