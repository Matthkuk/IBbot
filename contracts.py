from ibapi.contract import Contract

def create_contract(symbol: str, exchange="SMART", currency="USD"):
    contract = Contract()
    contract.symbol = symbol.upper()
    contract.secType = "STK"
    contract.exchange = exchange
    contract.currency = currency
    return contract
