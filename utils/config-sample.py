
class Config:
    bot_name = 'FeyiTechTradeBot'
    is_test = True
    update_messages = False
    max_leverage = 100
    max_positions_per_chart = 100
    timeframe = '1m'
    class secrets:
        telegram_token = '' # enter your Telegram Bot token
        admin_chat_id = '' # enter your chat ID/user ID to prevent other users to use the bot
    class Binance:
        class ReadAndWrite:
            key = ""
            secret = ""