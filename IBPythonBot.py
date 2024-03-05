import ibapi
from ibapi.client import EClient
from ibapi.common import BarData
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import ta
import numpy as np
import pandas as pd
import pytz
import math
from datetime import datetime, timedelta
import threading
import time
# Vars
orderId = 1
# Wrapper to translate messages to client
class IBWrapper(EWrapper):
    def __init__(self):
        EWrapper.__init__(self)
    
    # Listen to real-time bars
    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
        try:
            bot.on_bar_update(reqId, time, open, high, low, close, volume, wap, count)
        except Exception as e:
            print(e)

    # Historical Data
    def historicalData(self, reqId, bar):
        try:
            bot.on_bar_update(reqId, bar, False)
        except Exception as e:
            print(e)
    # On realtime bar after historical data finishes
    def historicalDataUpdate(self, reqId: int, bar: BarData):
        try:
            bot.on_bar_update(reqId, bar, True)
        except Exception as e:
            print(e)
    # On Historical Data End
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        print(reqId)
    # Get next order id we can use
    def nextValidId(self, nextOrderId: int):
        global orderId
        orderId = nextOrderId

# Client
class IBClient(EClient):
    def __init__(self):
        wrapper = IBWrapper()
        EClient.__init__(self, wrapper)

#Bar Object
class Bar:
    open = 0
    low = 0
    high = 0
    close = 0
    volume = 0
    date = ''
    def __init__(self):
        self.open = 0
        self.low = 0
        self.high = 0
        self.close = 0
        self.volume = 0
        self.date = ''

# Bot
class Bot():
    ib = None
    bar_size = 1
    current_bar = Bar()
    bars = []
    reqId = 1
    global orderId
    sma_period = 50
    symbol = ''
    initial_bar_time = datetime.now().astimezone(pytz.timezone("America/New_York"))
    def __init__(self):
        self.ib = IBClient()
        # Connect is causing the terminal freeze
        self.ib.connect("127.0.0.1", 7496, 1)
        ib_thread = threading.Thread(target=self.run_ib_client, daemon=True)
        ib_thread.start()
        # Pause to let logs finish for input
        time.sleep(1)
        self.symbol = input("Enter the symbol you want to trade: ")
        # Get bar size
        self.bar_size = input("Enter the barsize you want to trade in minutes: ")
        mintext = " min"
        if (int(self.bar_size) > 1):
            mintext = " mins"
        query_time = (datetime.now().astimezone(pytz.timezone("America/New_York")) - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y%m%d %H:%M:%S")
        # Create contract (subscription)
        contract = Contract()
        contract.symbol = self.symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        self.ib.reqIds(-1)
        # Request real-time market data
        # self.run_ib_client()
        # bars_thread = threading.Thread(target=self.request_real_time_bars, args=(contract,), daemon=True)
        # bars_thread.start()
        # self.ib.reqRealTimeBars(0, contract, 5, "TRADES", 1, [])
        self.ib.reqHistoricalData(self.reqId, contract, "", "2 D", str(self.bar_size) + mintext, "TRADES", 1, 1, True, [])
        # # Create order object
        # order = Order()
        # order.orderType = "MKT"
        # order.action = "BUY"
        # quantity = 1
        # order.totalQuantity = quantity
        # order.eTradeOnly = ''
        # order.firmQuoteOnly = ''
        # # Create contract object
        # contract = Contract()
        # contract.symbol = self.symbol.upper()
        # contract.secType = "STK" # or FUT for futures etc
        # contract.exchange = "SMART"
        # contract.primaryExchange = "ISLAND" # ISLAND is a way of routing exchanges through the NASDAQ
        # contract.currency = "USD"
        # # Place the order
        # self.ib.placeOrder(1, contract, order)
    
    def request_real_time_bars(self, contract):
        self.ib.reqRealTimeBars(0, contract, 5, "TRADES", 1, [])

    def run_ib_client(self):
        # self.ib.connect("127.0.0.1", 7496, 1)
        self.ib.run()

    # Bracket order setup
    def bracket_order(self, parent_order_id, action, quantity, profit_target, stop_loss):
        # Create parent order / initial entry
        parent_order = Order()
        parent_order.orderId = parent_order_id
        parent_order.orderType = "MKT"
        parent_order.action = action
        parent_order.totalQuantity = quantity
        parent_order.transmit = False
        parent_order.eTradeOnly = ''
        parent_order.firmQuoteOnly = ''
        # Profit Target
        profit_target_order = Order()
        profit_target_order.orderId = parent_order_id + 1
        profit_target_order.orderType = "LMT"
        profit_target_order.action = "SELL"
        profit_target_order.totalQuantity = quantity
        profit_target_order.lmtPrice = round(profit_target, 2)
        profit_target_order.transmit = False
        profit_target_order.eTradeOnly = ''
        profit_target_order.firmQuoteOnly = ''
        # Stop loss order
        stop_loss_order = Order()
        stop_loss_order.orderId = parent_order_id + 2
        stop_loss_order.orderType = "STP"
        stop_loss_order.action = "SELL"
        stop_loss_order.totalQuantity = quantity
        stop_loss_order.auxPrice = round(stop_loss, 2)
        stop_loss_order.transmit = True
        stop_loss_order.eTradeOnly = ''
        stop_loss_order.firmQuoteOnly = ''
        # Bracket Orders
        bracket_orders = [parent_order, profit_target_order, stop_loss_order]
        return bracket_orders

    
    # Pass realtime bar data back to bot
    def on_bar_update(self, reqId, bar, realtime):
        # Historical data to catch up
        if (realtime == False):
            self.bars.append(bar)
        else:
            bartime = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))
            minutes_diff = (bartime - self.initial_bar_time).total_seconds() / 60
            self.current_bar.date = bartime
            # On Bar Close
            if (minutes_diff > 0 and math.floor(minutes_diff) % self.bar_size == 0):
                # Entry - if we have a higher high, a higher low and we cross the 50 SMA - Buy
                # Calc SMA
                closes = []
                for bar in self.bars:
                    closes.append(bar.close)
                self.close_array = pd.Series(np.asarray(closes))
                self.sma = ta.trend.sma(self.close_array, self.sma_period, True)
                print("SMA :" + str(self.sma[len(self.sma) - 1]))
                # Calc higher highs and lows
                last_low = self.bars[len(self.bars) - 1].low
                last_high = self.bars[len(self.bars) - 1].high
                last_close = self.bars[len(self.bars) - 1].close
                last_bar = self.bars[len(self.bars) - 1]
                # Check Criteria
                if (bar.close > last_high 
                    and self.current_bar.low > last_low 
                    and bar.close > str(self.sma[len(self.sma) - 1])
                    and last_close < str(self.sma[len(self.sma) - 2])):
                    profit_target = bar.close * 1.02
                    stop_loss = bar.close * 0.99
                    quantity = 1
                    bracket = self.bracket_order(orderId, "BUY", quantity, profit_target, stop_loss)
                    # Place bracket order
                    contract = Contract()
                    contract.symbol = self.symbol.upper()
                    contract.secType = "STK" # or FUT for futures etc
                    contract.exchange = "SMART"
                    contract.primaryExchange = "ISLAND" # ISLAND is a way of routing exchanges through the NASDAQ
                    contract.currency = "USD"
                    for order in bracket:
                        order.ocaGroup = "OCA_" + str(orderId)
                        order.ocaType = 2
                        self.ib.placeOrder(order.orderId, contract, order)
                    orderId = orderId + 3
                # Bar closed append
                self.current_bar.close = bar.close
                if (self.current_bar.date != last_bar.date):
                    print("New bar!")
                    self.bars.append(self.current_bar)
                self.current_bar.open = bar.open
            # Build realtime bar
            if (self.current_bar.open == 0):
                self.current_bar.open = bar.open
            if (self.current_bar.high == 0 or bar.high > self.current_bar.high):
                self.current_bar.high = bar.high
            if (self.current_bar.low == 0 or bar.low < self.current_bar.high):
                self.current_bar.low = bar.low



    def exit_program(self):
        print("Exiting program...")
        self.ib.disconnect()

bot = Bot()
# time.sleep(10)
# bot.exit_program()