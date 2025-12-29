import asyncio
import json
import logging
import os
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from redis import asyncio as aioredis
from model import FraudDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RESULTS_HASH_KEY = os.getenv("RESULTS_HASH_KEY", "transaction_results")
SUSPICIOUS_LIST_KEY = os.getenv("SUSPICIOUS_LIST_KEY", "suspicious_transactions")

async def consume():
    consumer = AIOKafkaConsumer(
        "transactions",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="fraud-detector-group",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    redis = aioredis.from_url(REDIS_URL)
    detector = FraudDetector()

    # Kafka may not be ready immediately; retry bootstrap.
    last_err = None
    for attempt in range(1, 31):
        try:
            await consumer.start()
            break
        except KafkaConnectionError as e:
            last_err = e
            logger.warning(f"Kafka not ready yet (attempt {attempt}/30): {e}")
            await asyncio.sleep(min(1.0 + (attempt * 0.2), 5.0))
    else:
        raise last_err or RuntimeError("Kafka consumer failed to start")
    try:
        logger.info("Starting Consumer...")
        async for msg in consumer:
            transaction = msg.value
            amount = transaction.get("amount", 0.0)
            tx_id = transaction.get("transaction_id")
            
            is_fraud = detector.predict(amount)

            # Persist the decision for downstream consumers + integration tests.
            if tx_id:
                await redis.hset(
                    RESULTS_HASH_KEY,
                    tx_id,
                    json.dumps({"is_fraud": bool(is_fraud), "transaction": transaction}),
                )
            
            if is_fraud:
                logger.warning(f"Fraud detected for transaction {tx_id}: Amount {amount}")
                # Store in Redis for the Agent to pick up
                await redis.rpush(SUSPICIOUS_LIST_KEY, json.dumps(transaction))
            else:
                logger.info(f"Transaction {tx_id} is clean.")
                
    except Exception as e:
        logger.error(f"Error in consumer: {e}")
    finally:
        await consumer.stop()
        await redis.close()

if __name__ == "__main__":
    asyncio.run(consume())
