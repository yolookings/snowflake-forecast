import os
from fastapi import FastAPI, HTTPException
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
