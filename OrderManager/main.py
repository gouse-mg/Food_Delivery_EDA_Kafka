from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import json
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import random
import asyncio
from pydantic import BaseModel
from aiokafka import AIOKafkaConsumer
import json, asyncio
from aiokafka import AIOKafkaProducer
import json, asyncio
from Manager import order_manager
from Consumer import consume
import httpx
from Producer import start_producer,stop_producer
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    await start_producer()
    print("PRODUCER STARTUP RUNNING")
    asyncio.create_task(consume())
    print("Consumer Started")

@app.on_event("shutdown")
async def shutdown():
    await start_producer()


class OrderRequest(BaseModel):
    cart: list[list[int]]  
 
OrderStatus = {}

def ProcessCart(cart):
    result = {}
    for dish_id, res_id in cart:
        if res_id not in result:
            result[int(res_id)] = []
        result[int(res_id)].append(int(dish_id))
    return result

@app.post('/Order')
async def ProcessOrder(order: OrderRequest):
    cart = ProcessCart(order.cart)
    order_id = random.randint(1, 100)
    print("Order", order_id)
    # get the res ids here 
    locations = {}
    for res_ids in cart.keys():
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://resmanager-resmanager-1:8000/api/ResManager/res/restaurants/{res_ids}")
            data = response.json()
            print(data)
            res_lat = data['lat']
            res_long = data['long']
            locations[int(res_ids)] = [res_lat,res_long]
    lat, longi = 12.9716 + random.uniform(-0.03, 0.03), 77.5946 + random.uniform(-0.03, 0.03)

    order_manager.order_status[order_id] = {}
    order_manager.order_status[order_id]["res_locations"] = locations
    order_manager.order_status[order_id]["order_location"] = [lat,longi]
    event = {"order_id": order_id, "cart": cart,"Locations":locations,"Destin":[lat,longi]}

    print(f"Processing order {order_id}, cart: {cart}")

    try:
        from Producer import get_producer
        producer = get_producer()  # make sure you're using the right producer
        print(f"Producer state: {producer._closed}")  # False = healthy
        
        future = await producer.send(
            "order-created",
            json.dumps(event).encode("utf-8")
        )
        record_metadata = await future
        print(f"✅ Sent to {record_metadata.topic} offset={record_metadata.offset}")
    except Exception as e:
        print(f"❌ PRODUCER ERROR: {type(e).__name__}: {e}")
    return {"Status":"Requested"}

@app.get("/order-page", response_class=HTMLResponse)
async def serve_order_html():
    with open("static/ResAuth.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())




@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    await websocket.accept()
    print("Reached heree!")
    # 1. Validate JWT manually
    
        # 4. Register in manager
    order_manager.web_socket = websocket
        # 5. Send confirmation on connect
    await websocket.send_text(json.dumps({
        "flag": "Connected",
    }))

    # 6. Message loop
    while True:
        raw = await websocket.receive_text()
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        
