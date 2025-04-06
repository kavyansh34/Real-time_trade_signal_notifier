#hello everyone
# add all the librariws we need 
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta.momentum
import ta.trend
import requests
from datetime import datetime
from datetime import timezone
import os

BOT_TOKEN ="YOUR BOT TOKEN"
CHAT_ID = "YOUR CHAT ID" # telegraM 

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
API_KEY = 'YOUR API KEY'
API_SECRET ='YOUR API SECRET'

def wait_for_candle_close():
    while True:
        now = datetime.now(timezone.utc)
        seconds = now.second  # Current seconds value

        if seconds == 59:  # Wait until the last second of the candle
            time.sleep(1)  # Give some buffer time for data update
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
curr_trade = {}
def log_trade_entry(action, price, quantity, tp, sl):
    global curr_trade
    curr_trade = {
        "Action": action.capitalize(),
        "Entry Price": round(price, 2),
        "Quantity": quantity,
        "TP": tp,
        "SL": sl
    }

def log_trade_exit(exit_price, action, entry_price, quantity):
    global curr_trade
    pnl = (exit_price - entry_price) * quantity if action == "buy" else (entry_price - exit_price) * quantity
    exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    curr_trade.update({
        "Exit Price": round(exit_price, 2),
        "PnL": round(pnl, 2),
        "Exit Time": exit_time
    })

    fieldnames = ["Action", "Entry Price", "Quantity", "TP", "SL", "Exit Price", "PnL", "Exit Time"]
    file_exists = os.path.isfile("trade_log.csv")

    with open("trade_log.csv", mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(curr_trade)

    print("Trade logged:", curr_trade)
    curr_trade = {}  # Removing data to use it again
   

def get_historical_data(interval, limit = 50):
    
    # kline is term in binance for historical data measures
    klines = client.get_klines(symbol="BTCUSDT", interval= interval, limit=limit)
    df = pd.DataFrame(klines, columns=['time','open','high','low','close','volume',' ',' ',' ',' ',' ',' '])
    #type conversion as we are getting data as string but need flaott for calculation
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df


#automating trade selection
import time 
Momentum = None
trade_frequency = 57 # i used 57 instead of 59 otherwise it miss the data at HH:MM:00
last_momentum =  None
last_15m_candle_time = None

def check_trade_conditions():
    wait_for_candle_close()  # Wait for the candle to close before fetching data

    global SL, TP, active_trade, Momentum
    global last_momentum, last_15m_candle_time  

    df_1m = get_historical_data(Client.KLINE_INTERVAL_1MINUTE)
    df_15m = get_historical_data(Client.KLINE_INTERVAL_15MINUTE)

    if df_1m is None or df_15m is None:
        return False

    # Get the last fully closed 15-minute candle
    last_closed_15m_time = df_15m['time'].iloc[-2]  # -2 ensures it's the last closed candle

    # Update momentum only at the close of a new 15-minute candle
    if last_closed_15m_time != last_15m_candle_time:
        last_15m_candle_time = last_closed_15m_time  # Update last checked time
        
        df_15m['EMA_7'] = ta.trend.ema_indicator(df_15m['close'], window=7) # Using 15 min EMA to identify long-term trend
        df_15m['EMA_25'] = ta.trend.ema_indicator(df_15m['close'], window=25)
       

        # Calculate momentum based on the last closed 15m candle
        latest_15m_ema7 = df_15m['EMA_7'].iloc[-2]  
        latest_15m_ema25 = df_15m['EMA_25'].iloc[-2]  

        if latest_15m_ema7 > latest_15m_ema25:
            last_momentum = "bullish"  # Only take SELL trades
        else:                           
            last_momentum = "bearish"  # Only take BUY trades and the twist is --- ACTUALLY WE CAPTURE BIG MOVE AT TIME OF CHANGING TREND

    # Keep using last detected momentum until a new 15m candle closes
    Momentum = last_momentum
    
    #implementing rsi and ema 21 to filter the trend
    df_1m['EMA_25'] = ta.trend.ema_indicator(df_1m['close'], window=25)
    df_1m['EMA_7'] = ta.trend.ema_indicator(df_1m['close'], window= 7)
    df_1m['RSI'] = ta.momentum.rsi(df_1m['close'], window=14)
    #df_1m['volumeMA'] = ta.trend.ema_indicator(df_1m['volume'],window= 14)   #Using volume EMA to refine the trades
    
    
    curr_price = df_1m['close'].iloc[-1].astype(float)
    curr_low =df_1m['low'].iloc[-1].astype(float)
    curr_high = df_1m['high'].iloc[-1].astype(float)
    previous_low = df_1m['low'].iloc[-2].astype(float)
    previous_high = df_1m['high'].iloc[-2].astype(float)
    curr_ema = df_1m['EMA_25'].iloc[-2].astype(float)
    curr_ema7 = df_1m['EMA_7'].iloc[-2].astype(float)
    curr_rsi = df_1m['RSI'].iloc[-1].astype(float)
    curr_volume = df_1m['volume'].iloc[-1].astype(float)
    #curr_volumeMA = df_1m['volumeMA'].iloc[-1].astype(float)

    print(f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Price: {curr_price}, EMA 25: {curr_ema},EMA_7 :{curr_ema7} Rsi: {curr_rsi} Momentum : {Momentum}" )

    if active_trade:
        if (active_trade == 'buy' and curr_high >= TP) or (active_trade == 'sell' and curr_low <= TP):
            print("🎯 Take Profit Hit! Closing trade.")
            send_telegram_message(f"🎯 TP Hit ho gaya at {TP}!")
            log_trade_exit(TP)
            active_trade = None  # Reset trade state
        elif (active_trade == 'buy' and curr_low <= SL) or (active_trade == 'sell' and curr_high >=SL):
            print("❌ Stop Loss Hit! Closing trade.")
            send_telegram_message(f"❌ Stop Loss Hit at {SL}!")
            log_trade_exit(SL)
            active_trade = None  
        return  # Skip new trades if one is active

    
    if Momentum =='bearish' and curr_price > curr_ema and curr_ema7 < curr_ema and previous_low < curr_ema and active_trade == None: #and curr_volume > curr_volumeMA :
        order_type = 'buy'
        print('buying now')
        SL= curr_low
        TP= curr_price + (curr_price - SL)*3 # RISK: REWARD = 1:3
        log_trade_entry("buy", curr_price, quantity)
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

    elif Momentum == 'bullish' and curr_price < curr_ema and curr_ema7 > curr_ema and curr_high > curr_ema  and  active_trade == None: # and curr_volume> curr_volumeMA :
        order_type = 'sell'
        print('selling now')
        SL= curr_high     
        TP= curr_price - ( SL - curr_price )*3
        log_trade_entry("sell", curr_price, quantity)
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
  
  
