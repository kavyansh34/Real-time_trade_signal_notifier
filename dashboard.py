import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path

# --- Imports ---
import config  # Your new config file
from binance.client import Client
from binance.exceptions import BinanceAPIException
import plotly.graph_objects as go
# --------------------


# --- Page Configuration ---
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide"
)

# --- File Paths ---
STATUS_FILE = Path("bot_status.json")
TRADES_FILE = Path("trade_log.csv")
ALERTS_FILE = Path("alert.csv")

# --- Binance Client for Dashboard ---
try:
    client = Client(config.API_KEY, config.API_SECRET)
    client.ping() # Test connection
    st.session_state.binance_client_ready = True
except Exception as e:
    st.error(f"Failed to connect to Binance. API keys may be wrong. Error: {e}")
    st.session_state.binance_client_ready = False


# --- (NEW) Data Function for Ticker Bar ---
@st.cache_data(ttl=30) # Cache for 30 seconds
def fetch_ticker_data(symbols):
    """Fetches 24hr ticker data for a list of symbols."""
    if not st.session_state.binance_client_ready:
        return []
    
    ticker_data = []
    for symbol in symbols:
        try:
            data = client.get_ticker(symbol=symbol)
            ticker_data.append(data)
        except BinanceAPIException as e:
            st.error(f"Error fetching {symbol}: {e.message}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            
    return ticker_data

# --- (NEW) UI Function for Ticker Bar ---
def create_ticker_bar(ticker_data):
    """Creates the metric columns for the price bar."""
    if not ticker_data:
        st.warning("Could not fetch price bar data.")
        return

    cols = st.columns(len(ticker_data))
    
    for i, data in enumerate(ticker_data):
        with cols[i]:
            # Extract price and 24h change
            price = float(data.get('lastPrice', 0))
            change_pct = float(data.get('priceChangePercent', 0))
            
            # Format delta for st.metric
            delta = f"{change_pct:.2f}%"
            
            # Display the metric
            st.metric(
                label=data['symbol'],
                value=f"${price:,.2f}", # Format price with 2 decimal places
                delta=delta
            )

# --- Charting Functions ---
@st.cache_data(ttl=60)
def fetch_chart_data(symbol, interval, limit):
    """Fetches kline data from Binance for the chart."""
    if not st.session_state.binance_client_ready:
        return pd.DataFrame() 
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=['time','open','high','low','close','volume',' ',' ',' ',' ',' ',' '])
        df = df[['time', 'open', 'high', 'low', 'close']]
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col])
        return df
    except Exception as e:
        st.error(f"Error fetching chart data: {e}")
        return pd.DataFrame()

def create_price_chart(df):
    """Creates a Plotly candlestick chart."""
    if df.empty:
        return go.Figure().update_layout(title="No chart data loaded")
        
    fig = go.Figure(data=[go.Candlestick(
        x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=config.SYMBOL
    )])
    fig.update_layout(
        title=f"{config.SYMBOL} 5-Minute Chart",
        xaxis_title=None, yaxis_title="Price (USDT)",
        xaxis_rangeslider_visible=False, height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# --- Data Loading Functions ---
def load_status_data():
    """Loads the bot_status.json file."""
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "Bot status file not found. Is the bot running?"}
    except json.JSONDecodeError:
        return {"error": "Bot status file is loading. Please wait."}
    except Exception as e:
        return {"error": f"Error loading status: {e}"}

def load_trade_log():
    """Loads the trade_log.csv file."""
    if not TRADES_FILE.exists(): return None
    try:
        df = pd.read_csv(TRADES_FILE, skipinitialspace=True)
        return df.sort_values(by="Exit Time", ascending=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading trade log: {e}")
        return None

def load_alerts(num_lines=20):
    """Loads the last N lines from the alerts.log file."""
    if not ALERTS_FILE.exists():
        return "No alerts found. (alert.csv missing)"
    try:
        with open(ALERTS_FILE, "r") as f:
            lines = f.readlines()
            last_lines = lines[-num_lines:]
            last_lines.reverse()
            return "".join(last_lines)
    except Exception as e:
        return f"Error loading alerts: {e}"

# --- ================================== ---
# ---       MAIN DASHBOARD LAYOUT        ---
# --- ================================== ---

# --- (NEW) Section 0: Price Ticker Bar ---
# Fetches data and builds the top bar

st.title("🤖 Live Trading Bot Dashboard")
st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
ticker_data = fetch_ticker_data(config.TICKER_ASSETS)
create_ticker_bar(ticker_data)
st.divider() # Add a line below the bar
# --- (END NEW SECTION) ---


# --- Section 1: Status and Chart ---
col_status, col_chart = st.columns([1, 1])

with col_status:
    st.header("📈 Current Trade")
    status_data = load_status_data()

    if "error" in status_data:
        st.warning(status_data["error"])
    else:
        active_trade = status_data.get("active_trade")
        
        if active_trade:
            pnl = status_data.get("current_pnl", 0)
            pnl_color = "normal" if pnl == 0 else ("inverse" if pnl < 0 else "normal")
            
            if active_trade.lower() == 'buy':
                st.success(f"## LONG: {active_trade.upper()}")
            else:
                st.error(f"## SHORT: {active_trade.upper()}")
            
            st.metric(label="Current P&L ($)", value=f"{pnl:,.2f}", delta_color=pnl_color)
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric(label="Entry Price", value=f"${status_data.get('entry_price', 0):,.2f}")
                st.metric(label="Take Profit", value=f"${status_data.get('take_profit', 0):,.2f}")
            with c2:
                st.metric(label="Current Price", value=f"${status_data.get('current_price', 0):,.2f}")
                st.metric(label="Stop Loss", value=f"${status_data.get('stop_loss', 0):,.2f}")
        
        else:
            st.info("No active trade. Waiting for signal...")

        st.caption(f"15m Momentum: **{status_data.get('momentum', 'N/A')}**")

with col_chart:
    st.header("📊 Live Price")
    chart_df = fetch_chart_data(config.SYMBOL, Client.KLINE_INTERVAL_5MINUTE, 120)
    fig = create_price_chart(chart_df)
    st.plotly_chart(fig, width='content')


st.divider()

# --- Section 2: Logs and History ---
col_alerts, col_history = st.columns([1, 2])

with col_alerts:
    st.subheader("🔔 Recent Alerts")
    alerts_text = load_alerts()
    st.text_area("Latest 20 alerts (newest first):", alerts_text, height=400)

with col_history:
    st.subheader("📚 Trade History")
    trades_df = load_trade_log()
    
    if trades_df is None:
        st.warning("trade_log.csv not found.")
    elif trades_df.empty:
        st.info("No completed trades yet.")
    else:
        total_pnl = trades_df["PnL"].sum()
        total_trades = len(trades_df)
        wins = trades_df[trades_df["PnL"] > 0]
        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Total PnL", f"${total_pnl:,.2f}")
        metric_col2.metric("Total Trades", total_trades)
        metric_col3.metric("Win Rate", f"{win_rate:.1f}%")
        
        st.dataframe(trades_df, use_container_width=True)

# --- Auto-refresh logic ---
time.sleep(2) 
st.rerun()
