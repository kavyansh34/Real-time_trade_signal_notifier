## Real-Time Smart Trade Signal Notifier
This is an trading notifier which is a impactful solution for traders saving their time and efforts. This indicator actually sends alerts when strategy gets activated in real time market with execution price, trading SL and TP, also saves them from FOMO and Burn-outs.

## 🚀 Features
- 📈 Monitors market conditions (e.g., price breakouts, EMA/RSI signals, etc.)
- 🔔 Sends real-time alerts via Telegram
- 📝 Logs trade alerts and signals
- ⏱️ Supports scheduled or interval-based checks
- 💡 Easy to customize for any asset, indicator, or logic
  
## NOTE
* Any strategy can be integrated with this Smart Trade Notifier as per the different trading style
* This strategy is applicable in volatile market and work when liquidity in pretty much good and it is tested on BITCOIN, TRUMP COIN and other meme coins as well on shorter time frame as well as bigger time frames.

## Implemented strategy  
I have analysed that the when EMA 7 is below the EMA 25 and and candle closes above the EMA 25, we can place a long trade with taking closing candle's low as SL and Risk to Reward ratio of 1:3. The condition is same with the short position. In short trades, EMA 7 must be above the EMA 25 and if candle closes below the EMA 25 the taking breaking candle's high as SL, we can trade a short position with 1:4 Risk to Reward ratio.

* Sample telegram alerts are available as 'image.png' in this repository.
* Sample trade based on strategy integrated in this code is mentioned as 'sample_trade.png'
* backtest result screenshot is avialable as 'ema_backtest4_1year.png' of past 1 year data 'BTCUSDT'
## Run 'tradingbot.py' to run the bot
# All the requirements are availaible in 'requirement.txt'.
