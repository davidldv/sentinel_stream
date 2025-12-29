import json
from aiokafka import AIOKafkaProducer
import asyncio
import os
from aiokafka.errors import KafkaConnectionError

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

class KafkaProducerClient:
    def __init__(self):
        self.producer = None

    async def start(self):
        # Kafka can take a few seconds to become ready after container start.
        # Retry bootstrap to avoid crashing the API during startup.
        last_err = None
        for attempt in range(1, 31):
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                )
                await self.producer.start()
                return
            except KafkaConnectionError as e:
                last_err = e
                await asyncio.sleep(min(1.0 + (attempt * 0.2), 5.0))

        raise last_err or RuntimeError("Kafka producer failed to start")

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_message(self, topic: str, message: dict):
        if not self.producer:
            raise Exception("Producer not started")
        await self.producer.send_and_wait(topic, message)

kafka_client = KafkaProducerClient()
