import manager


async def handle_order_placed(event: dict):
    """
    Consumes an Order-placed event and stores order_info
    into the global order_status dict keyed by order_id.

    Expected event shape:
    {
        "order_id": str,
        "cart":     any,
        "flag":     any,
        "order_info": {
            "res-available": {"res_id": int, "location": [lat, lng]},
            "del location":  [lat, lng],
            "order-location": [lat, lng]
        }
    }
    """
    oid        = str(event.get("order_id"))
    order_info = event.get("order_info")

    if not oid:
        print(f"[handle_order_placed] Missing order_id in event: {event}")
        return

    if not order_info:
        print(f"[handle_order_placed] Missing order_info for order {oid}")
        return

    manager.order_status[oid] = order_info
    print(f"[handle_order_placed] Stored order_info for order_id={oid}: {order_info}")
