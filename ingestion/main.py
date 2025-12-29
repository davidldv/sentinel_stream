from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException

from models import Transaction

kafka_client = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(*, enable_kafka: bool = True) -> FastAPI:
    global kafka_client
    if enable_kafka and kafka_client is None:
        # Import lazily so unit tests can run without Kafka deps.
        from producer import kafka_client as _kafka_client

        kafka_client = _kafka_client

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if enable_kafka:
            logger.info("Starting Kafka Producer...")
            await kafka_client.start()
        yield
        if enable_kafka:
            logger.info("Stopping Kafka Producer...")
            await kafka_client.stop()

    app = FastAPI(title="SentinelStream Ingestion", lifespan=lifespan)

    @app.post("/transactions/")
    async def create_transaction(transaction: Transaction):
        try:
            # Ensure the payload is JSON-serializable (e.g., datetime -> ISO string)
            if hasattr(transaction, "model_dump"):
                payload = transaction.model_dump(mode="json", exclude_none=True)
            else:
                payload = transaction.dict(exclude_none=True)

            if kafka_client is None:
                raise RuntimeError("Kafka client is not configured")

            await kafka_client.send_message("transactions", payload)
            return {"status": "queued", "transaction_id": transaction.transaction_id}
        except Exception as e:
            logger.error(f"Failed to send transaction: {e}")
            raise HTTPException(status_code=500, detail="Failed to process transaction")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


try:
    app = create_app(enable_kafka=True)
except Exception:
    # Allows unit tests (and local imports) to work without Kafka dependencies.
    app = create_app(enable_kafka=False)


