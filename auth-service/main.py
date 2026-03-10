from fastapi import FastAPI

app = FastAPI(title="VKR Auth Service")

@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}