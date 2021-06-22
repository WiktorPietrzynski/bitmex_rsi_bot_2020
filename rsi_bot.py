import bitmex
import numpy as np
import pandas as pd
import json
import requests
import time
import datetime
import sys
from termcolor import colored

# nohup python3 -u rsi_pandas.py > rsi_pandas.log &

sys.setrecursionlimit(10 ** 6)
my_size = 30

# bitmex
id = ""
secret = ""
client = bitmex.bitmex(test=False, api_key=id, api_secret=secret)
endpoint = "wss://www.bitmex.com/realtime"


# ws = BitMEXWebsocket(endpoint=endpoint, symbol="XBTUSD", api_key=id, api_secret=secret)

# testnet
# id=""
# secret=""
# client = bitmex.bitmex( api_key=id, api_secret=secret)
# endpoint = "wss://testnet.bitmex.com/realtime"
# ws = BitMEXWebsocket(endpoint=endpoint, symbol="XBTUSD", api_key=id, api_secret=secret)


def book():
    while True:
        try:
            order_book_response = requests.get('https://www.bitmex.com/api/v1/orderBook/L2?symbol=xbt&depth=1')
            order_book = order_book_response.json()
            short_price = order_book[0]['price']
            long_price = order_book[1]['price']
            break
        except Exception as e:
            print("")
            print(colored("Book error", "red"))
            print(colored(e, "red"))
            time.sleep(10)
    return short_price, long_price


def orders():
    while True:
        try:
            # my_orders=ws.open_orders('')
            my_orders = client.Order.Order_getOrders(symbol='XBTUSD', reverse=True, count=10,
                                                     filter=json.dumps({"open": True})).result()
            break
        except Exception as e:
            print("")
            print(colored("Orders error", "red"))
            print(colored(e, "red"))
            time.sleep(10)
    return my_orders[0]


def closed_orders():
    while True:
        try:
            # my_orders=ws.open_orders('')
            my_orders = client.Order.Order_getOrders(symbol='XBTUSD', reverse=True, count=1).result()
            break
        except Exception as e:
            print("")
            print(colored("Orders error", "red"))
            print(colored(e, "red"))
            time.sleep(10)
    return my_orders[0]


def position():
    while True:
        try:
            # my_position = ws.positions()
            my_position = client.Position.Position_get(filter=json.dumps({"symbol": "XBTUSD"})).result()
            # my_position_qty = my_position[0]['currentQty']
            # entry_price = my_position[0]["avgEntryPrice"]
            break
        except Exception as e:
            print("")
            print(colored("Position error", "red"))
            print(colored(e, "red"))
            time.sleep(10)
    return my_position[0]


def get_rsi():
    bin_size = "1m"
    count = "125"
    while True:
        try:
            close_response = requests.get(
                "https://www.bitmex.com/api/v1/trade/bucketed?binSize=" + bin_size + "&partial=false&symbol=.BXBT&count=" + count + "&reverse=True")
            close_book = close_response.json()
            closes = []
            trades = {}
            for trade in close_book:
                for key in trade:
                    if key == "close":
                        closes.append(trade["close"])

            trades["close"] = closes
            trades["close"].reverse()
            ohlc = pd.DataFrame(trades)
            period = 14
            try:
                delta = ohlc["close"].diff()

                up, down = delta.copy(), delta.copy()
                up[up < 0] = 0
                down[down > 0] = 0

                _gain = up.ewm(com=(period - 1), min_periods=period).mean()
                _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()

                rs = _gain / _loss
                rsi = pd.Series(100 - (100 / (1 + rs)), name="RSI")
                last_rsi = rsi.iloc[-1]
                round_rsi = int(last_rsi)
                break
            except Exception as e:
                print("")
                print(colored("RSI calc error", "red"))
                print(colored(e, "red"))
                time.sleep(10)
        except Exception as e:
            print("")
            print(colored("close history error", "red"))
            print(colored(e, "red"))
            time.sleep(10)
    return round_rsi


# advanced


def cancel_orders():
    while True:
        try:
            client.Order.Order_cancelAll().result()
            break
        except Exception as e:
            print("")
            print(colored("Cancel Orders error", "red"))
            print(colored(e, "red"))
            time.sleep(10)


def close_position():
    while True:
        try:
            print("Stop Loss")
            client.Order.Order_closePosition(symbol='XBTUSD').result()
            break
        except Exception as e:
            print("")
            print(colored("Close position error", "red"))
            print(colored(e, "red"))
            time.sleep(10)


def change_close():
    while True:
        try:
            print("")
            last_order = orders()
            last_order = last_order[0]
            order_id = last_order["orderID"]
            order_side = last_order["side"]
            order_price = last_order["price"]
            if order_side == "Buy":
                print("change buy")
                market = book()
                book_price = market[1]
                if order_price != book_price:
                    new_price = book_price
                    client.Order.Order_amend(orderID=order_id, price=new_price).result()
                    break
                else:
                    break
            elif order_side == "Sell":
                print("change sell")
                market = book()
                book_price = market[0]
                if order_price != book_price:
                    new_price = book_price
                    client.Order.Order_amend(orderID=order_id, price=new_price).result()
                    break
                else:
                    break
            else:
                time.sleep(10)
        except Exception as e:
            print("exception")
            pass


def test_short(my_size):
    position_list = position()
    entry_price = position_list[0]["avgEntryPrice"]
    while True:
        print("")
        print("testing_short")

        current_time = datetime.datetime.now()
        print(current_time)

        my_position = position()
        my_position_qty = my_position[0]['currentQty']
        print("MPQ: ", my_position_qty)

        order_list = orders()
        order_list_size = len(order_list)
        print("Orders: ",order_list_size)

        rsi_value = get_rsi()
        print("RSI value: ", rsi_value)

        market = book()
        book_price = market[0]

        diff = entry_price - book_price
        # 1000-900 = 100 profit
        # 1000-1100 = -100 lost
        if my_position_qty!=0 and order_list_size==0:
            print("Where is close order?")
            status = "return"
            break
        if diff > 0:
            print(colored("Price Diff: ", "green"), entry_price, " - ", book_price, " = ", colored(str(diff), "green"))
            time.sleep(5)
            if my_position_qty == 0:
                print("")
                closed_order = closed_orders()
                closed_order_price = closed_order[0]["price"]
                profit = entry_price - closed_order_price
                print(colored("Take Profit", "green"), "Profit:", profit)
                status = "return"
                break
        elif diff < 0:
            print(colored("Price Diff: ", "red"), entry_price, " - ", book_price, " = ", colored(str(diff), "red"))
            stop = 0
            if my_position_qty == 0:
                closed_order = closed_orders()
                closed_order_price = closed_order[0]["price"]
                loss = entry_price - closed_order_price
                print("")
                print(colored("Stop Loss", "red"), "Loss:", loss)
                cancel_orders()
                status = "return"
                break
            if diff <= stop:
                if order_list_size != 0:
                    change_close()
                    time.sleep(5)
            time.sleep(5)
        else:
            print("Price Diff: ", entry_price, " - ", book_price, " = ", diff)
            time.sleep(5)
    if status == "success":
        cancel_orders()
        close_position()
    else:
        pass


def test_long(my_size):
    position_list = position()
    entry_price = position_list[0]["avgEntryPrice"]
    while True:
        print("")
        print("testing_long")

        current_time = datetime.datetime.now()
        print(current_time)

        order_list = orders()
        order_list_size = len(order_list)
        print("Orders: ",order_list_size)

        rsi_value = get_rsi()
        print("RSI_value: ", rsi_value)

        my_position = position()
        my_position_qty = my_position[0]['currentQty']
        print("MPQ: ", my_position_qty)

        market = book()
        book_price = market[1]

        diff = entry_price - book_price
        # 1000-900 = 100 lost
        # 1000-1100 = -100 profit
        if my_position_qty!=0 and order_list_size==0:
            print("Where is close order?")
            status = "return"
            break
        if diff > 0:
            print(colored("Price Diff: ", "red"), entry_price, " - ", book_price, " = ", colored(str(diff), "red"))
            stop = 0
            if my_position_qty == 0:
                closed_order = closed_orders()
                closed_order_price = closed_order[0]["price"]
                loss = entry_price - closed_order_price
                print("")
                print(colored("Stop Loss", "red"), "Loss:", loss)
                cancel_orders()
                status = "return"
                break
            if diff >= stop:
                if order_list_size != 0:
                    change_close()
                    time.sleep(5)
            time.sleep(5)
        elif diff < 0:
            print(colored("Price Diff: ", "green"), entry_price, " - ", book_price, " = ", colored(str(diff), "green"))
            time.sleep(5)
            if my_position_qty == 0:
                print("")
                closed_order = closed_orders()
                closed_order_price = closed_order[0]["price"]
                profit = entry_price - closed_order_price
                print(colored("Take Profit", "green"), "Profit:", profit)
                cancel_orders()
                status = "return"
                break
        else:
            print("Price Diff: ", entry_price, " - ", book_price, " = ", diff)
            time.sleep(5)
    if status == "success":
        cancel_orders()
        close_position()
    else:
        pass


def orders_long(my_size):
    profit = 0.5
    position_list = position()
    my_position_qty = position_list[0]["currentQty"]
    entry_price = position_list[0]["avgEntryPrice"]
    while True:
        print("")
        print(colored("orders_long", "green"))
        print(entry_price)

        current_time = datetime.datetime.now()
        print(current_time)

        my_ordType = "Limit"
        my_symbol = "XBTUSD"
        my_execInst = 'ParticipateDoNotInitiate'
        my_size = my_position_qty * (-1)
        # my_close = entry_price * 1.0005
        # my_close = round(my_close*2)/2
        my_close = entry_price + profit
        market = book()
        short_price = market[0]

        if short_price > my_close:
            my_close = short_price

        try:
            my_order = client.Order.Order_new(ordType=my_ordType, symbol=my_symbol, orderQty=my_size, price=my_close,
                                              execInst=my_execInst).result()

            my_order_id = my_order[0]["orderID"]
            my_order_status = my_order[0]["ordStatus"]
            print("order id: ", my_order_id)
            print("order status: ", my_order_status)
            if my_order_status == "New" or my_order_status == "Filled":
                print(colored("Close order submitted", "green"))
                status = "success"
                break
            elif my_order_status == "Canceled":
                del my_order
                del my_order_id
                del my_order_status
                print(colored("Post Only...", "red"))
                time.sleep(5)
        except Exception as e:
            print("Error")
            print(e)
            status = "return"
            break
    if status == "success":
        time.sleep(5)
        test_long(my_size)
    else:
        pass


def orders_short(my_size):
    profit = 0.5
    position_list = position()
    my_position_qty = position_list[0]["currentQty"]
    entry_price = position_list[0]["avgEntryPrice"]
    while True:
        print("")
        print(colored("orders short", "red"))
        print(entry_price)

        current_time = datetime.datetime.now()
        print(current_time)

        my_ordType = "Limit"
        my_symbol = "XBTUSD"
        my_execInst = 'ParticipateDoNotInitiate'
        my_size = my_position_qty * (-1)
        # my_close = entry_price * 0.9995
        # my_close = round(my_close*2)/2
        my_close = entry_price - profit
        market = book()
        short_price = market[1]

        if short_price < my_close:
            my_close = short_price

        try:
            my_order = client.Order.Order_new(ordType=my_ordType, symbol=my_symbol, orderQty=my_size, price=my_close,
                                              execInst=my_execInst).result()
            my_order_id = my_order[0]["orderID"]
            my_order_status = my_order[0]["ordStatus"]
            print("order id: ", my_order_id)
            print("order status: ", my_order_status)
            if my_order_status == "New" or my_order_status == "Filled":
                print(colored("Close order submitted", "green"))
                status = "success"
                break
            elif my_order_status == "Canceled":
                del my_order
                del my_order_id
                del my_order_status
                print(colored("Post Only...", "red"))
                time.sleep(5)
        except Exception as e:
            print("Error")
            print(e)
            status = "return"
            break
    if status == "success":
        time.sleep(5)
        test_short(my_size)
    else:
        pass


def watch_position(my_size):
    while True:
        print("")
        print("Watching")
        order_list = orders()
        list_size = len(order_list)
        if list_size == 0:
            status = "success"
            break
        side = order_list[0]["side"]
        if side == "Buy":
            print("Side: ", colored(side, "green"))

            last_order = order_list[0]
            last_order_price = last_order["price"]

            market = book()
            my_open = market[1]
            if last_order_price != my_open:
                change_close()
                print("change open")

        if side == "Sell":
            print("Side: ", colored(side, "red"))

            last_order = order_list[0]
            last_order_price = last_order["price"]

            market = book()
            my_open = market[0]
            if last_order_price != my_open:
                change_close()

        rsi_value = get_rsi()
        print("RSI_value: ", rsi_value)

        if side == "Buy" and rsi_value > 35:
            print(colored("Cancel long", "red"))
            cancel_orders()
            status = "return"
            break
        elif side == "Sell" and rsi_value < 65:
            print(colored("Cancel short", "red"))
            cancel_orders()
            status = "return"
            break
        time.sleep(10)
    if status == "success":
        position_list = position()
        my_position_qty = position_list[0]["currentQty"]
        if my_position_qty < 0:
            orders_short(my_size)
        elif my_position_qty > 0:
            orders_long(my_size)
    else:
        pass


def go_short(my_size):
    while True:
        print("")
        print(colored("going_short", "red"))
        current_time = datetime.datetime.now()
        print(current_time)

        my_ord_type = "Limit"
        my_symbol = "XBTUSD"
        my_exec_inst = 'ParticipateDoNotInitiate'
        my_size = my_size * (-1)
        market = book()
        my_open = market[0]
        print(my_open)
        try:
            my_order = client.Order.Order_new(ordType=my_ord_type, symbol=my_symbol, orderQty=my_size, price=my_open,
                                              execInst=my_exec_inst).result()
            my_order_id = my_order[0]["orderID"]
            my_order_status = my_order[0]["ordStatus"]
            print("order id: ", my_order_id)
            print("order status: ", my_order_status)
            if my_order_status == "New" or my_order_status == "Filled":
                print(colored("Close order submitted", "green"))
                status = "success"
                break
            elif my_order_status == "Canceled":
                del my_order
                del my_order_id
                del my_order_status
                del market
                del my_open
                print(colored("Post Only...", "red"))
                rsi_value = get_rsi()
                print("RSI value: ", rsi_value)
                if rsi_value < 70:
                    print(colored("RSI cancel", "red"))
                    status = "return"
                    break
                time.sleep(5)
        except Exception as e:
            print("Error")
            print(e)
            status = "return"
            break
    if status == "success":
        watch_position(my_size)
    else:
        pass


def go_long(my_size):
    while True:
        print("")
        print(colored("going_long", "green"))
        current_time = datetime.datetime.now()
        print(current_time)

        my_ord_type = "Limit"
        my_symbol = "XBTUSD"
        my_exec_inst = 'ParticipateDoNotInitiate'
        my_size = my_size
        market = book()
        my_open = market[1]
        print(my_open)
        try:
            my_order = client.Order.Order_new(ordType=my_ord_type, symbol=my_symbol, orderQty=my_size, price=my_open,
                                              execInst=my_exec_inst).result()
            my_order_id = my_order[0]["orderID"]
            my_order_status = my_order[0]["ordStatus"]
            print("order id: ", my_order_id)
            print("order status: ", my_order_status)
            if my_order_status == "New" or my_order_status == "Filled":
                print(colored("Close order submitted", "green"))
                status = "success"
                break
            elif my_order_status == "Canceled":
                del my_order
                del my_order_id
                del my_order_status
                del market
                del my_open
                print(colored("Post Only...", "red"))
                rsi_value = get_rsi()
                print("RSI value: ", rsi_value)
                if rsi_value > 30:
                    print(colored("RSI cancel", "red"))
                    status = "return"
                    break
                time.sleep(5)
        except Exception as e:
            print("Error")
            print(e)
            status = "return"
            break
    if status == "success":
        watch_position(my_size)
    else:
        pass


def place_order(my_size):
    while True:
        print("")
        rsi_value = get_rsi()
        print("RSI value: ", rsi_value)
        if rsi_value >= 70 or rsi_value <= 30:
            break
        else:
            print("")
            print("W8 4 RSI")
            current_time = datetime.datetime.now()
            seconds = current_time.second
            diff = 60 - seconds
            print("Czekaj ", diff + 20, "sekund")
            time.sleep(diff + 20)
    if rsi_value >= 70:
        go_short(my_size)
    elif rsi_value <= 30:
        go_long(my_size)


def start(my_size):
    profit = 0.5
    while True:
        order_list = orders()
        order_list_size = len(order_list)

        position_list = position()
        my_position_qty = position_list[0]["currentQty"]
        entry_price = position_list[0]["avgEntryPrice"]

        print("")
        print("Order: ", order_list_size)
        print("Qty: ", my_position_qty)

        if my_position_qty >= 60 or my_position_qty <= -60 or order_list_size >= 2:
            print("")
            print(colored("Co jest  xD", "red"))
            exit()

        if my_position_qty == 0 and order_list_size == 0:
            print("")
            print("Brak pozycji i zleceń")
            place_order(my_size)

        elif my_position_qty == 0 and order_list_size == 1:
            print("")
            print("Brak pozycji")
            watch_position(my_size)

        elif my_position_qty != 0 and order_list_size == 0:
            print("")
            print("Brak zleceń")
            if my_position_qty > 0:
                orders_long(my_size)
            elif my_position_qty < 0:
                orders_short(my_size)
        elif my_position_qty != 0 and order_list_size != 0:
            print("")
            print("Wszystko jest")
            if my_position_qty > 0:
                test_long(my_size)
            elif my_position_qty < 0:
                test_short(my_size)
        else:
            print("")
            print(colored("Co jest  xD!", "red"))
            exit()
        time.sleep(10)


start(my_size)
