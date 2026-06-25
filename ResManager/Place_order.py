



async def ProcessOrder(cart):                          # ✅ async
    cart = ProcessCart(cart)
    order = Order(cart, cart.keys(), 2)
    print("Order",order.oid)
    order_manager.orders[order.oid] = order
    order_manager.OrderStatus[order.oid] = "True" 
    for idx,res_id in enumerate(cart.keys()):
        await order_manager.RequestOrder(     # ✅ awaited
            order.oid, res_id, cart[res_id]
        )
    await asyncio.sleep(10)
    if order_manager.OrderStatus[order.oid]:
        await order_manager.ConfirmOrder(order.oid)
        return "Order Confirmed",order.oid
    else:
        return "Order Rejected",order.oid