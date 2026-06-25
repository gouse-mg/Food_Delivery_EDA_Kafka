import json
class Partners:
    def __init__(self,id,name,Socket,menu=None,data=None):
        self.partner_id = id
        self.data = data
        self.Socket = Socket
        self.name = name
        
class PartnerManager:
    def __init__(self,data=None):
        self.data = data
        self.partners  = {}
        
par_manager = PartnerManager()