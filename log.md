# 📋 Project Changelog & Learning Log: PT ANTAM Gold MRP System

Dokumen ini mencatat riwayat pembaruan sistem secara berurutan bernomor (*numbered updates*), lengkap dengan penjelasan konsep, masalah yang ditemukan, solusi, dan potongan kode singkat sebagai referensi pembelajaran.

---

## 1. Perbaikan Autentikasi Snowflake & Stabilitas Backend API (`main.py`)

### 🔍 Masalah & Analisis
- Pada kode awal, koneksi database masih menggunakan placeholder teks `password='YOUR_PASSWORD'`.
- Saat endpoint `/api/mrp` dipanggil, `snowflake.connector` gagal melakukan autentikasi (`DatabaseError: Incorrect username or password`), sehingga FastAPI mengembalikan status **HTTP 500 (Internal Server Error)**.
- Setiap *request* membuka koneksi baru tanpa pernah menutupnya (`conn.close()`), yang berisiko menyebabkan *connection leak* (kebocoran sumber daya koneksi).

### 💡 Solusi
- Memanfaatkan integrasi profil bawaan Snowflake CLI (`connection_name="mwlanaz_connection"`) yang sudah tersimpan di sistem Mac, sehingga tidak perlu menuliskan password secara terbuka/hardcoded (memenuhi prinsip keamanan data).
- Menambahkan *context manager* (`with conn.cursor() as cursor:`) dan perintah `conn.close()` agar koneksi ditutup rapi setelah query selesai.
- Menambahkan *error handling* (`HTTPException`) agar jika terjadi kendala jaringan/database, pesan error dapat dibaca dengan jelas.

### 💻 Kode Singkat (`main.py`)
```python
import os
from fastapi import FastAPI, HTTPException
import snowflake.connector

app = FastAPI(title="ANTAM Gold MRP API")

def get_snowflake_connection():
    # Membaca profil koneksi CLI yang aman tanpa hardcode password
    conn_name = os.getenv("SNOWFLAKE_CONNECTION", "mwlanaz_connection")
    return snowflake.connector.connect(
        connection_name=conn_name,
        database="PT_ANTAM_GOLD",
        schema="PUBLIC",
        warehouse="COMPUTE_WH",
        role="ACCOUNTADMIN"
    )

@app.get("/api/mrp")
def get_mrp_data():
    try:
        conn = get_snowflake_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT period, target_gold_kg, material_name, 
                       total_material_required, unit, total_cost_idr 
                FROM v_mrp_calculation 
                ORDER BY period, material_name;
            """)
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close() # Menutup koneksi database secara tertib
        return {"status": "success", "data": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke Snowflake: {str(exc)}")
```

---

## 2. Pembuatan Dashboard Web Frontend & Integrasi Routing (`index.html`)

### 🔍 Masalah & Analisis
- File frontend sebelumnya salah tersimpan dengan nama `index.htmly` dan isinya tertimpa oleh kode Python.
- Saat endpoint root `/` dipanggil dengan `with open("index.html")`, Python mengalami `FileNotFoundError` sehingga memicu **HTTP 500 Internal Server Error**.
- Belum ada antarmuka web interaktif yang memvisualisasikan data JSON dari Snowflake menjadi kartu metrik dan tabel yang mudah dipahami oleh operasional/manajemen.

### 💡 Solusi
- Menghapus file `index.htmly` dan membuat file baru `index.html` dengan desain modern dan responsif.
- Di `main.py`, menyajikan file menggunakan `FileResponse` dengan path absolut (`os.path.abspath`) agar file selalu terbaca valid di direktori manapun uvicorn dijalankan.
- Di frontend JavaScript, memanggil endpoint relatif `/api/mrp`, menghitung akumulasi target emas & total estimasi biaya ke dalam kartu KPI, serta memformat angka ke standar lokal Rupiah (`id-ID`).

### 💻 Kode Singkat

**Backend Routing (`main.py`):**
```python
from fastapi.responses import FileResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE_PATH = os.path.join(BASE_DIR, "index.html")

@app.get("/", response_class=FileResponse)
def read_root():
    if not os.path.exists(INDEX_FILE_PATH):
        raise HTTPException(status_code=404, detail="File index.html tidak ditemukan.")
    return FileResponse(INDEX_FILE_PATH)
```

**Frontend Fetch & Render (`index.html`):**
```javascript
async function fetchMRPData() {
    try {
        const response = await fetch('/api/mrp');
        const result = await response.json();
        const data = result.data;
        
        let totalCost = 0;
        data.forEach(item => {
            totalCost += Number(item.total_cost_idr) || 0;
            // Render baris tabel kuartal, target, bahan baku, dan biaya
        });
        
        // Tampilkan metrik ringkasan
        document.getElementById('kpi-total-cost').innerText = 'Rp ' + totalCost.toLocaleString('id-ID');
    } catch (err) {
        console.error("Gagal memuat data:", err);
    }
}
```

---

## 3. Optimasi Biaya & Resource Snowflake (Auto-Suspend & Auto-Resume)

### 🔍 Masalah & Analisis
- Secara *default*, virtual warehouse Snowflake (`COMPUTE_WH`) memiliki pengaturan `AUTO_SUSPEND = 300` (5 menit).
- Hal ini berarti warehouse tetap menyala dan mengonsumsi *credit* Snowflake selama 5 menit penuh meskipun query sudah selesai dieksekusi dalam hitungan milidetik.

### 💡 Solusi
- Menurunkan durasi *idle* `AUTO_SUSPEND` menjadi **60 detik (1 menit)**, yang merupakan batas minimum optimal yang direkomendasikan Snowflake untuk lingkungan development.
- Memastikan `AUTO_RESUME = TRUE` aktif agar saat web dashboard dibuka atau tombol *Refresh* ditekan, warehouse langsung terbangun (*wake up*) otomatis tanpa intervensi manual.
- Mengistirahatkan warehouse ke status **`SUSPENDED`** saat tidak sedang digunakan agar pemakaian kredit menjadi **0 credit (hemat maksimal)**.

### 💻 Kode Singkat (Snowflake SQL)
```sql
-- 1. Optimasi Auto-Suspend menjadi 1 menit (60 detik) dan aktifkan Auto-Resume
ALTER WAREHOUSE COMPUTE_WH 
SET AUTO_SUSPEND = 60, AUTO_RESUME = TRUE;

ALTER WAREHOUSE SNOWFLAKE_LEARNING_WH 
SET AUTO_SUSPEND = 60, AUTO_RESUME = TRUE;

-- 2. Mengistirahatkan warehouse segera setelah setup
ALTER WAREHOUSE COMPUTE_WH SUSPEND;

-- 3. Verifikasi status warehouse
SHOW WAREHOUSES LIKE 'COMPUTE_WH';
-- Hasil: state = 'SUSPENDED', auto_suspend = 60, auto_resume = 'true'
```

---

## 4. Konfigurasi Deployment Vercel Serverless Function & Penanganan HTTP 404

### 🔍 Masalah & Analisis
- Saat proyek di-deploy ke Vercel, muncul pesan error di browser: `Gagal memuat data dari Snowflake: HTTP error! status: 404`.
- **Penyebab 1 (Ketiadaan Serverless Runtime):** Vercel secara default mendeteksi repo ini sebagai situs statis HTML biasa karena tidak ada file `requirements.txt`, folder `api/`, maupun `vercel.json`. Akibatnya, backend FastAPI tidak pernah dijalankan di cloud Vercel.
- **Penyebab 2 (Missing Routing Rewrite):** Ketika frontend memanggil `fetch('/api/mrp')`, Vercel mencari file statis `/api/mrp` yang tentu saja tidak ada, sehingga menghasilkan status **404 Not Found**.
- **Penyebab 3 (Environment Variables Snowflake di Cloud):** Di laptop lokal, koneksi membaca file `~/.snowflake/config.toml`. Di serverless Vercel (AWS Lambda Linux), file lokal tersebut tidak ada, sehingga kredensial harus dibaca melalui Vercel Environment Variables.

### 💡 Solusi
- **Menambahkan `requirements.txt`:** Memberi tahu Vercel untuk menginstal paket `fastapi`, `uvicorn`, dan `snowflake-connector-python`.
- **Membuat Entrypoint Serverless `api/index.py`:** Memindahkan/mengarahkan instance FastAPI ke struktur standar Vercel `@vercel/python`.
- **Menambahkan `vercel.json`:** Mendaftarkan *rewrite rule* agar semua request berawalan `/api/(.*)` diteruskan secara otomatis ke `api/index.py`.
- **Mendukung Dual-Mode Connection:** Kode di `api/index.py` secara cerdas mengecek ketersediaan `SNOWFLAKE_PASSWORD` di Environment Variables untuk mode cloud/Vercel, atau fallback ke profil CLI `mwlanaz_connection` untuk mode lokal Mac.

### 💻 Kode Singkat

**1. Konfigurasi Vercel Routing (`vercel.json`):**
```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/index.py"
    }
  ]
}
```

**2. Dependensi Vercel (`requirements.txt`):**
```text
fastapi
uvicorn
snowflake-connector-python
```

**3. Dual-Mode Connection di Serverless (`api/index.py`):**
```python
def get_snowflake_connection():
    password = os.getenv("SNOWFLAKE_PASSWORD")
    if password:
        # Mode Production (Vercel): Membaca kredensial dari Environment Variables
        return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER", "mwlanaz"),
            password=password,
            account=os.getenv("SNOWFLAKE_ACCOUNT", "jrxfgwa-eh89698"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "PT_ANTAM_GOLD"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
            role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
        )
    else:
        # Mode Local (Mac): Membaca profil Snowflake CLI 'mwlanaz_connection'
        return snowflake.connector.connect(
            connection_name=os.getenv("SNOWFLAKE_CONNECTION", "mwlanaz_connection"),
            database="PT_ANTAM_GOLD",
            schema="PUBLIC",
            warehouse="COMPUTE_WH",
            role="ACCOUNTADMIN"
        )
```

---

## 5. Implementasi Navigasi Sidebar (3 Menu) & Simulator Metalurgi Emas (Padatan &rarr; Buih &rarr; Bubuk)

### 🔍 Masalah & Analisis
- Tampilan sebelumnya hanya berupa satu halaman tabel statis sederhana tanpa pemisahan fungsi analitik, operasional, dan prediksi.
- Diperlukan struktur modular berbasis **Sidebar Navigasi** yang membagi aplikasi menjadi 3 menu utama:
  1. **Dashboard**: Ringkasan eksekutif target tahunan, grafik progress kuartal, komposisi biaya, dan alur SOP metalurgi.
  2. **Data Viewer**: Tabel operasional untuk menjelajahi data Snowflake (`v_mrp_calculation`) dengan filter periode dan fitur pencarian.
  3. **Forecast & Simulator**: Fitur simulasi prediksi kebutuhan bahan baku bila user ingin memproduksi emas dalam jumlah tertentu (misal: 1.000 Ton atau 1.000 Kg emas), lengkap dengan kalkulasi kimiawi transisi fase:
     - **Padatan (Ore Mining & Grinding)**: Kebutuhan batuan bijih mentah.
     - **Padatan &rarr; Buih (Flotasi Konsentrat)**: Penambahan Kolektor (*Potassium Amyl Xanthate / PAX*), Pembuih (*MIBC*), dan Pengatur pH (*Kapur Tohor*).
     - **Buih &rarr; Larutan (Pelindian / Leaching)**: Pelarutan emas dengan *Sodium Cyanide (NaCN)* dan adsorpsi *Karbon Aktif*.
     - **Larutan &rarr; Bubuk & Batangan (Presipitasi & Smelting)**: Reduksi larutan menjadi endapan bubuk emas menggunakan *Zinc Powder (Merrill-Crowe)*, peleburan dengan *Flux Boraks*, dan konsumsi daya listrik furnace.

### 💡 Solusi
- **Backend API (`api/index.py`):** Menambahkan endpoint fleksibel `/api/simulate` yang menerima parameter `target` dan `unit` (kg/ton), kemudian menghitung secara detail kebutuhan kuantitas, satuan, biaya satuan, subtotal, dan deskripsi fungsi kimiawi untuk tiap tahapan proses.
- **Frontend Interaktif (`index.html`):** 
  - Membangun sidebar bernuansa *corporate dark gold* PT ANTAM dengan indikator live cloud Snowflake.
  - Menerapkan arsitektur *Single Page Application* (SPA tab switching) tanpa *reload* halaman.
  - Menambahkan kontrol simulasi dengan *preset buttons* (500 Kg, 1.000 Kg, 5.000 Kg, 1.000 Ton), kartu rincian reagen kimia, serta tabel breakdown per tahapan metalurgi.

### 💻 Kode Singkat

**1. Endpoint Simulasi Metalurgi (`api/index.py`):**
```python
@app.get("/api/simulate")
def simulate_forecast(target: float = 1000.0, unit: str = "kg"):
    target_kg = target * 1000.0 if unit.lower() == "ton" else target
    
    # Formula kebutuhan per 1 kg emas:
    # 1. Padatan: 150 Ton Gold Ore
    # 2. Padatan -> Buih: 22.5 kg PAX (Collector), 7.5 kg MIBC (Frother), 225 kg Kapur Tohor
    # 3. Buih -> Larutan: 45 kg Sodium Cyanide, 12 kg Karbon Aktif
    # 4. Larutan -> Bubuk: 1.2 kg Zinc Powder (Merrill-Crowe), 2.5 kg Flux, 1.200 kWh Listrik
    
    # Hitung total kuantitas dan estimasi biaya per tahapan metalurgi
    # Kembalikan response JSON terstruktur
```

**2. Tab Switching & Real-Time Calculation (`index.html`):**
```javascript
function switchTab(tabId) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    
    document.getElementById('tab-' + tabId).classList.add('active');
    if (tabId === 'forecast') runSimulation();
}

async function runSimulation() {
    const target = document.getElementById('sim-target-input').value;
    const unit = document.getElementById('sim-unit-select').value;
    const res = await fetch(`/api/simulate?target=${target}&unit=${unit}`);
    const data = await res.json();
    // Render 4 kartu KPI simulasi dan tabel rincian tahapan kimiawi
}
```
