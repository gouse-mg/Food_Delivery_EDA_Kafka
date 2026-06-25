class OrderManager:
    def __init__(self):
        self.order_status = {}
        self.Event_counter = {}
        self.web_socket  = None
order_manager = OrderManager()