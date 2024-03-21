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
from ibapi.common import BarData
import strategy

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
    current_bar = BarData()
    bars = []
    reqId = 1
    order_id = 0
    sma_period = 50
    symbol = "AAPL"
    initial_bar_time = datetime.now().astimezone(pytz.timezone("America/New_York"))
    def __init__(self, contract: Contract, historical_data):

        self.ib = IBClient(self) # pass in instance of Bot()

        # Connect is causing the terminal freeze
        self.ib.connect("127.0.0.1", 7496, 1)
        ib_thread = threading.Thread(target=self.ib.run, daemon=True)
        ib_thread.start()
        while(self.ib.next_valid_order_id == None):
            print("Waiting for TWS connection acknowledgement ...")

        print("Connection Established")
        # if (int(self.bar_size) > 1):
        #     mintext = " mins"
        # query_time = (datetime.now().astimezone(pytz.timezone("America/New_York")) - timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y%m%d %H:%M:%S")
        self.ib.reqIds(-1)
        self.ib.reqHistoricalData(*historical_data)
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
    def on_bar_update(self, reqId, bar: BarData, realtime):
        # STRIP THIS IN THE FUTURE TO ANOTHER FILE TO HAVE MULTIPLE STRATEGIES
        if not self.current_bar:
            # Initialize a new bar if there's no current bar
            self.current_bar = BarData()

        if not realtime:
            # Historical data - simply append to the bars list
            self.bars.append(bar)
            # return
        
        self.initial_bar_time = datetime.now(pytz.timezone("America/New_York"))

        # Check if the last bar in historical data is complete or incomplete
        if len(self.bars) >= 1:
            last_bar = self.bars[-1]

            last_bartime = datetime.strptime(last_bar.date, "%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))

            time_diff = (self.initial_bar_time - last_bartime).total_seconds() / 60

            if time_diff >= self.bar_size:
                print(f"Last historical bar is complete: {time_diff}")
                self.current_bar = BarData()
            else:
                print(f"Last historical bar is incomplete: {time_diff}")
                # Enter last entry for modification
                self.current_bar = last_bar
                # Remove last entry
                self.bars = self.bars[:-1]

        # bartime = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))
        # minutes_diff = (bartime - self.initial_bar_time).total_seconds() / 60

        # if minutes_diff > 0 and math.floor(minutes_diff) % self.bar_size == 0:
        #     # Current bar is complete
        #     self.current_bar.close = bar.close
        #     self.bars.append(self.current_bar)  # Add the completed bar to the list of bars

        #     # Start a new bar
        #     self.current_bar = BarData(date=bartime, open=bar.open, high=bar.open, low=bar.open, volume=0)
        # else:
        #     # Update current incomplete bar with latest data
        #     self.current_bar.high = max(self.current_bar.high, bar.high)
        #     self.current_bar.low = min(self.current_bar.low, bar.low)
        #     self.current_bar.volume += bar.volume



        # # Update current bar with closing time of bar
        # self.current_bar.date = bartime
        # # On Bar Close
        # if (minutes_diff > 0 and math.floor(minutes_diff) % self.bar_size == 0):
        #     # Append the closed bar and initiate the open price of the new bar
        #     self.current_bar.close = bar.close
        #     if (self.current_bar.date != last_bar.date):
        #         print("New bar!")
        #         self.bars.append(self.current_bar)
        #     # Reset the fields of bar other than close and date
        #     self.current_bar.open = bar.open
        #     self.current_bar.high = bar.open
        #     self.current_bar.low = bar.open
        #     self.current_bar.volume = 0
        #     # Create Criteria
        #     signals = strategy.simple_trading_strategy(self.bars)
        #     # Check Criteria
        #     if (bar.close > last_high 
        #         and self.current_bar.low > last_low 
        #         and bar.close > str(self.sma[len(self.sma) - 1])
        #         and last_close < str(self.sma[len(self.sma) - 2])):
        #         # Create bracket order
        #         profit_target = bar.close * 1.02
        #         stop_loss = bar.close * 0.99
        #         quantity = 1
        #         bracket = self.bracket_order(orderId, "BUY", quantity, profit_target, stop_loss)
        #         # Place bracket order
        #         contract = Contract()
        #         contract.symbol = self.symbol.upper()
        #         contract.secType = "STK" # or FUT for futures etc
        #         contract.exchange = "SMART"
        #         contract.primaryExchange = "ISLAND" # ISLAND is a way of routing exchanges through the NASDAQ
        #         contract.currency = "USD"
        #         for order in bracket:
        #             order.ocaGroup = "OCA_" + str(orderId)
        #             order.ocaType = 2
        #             self.ib.placeOrder(order.orderId, contract, order)
        #         orderId = orderId + 3
        # # Build realtime bar
        # if (self.current_bar.open == 0):
        #     self.current_bar.open = bar.open
        # if (self.current_bar.high == 0 or bar.high > self.current_bar.high):
        #     self.current_bar.high = bar.high
        # if (self.current_bar.low == 0 or bar.low < self.current_bar.high):
        #     self.current_bar.low = bar.low
        # print('FLASHING:', self.bars[0])
        # df = strategy.create_dataframe(self.bars)
        # print(df)

# bot = Bot()