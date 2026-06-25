from aiokafka import AIOKafkaProducer

producer: AIOKafkaProducer | None = None

async def start_producer():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    await producer.start()

async def stop_producer():
    global producer
    if producer:
        await producer.stop()

def get_producer() -> AIOKafkaProducer:
    if producer is None:
        raise RuntimeError("Producer not started")
    return producer