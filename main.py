import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands


# =========================
# LOAD ENV
# =========================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("CHAT_ID", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

UNIVERSE_FILE = os.getenv("UNIVERSE_FILE", "data/syariah_universe.csv")
YF_PERIOD = os.getenv("YF_PERIOD", "6mo")
YF_INTERVAL = os.getenv("YF_INTERVAL", "1d")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "25"))
BATCH_SLEEP_SECONDS = float(os.getenv("BATCH_SLEEP_SECONDS", "1.0"))

MAX_TOP_GLOBAL = int(os.getenv("MAX_TOP_GLOBAL", "20"))
MAX_PER_CATEGORY = int(os.getenv("MAX_PER_CATEGORY", "5"))
MIN_ROWS = int(os.getenv("MIN_ROWS", "40"))
MESSAGE_LIMIT = int(os.getenv("MESSAGE_LIMIT", "3900"))

ENABLE_AI = os.getenv("ENABLE_AI", "true").strip().lower() == "true"
AI_MAX_COUNT = int(os.getenv("AI_MAX_COUNT", "5"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

SEND_CSV_REPORT = os.getenv("SEND_CSV_REPORT", "false").strip().lower() == "true"

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# =========================
# BASIC UTILS
# =========================
def log(msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def chunk_list(items: List, size: int) -> List[List]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def normalize_ticker(code: str) -> str:
    code = str(code).strip().upper()
    if not code:
        return code
    if not code.endswith(".JK"):
        code = f"{code}.JK"
    return code


def normalize_category(raw: str) -> str:
    if raw is None:
        return "LAINNYA"

    text = str(raw).strip()
    if not text:
        return "LAINNYA"

    key = (
        text.upper()
        .replace("&", "AND")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )

    mapping = {
        "INFRA": "INFRASTRUKTUR",
        "INFRASTRUKTUR": "INFRASTRUKTUR",
        "OIL_GAS": "OIL & GAS",
        "OILANDGAS": "OIL & GAS",
        "MIGAS": "OIL & GAS",
        "BATUBARA": "BATUBARA",
        "COAL": "BATUBARA",
        "ENERGI": "ENERGI",
        "MINING": "PERTAMBANGAN",
        "PERTAMBANGAN": "PERTAMBANGAN",
        "TEKNOLOGI": "TEKNOLOGI",
        "INFOTECH": "TEKNOLOGI",
        "TELEKOMUNIKASI": "TELEKOMUNIKASI",
        "KONSUMER": "KONSUMER",
        "CONSUMER": "KONSUMER",
        "PROPERTI": "PROPERTI",
        "PROPERTY": "PROPERTI",
        "KESEHATAN": "KESEHATAN",
        "HEALTHCARE": "KESEHATAN",
        "TRANSPORTASI": "TRANSPORTASI",
        "LOGISTIK": "TRANSPORTASI",
        "INDUSTRI": "INDUSTRI",
        "MANUFAKTUR": "INDUSTRI",
        "PERDAGANGAN": "PERDAGANGAN",
        "RETAIL": "PERDAGANGAN",
        "KONSTRUKSI": "KONSTRUKSI",
        "BAHAN_BAKU": "BAHAN BAKU",
        "BASIC_MATERIALS": "BAHAN BAKU",
        "UTILITAS": "UTILITAS",
        "PARIWISATA": "PARIWISATA",
        "AGRI": "AGRI",
        "PERTANIAN": "AGRI",
        "PERIKANAN": "AGRI",
        "LAINNYA": "LAINNYA",
    }

    return mapping.get(key, text.upper())


# =========================
# LOAD UNIVERSE CSV
# =========================
def load_universe(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"File universe tidak ditemukan: {path}. "
            f"Buat CSV dengan kolom minimal: ticker,category"
        )

    df = pd.read_csv(path)

    if "ticker" not in df.columns:
        raise ValueError("Kolom 'ticker' wajib ada di file universe CSV")

    if "category" not in df.columns:
        df["category"] = "LAINNYA"

    if "name" not in df.columns:
        df["name"] = ""

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper().apply(normalize_ticker)
    df["category"] = df["category"].astype(str).apply(normalize_category)
    df["name"] = df["name"].fillna("").astype(str).str.strip()

    df = df[df["ticker"] != ""].copy()
    df = df.drop_duplicates(subset=["ticker"], keep="first").reset_index(drop=True)

    return df[["ticker", "name", "category"]].to_dict(orient="records")


# =========================
# YFINANCE HELPERS
# =========================
def clean_ohlcv_frame(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None

    work = df.copy()

    if isinstance(work.columns, pd.MultiIndex):
        work.columns = [c[-1] if isinstance(c, tuple) else c for c in work.columns]

    required = ["Open", "High", "Low", "Close"]
    available = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in work.columns]
    work = work[available].copy()

    for col in available:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.dropna(subset=required)

    if len(work) < MIN_ROWS:
        return None

    return work


def extract_ticker_frame(batch_df: pd.DataFrame, ticker: str, batch_size: int) -> Optional[pd.DataFrame]:
    if batch_df is None or batch_df.empty:
        return None

    if batch_size == 1 and not isinstance(batch_df.columns, pd.MultiIndex):
        return clean_ohlcv_frame(batch_df)

    if isinstance(batch_df.columns, pd.MultiIndex):
        lvl0 = batch_df.columns.get_level_values(0)
        lvl1 = batch_df.columns.get_level_values(1)

        if ticker in set(lvl0):
            sub = batch_df[ticker].copy()
            return clean_ohlcv_frame(sub)

        if ticker in set(lvl1):
            sub = batch_df.xs(ticker, axis=1, level=1).copy()
            return clean_ohlcv_frame(sub)

    return None


def download_batch(tickers: List[str]) -> Optional[pd.DataFrame]:
    try:
        data = yf.download(
            tickers=tickers,
            period=YF_PERIOD,
            interval=YF_INTERVAL,
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
        return data
    except Exception as e:
        log(f"Error download batch {tickers[:3]}...: {e}")
        return None


# =========================
# INDICATORS
# =========================
def get_series(df: pd.DataFrame, col_name: str) -> pd.Series:
    if col_name not in df.columns:
        raise KeyError(f"Kolom '{col_name}' tidak ditemukan")

    col = df[col_name]
    if isinstance(col, pd.DataFrame):
        col = col.iloc[:, -1]

    return pd.to_numeric(col, errors="coerce")


def get_last_scalar(df: pd.DataFrame, col_name: str) -> float:
    s = get_series(df, col_name).dropna()
    if s.empty:
        raise ValueError(f"Kolom '{col_name}' kosong")
    return float(s.iloc[-1])


def analyze(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None

    work = df.copy()

    close = get_series(work, "Close")
    volume = get_series(work, "Volume") if "Volume" in work.columns else pd.Series(index=work.index, dtype="float64")

    work["RSI"] = RSIIndicator(close=close, window=14).rsi()
    work["EMA5"] = EMAIndicator(close=close, window=5).ema_indicator()
    work["EMA20"] = EMAIndicator(close=close, window=20).ema_indicator()
    work["EMA50"] = EMAIndicator(close=close, window=50).ema_indicator()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    work["BBU"] = bb.bollinger_hband()
    work["BBL"] = bb.bollinger_lband()
    work["BBM"] = bb.bollinger_mavg()

    if not volume.empty:
        work["VOLMA20"] = volume.rolling(20).mean()
    else:
        work["VOLMA20"] = float("nan")

    work["RET1D"] = close.pct_change() * 100
    work["RET5D"] = close.pct_change(5) * 100

    work = work.dropna(subset=["RSI", "EMA5", "EMA20", "EMA50", "BBU", "BBL"])
    if work.empty or len(work) < 2:
        return None

    return work


# =========================
# SIGNAL ENGINE
# =========================
def support_resistance(df: pd.DataFrame) -> (float, float):
    low = get_series(df, "Low").tail(10)
    high = get_series(df, "High").tail(10)
    return float(low.min()), float(high.max())


def decision(df: pd.DataFrame) -> Dict:
    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = safe_float(last["Close"])
    prev_price = safe_float(prev["Close"])
    rsi = safe_float(last["RSI"])
    ema5 = safe_float(last["EMA5"])
    ema20 = safe_float(last["EMA20"])
    ema50 = safe_float(last["EMA50"])
    bbu = safe_float(last["BBU"])
    bbl = safe_float(last["BBL"])
    ret1d = safe_float(last["RET1D"])
    ret5d = safe_float(last["RET5D"])
    volume = safe_float(last["Volume"]) if "Volume" in df.columns else 0.0
    volma20 = safe_float(last["VOLMA20"])

    score = 0
    notes = []

    if ema5 > ema20:
        score += 2
        notes.append("EMA5 di atas EMA20")
    else:
        score -= 1

    if ema20 > ema50:
        score += 1
        notes.append("EMA20 di atas EMA50")
    else:
        score -= 1

    if price > ema20:
        score += 1
        notes.append("harga di atas EMA20")
    else:
        score -= 1

    if 45 <= rsi <= 65:
        score += 1
        notes.append("RSI sehat")
    elif rsi < 35:
        score += 1
        notes.append("RSI rendah / area pantau rebound")
    elif rsi > 72:
        score -= 2
        notes.append("RSI overbought")

    if ret1d > 0:
        score += 1
    if ret5d > 0:
        score += 1

    if volma20 > 0 and volume > volma20:
        score += 1
        notes.append("volume di atas rata-rata")

    if price > bbu:
        score -= 2
        notes.append("harga di atas upper band")
    elif price < bbl:
        score += 1
        notes.append("harga dekat lower band")

    signal = "WAIT"
    emoji = "🟡"
    strength = "NORMAL"
    reason = "Belum ada sinyal dominan"

    if ema5 > ema20 and price > ema20 and score >= 4:
        signal = "BUY"
        emoji = "🔵"
        strength = "STRONG" if score >= 6 else "MEDIUM"
        reason = "Momentum bullish mulai terbentuk"

    if (rsi > 75 and price > bbu) or (ema5 < ema20 and price < ema20 and score <= -2):
        signal = "SELL"
        emoji = "🔴"
        strength = "STRONG" if score <= -4 or rsi > 80 else "MEDIUM"
        reason = "Rawan koreksi / pelemahan trend"

    change = 0.0 if prev_price == 0 else ((price - prev_price) / prev_price) * 100
    support, resistance = support_resistance(df)

    return {
        "signal": signal,
        "emoji": emoji,
        "strength": strength,
        "score": score,
        "reason": reason,
        "notes": ", ".join(notes[:4]) if notes else "-",
        "price": price,
        "change": change,
        "rsi": rsi,
        "ema5": ema5,
        "ema20": ema20,
        "ema50": ema50,
        "bbu": bbu,
        "bbl": bbl,
        "support": support,
        "resistance": resistance,
        "snapshot": df[["Open", "High", "Low", "Close", "RSI", "EMA5", "EMA20"]].tail(6).copy(),
    }


# =========================
# GEMINI AI REASON
# =========================
def ai_reason(snapshot: pd.DataFrame, base_reason: str) -> str:
    if not ENABLE_AI or client is None:
        return base_reason

    try:
        data_text = snapshot.round(2).to_string()

        prompt = f"""
Anda analis saham Indonesia.
Buat 1 kalimat singkat, tajam, profesional, dan langsung ke inti.
Gunakan bahasa Indonesia.
Maksimal 20 kata.

Data:
{data_text}

Inti sinyal:
{base_reason}
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        if text:
            return text.strip()

        return base_reason

    except Exception as e:
        log(f"Gemini AI error: {e}")
        return base_reason


# =========================
# TELEGRAM
# =========================
def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        log("Telegram secret belum lengkap. Pesan tidak dikirim.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
        }
        r = requests.post(url, data=payload, timeout=30)
        if r.status_code != 200:
            log(f"Telegram sendMessage gagal: {r.status_code} {r.text}")
    except Exception as e:
        log(f"Telegram error: {e}")


def send_telegram_document(filepath: str, caption: str = "") -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID or not os.path.exists(filepath):
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(filepath, "rb") as f:
            files = {"document": f}
            data = {"chat_id": CHAT_ID, "caption": caption[:1024]}
            r = requests.post(url, data=data, files=files, timeout=60)
            if r.status_code != 200:
                log(f"Telegram sendDocument gagal: {r.status_code} {r.text}")
    except Exception as e:
        log(f"Telegram document error: {e}")


# =========================
# FORMATTER
# =========================
def format_row(item: Dict, include_category: bool = False) -> str:
    category_text = f"[{item['category']}] " if include_category else ""
    strength_text = f" ({item['strength']})" if item.get("strength") else ""

    return (
        f"{category_text}{item['ticker']} {item['emoji']} {item['signal']}{strength_text}\n"
        f"Price: {item['price']:.2f} ({item['change']:.2f}%) | RSI: {item['rsi']:.1f}\n"
        f"Area: {item['support']:.2f} - {item['resistance']:.2f}\n"
        f"Reason: {item['ai_reason']}\n"
    )


def split_long_message(lines: List[str], header: str) -> List[str]:
    messages = []
    current = header

    for line in lines:
        if len(current) + len(line) + 2 > MESSAGE_LIMIT:
            messages.append(current.rstrip())
            current = header + line + "\n"
        else:
            current += line + "\n"

    if current.strip():
        messages.append(current.rstrip())

    return messages


# =========================
# SAVE REPORT
# =========================
def save_report(results: List[Dict]) -> Optional[str]:
    if not results:
        return None

    ensure_directory("output")
    today = datetime.now().strftime("%Y%m%d")

    rows = []
    for x in results:
        rows.append({
            "ticker": x["ticker"],
            "name": x["name"],
            "category": x["category"],
            "signal": x["signal"],
            "strength": x["strength"],
            "score": x["score"],
            "price": round(x["price"], 2),
            "change_pct": round(x["change"], 2),
            "rsi": round(x["rsi"], 2),
            "support": round(x["support"], 2),
            "resistance": round(x["resistance"], 2),
            "reason": x["ai_reason"],
            "notes": x["notes"],
        })

    df = pd.DataFrame(rows)
    path = f"output/syariah_scan_{today}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


# =========================
# MAIN
# =========================
def main() -> None:
    started = time.time()
    today_human = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    universe = load_universe(UNIVERSE_FILE)
    total_universe = len(universe)

    if total_universe == 0:
        send_telegram("📊 Morning Signal Syariah\nUniverse kosong.")
        return

    log(f"Universe loaded: {total_universe} ticker")

    ticker_map = {x["ticker"]: x for x in universe}
    tickers = [x["ticker"] for x in universe]

    all_results: List[Dict] = []
    failed_tickers: List[str] = []

    batches = chunk_list(tickers, BATCH_SIZE)
    total_batches = len(batches)

    for idx, batch in enumerate(batches, start=1):
        log(f"Download batch {idx}/{total_batches} ({len(batch)} ticker)")
        batch_df = download_batch(batch)

        if batch_df is None or batch_df.empty:
            failed_tickers.extend(batch)
            time.sleep(BATCH_SLEEP_SECONDS)
            continue

        for ticker in batch:
            try:
                raw = extract_ticker_frame(batch_df, ticker, len(batch))
                if raw is None or raw.empty:
                    failed_tickers.append(ticker)
                    continue

                analyzed = analyze(raw)
                if analyzed is None or analyzed.empty:
                    failed_tickers.append(ticker)
                    continue

                dec = decision(analyzed)
                meta = ticker_map[ticker]

                all_results.append({
                    "ticker": ticker,
                    "name": meta.get("name", ""),
                    "category": meta.get("category", "LAINNYA"),
                    **dec,
                })

            except Exception as e:
                log(f"Error process {ticker}: {e}")
                failed_tickers.append(ticker)

        time.sleep(BATCH_SLEEP_SECONDS)

    if not all_results:
        send_telegram(
            f"📊 MORNING SIGNAL SYARIAH\n"
            f"Waktu: {today_human}\n"
            f"Universe: {total_universe}\n"
            f"Tidak ada data yang berhasil diproses."
        )
        return

    all_results.sort(
        key=lambda x: (
            x["signal"] != "BUY",
            x["strength"] != "STRONG",
            -x["score"],
            -x["change"],
            x["rsi"],
        )
    )

    buy_list = [x for x in all_results if x["signal"] == "BUY"]
    sell_list = [x for x in all_results if x["signal"] == "SELL"]
    wait_list = [x for x in all_results if x["signal"] == "WAIT"]

    ai_targets = []
    ai_targets.extend(buy_list[:AI_MAX_COUNT])
    remaining = max(0, AI_MAX_COUNT - len(ai_targets))
    ai_targets.extend(sell_list[:remaining])

    ai_target_ids = {f"{x['ticker']}|{x['signal']}" for x in ai_targets}

    for item in all_results:
        key = f"{item['ticker']}|{item['signal']}"
        if key in ai_target_ids:
            item["ai_reason"] = ai_reason(item["snapshot"], item["reason"])
        else:
            item["ai_reason"] = item["reason"]

    elapsed = time.time() - started

    category_summary: Dict[str, Dict[str, int]] = {}
    for item in all_results:
        cat = item["category"]
        if cat not in category_summary:
            category_summary[cat] = {"BUY": 0, "SELL": 0, "WAIT": 0}
        category_summary[cat][item["signal"]] += 1

    category_lines = []
    for cat, cnt in sorted(category_summary.items(), key=lambda kv: (-kv[1]["BUY"], kv[0])):
        category_lines.append(
            f"{cat}: BUY {cnt['BUY']} | SELL {cnt['SELL']} | WAIT {cnt['WAIT']}"
        )

    header = (
        f"📊 MORNING SIGNAL SYARIAH\n"
        f"Waktu: {today_human}\n"
        f"Universe: {total_universe}\n"
        f"Berhasil: {len(all_results)} | Gagal: {len(set(failed_tickers))}\n"
        f"BUY: {len(buy_list)} | SELL: {len(sell_list)} | WAIT: {len(wait_list)}\n"
        f"Durasi: {elapsed:.1f} detik\n"
        f"--------------------------\n"
    )

    send_telegram(header + "\n".join(category_lines[:25]))

    if buy_list:
        top_buy = buy_list[:MAX_TOP_GLOBAL]
        lines = [format_row(x, include_category=True) for x in top_buy]
        msgs = split_long_message(lines, "🟦 TOP BUY SYARIAH\n--------------------------\n")
        for msg in msgs:
            send_telegram(msg)

    if sell_list:
        top_sell = sell_list[:MAX_TOP_GLOBAL]
        lines = [format_row(x, include_category=True) for x in top_sell]
        msgs = split_long_message(lines, "🟥 TOP SELL / TAKE PROFIT\n--------------------------\n")
        for msg in msgs:
            send_telegram(msg)

    categories = sorted(set(x["category"] for x in all_results))
    for cat in categories:
        cat_buy = [x for x in buy_list if x["category"] == cat][:MAX_PER_CATEGORY]
        cat_sell = [x for x in sell_list if x["category"] == cat][:MAX_PER_CATEGORY]

        if not cat_buy and not cat_sell:
            continue

        lines = []
        if cat_buy:
            lines.append(f"Kategori {cat} - BUY")
            for x in cat_buy:
                lines.append(format_row(x))

        if cat_sell:
            lines.append(f"Kategori {cat} - SELL")
            for x in cat_sell:
                lines.append(format_row(x))

        msgs = split_long_message(lines, f"📂 {cat}\n--------------------------\n")
        for msg in msgs:
            send_telegram(msg)

    report_path = save_report(all_results)
    if SEND_CSV_REPORT and report_path:
        send_telegram_document(report_path, "Laporan scan saham syariah harian")

    log("Done.")


if __name__ == "__main__":
    main()