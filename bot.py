from ib_client import IBClient
import threading
import time
from datetime import datetime, timedelta
import pytz
import math
import numpy as np
import pandas as pd
import ta
from ibapi.contract import Contract
from ibapi.order import Order

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

class Bot():
    ib = None
    bar_size = 5 # in minutes
    current_bar = Bar()
    bars = []
    reqId = 1
    order_id = 0
    sma_period = 50
    symbol = "AAPL"
    initial_bar_time = datetime.now().astimezone(pytz.timezone("America/New_York"))
    def __init__(self, contract: Contract):

        self.ib = IBClient(self) # pass in instance of Bot()

        # Connect is causing the terminal freeze
        self.ib.connect("127.0.0.1", 7496, 1)
        ib_thread = threading.Thread(target=self.ib.run, daemon=True)
        ib_thread.start()
        while(self.ib.next_valid_order_id == None):
            print("Waiting for TWS connection acknowledgement ...")

        print("Connection Established")
        if (int(self.bar_size) > 1):
            mintext = " mins"
        # query_time = (datetime.now().astimezone(pytz.timezone("America/New_York")) - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y%m%d %H:%M:%S")
        # Create contract (subscription)
        # contract = Contract()
        # contract.symbol = self.symbol.upper()
        # contract.secType = "STK"
        # contract.exchange = "SMART"
        # contract.currency = "USD"
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
        # STRIP THIS IN THE FUTURE TO ANOTHER FILE TO HAVE MULTIPLE STRATEGIES
        # Historical data to catch up
        if (realtime == False):
            self.bars.append(bar)
            print(bar, type(bar))
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
        # print('FLASHING:', self.bars[0])



    def exit_program(self):
        print("Exiting program...")
        self.ib.disconnect()

# bot = Bot()