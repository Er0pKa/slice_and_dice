# import statistics
import time
import datetime
import secret       # use your api keys
from binance.websockets import BinanceSocketManager
from binance.client import Client

client = Client(secret.api_key, secret.api_secret)
connected = 0
balance = {}
prices = {}
volatility = {}
# balance = [['BTC', '0.00000050'], ['ETH', '0.00000106'], ['BNB', '10.31293969'], ['USDT', '1304.85375110'],
#            ['ETC', '0.00319653'], ['SXP', '0.74872383']]
prices_1m = []
percents = []
diminishing_returns = 1
current_price = 0
target_buy_price = 0
profit = 0
commission = 0.2 / 100
start_balance = 0
current_balance = 0
start_time = datetime.datetime.now()
available_percent = 50 / 100
order_volume_percent = 15 / 100
orders = []
orders_quantity = 0
binance_orders = []
binance_open_orders = []
symbol = '1INCHUSDT'


class bColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def moving_average(arr):
    max = 0
    min = 500000
    sum = 0

    for item in arr:
        # print(item)
        open_price = float(item[1])
        high_price = float(item[2])
        low_price = float(item[3])
        close_price = float(item[4])

        prices_1m.append(close_price)
        sum += close_price

        if high_price > max:
            max = high_price
        if low_price < min:
            min = low_price

    # average = (max + min) / 2
    average = sum / len(arr)
    dispersion = max - average
    percent = round(dispersion * 100 / average, 2)
    ma = {'percent': percent, 'average': average}
    # print(open_price, high_price, low_price, close_price)
    # print('n', n)

    return ma


def get_open_orders(symbol):
    print(f"{bColors.OKBLUE}get_open_orders.{bColors.ENDC}")
    global binance_open_orders
    global diminishing_returns
    try:  # if connection is not ok
        binance_open_orders = client.get_open_orders(symbol=symbol)
    except ConnectionError:
        print('Connection Error get_open_orders time.ctime()')
    diminishing_returns = 1 - len(binance_open_orders)/10
    print('binance_open_orders', len(binance_open_orders))


def get_orders():
    print(f"{bColors.OKBLUE}get_orders.{bColors.ENDC}")
    global binance_orders
    try:  # if connection is not ok
        binance_orders = client.get_all_orders(symbol=symbol)
    except ConnectionError:
        print('Connection Error get_orders time.ctime()')
    print('binance_orders', len(binance_orders))


def get_volatility(symbol):
    global volatility
    print(f"{bColors.OKBLUE}get_volatility.{bColors.ENDC}")
    # print('get_volatility for ', symbol)
    # ticker = client.get_ticker(symbol)
    try:  # if connection is not ok
        klines60 = client.get_historical_klines(symbol, '1m', '1 hour ago UTC', 'now UTC', limit=500)
    except ConnectionError:
        print('Connection Error get_volatility time.ctime()')
    # print(klines)
    # print('max', max, 'min', min, 'average', average, 'dispersion', dispersion, 'percent', percent)
    klines25 = klines60[-25:]
    ma = moving_average(klines60)
    ma60 = ma['average']
    percent = ma['percent']
    ma25 = moving_average(klines25)['average']
    volatility = {'symbol': symbol, 'percent': percent, 'ma25': ma25, 'ma60': ma60}
    # print('median_percent', median_percent)

    print('volatility', volatility)

    # print('prices_1m', prices_1m)
    # print('max', max)
    # print('min', min)

    return volatility


# volatility = get_volatility('ETHUSDT')


def get_prices(arr):
    tickers = []
    print(f"{bColors.OKBLUE}get_prices.{bColors.ENDC}")

    try:  # if connection is not ok
        tickers = client.get_all_tickers()
    except ConnectionError:
        print('Connection Error get_prices time.ctime()')

    # print(tickers)

    if tickers:
        for item_arr in arr:
            symbol = item_arr
            # quantity = arr[item_arr]
            # print('symbol', symbol, 'quantity', quantity)
            for item in tickers:
                test_name = symbol + "USDT"
                if item['symbol'] == test_name:
                    price = float(item['price'])
                    # prices.append([test_name, price])
                    prices[test_name] = price
    print(prices)


def get_balances():
    global start_balance
    global current_balance
    global prices_1m
    global percents
    global current_price
    global start_balance
    global current_balance
    global available_percent
    global order_volume_percent
    global orders
    print(f"{bColors.OKBLUE}get_balances.{bColors.ENDC}")

    try:  # if connection is not ok
        account = client.get_account()
    except ConnectionError:
        print('Connection Error get_balances time.ctime()')

    balances = account['balances']
    for item in balances:
        if float(item['free']) > 0:
            # balance.append([item['asset'], item['free']])
            symbol = item['asset']
            volume = item['free']
            balance[symbol] = volume
    print(balance)
    if start_balance == 0:
        start_balance = float(balance['USDT'])
    current_balance = float(balance['USDT'])
    print('start_balance', start_balance, 'current_balance', current_balance)
    return balance


def make_order(symbol, side, quantity, price):
    if side == 'buy':
        order = client.create_order(
            symbol=symbol,
            side='BUY',
            type='MARKET',
            quantity=quantity)
    if side == 'sell':
        order = client.create_order(
            symbol=symbol,
            side='SELL',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=price)

    print('make order', order)
    time.sleep(5)
    get_orders()


def process_message(msg):
    # print("message type: {}".format(msg['e']))
    # print(msg)
    # do something
    global current_price
    global connected
    global timer
    try:
        current_price = float(msg['p'])
        connected = 1
        timer = 10
    except:
        print('Not connected', time.ctime())
        connected = 0


def dummy_strategy():
    global orders_quantity
    global current_balance
    global commission
    global target_buy_price
    global profit
    global orders
    global current_price

    # direction = average - average_long  # where chart is going '+' means up '-' is down trend
    percent = volatility['percent'] / 100

    profit = percent - commission
    target_buy_price = average * diminishing_returns - average * profit / 2

    if target_buy_price > current_price > 0 and available_percent > 0 and 0.02 > profit > commission * 2:
        volume = start_balance * order_volume_percent
        curr_quantity = round(volume / current_price, 3)
        desired_price = current_price + current_price * profit / 2
        current_balance -= current_price * curr_quantity
        orders_quantity += 1
        orders.append([current_price, volume, curr_quantity, desired_price, time.ctime()])
        print(f"{bColors.OKGREEN}Want to buy some. {bColors.ENDC}", curr_quantity)

        make_order(symbol, 'buy', curr_quantity, 'dummy')  # order here
        get_open_orders(symbol)
        time.sleep(5)

        print('order_volume_percent:', order_volume_percent, 'current_price:', current_price,
              'desired_price:', desired_price, 'profit:', profit * volume)
        print(orders)


# def connect_stonks():
timer = 10
# global diminishing_returns
# global current_balance
while not balance:
    get_balances()
    time.sleep(1)
while not prices:
    get_prices(balance)
    time.sleep(1)
while not volatility:
    get_volatility(symbol)
    time.sleep(1)
# while not binance_orders:
    get_orders()
    time.sleep(1)
if balance and prices:
    bm = BinanceSocketManager(client)  # start any sockets here, i.e a trade socket
    conn_key = bm.start_trade_socket(symbol, process_message)  # then start the socket manager

    while not connected:
        if timer >= 60:
            timer = 60
        bm.start()
        time.sleep(timer)
        timer += 3

timing_1s = time.time()
timing_1m = time.time()
while True:
    # print(time.time())
    if time.time() - timing_1s > 1.0:
        # print('volatility', volatility)
        average = volatility['ma25']
        average_long = volatility['ma60']
        timing_1s = time.time()
        # print("1 seconds")
        # print('average', average, 'current_price', current_price)

        if len(orders) > 0:
            last_order = orders[len(orders) - 1]
            desired_price = last_order[3]
            last_order_binance = binance_orders[len(binance_orders) - 1]
            last_order_binance_status = last_order_binance['status']
            last_order_binance_side = last_order_binance['side']

            if last_order_binance_status == 'FILLED' and last_order_binance_side == 'BUY':
                print(f"{bColors.OKGREEN}Want to sell some.{bColors.ENDC}")
                curr_quantity = last_order[2]
                desired_price = round(last_order[3], 4)

                make_order(symbol, 'sell', curr_quantity, desired_price)  # order here

            if last_order_binance_status == 'FILLED' and last_order_binance_side == 'SELL':
                print(f"{bColors.OKGREEN}Sell complete.{bColors.ENDC}")
                orders.pop()
                get_orders()
                get_balances()
                print('current_balance:', current_balance, 'start_balance:', start_balance,
                      ',made ', current_balance - start_balance, 'dolas', time.ctime())

            # if current_price >= desired_price:    # old but usefull
            #     curr_quantity = last_order[2]
            #     current_balance += curr_quantity * current_price
            #     print(f"{bColors.OKGREEN}Sell time.{bColors.ENDC}")
            #     print('current_balance:', current_balance, 'start_balance:', start_balance,
            #           ',made ', current_balance - start_balance, 'dollas', time.ctime())
            #     orders.pop()
            #     diminishing_returns += 0.1

        target_buy_price = average * diminishing_returns
        direction = average - average_long  # where chart is going '+' means up '-' is down trend
        percent = volatility['percent'] / 100
        commission = 0.2 / 100
        profit = percent - commission
        # print('cur_price: ', current_price, 'approximation_average', approximation_average, 'orders:', len(orders))
        # print("\33[3 A")
        # if approximation_average > current_price > 0 and available_percent > 0 and direction > 0:
        #
        # use strategies here
        #
        dummy_strategy()

    if time.time() - timing_1m > 60.0:
        timing_1m = time.time()
        now = datetime.datetime.now()
        uptime = now - start_time
        print(f"{bColors.HEADER}Update prices.{bColors.ENDC}", uptime)
        print('current_balance:', current_balance, 'start_balance:', start_balance, time.ctime())
        print('orders', orders_quantity, orders)
        # average * diminishing_returns - average * profit
        print('will buy when ', target_buy_price, diminishing_returns, ' > ', current_price, ' and ',
              available_percent, ' > 0', 'current profit:', profit * 100)

        get_volatility(symbol)
        get_orders()
        get_open_orders(symbol)

        # some new strategy
        # percent = volatility['percent'] / 200   # 200 cuz +- deviation, just divide by 2
        # average_short = volatility['ma25']
        # diff_price = average_short * percent
        # price_for_buy = average_short - diff_price
        # price_for_sell = average_short + diff_price
        # print('price for buy:', price_for_buy, 'price for sell:', price_for_sell,
        #       'diff_price:', diff_price, 'percent:', percent, )
