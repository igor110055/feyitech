
class Config:
    bot_name = 'FeyiTechTradeBot'
    personal_website= 'https://feyitech.com'
    company_website= 'https://softbaker.com'
    personal_email= 'hello@feyitech.com'
    company_email= 'hello@softbaker.com'
    phone_number= '+234-9024-500-275'
    twitter= 'https://twitter.com/feyi_tech'
    telegram= 'https://t.me/feyitech'
    is_test = True
    update_messages = False
    max_leverage = 100
    max_positions_per_chart = 100
    timeframe = '1m'
    class secrets:
        telegram_token = '5419643187:AAFh3mwyee1gRclVRspO3HhtNLe8GukG1jo' # enter your Telegram Bot token
        admin_chat_id = 916028969#5241980113 # enter your chat ID/user ID to prevent other users to use the bot
    class Binance:
        class ReadOnly:
            key = "6QbgYsJyNyziVatP89iYOZxRjJQm4gHNfTeSbQr9QlivgwVDgEjJlcYdxC8QlJFP"
            secret = "7dbjUDTqTe6z41ojCQnZpGTOzuutEIfyqXQlf9izxfMhmDQ2FXm4T9Io6EGJ3lXb"
        class ReadAndWrite:
            key = "4hujbcxhNKoPNdev14IJpMKAGEPZigP98rfmngim76kaVUqZijpsw7gk1s04Si8N"
            secret = "UbLKzMvbkd1cvr5ec4HArGFlHCL5Q46hC7KNmeWDGK4PqIO7gnxGdxGKrsRFJ57w"