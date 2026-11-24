from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database.session import Base, engine, SessionLocal
from app.models.entities import *
from app.api.routes import router, seed_db
import asyncio

Base.metadata.create_all(bind=engine)
app=FastAPI(title=settings.app_name,version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)

@app.on_event("startup")
def startup():
    db=SessionLocal(); seed_db(db); db.close()
@app.get("/health")
def health(): return {"status":"ok","simulation_mode":settings.simulation_mode}

@app.websocket("/ws/metrics")
async def metrics_socket(ws:WebSocket):
    await ws.accept()
    try:
        while True:
            db=SessionLocal(); m=db.query(ResourceMetric).order_by(ResourceMetric.id.desc()).first(); db.close()
            if m: await ws.send_json({"timestamp":m.timestamp.isoformat(),"cpu_percent":m.cpu_percent,"memory_percent":m.memory_percent,"network_usage":m.network_usage,"active_workloads":m.active_workloads,"instances":m.instances})
            await asyncio.sleep(2)
    except Exception: pass
