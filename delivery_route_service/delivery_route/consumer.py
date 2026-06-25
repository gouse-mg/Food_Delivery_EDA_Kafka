import asyncio
import json

from aiokafka import AIOKafkaConsumer

from Handler.order_placed import handle_order_placed


async def consume():
    """
    Subscribes to the Order-placed topic.
    Reconnects automatically on failure.
    """
    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(
                "Order-placed",
                bootstrap_servers="kafka:9092",
                group_id="route-service-group",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                fetch_max_wait_ms=100,
            )
            await consumer.start()
            print("Consumer ready, waiting for Order-placed messages...")

            async for msg in consumer:
                event = json.loads(msg.value.decode("utf-8"))
                event["topic"] = msg.topic
                print(f"[consumer] Received event on topic={msg.topic} partition={msg.partition} offset={msg.offset}")
                asyncio.create_task(handle_order_placed(event))  # non-blocking

        except asyncio.CancelledError:
            print("[consumer] Cancelled, shutting down.")
            break
        except Exception as e:
            print(f"[consumer] Error: {e} — retrying in 3s...")
            await asyncio.sleep(3)
        finally:
            if consumer:
                try:
                    await consumer.stop()
                except Exception:
                    pass
