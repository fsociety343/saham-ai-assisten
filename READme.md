# 📊 Morning Signal PRO Bot

Bot ini adalah **AI-assisted Technical Analysis System** berbasis Python untuk memantau **saham syariah Indonesia** secara otomatis.

Bot akan:

- Mengambil data harga saham dari **Yahoo Finance**
- Menganalisis indikator teknikal seperti **RSI, EMA, dan Bollinger Bands**
- Menghasilkan sinyal **BUY / SELL / WAIT**
- Menggunakan **Gemini API** untuk membuat reasoning analisis singkat
- Mengelompokkan hasil berdasarkan **kategori saham** seperti:
  - Infrastruktur
  - Oil & Gas
  - Batubara
  - Energi
  - Telekomunikasi
  - Teknologi
  - dan kategori lainnya
- Mengirim notifikasi otomatis ke **Telegram**
- Berjalan otomatis via **GitHub Actions** tanpa server sendiri

---

# 🚀 Fitur Utama

- Scan **semua saham syariah Indonesia** dari file universe CSV
- Multi-indikator teknikal:
  - RSI
  - EMA 5 / 20 / 50
  - Bollinger Bands
  - Volume average
- Klasifikasi sinyal:
  - BUY
  - SELL
  - WAIT
- Ranking sinyal berdasarkan skor teknikal
- Ringkasan hasil per kategori sektor
- AI reasoning menggunakan **Google Gemini**
- Output notifikasi ke Telegram
- Auto save laporan hasil scan ke CSV
- Auto run via GitHub Actions
- Konfigurasi fleksibel via **GitHub Secrets** dan **GitHub Variables**

---

# 🆕 Perubahan Hari Ini

Perubahan utama yang sudah diterapkan:

- Migrasi AI dari **OpenAI** ke **Gemini API**
- Struktur bot diubah dari beberapa ticker manual menjadi **universe saham syariah Indonesia**
- Penambahan dukungan **kategori sektor saham**
- Pembacaan data saham dari file:
  - `data/syariah_universe.csv`
- Perbaikan pembacaan data `yfinance` agar aman untuk format kolom **MultiIndex**
- Penambahan ranking hasil scan:
  - Top BUY global
  - Top SELL global
  - Ringkasan per kategori
- Penyesuaian deployment untuk **GitHub Actions**
- Konfigurasi `.env` lokal dibuat kompatibel dengan **Secrets** dan **Variables** di GitHub

---

# 🧠 Contoh Output Telegram

```text
📊 MORNING SIGNAL SYARIAH
Waktu: 2026-04-15 08:30:00
Universe: 250
Berhasil: 240 | Gagal: 10
BUY: 18 | SELL: 9 | WAIT: 213
Durasi: 145.2 detik
--------------------------
BATUBARA: BUY 4 | SELL 1 | WAIT 18
INFRASTRUKTUR: BUY 3 | SELL 0 | WAIT 21
OIL & GAS: BUY 2 | SELL 2 | WAIT 14
```

Contoh sinyal:

```text
[BATUBARA] ADRO.JK 🔵 BUY (STRONG)
Price: 2450.00 (2.13%) | RSI: 58.4
Area: 2360.00 - 2485.00
Reason: Momentum bullish mulai terbentuk
```

---

# 📦 Requirements

Install dependency:

```bash
pip install -r requirements.txt
```

Isi `requirements.txt`:

```txt
yfinance==1.2.1
pandas>=2.2,<3.0
requests>=2.31.0
python-dotenv>=1.0.1
google-genai>=1.0.0
ta>=0.11.0
```

---

# ⚙️ Konfigurasi Environment

Untuk local testing, Anda bisa membuat file `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
CHAT_ID=your_chat_id
GEMINI_API_KEY=your_gemini_api_key

UNIVERSE_FILE=data/syariah_universe.csv
YF_PERIOD=6mo
YF_INTERVAL=1d
BATCH_SIZE=25
BATCH_SLEEP_SECONDS=1
MAX_TOP_GLOBAL=20
MAX_PER_CATEGORY=5
MIN_ROWS=40
MESSAGE_LIMIT=3900

ENABLE_AI=true
AI_MAX_COUNT=5
GEMINI_MODEL=gemini-2.0-flash

SEND_CSV_REPORT=false
```

> Catatan: saat deploy di GitHub Actions, file `.env` **tidak perlu di-upload** ke repo. Gunakan **Secrets** dan **Variables**.

---

# 📄 Format Data Universe Saham

Buat file:

```text
data/syariah_universe.csv
```

Contoh isi:

```csv
ticker,name,category
AKRA,AKR Corporindo,OIL_GAS
ADRO,Alamtri Resources Indonesia,BATUBARA
ITMG,Indo Tambangraya Megah,BATUBARA
MEDC,Medco Energi Internasional,OIL_GAS
PGAS,Perusahaan Gas Negara,OIL_GAS
JSMR,Jasa Marga,INFRASTRUKTUR
TLKM,Telkom Indonesia,TELEKOMUNIKASI
MTEL,Dayamitra Telekomunikasi,INFRASTRUKTUR
EXCL,XL Axiata,TELEKOMUNIKASI
ISAT,Indosat,TELEKOMUNIKASI
```

Kolom yang dipakai:

- `ticker` → kode saham
- `name` → nama emiten
- `category` → kategori sektor

---

# 🔐 Setup Telegram Bot

1. Buka Telegram
2. Chat ke **@BotFather**
3. Buat bot baru
4. Simpan token bot

Untuk mendapatkan `CHAT_ID`:

1. Chat ke bot Anda terlebih dahulu
2. Gunakan bot seperti **@userinfobot** untuk melihat chat ID Anda

---

# 🤖 Setup Gemini API

1. Buka **Google AI Studio**
2. Buat API key Gemini
3. Simpan API key tersebut sebagai:
   - `GEMINI_API_KEY`

Model default yang dipakai:

```text
gemini-2.0-flash
```

---

# ☁️ Deploy ke GitHub Actions

## 1. Push project ke GitHub

```bash
git init
git add .
git commit -m "init morning signal pro"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

---

## 2. Setup GitHub Secrets

Masuk ke:

```text
Repository → Settings → Secrets and variables → Actions
```

Tambahkan pada tab **Secrets**:

- `TELEGRAM_BOT_TOKEN`
- `CHAT_ID`
- `GEMINI_API_KEY`

---

## 3. Setup GitHub Variables

Tambahkan pada tab **Variables** bila ingin mengubah konfigurasi tanpa edit file workflow:

- `UNIVERSE_FILE`
- `YF_PERIOD`
- `YF_INTERVAL`
- `BATCH_SIZE`
- `BATCH_SLEEP_SECONDS`
- `MAX_TOP_GLOBAL`
- `MAX_PER_CATEGORY`
- `MIN_ROWS`
- `MESSAGE_LIMIT`
- `ENABLE_AI`
- `AI_MAX_COUNT`
- `GEMINI_MODEL`
- `SEND_CSV_REPORT`

> Nilai-nilai ini bisa tetap kosong jika workflow sudah memiliki default value.

---

## 4. Jalankan Manual untuk Testing

Masuk ke:

```text
Actions → Morning Signal PRO → Run workflow
```

---

## 5. Jadwal Otomatis

Workflow bisa dijalankan otomatis sesuai kebutuhan.

Contoh:
- setiap hari kerja jam tertentu
- setiap 3 jam sekali pada jam kerja
- atau jadwal lain sesuai cron

Contoh cron untuk setiap 3 jam pada jam kerja:

```yaml
schedule:
  - cron: "0 8,11,14,17 * * 1-5"
    timezone: "Asia/Jakarta"
```

Artinya:
- Senin–Jumat
- jalan pada:
  - 08:00 WIB
  - 11:00 WIB
  - 14:00 WIB
  - 17:00 WIB

---

# 📁 Struktur Project

```text
project/
├── main.py
├── requirements.txt
├── README.md
├── data/
│   └── syariah_universe.csv
├── output/
│   └── syariah_scan_YYYYMMDD.csv
└── .github/
    └── workflows/
        └── morning.yml
```

---

# ⚙️ Cara Kerja Sistem

Alur kerja bot:

1. Membaca daftar saham dari `syariah_universe.csv`
2. Mengunduh data OHLCV dari Yahoo Finance
3. Menghitung indikator teknikal
4. Membentuk sinyal:
   - BUY
   - SELL
   - WAIT
5. Melakukan ranking saham dengan skor teknikal
6. Menyusun ringkasan:
   - summary keseluruhan
   - top buy
   - top sell
   - hasil per kategori
7. Menambahkan reasoning singkat dari Gemini untuk kandidat terbaik
8. Mengirim hasil ke Telegram
9. Menyimpan hasil scan ke CSV

---

# ⚠️ Troubleshooting

## ❌ Telegram tidak mengirim pesan

Periksa:
- `TELEGRAM_BOT_TOKEN`
- `CHAT_ID`
- apakah bot sudah pernah menerima chat dari akun Anda

## ❌ Workflow gagal di GitHub Actions

Periksa:
- log pada tab **Actions**
- file `.github/workflows/morning.yml`
- dependency di `requirements.txt`
- apakah secrets sudah terisi

## ❌ Gemini AI tidak jalan

Periksa:
- `GEMINI_API_KEY`
- `ENABLE_AI=true`
- model Gemini yang digunakan

## ❌ Data saham banyak yang gagal

Periksa:
- kode ticker pada `syariah_universe.csv`
- koneksi ke Yahoo Finance
- ukuran batch terlalu besar atau tidak

---

# 🔥 Roadmap Upgrade

Pengembangan lanjutan yang bisa ditambahkan:

- Auto update daftar saham syariah dari sumber resmi
- Backtesting engine
- Dashboard web monitoring
- Multi-timeframe analysis
- Risk management lanjutan
- Portfolio scoring
- Export PDF / Excel report
- Integrasi broker API

---

# 🧠 Catatan

Bot ini menggunakan pendekatan:

**Rule-Based + AI Assisted Analysis**

Artinya:

- sinyal utama tetap berbasis aturan teknikal
- AI hanya membantu merangkum reasoning
- hasil lebih stabil dan lebih mudah diaudit
- cocok untuk monitoring semi-otomatis

---

# ⚡ Disclaimer

Bot ini dibuat untuk edukasi, riset, dan analisis teknikal.

Bukan financial advice dan bukan rekomendasi investasi mutlak.

Gunakan dengan manajemen risiko yang baik.

---

# 🤝 Kontribusi

Silakan fork dan kembangkan sesuai kebutuhan:

- tambah indikator
- tambah kategori sektor
- optimasi scoring
- integrasi data fundamental
- integrasi broker
- pengembangan dashboard

---

# 🚀 Author

Built for automated technical analysis and signal monitoring system development.
