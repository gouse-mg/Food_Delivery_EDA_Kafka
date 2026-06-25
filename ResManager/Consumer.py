from aiokafka import AIOKafkaConsumer
import json
import asyncio
from Handlers.Ordercreated import ProcessOrder



async def consume():
    print("🔥 consume() function entered") 
    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(
                "order-created","Order-placed",
                bootstrap_servers="kafka:9092",
                group_id="resmanager-group-test",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                fetch_max_wait_ms=100,
            )
            await consumer.start()
            print("Consumer ready, waiting for messages...")
            async for msg in consumer:
                print("Received!!")
                event = json.loads(msg.value.decode("utf-8"))
                event['topic'] = msg.topic

                asyncio.create_task(ProcessOrder(event))  # ✅ non-blocking
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Consumer error: {e}, retrying in 3s...")
            await asyncio.sleep(3)
        finally:
            if consumer:
                try:
                    await consumer.stop()
                except:
                    pass