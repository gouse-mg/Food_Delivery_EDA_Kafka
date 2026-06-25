from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from jose import JWTError
from Dependencies.data import SessionLocal
from DataModels.Restruarants import Restaurant
from Config.Security import decode_token
import Manager
import json
import random
router = APIRouter(prefix = "/communicate")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    restaurant_id: int = Query(...),
    token: str = Query(...),
):
    await websocket.accept()
    
    print("Reached heree!!")
    # 1. Validate JWT manually
    try:
        payload = decode_token(token)
        current_id: int = int(payload.get("sub"))
        if current_id is None:
            await websocket.close(code=1008, reason="Invalid token payload")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    # 2. Ownership check
    if current_id != restaurant_id:
        await websocket.close(code=1008, reason="Not your restaurant")
        return

    # 3. Manual DB session
    db: Session = SessionLocal()
    try:
        restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
        if not restaurant:
            await websocket.close(code=1008, reason="Restaurant not found")
            return

        # 4. Register in manager
         
        lat, longi = 12.9716 + random.uniform(-0.03, 0.03), 77.5946 + random.uniform(-0.03, 0.03)

        res = Manager.Restrurant(
            id=restaurant.id,
            Socket=websocket,
            name=restaurant.name,
            lat = lat,
            longi = longi
        )
        Manager.res_manager.restaurants[restaurant_id] = res
        print(Manager.res_manager.restaurants)

        # 5. Send confirmation on connect
        await websocket.send_text(json.dumps({
            "flag": "Connected",
            "name": restaurant.name
        }))

        # 6. Message loop
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue

            flag = message.get("flag")
            oid = message.get("oid")
            res.OrderStatus[oid] = flag
            
    except WebSocketDisconnect:
        print(f"Restaurant {restaurant_id} disconnected")

    finally:
        Manager.res_manager.restaurants.pop(restaurant_id, None)
        db.close()