# send the message back to the order or user using websocket
from  Manager import order_manager
import asyncio
import json
from Producer import get_producer



async def handle_res_available(event):
    socket = order_manager.web_socket
    print(event['topic'])
    if event['topic'] == 'res-available':

        print("Event consumed res-available")
        cart = event['cart']
        oid = int(event['order_id'])
        flag = event['flag']
        
        if oid in order_manager.Event_counter:
            order_manager.Event_counter[oid]+=1
        else:
            order_manager.Event_counter[oid] = 1
        if oid in order_manager.Event_counter and order_manager.Event_counter[oid] ==2:
            # emmit an event With OrderPlaced
            producer  = get_producer()
            event = {"order_id": oid, "cart": cart,"flag":flag,"order_info":order_manager.order_status[oid]}
            try:
                future = await producer.send(
                    "Order-placed",
                    json.dumps(event).encode("utf-8")
                )
                record_metadata = await future  # ✅ await the future to get actual metadata
                print(f"Message sent to topic={record_metadata.topic} partition={record_metadata.partition} offset={record_metadata.offset}")
                await producer.flush()
            except Exception as e:
                print(f"PRODUCER ERROR: {e}")

            print("Sent an event")
            await socket.send_text(
                json.dumps({"oid":oid,"flag":flag})
            )
            print(order_manager.order_status[oid])

    elif event['topic'] == 'Del-available':
        print("Event consumed del-available")
        # cart = event['cart']
        oid = int(event['order_id'])
        lat = event['lat']
        longi = event['long']
        order_manager.order_status[oid]["del_location"] = [lat,longi]
        flag = event['flag']
        if oid in order_manager.Event_counter:
            order_manager.Event_counter[oid]+=1
        else:
            order_manager.Event_counter[oid] = 1
        if oid in order_manager.Event_counter and order_manager.Event_counter[oid] ==2:
            # emmit an event With OrderPlaced
            producer  = get_producer()
            print("placing order with ",flag)
            event = {"order_id": oid, "cart": cart,"flag":flag,"order_info":order_manager.order_status[oid]}
            try:
                future = await producer.send(
                    "Order-placed",
                    json.dumps(event).encode("utf-8")
                )
                record_metadata = await future  # ✅ await the future to get actual metadata
                print(f"Message sent to topic={record_metadata.topic} partition={record_metadata.partition} offset={record_metadata.offset}")
                await producer.flush()
            except Exception as e:
                print(f"PRODUCER ERROR: {e}")

            print("Sent an event")
            await socket.send_text(
                json.dumps({"oid":oid,"flag":flag})
            )
            print(order_manager.order_status[oid])
        





