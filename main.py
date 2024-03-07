from bot import Bot
import configs

contract, historical_data_params = configs.bot_config()

bot = Bot(contract, historical_data_params)