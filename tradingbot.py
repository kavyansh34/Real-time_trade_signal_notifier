#hello everyone
# add all the libraries we need 
import config
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta.momentum
import ta.trend
import requests
from datetime import datetime
from datetime import timezone
import os
import json
import time # <-- Added this import
import pandas as pd
import ta
import csv

BOT_TOKEN =config.BOT_TOKEN 
CHAT_ID = config.CHAT_ID 

symbol = config.SYMBOL 
quantity = None 

initial_capital = 10000
capital = 10000
Risk_percnt_per_trade = 1

active_trade = None # using this as a flag 
SL = None
TP = None
entry_price = None # Ensure entry_price is global

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
API_KEY = config.API_KEY 
API_SECRET =config.API_SECRET 
def wait_for_candle_close():
    # Fixed indentation errors from copy-paste
    while True:
        now = datetime.now(timezone.utc)
        seconds = now.second  # Current seconds value

        if seconds == 59:  # Wait until the last second of the candle
            time.sleep(3)  # Give some buffer time for data update
            break
        
        time.sleep(0.5)  # Check every 0.5 sec

client = Client(API_KEY, API_SECRET)
# fetching account balance
try:
    account_info = client.get_account()
    print("Account info fetched successfully.")
    # print(account_info) # Optional: uncomment to see full details
except BinanceAPIException as e:
    print(f"Error fetching account info: {e}")
    # Handle error appropriately, maybe exit
except requests.exceptions.RequestException as e:
    print(f"Network error fetching account info: {e}")


# maintaining journal of trades by using file management
curr_trade = {}
def log_trade_entry(action, price, qty, tp_val, sl_val):
    global curr_trade
    curr_trade = {
        "Action": action.capitalize(),
        "Entry Price": round(price, 2),
        "Quantity": qty,
        "TP": tp_val,
        "SL": sl_val
    }

def log_trade_exit(exit_price, action, entry_pr, qty):
    global curr_trade
    pnl = (exit_price - entry_pr) * qty if action == "buy" else (entry_pr - exit_price) * qty
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
    try:
        # kline is term in binance for historical data measures
        klines = client.get_klines(symbol="BTCUSDT", interval= interval, limit=limit)
        df = pd.DataFrame(klines, columns=['time','open','high','low','close','volume',' ',' ',' ',' ',' ',' '])
        #type conversion as we are getting data as string but need flaott for calculation
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        df['time'] = pd.to_datetime(df['time'], unit='ms') # Convert timestamp
        return df
    except BinanceAPIException as e:
        print(f"Error fetching klines: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching klines: {e}")
        return None


#automating trade selection
Momentum = None
trade_frequency = 57 # i used 57 instead of 59 otherwise it miss the data at HH:MM:00
last_momentum =  None
last_15m_candle_time = None

def check_trade_conditions():
    # wait_for_candle_close()  # Wait for the candle to close before fetching data
    # Disabling wait_for_candle_close to allow loop to run every 'trade_frequency' seconds
    
    global SL, TP, active_trade, Momentum, entry_price, quantity
    global last_momentum, last_15m_candle_time  

    df_1m = get_historical_data(Client.KLINE_INTERVAL_1MINUTE)
    df_15m = get_historical_data(Client.KLINE_INTERVAL_15MINUTE)

    if df_1m is None or df_15m is None:
        print("Failed to get data, skipping check.")
        return False # Return False to sleep for 1 sec

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
            last_momentum = "bearish"  # Only take BUY trades

    # Keep using last detected momentum until a new 15m candle closes
    Momentum = last_momentum
    
    #implementing rsi and ema 21 to filter the trend
    df_1m['EMA_25'] = ta.trend.ema_indicator(df_1m['close'], window=25)
    df_1m['EMA_7'] = ta.trend.ema_indicator(df_1m['close'], window= 7)
    df_1m['RSI'] = ta.momentum.rsi(df_1m['close'], window=14)
    
    curr_price = df_1m['close'].iloc[-1]
    curr_low = df_1m['low'].iloc[-1]
    curr_high = df_1m['high'].iloc[-1]
    previous_low = df_1m['low'].iloc[-2]
    previous_high = df_1m['high'].iloc[-2]
    curr_ema = df_1m['EMA_25'].iloc[-2]
    curr_ema7 = df_1m['EMA_7'].iloc[-2]
    curr_rsi = df_1m['RSI'].iloc[-1]
    curr_volume = df_1m['volume'].iloc[-1]

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Price: {round(curr_price, 2)} | EMA 25: {round(curr_ema, 4)} | EMA_7 :{round(curr_ema7, 4)} | Rsi: {round(curr_rsi, 4)} | Momentum : {Momentum}" )
  
    if active_trade:
        if (active_trade == 'buy' and curr_high >= TP):  
            print("🎯 Take Profit Hit! Closing trade.")
            send_telegram_message(f"🎯 TP Hit ho gaya at {TP}!")
            log_trade_exit(TP, 'buy', entry_price , quantity)
            active_trade = None  # Reset trade state

        elif (active_trade == 'sell' and curr_low <= TP):
            print("🎯 Take Profit Hit! Closing trade.")
            send_telegram_message(f"🎯 TP Hit ho gaya at {TP}!")
            log_trade_exit(TP, 'sell', entry_price , quantity) # Fixed: was 'buy'
            active_trade = None  # Reset trade state

        elif (active_trade == 'buy' and curr_low <= SL): 
            print("❌ Stop Loss Hit! Closing trade.")
            send_telegram_message(f"❌ Stop Loss Hit at {SL}!")
            log_trade_exit(SL, 'buy', entry_price, quantity) # Fixed: was 'sell'
            active_trade = None  # Reset trade state

        elif (active_trade == 'sell' and curr_high >=SL):
            print("❌ Stop Loss Hit! Closing trade.")
            send_telegram_message(f"❌ Stop Loss Hit at {SL}!")
            log_trade_exit(SL, 'sell', entry_price, quantity)
            active_trade = None  # Reset trade state
        
        # This return was causing the status JSON to not be written when a trade was active
        # We will move it to the end of the 'if active_trade:' block
        pass # Allow code to continue to JSON status update

    
    # Only check for new trades if one is NOT active
    if active_trade is None:
        if Momentum =='bearish' and curr_price > curr_ema and curr_ema7 < curr_ema and previous_low < curr_ema: 
            order_type = 'buy'
            print('buying now')
            entry_price = curr_price
            SL = curr_low
            TP = curr_price + (curr_price - SL) * 3 # RISK: REWARD = 1:3
            # Ensure (curr_price - SL) is not zero to avoid ZeroDivisionError
            if (curr_price - SL) == 0:
                print("Skipping trade, zero risk (SL == entry)")
                return True # Skip to next cycle
            
            quantity = (Risk_percnt_per_trade / 100) * initial_capital / (curr_price - SL)
            log_trade_entry("buy", entry_price, quantity, TP, SL) 
            active_trade = order_type
            message =(
            f"🚀 *Trade Alert!* 🚀\n"
            f"🟢 {order_type.upper()} executed at: {curr_price}\n" 
            f"📉 Stoploss: {SL}\n"
            f"📈 Take Profit: {TP}\n"
            f"📊 Symbol: {symbol}\n"
            f"📦 Quantity: {quantity:.2f}\n" 
            )
            send_telegram_message(message)
            print("ALERT SENT")

        elif Momentum == 'bullish' and curr_price < curr_ema and curr_ema7 > curr_ema and curr_high > curr_ema: 
            order_type = 'sell'
            print('selling now')
            entry_price = curr_price
            SL = curr_high     
            TP = curr_price - (SL - curr_price) * 3
            # Ensure (SL - curr_price) is not zero
            if (SL - curr_price) == 0:
                print("Skipping trade, zero risk (SL == entry)")
                return True # Skip to next cycle

            quantity = (Risk_percnt_per_trade / 100) * initial_capital / (SL - curr_price)
            log_trade_entry("sell", entry_price, quantity, TP, SL)
            active_trade = order_type
            message =(
            f"🚀 *Trade Alert!* 🚀\n"
            f"🔴 {order_type.upper()} executed at: {curr_price}\n"
            f"📉 Stoploss: {SL}\n"
            f"📈 Take Profit: {TP}\n"
            f"📊 Symbol: {symbol}\n"
            f"📦 Quantity: {quantity:.2f}\n"
            )
            send_telegram_message(message)
            print("ALERT SENT")

    # --- STATUS JSON WRITER ---
    # This block now runs on every check, whether a trade is active or not

    status_data = {
        "current_price": curr_price,
        "momentum": Momentum,
        "active_trade": active_trade,
        "entry_price": None,
        "stop_loss": None,
        "take_profit": None,
        "current_pnl": 0.0,
        "last_update": datetime.now().isoformat()
    }

    if active_trade:
        status_data["entry_price"] = entry_price
        status_data["stop_loss"] = SL
        status_data["take_profit"] = TP
        
        # Calculate live P&L
        if active_trade == 'buy':
            status_data["current_pnl"] = (curr_price - entry_price) * quantity
        elif active_trade == 'sell':
            status_data["current_pnl"] = (entry_price - curr_price) * quantity

    # Write status to a JSON file for the dashboard to read
    try:
        with open("bot_status.json", "w") as f:
            json.dump(status_data, f, indent=4)
    except Exception as e:
        print(f"Error writing status file: {e}")

    return True    

print("Bot starting... Waiting for first trade.")
while True:
    success = check_trade_conditions()
    if not success :
        print("Check failed, retrying in 1s...")
        time.sleep(1)
    else:    
        # Sleep for the defined frequency
        time.sleep(trade_frequency)
  

