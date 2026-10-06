import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import snowflake.connector

app = FastAPI(title="ANTAM Gold MRP API")

# Biarkan Frontend mengakses API tanpa kendala CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_FILE_PATH = os.path.join(BASE_DIR, "index.html")
ANTAM_LOGO_FILE_PATH = os.path.join(BASE_DIR, "antam.svg")

def get_snowflake_connection():
    """
    Koneksi ke Snowflake:
    1. Di Cloud / Vercel: Menggunakan Environment Variables (SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, dsb.)
    2. Di Local (Mac): Menggunakan profil Snowflake CLI ('mwlanaz_connection')
    """
    password = os.getenv("SNOWFLAKE_PASSWORD")
    user = os.getenv("SNOWFLAKE_USER", "mwlanaz")
    account = os.getenv("SNOWFLAKE_ACCOUNT", "jrxfgwa-eh89698")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    database = os.getenv("SNOWFLAKE_DATABASE", "PT_ANTAM_GOLD")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

    if password:
        # Mode Production (Vercel)
        return snowflake.connector.connect(
            user=user,
            password=password,
            account=account,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role
        )
    else:
        # Mode Local (menggunakan config Snowflake CLI di Mac)
        conn_name = os.getenv("SNOWFLAKE_CONNECTION", "mwlanaz_connection")
        try:
            return snowflake.connector.connect(
                connection_name=conn_name,
                database=database,
                schema=schema,
                warehouse=warehouse,
                role=role
            )
        except Exception as err:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Gagal koneksi ke Snowflake: {str(err)}. "
                    "Jika berjalan di Vercel, pastikan Environment Variable SNOWFLAKE_PASSWORD sudah diisi."
                )
            )

# Rute root (untuk running local atau direct routing)
@app.get("/", response_class=FileResponse)
def read_root():
    if os.path.exists(INDEX_FILE_PATH):
        return FileResponse(INDEX_FILE_PATH)
    return {"status": "success", "message": "ANTAM Gold MRP API is running"}

# Asset logo dipakai langsung oleh shell HTML. Rute ini menjaga preview lokal
# melalui Uvicorn tetap sama dengan deployment yang menyajikan file statis.
@app.get("/antam.svg", response_class=FileResponse)
def read_antam_logo():
    if os.path.exists(ANTAM_LOGO_FILE_PATH):
        return FileResponse(ANTAM_LOGO_FILE_PATH, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Logo ANTAM tidak ditemukan")

# Health check
@app.get("/api/health")
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Rute API MRP (Mendukung /api/mrp maupun /mrp untuk fleksibilitas Vercel rewrite)
@app.get("/api/mrp")
@app.get("/mrp")
def get_mrp_data():
    try:
        conn = get_snowflake_connection()
        with conn.cursor() as cursor:
            query = """
                SELECT period, target_gold_kg, material_name, 
                       total_material_required, unit, total_cost_idr 
                FROM v_mrp_calculation 
                ORDER BY period, material_name;
            """
            cursor.execute(query)
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return {"status": "success", "data": results}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Error saat mengeksekusi query Snowflake: {str(exc)}"
        )

# Rute Simulasi Forecast Kebutuhan Bahan Kimia & Ore (Tahap Padatan -> Buih -> Bubuk)
@app.get("/api/simulate")
@app.get("/simulate")
def simulate_forecast(
    target: float = Query(1000.0, description="Target produksi emas"),
    unit: str = Query("kg", description="Satuan target: kg atau ton")
):
    """
    Simulasi kebutuhan material & reagen kimia untuk produksi emas
    berdasarkan siklus metalurgi:
    1. Padatan (Bijih Emas / Ore)
    2. Flotasi (Padatan -> Buih / Froth Flotation)
    3. Pelindian Konsentrat (Buih -> Larutan Kaya)
    4. Presipitasi & Smelting (Larutan -> Bubuk Emas & Batangan)
    """
    target_kg = target * 1000.0 if unit.lower() == "ton" else target

    # Formulasi kebutuhan per 1 kg emas
    stages = [
        {
            "stage_id": 1,
            "stage_name": "Tahap 1: Penambangan & Preparasi Bijih (Padatan)",
            "description": "Penggalian dan penghancuran batuan bijih mentah (ore) menjadi butiran halus.",
            "items": [
                {
                    "name": "Gold Ore (Bijih Emas Mentah)",
                    "category": "Raw Material",
                    "rate_per_kg": 150.0,
                    "unit": "Tonne",
                    "unit_cost_idr": 1200000.0,
                    "function": "Bahan baku batuan pembawa mineral emas (kadar rata-rata ~6.67 g/t)."
                }
            ]
        },
        {
            "stage_id": 2,
            "stage_name": "Tahap 2: Flotasi Konsentrat (Padatan Menjadi Buih)",
            "description": "Proses fisika-kimia memisahkan mineral sulfida emas dari batuan pengotor dengan menempelkan partikel ke gelembung udara hingga menjadi buih.",
            "items": [
                {
                    "name": "Collector (Potassium Amyl Xanthate / PAX)",
                    "category": "Flotation Reagent",
                    "rate_per_kg": 22.5,
                    "unit": "Kg",
                    "unit_cost_idr": 45000.0,
                    "function": "Mengikat partikel emas agar bersifat hidrofobik dan menempel ke gelembung."
                },
                {
                    "name": "Frother (Methyl Isobutyl Carbinol / MIBC)",
                    "category": "Flotation Reagent",
                    "rate_per_kg": 7.5,
                    "unit": "Kg",
                    "unit_cost_idr": 65000.0,
                    "function": "Membentuk dan menstabilkan busa/buih di permukaan sel flotasi."
                },
                {
                    "name": "pH Modifier (Quicklime / Kapur Tohor)",
                    "category": "Flotation Reagent",
                    "rate_per_kg": 225.0,
                    "unit": "Kg",
                    "unit_cost_idr": 2500.0,
                    "function": "Mengatur alkalinitas bubur bijih (pH 10.5 - 11.0) untuk efisiensi flotasi."
                }
            ]
        },
        {
            "stage_id": 3,
            "stage_name": "Tahap 3: Pelindian Konsentrat (Buih Menjadi Larutan Kaya)",
            "description": "Buih konsentrat dilarutkan menggunakan larutan sianida untuk melarutkan logam emas menjadi kompleks aurocyanide cair.",
            "items": [
                {
                    "name": "Sodium Cyanide (NaCN)",
                    "category": "Leaching Agent",
                    "rate_per_kg": 45.0,
                    "unit": "Kg",
                    "unit_cost_idr": 35000.0,
                    "function": "Reagen pelarut utama untuk mengekstraksi emas dari konsentrat padat ke larutan."
                },
                {
                    "name": "Karbon Aktif (Activated Carbon)",
                    "category": "Adsorption",
                    "rate_per_kg": 12.0,
                    "unit": "Kg",
                    "unit_cost_idr": 40000.0,
                    "function": "Menyerap (adsorpsi) kompleks emas terlarut dari cairan pulp (proses CIL/CIP)."
                }
            ]
        },
        {
            "stage_id": 4,
            "stage_name": "Tahap 4: Presipitasi & Peleburan (Larutan Menjadi Bubuk Emas & Batangan)",
            "description": "Emas terlarut diendapkan kembali menjadi bubuk logam (presipitat) lalu dilebur menjadi emas batangan dore.",
            "items": [
                {
                    "name": "Zinc Powder (Merrill-Crowe Precipitation)",
                    "category": "Precipitant",
                    "rate_per_kg": 1.2,
                    "unit": "Kg",
                    "unit_cost_idr": 75000.0,
                    "function": "Mereduksi larutan emas menjadi endapan bubuk emas (gold precipitate powder)."
                },
                {
                    "name": "Smelting Flux (Borax & Silica Sand)",
                    "category": "Smelting Flux",
                    "rate_per_kg": 2.5,
                    "unit": "Kg",
                    "unit_cost_idr": 30000.0,
                    "function": "Campuran peleburan untuk mengikat terak/kotoran saat bubuk emas dicairkan di tanur."
                },
                {
                    "name": "Electricity (Daya Listrik Tanur & Pabrik)",
                    "category": "Energy & Power",
                    "rate_per_kg": 1200.0,
                    "unit": "kWh",
                    "unit_cost_idr": 1500.0,
                    "function": "Energi operasional ball mill, sel flotasi, electrowinning, dan induction furnace."
                }
            ]
        }
    ]

    total_cost_overall = 0.0
    detailed_stages = []

    for st in stages:
        st_items = []
        st_cost = 0.0
        for item in st["items"]:
            total_qty = target_kg * item["rate_per_kg"]
            cost = total_qty * item["unit_cost_idr"]
            st_cost += cost
            st_items.append({
                "name": item["name"],
                "category": item["category"],
                "total_quantity": total_qty,
                "unit": item["unit"],
                "unit_cost_idr": item["unit_cost_idr"],
                "total_cost_idr": cost,
                "function": item["function"]
            })
        total_cost_overall += st_cost
        detailed_stages.append({
            "stage_id": st["stage_id"],
            "stage_name": st["stage_name"],
            "description": st["description"],
            "subtotal_cost_idr": st_cost,
            "items": st_items
        })

    return {
        "status": "success",
        "input": {
            "target_input": target,
            "unit": unit,
            "target_gold_kg": target_kg,
            "target_gold_ton": target_kg / 1000.0
        },
        "total_cost_idr": total_cost_overall,
        "stages": detailed_stages
    }
