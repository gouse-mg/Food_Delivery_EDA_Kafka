from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from jose import JWTError
from Dependencies.data import SessionLocal
from DataModels.Partners import Partners
from Config.Security import decode_token
import Manager
import json

router = APIRouter(prefix = "/communicate")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    partner_id: int = Query(...),
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
    if current_id != partner_id:
        await websocket.close(code=1008, reason="Not your restaurant")
        return

    # 3. Manual DB session
    db: Session = SessionLocal()
    try:
        partner = db.query(Partners).filter(Partners.id == partner_id).first()
        if not partner:
            await websocket.close(code=1008, reason="Partners not found")
            return

        # 4. Register in manager
        part = Manager.Partners(
            id=partner.id,
            Socket=websocket,
            name=partner.name
        )
        Manager.par_manager.partners[partner_id] = part

        # 5. Send confirmation on connect
        await websocket.send_text(json.dumps({
            "flag": "Connected",
            "name": partner.name
        }))
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # handle incoming messages from partner here
            print(f"Received from partner {partner_id}: {message}")

            
    except WebSocketDisconnect:
        print(f"Restaurant {partner_id} disconnected")

    finally:
        Manager.par_manager.partners.pop(partner_id, None)
        db.close()