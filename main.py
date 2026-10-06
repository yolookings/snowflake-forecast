# Entrypoint lokal untuk uvicorn
# Menghubungkan ke instance FastAPI di api/index.py
from api.index import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
