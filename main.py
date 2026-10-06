import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import snowflake.connector

app = FastAPI(title="ANTAM Gold MRP API")

# Biarkan Frontend mengakses API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE_PATH = os.path.join(BASE_DIR, "index.html")

def get_snowflake_connection():
    """
    Koneksi ke Snowflake menggunakan profil Snowflake CLI (mwlanaz_connection)
    atau melalui Environment Variable bila tersedia.
    """
    conn_name = os.getenv("SNOWFLAKE_CONNECTION", "mwlanaz_connection")
    try:
        return snowflake.connector.connect(
            connection_name=conn_name,
            database="PT_ANTAM_GOLD",
            schema="PUBLIC",
            warehouse="COMPUTE_WH",
            role="ACCOUNTADMIN"
        )
    except Exception as err:
        # Fallback apabila environment variable password diisi langsung
        user = os.getenv("SNOWFLAKE_USER", "mwlanaz")
        password = os.getenv("SNOWFLAKE_PASSWORD")
        account = os.getenv("SNOWFLAKE_ACCOUNT", "jrxfgwa-eh89698")
        if password:
            return snowflake.connector.connect(
                user=user,
                password=password,
                account=account,
                warehouse="COMPUTE_WH",
                database="PT_ANTAM_GOLD",
                schema="PUBLIC",
                role="ACCOUNTADMIN"
            )
        raise err

# 1. Rute untuk menyajikan halaman Dashboard HTML
@app.get("/", response_class=FileResponse)
def read_root():
    if not os.path.exists(INDEX_FILE_PATH):
        raise HTTPException(status_code=404, detail="File index.html tidak ditemukan.")
    return FileResponse(INDEX_FILE_PATH)

# 2. Rute API untuk mengambil data MRP dari Snowflake
@app.get("/api/mrp")
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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal terhubung ke Snowflake: {str(exc)}")
