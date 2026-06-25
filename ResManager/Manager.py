import json
class Restrurant:
    def __init__(self,id,name,Socket,lat,longi,menu=None,data=None):
        self.restaurant_id = id
        self.menu = menu
        self.data = data
        self.oder_queue = {}
        self.Socket = Socket
        self.name = name
        self.OrderStatus = {}
        self.lat = lat
        self.longi = longi
        
class RestraurantManager:
    def __init__(self,data=None):
        self.data = data
        self.restaurants  = {}
        self.order_status = {}


    async def RequestOrder(self, oid, Res_ids, menu):   # ✅ async
        print("Louda",self.restaurants)
        for res_id in Res_ids:
            res_id = res_id
            await self.restaurants[int(res_id)].Socket.send_text(
                json.dumps({"message": "Got an order", "menu": menu[res_id],"flag":"Order","oid":oid})
            )
            self.restaurants[int(res_id)].OrderStatus[oid] = "Requested"
    
    async def ConfirmOrder(self, Res_ids,oid,menu):
        for res_id in Res_ids:
            print("Confirming order!!")
            await res_manager.restaurants[int(res_id)].Socket.send_text(
            json.dumps({"message": "Confirmed the order !!!","oid":oid,"flag":"Confirm","menu": menu[res_id]})
        )
res_manager = RestraurantManager()



# add logic to push the resrtrrants and receive