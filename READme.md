# 📊 Morning Signal PRO Bot

Bot ini adalah **AI-assisted Technical Analysis System** berbasis Python yang:

* Mengambil data saham otomatis (Yahoo Finance)
* Menganalisis indikator teknikal (RSI, EMA, Bollinger Bands, ATR)
* Menghasilkan sinyal trading (BUY / SELL / WAIT)
* Menggunakan AI untuk reasoning analisis
* Mengirim notifikasi ke Telegram setiap pagi
* Berjalan otomatis via GitHub Actions (gratis, tanpa server)

---

# 🚀 Fitur Utama

✔ Multi-indikator teknikal (RSI, EMA, BB, ATR)
✔ AI reasoning (OpenAI)
✔ Confidence score (0–100%)
✔ Risk management (Stop Loss & Take Profit)
✔ Filter sinyal kuat (noise reduction)
✔ Auto run tiap hari kerja (08:30 WIB)

---

# 🧠 Contoh Output

```
📊 MORNING SIGNAL PRO 12-04-2026
--------------------------------
🔵 BBCA.JK: BUY (70%)
Price: 9850 (+1.25%)
Entry: 9700
SL: 9600 | TP: 10050
Reason: RSI low, Uptrend
AI: Momentum bullish menguat setelah konsolidasi sempit dengan tekanan beli dominan
```

---

# 📦 Requirement

Install dependency:

```bash
pip install -r requirements.txt
```

Atau manual:

```bash
pip install yfinance pandas pandas_ta python-dotenv requests openai
```

---

# ⚙️ Konfigurasi Environment

Buat file `.env` di lokal (opsional untuk testing):

```
TELEGRAM_BOT_TOKEN=your_token
CHAT_ID=your_chat_id
OPENAI_API_KEY=your_openai_key
```

---

# 🔐 Setup Telegram Bot

1. Buka Telegram
2. Chat ke **@BotFather**
3. Buat bot baru → dapatkan TOKEN

Untuk Chat ID:

* Chat ke **@userinfobot**
* Copy ID kamu

---

# ☁️ Deploy ke GitHub Actions (GRATIS)

## 1. Push Project ke GitHub

```bash
git init
git add .
git commit -m "init bot"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

---

## 2. Setup Secrets

Masuk ke:

```
Repository → Settings → Secrets → Actions
```

Tambahkan:

* `TELEGRAM_BOT_TOKEN`
* `CHAT_ID`
* `OPENAI_API_KEY`

---

## 3. Jalankan Manual (Testing)

Masuk ke:

```
Actions → Morning Signal PRO → Run workflow
```

---

## 4. Jadwal Otomatis

Bot akan berjalan otomatis:

```
Senin - Jumat jam 08:30 WIB
```

(Cron: `30 1 * * 1-5`)

---

# 📁 Struktur Project

```
project/
 ├── main.py
 ├── requirements.txt
 └── .github/
     └── workflows/
         └── morning.yml
```

---

# ⚠️ Troubleshooting

## ❌ Tidak kirim Telegram

* Cek TOKEN
* Cek CHAT_ID

## ❌ Workflow gagal

* Cek log di tab Actions
* Pastikan file `.github/workflows/morning.yml` benar

## ❌ AI tidak jalan

* Pastikan `OPENAI_API_KEY` sudah di-set di Secrets

---

# 🔥 Roadmap Upgrade

* Backtesting engine (winrate analysis)
* Auto trading (integrasi broker API)
* Web dashboard (monitoring real-time)
* Multi-timeframe analysis (H1, H4, D1)
* Portfolio & risk allocation

---

# 🧠 Catatan

Bot ini menggunakan pendekatan:

**Rule-Based + AI Assisted Decision**

Artinya:

* Stabil & bisa dikontrol
* Tidak overfit seperti full AI
* Cocok untuk semi-automation trading

---

# ⚡ Disclaimer

Bot ini hanya untuk edukasi & analisis.
Bukan financial advice.

Gunakan dengan manajemen risiko yang baik.

---

# 🤝 Kontribusi

Silakan fork & improve sesuai kebutuhan:

* Tambah indikator
* Improve AI prompt
* Integrasi broker

---

# 🚀 Author

Built for automated trading signal system development.
