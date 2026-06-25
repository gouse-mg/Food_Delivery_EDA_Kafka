from aiokafka import AIOKafkaConsumer
import json
import asyncio
from Handler.res_available import handle_res_available

async def consume():
    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(
                "res-available","Del-available",
                bootstrap_servers="kafka:9092",
                group_id="orderapi-group",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                fetch_max_wait_ms=100,
            )
            await consumer.start()
            print("Consumer ready, waiting for messages...")
            async for msg in consumer:
                
                event = json.loads(msg.value.decode("utf-8"))
                event['topic'] = msg.topic
                print("Received event")
                asyncio.create_task(handle_res_available(event))  # ✅ non-blocking
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