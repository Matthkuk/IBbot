from ibapi.contract import Contract
import yaml

# def create_contract(symbol: str, exchange = "SMART", currency = "USD"):
#     contract = Contract()
#     contract.symbol = symbol.upper()
#     contract.secType = "STK"
#     contract.exchange = exchange
#     contract.currency = currency
#     return contract

def bot_config(file_path = "IBbot/AAPL.yaml"):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    
    contract_data = config['contract']
    contract = Contract()
    contract.symbol = contract_data['symbol']
    contract.secType = contract_data['secType']
    contract.exchange = contract_data['exchange']
    contract.currency = contract_data['currency']

    historical_data_params = [
        config['historical_data']['reqId'],
        contract,
        config['historical_data']['endDateTime'],
        config['historical_data']['durationStr'],
        config['historical_data']['barSizeSetting'],
        config['historical_data']['whatToShow'],
        config['historical_data']['useRTH'],
        config['historical_data']['formatDate'],
        config['historical_data']['keepUpToDate'],
        config['historical_data']['chartOptions']
    ]

    return contract, historical_data_params