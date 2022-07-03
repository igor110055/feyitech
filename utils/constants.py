
class Constants:
    accounts_db_name = 'accounts'
    settings_db_name = 'settings'
    trade_keys_separator = '|'
    chart_photos_dir_name = 'chart_photos'
    logo_filename = 'assets/logo.png'
    dev_logo_filename = 'assets/dev-logo.png'
    class TradeType:
        futures = 'futures'
        spot = 'spot'
    
    class Commands:
        start = 'start'
        status = 'status'
        addtrade = 'addtrade'
        updatetrade = 'updatetrade'
        removetrade = 'stoptrade'