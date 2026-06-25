from aiokafka import AIOKafkaProducer

producer: AIOKafkaProducer | None = None


async def start_producer():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    await producer.start()
    print("Kafka producer started")


async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        print("Kafka producer stopped")
