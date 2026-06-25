from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import json
from fastapi.responses import JSONResponse
# from Routes import router
from fastapi.middleware.cors import CORSMiddleware
# from database import engine, Base
from fastapi.staticfiles import StaticFiles
import random
import asyncio
from Producer import start_producer,stop_producer
from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer
# Base.metadata.create_all(bind=engine)  # Creates tables on startup
from Consumer import consume
app = FastAPI()

@app.on_event("startup")
async def startup():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    await start_producer()
    print("Producer ready")
    asyncio.create_task(consume())
    await asyncio.sleep(0)
    print("Consumer task started")

@app.on_event("shutdown")
async def shutdown():
    await stop_producer()
    print("Producer stopped")

    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── 1. Serve the order page ─────────────────────────────────────────────────
# app.include_router(router)
