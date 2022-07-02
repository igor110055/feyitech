
class Constants:
    accounts_db_name = 'accounts'
    settings_db_name = 'settings'
    trade_keys_separator = '|'
    chart_photos_dir_name = 'chart_photos'
    class TradeType:
        futures = 'futures'
        spot = 'spot'
    
    class Commands:
        start = 'start'
        status = 'status'
        addtrade = 'addtrade'
        updatetrade = 'updatetrade'
        removetrade = 'removetrade'
        cancelalltrades = 'cancelalltrades'