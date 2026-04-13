import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

# Load ENV
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

TICKERS = ["BBCA.JK", "TLKM.JK", "GOTO.JK", "AAPL", "NVDA"]


def flatten_columns(df):
    """
    Ratakan kolom MultiIndex dari yfinance menjadi 1 level.
    Karena download dilakukan per ticker, level kedua biasanya hanya nama ticker.
    """
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df


def get_series(df, col_name):
    """
    Ambil kolom sebagai Series 1D yang bersih.
    Aman jika ternyata kolom duplikat / hasil select masih DataFrame.
    """
    if col_name not in df.columns:
        raise KeyError(f"Kolom '{col_name}' tidak ditemukan. Kolom tersedia: {list(df.columns)}")

    col = df[col_name]

    # Jika masih DataFrame (mis. karena duplicate column), ambil kolom terakhir
    if isinstance(col, pd.DataFrame):
        col = col.iloc[:, -1]

    return pd.to_numeric(col, errors="coerce")


def get_last_scalar(df, col_name):
    """
    Ambil nilai terakhir sebagai float scalar.
    """
    s = get_series(df, col_name).dropna()
    if s.empty:
        raise ValueError(f"Kolom '{col_name}' tidak memiliki nilai valid.")
    return float(s.iloc[-1])


def get_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        df = flatten_columns(df).copy()

        # Ambil hanya kolom penting bila tersedia
        needed_cols = ["Open", "High", "Low", "Close", "Volume"]
        available_cols = [c for c in needed_cols if c in df.columns]
        df = df[available_cols].copy()

        # Pastikan numerik
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["Open", "High", "Low", "Close"])

        if df.empty:
            return None

        return df

    except Exception as e:
        print(f"Error fetch {ticker}: {e}")
        return None


def analyze(df):
    df = df.copy()

    close = get_series(df, "Close")
    high = get_series(df, "High")
    low = get_series(df, "Low")

    # RSI
    df["RSI"] = RSIIndicator(close=close, window=14).rsi()

    # EMA
    df["EMA5"] = EMAIndicator(close=close, window=5).ema_indicator()
    df["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()

    # Bollinger Bands
    bb = BollingerBands(close=close, window=20)
    df["BBU"] = bb.bollinger_hband()
    df["BBL"] = bb.bollinger_lband()

    # Buang baris yang indikatornya belum terbentuk
    df = df.dropna(subset=["RSI", "EMA5", "EMA20", "BBU", "BBL"])

    return df


def decision(df):
    rsi = get_last_scalar(df, "RSI")
    price = get_last_scalar(df, "Close")
    ema5 = get_last_scalar(df, "EMA5")
    ema20 = get_last_scalar(df, "EMA20")
    bbu = get_last_scalar(df, "BBU")
    bbl = get_last_scalar(df, "BBL")

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
    low = get_series(df, "Low").tail(7)
    high = get_series(df, "High").tail(7)

    support = float(low.min())
    resistance = float(high.max())
    return support, resistance


def ai_reason(df):
    try:
        last5 = df[["Open", "High", "Low", "Close"]].tail(5).copy()
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
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print("Telegram error:", e)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    final_message = f"📊 MORNING SIGNAL {today}\n--------------------------\n"

    for ticker in TICKERS:
        try:
            df = get_data(ticker)
            if df is None or df.empty:
                print(f"Skip {ticker}: data kosong")
                continue

            df = analyze(df)
            if df is None or df.empty or len(df) < 2:
                print(f"Skip {ticker}: data indikator belum cukup")
                continue

            signal, emoji, reason = decision(df)
            support, resistance = support_resistance(df)

            close_series = get_series(df, "Close").dropna()
            if len(close_series) < 2:
                print(f"Skip {ticker}: close data kurang dari 2 baris")
                continue

            last_price = float(close_series.iloc[-1])
            prev_price = float(close_series.iloc[-2])

            if prev_price == 0:
                change = 0.0
            else:
                change = ((last_price - prev_price) / prev_price) * 100

            ai_text = ai_reason(df)

            message = f"""
{ticker}: {emoji} {signal}
Price: {last_price:.2f} ({change:.2f}%)
Area: {support:.2f} - {resistance:.2f}
Reason: {ai_text}
"""
            final_message += message + "\n"

        except Exception as e:
            print(f"Error process {ticker}: {e}")
            continue

    send_telegram(final_message)


if __name__ == "__main__":
    main()