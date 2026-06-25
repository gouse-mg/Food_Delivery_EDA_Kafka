from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import json
from fastapi.responses import JSONResponse
from Routes import router
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from fastapi.staticfiles import StaticFiles
import Manager
import random
import asyncio
from pydantic import BaseModel
from aiokafka import AIOKafkaConsumer
from aiokafka import AIOKafkaProducer
from Producer import start_producer,stop_producer
from Consumer import consume  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router)

producer = None


@app.on_event("startup")
async def startup():
    global producer
    Base.metadata.create_all(bind=engine)
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



@app.get("/", response_class=HTMLResponse)
async def serve_order_page():
    with open("static/ResAuth.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
