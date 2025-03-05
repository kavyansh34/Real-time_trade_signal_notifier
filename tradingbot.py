#hello everyone
# add all the librariws we need 
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta.momentum
import ta.trend
import requests
from datetime import datetime
from datetime import timezone


BOT_TOKEN ="7788240253:AAEOasa3MkBWjFwwFdqekrymTdgK9V6eyes"
CHAT_ID = "5040555838" # telegram 

symbol = "BTC-USD"
quantity = 1

active_trade = None # using this as a flag 
SL = None
TP = None

# function that handles telegram message
def send_telegram_message(message):
    url =f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": message}

    response = requests.get(url,params= params)
    
    if response.status_code != 200 :
        print(f"Failed to send Telegram message: {response.text}")

    else :
        print("Telegram message sent successfully" )    

# my api credentials
API_KEY = 'ERcJWtNfoU4WP1UW2lpO8joLuJNSLFqLBo0zXDqm4Go1a7ujkSDOhwZFhUHWh4Ap'
API_SECRET ='2nzlI33MeyYU8YiGd7jKsF43XhetXbgbuAwwxDGt2J7HedsTM49l7E1gJL9Qpfx6'

#BASE_URL=  "https://api.delta.exchange"

#API_KEY = 'TaXg9Bd97yU3cqyV5W2rzwIzkV2W3l'
#API_SECRET = 'E9k6TkW4s2mmShwL5yDxakJvGBi7uXI54yFY3otxrgWcvIYPd4QyYfNb4WwE'

def wait_for_candle_close():
    while True:
        now = datetime.now(timezone.utc)
        seconds = now.second  # Current seconds value

        if seconds == 59:  # Wait until the last second of the candle
            time.sleep(1.5)  # Give some buffer time for data update
            break
        
        time.sleep(0.5)  # Check every 0.5 sec

client = Client(API_KEY, API_SECRET)
# fetching account balance
account_info = client.get_account()
print(account_info)

import pandas as pd
import numpy as np
import ta

# maintaining journal of trades by using file management
import csv
def log_trade(action, price, quantity):
    with open("trade_log.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, price, quantity, TP, SL ])
    print(f"logged trade: {action} at {price}")

def get_historical_data():
    
    # kline is term in binance for historical data measures
    klines = client.get_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_3MINUTE, limit=50)
    df = pd.DataFrame(klines, columns=['time','open','high','low','close','volume',' ',' ',' ',' ',' ',' '])
    #type conversion as we are getting data as string but need flaott for calculation
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    return df


#automating trade selection
import time

trade_frequency = 180
interval = Client.KLINE_INTERVAL_3MINUTE

def check_trade_conditions():
    wait_for_candle_close()  # Wait for the candle to close before fetching data

    global SL, TP, active_trade
    df = get_historical_data()
    if df is None:
        return False
    #implementing rsi and ema 21 to filter the trend
    df['EMA_25'] = ta.trend.ema_indicator(df['close'], window=25)
    df['EMA_7'] = ta.trend.ema_indicator(df['close'], window= 7)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    
    curr_price = df['close'].iloc[-1].astype(float)
    curr_low =df['low'].iloc[-1].astype(float)
    curr_high = df['high'].iloc[-1].astype(float)
    previous_low = df['low'].iloc[-2].astype(float)
    previous_high = df['high'].iloc[-2].astype(float)
    curr_ema = df['EMA_25'].iloc[-1].astype(float)
    curr_ema7 = df['EMA_7'].iloc[-1].astype(float)
    curr_rsi = df['RSI'].iloc[-1].astype(float)
    print(f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Price: {curr_price}, EMA 25: {curr_ema},EMA_7 :{curr_ema7} Rsi: {curr_rsi}")

    if active_trade:
        if (active_trade == 'buy' and curr_price >= TP) or (active_trade == 'sell' and curr_price <= TP):
            print("🎯 Take Profit Hit! Closing trade.")
            send_telegram_message(f"🎯 TP Hit ho gaya at {curr_price}!")
            active_trade = None  # Reset trade state
        elif (active_trade == 'buy' and curr_price <= SL) or (active_trade == 'sell' and curr_price >=SL):
            print("❌ Stop Loss Hit! Closing trade.")
            send_telegram_message(f"❌ Stop Loss Hit at {curr_price}!")
            active_trade = None  # Reset trade state
        return  # Skip new trades if one is active

    
    if curr_price > curr_ema and curr_ema7 < curr_ema and previous_low < curr_ema and active_trade == None:
        flag =1
        order_type = 'buy'
        print('buying now')
        SL= curr_low
        TP= curr_price + (curr_price - SL)*2
        log_trade("buy", curr_price, quantity)
        active_trade = order_type
        message =(
        f"🚀 *Trade Alert!* 🚀\n"
        f"🟢 {order_type.upper()} executed at: {curr_price}\n"
        f"📉 Stoploss: {SL}\n"
        f"📈 Take Profit: {TP}\n"
        f"📊 Symbol: {symbol}"
        )
        send_telegram_message(message)
        print("ALERT SENT")

    elif curr_price < curr_ema and curr_ema7 > curr_ema and curr_high > curr_ema and curr_rsi>= 45 and active_trade == None :
        flag =-1
        order_type = 'sell'
        print('selling now')
        SL= curr_high     
        TP= curr_price - ( SL - curr_price )*2
        log_trade("sell", curr_price, quantity)
        active_trade = order_type
        message =(
        f"🚀 *Trade Alert!* 🚀\n"
        f"🔴 {order_type.upper()} executed at: {curr_price}\n"
        f"📉 Stoploss: {SL}\n"
        f"📈 Take Profit: {TP}\n"
        f"📊 Symbol: {symbol}"
        )
        send_telegram_message(message)
        print("ALERT SENT")
    return True    

while True:
    success = check_trade_conditions()
    if not success :
        time.sleep(1)
    else:    
        time.sleep(trade_frequency)
  

#lets wait for trade now....
