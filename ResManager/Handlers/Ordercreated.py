import random
import asyncio
import Manager
from Producer import get_producer
import json
def ProcessCart(cart):
    result = {}
    for dish_id, res_id in cart:
        if res_id not in result:
            result[res_id] = []
        result[res_id].append(dish_id)
    return result

async def ProcessOrder(event):
    print("Loudddddddddddd")
    cart = event['cart']
    print(cart)
    order_id = int(event['order_id'])
    print("Handling the Event.....",event['topic'])
    print("Order", order_id)
    if event['topic'] == 'order-created': 
        print("Received order created")
        await Manager.res_manager.RequestOrder(order_id, cart.keys(), cart)
        Manager.res_manager.order_status[int(order_id)] = "Requested"
        await asyncio.sleep(10)
        flag = True
        for res_ids in cart.keys():
            if order_id in Manager.res_manager.restaurants[int(res_ids)].OrderStatus and \
            Manager.res_manager.restaurants[int(res_ids)].OrderStatus[order_id] == "accepted":
                continue
            else:
                flag = False
                break
        if flag:
            Manager.res_manager.order_status[int(order_id)] = "Available"
        # emmit an event saying that res-available
        producer  = get_producer()

        event = {"order_id": order_id, "cart": cart,"flag":flag}
        try:
            future = await producer.send(
                "res-available",
                json.dumps(event).encode("utf-8")
            )
            record_metadata = await future  # ✅ await the future to get actual metadata
            print(f"Message sent to topic={record_metadata.topic} partition={record_metadata.partition} offset={record_metadata.offset}")
            await producer.flush()
        except Exception as e:
            print(f"PRODUCER ERROR: {e}")

        print("Sent an event")
        return {"Status":"Requested"}
    elif event['topic'] == 'Order-placed':
        print("Recived-created")
        await Manager.res_manager.ConfirmOrder(cart.keys(), order_id, cart)

