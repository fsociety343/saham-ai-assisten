import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
from dotenv import load_dotenv
from openai import OpenAI

# Load ENV
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

TICKERS = ["BBCA.JK", "TLKM.JK", "GOTO.JK", "AAPL", "NVDA"]

def get_data(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        return df.dropna()
    except Exception as e:
        print(f"Error fetch {ticker}: {e}")
        return None

def analyze(df):
    # FIX: pastikan semua kolom jadi 1D Series
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()

    # RSI
    df["RSI"] = RSIIndicator(close, window=14).rsi()

    # EMA
    df["EMA5"] = EMAIndicator(close, window=5).ema_indicator()
    df["EMA20"] = EMAIndicator(close, window=20).ema_indicator()

    # Bollinger Bands
    bb = BollingerBands(close, window=20)
    df["BBU"] = bb.bollinger_hband()
    df["BBL"] = bb.bollinger_lband()

    return df

def decision(df):
    last = df.iloc[-1]

    rsi = last["RSI"]
    price = last["Close"]
    ema5 = last["EMA5"]
    ema20 = last["EMA20"]
    bbu = last["BBU"]
    bbl = last["BBL"]

    signal = "WAIT"
    emoji = "🟡"
    reason = "Konsolidasi / belum ada sinyal kuat"

    # BUY condition
    if (rsi < 40 and price > ema20) or (ema5 > ema20):
        signal = "BUY"
        emoji = "🔵"
        reason = "Momentum bullish awal"

    # SELL condition
    elif rsi > 70 or price > bbu:
        signal = "SELL"
        emoji = "🔴"
        reason = "Overbought / potensi koreksi"

    return signal, emoji, reason

def support_resistance(df):
    support = df["Low"].tail(7).min()
    resistance = df["High"].tail(7).max()
    return support, resistance

def ai_reason(df):
    try:
        last5 = df.tail(5)[["Open", "High", "Low", "Close"]]
        data_text = last5.to_string()

        prompt = f"""
Analisa data OHLC berikut dan berikan 1 kalimat tajam seperti analis profesional:

{data_text}

Contoh:
"Momentum bullish dengan tekanan beli meningkat setelah pullback minor"
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI error:", e)
        return "Analisa AI tidak tersedia"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram error:", e)

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    final_message = f"📊 MORNING SIGNAL {today}\n--------------------------\n"

    for ticker in TICKERS:
        df = get_data(ticker)
        if df is None or df.empty:
            continue

        df = analyze(df)

        signal, emoji, reason = decision(df)
        support, resistance = support_resistance(df)

        last_price = df["Close"].iloc[-1]
        prev_price = df["Close"].iloc[-2]
        change = ((last_price - prev_price) / prev_price) * 100

        ai_text = ai_reason(df)

        message = f"""
{ticker}: {emoji} {signal}
Price: {last_price:.2f} ({change:.2f}%)
Area: {support:.2f} - {resistance:.2f}
Reason: {ai_text}
"""
        final_message += message + "\n"

    send_telegram(final_message)

if __name__ == "__main__":
    main()
