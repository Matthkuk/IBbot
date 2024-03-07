from bot import Bot
import contracts

contract = contracts.create_contract("AAPL")

bot = Bot(contract)