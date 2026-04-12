import os
import time
import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

TICKERS = ["BBCA.JK", "TLKM.JK", "GOTO.JK", "AAPL", "NVDA"]

# ==============================
# TELEGRAM
# ==============================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# ==============================
# AI REASON
# ==============================
def ai_reason(df):
    try:
        last5 = df.tail(5)[["Open","High","Low","Close"]]

        text = ""
        for i,row in last5.iterrows():
            text += f"{i.date()} O:{row['Open']:.2f} H:{row['High']:.2f} L:{row['Low']:.2f} C:{row['Close']:.2f}\n"

        prompt = f"""
Anda adalah analis teknikal profesional.
Berikan 1 kalimat analisis tajam, singkat, trading-oriented.

Data:
{text}
"""

        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=50,
            temperature=0.7
        )

        return res.choices[0].message.content.strip()

    except Exception as e:
        print("[AI ERROR]", e)
        return "AI unavailable"

# ==============================
# ANALYSIS CORE
# ==============================
def analyze(ticker):
    try:
        df = yf.download(ticker, period="90d", progress=False)

        if df.empty:
            return None

        # INDICATORS
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df["EMA5"] = ta.ema(df["Close"], length=5)
        df["EMA20"] = ta.ema(df["Close"], length=20)
        df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=14)

        bb = ta.bbands(df["Close"])
        df["BBU"] = bb["BBU_20_2.0"]
        df["BBL"] = bb["BBL_20_2.0"]

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price = last["Close"]
        change = ((price - prev["Close"]) / prev["Close"]) * 100

        rsi = last["RSI"]
        ema5 = last["EMA5"]
        ema20 = last["EMA20"]
        atr = last["ATR"]

        support = df["Low"].tail(7).min()
        resistance = df["High"].tail(7).max()

        # ==============================
        # SCORING SYSTEM
        # ==============================
        score = 0
        reasons = []

        if rsi < 40:
            score += 2
            reasons.append("RSI low")

        if rsi > 70:
            score -= 2
            reasons.append("RSI high")

        if ema5 > ema20:
            score += 2
            reasons.append("Uptrend")

        if prev["EMA5"] < prev["EMA20"] and ema5 > ema20:
            score += 3
            reasons.append("Golden Cross")

        if price < last["BBL"]:
            score += 1
            reasons.append("Lower BB")

        if price > last["BBU"]:
            score -= 2
            reasons.append("Upper BB")

        # ==============================
        # SIGNAL
        # ==============================
        if score >= 4:
            signal = "BUY"
            emoji = "🔵"
        elif score <= -2:
            signal = "SELL/TP"
            emoji = "🔴"
        else:
            signal = "WAIT"
            emoji = "🟡"

        confidence = min(max((score + 5) * 10, 0), 100)

        # ==============================
        # RISK MANAGEMENT
        # ==============================
        entry = support
        stoploss = support - atr
        takeprofit = resistance

        # ==============================
        # AI
        # ==============================
        ai = ai_reason(df)

        return {
            "ticker": ticker,
            "emoji": emoji,
            "signal": signal,
            "price": price,
            "change": change,
            "entry": entry,
            "sl": stoploss,
            "tp": takeprofit,
            "confidence": confidence,
            "reason": ", ".join(reasons),
            "ai": ai
        }

    except Exception as e:
        print(f"[ERROR {ticker}]", e)
        return None

# ==============================
# MAIN
# ==============================
def main():
    today = datetime.now().strftime("%d-%m-%Y")

    msg = f"📊 *MORNING SIGNAL PRO {today}*\n"
    msg += "--------------------------------\n"

    for t in TICKERS:
        data = analyze(t)
        time.sleep(1)

        if not data:
            continue

        # FILTER SINYAL KUAT
        if data["confidence"] < 50:
            continue

        msg += (
            f"{data['emoji']} *{data['ticker']}*: {data['signal']} ({data['confidence']}%)\n"
            f"Price: {data['price']:.2f} ({data['change']:.2f}%)\n"
            f"Entry: {data['entry']:.2f}\n"
            f"SL: {data['sl']:.2f} | TP: {data['tp']:.2f}\n"
            f"Reason: {data['reason']}\n"
            f"AI: {data['ai']}\n\n"
        )

    send_telegram(msg)


if __name__ == "__main__":
    main()