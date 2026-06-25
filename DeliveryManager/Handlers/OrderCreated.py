import asyncio
from Producer import get_producer
import random
import json
async def ProcessOrder(event):
    # res_locations here res_id :[lat,long]
    print("Received the event here")
    res_locations = event['Locations']
    order_id = event['order_id']
    user_location = event['Destin']
    # assign the nearest available partner to one of the re
    flag = 0
    lat, longi = 12.9716 + random.uniform(-0.03, 0.03), 77.5946 + random.uniform(-0.03, 0.03)

    # place the event saying that the Delivery-available is available with the locations of the driver
    producer  = get_producer()

    event = {"order_id": order_id, "lat":lat,"long":longi,"flag":flag}
    try:
        future = await producer.send(
            "Del-available",
            json.dumps(event).encode("utf-8")
        )
        record_metadata = await future  # ✅ await the future to get actual metadata
        print(f"Message sent to topic={record_metadata.topic} partition={record_metadata.partition} offset={record_metadata.offset}")
        await producer.flush()
    except Exception as e:
        print(f"PRODUCER ERROR: {e}")

    print("Sent an event")
    return {"Status":"Requested"}


    

    