
from utils.constants import Constants


class MSG:
    trade_exists_error = '⛔️ A trade with this symbol already exist. Cancel the trade first or edit it instead.'
    input_error = '⛔️ An input error occurred. Check your input and try again.'
    no_trade_info = f'ℹ️ You currently have no trade. \n\n To add a trade, use the <a href="/{Constants.Commands.addtrade}">/{Constants.Commands.addtrade}</a> command.'