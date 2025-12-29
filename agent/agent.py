import asyncio
import json
import logging
import os
from redis import asyncio as aioredis
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def analyze_transaction(transaction_data: dict):
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. Skipping LLM analysis.")
        return "Analysis skipped (No API Key)"

    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-3.5-turbo")
    
    prompt = ChatPromptTemplate.from_template(
        "You are a security expert. Analyze the following suspicious transaction and explain why it might be fraudulent based on the amount and location.\n\nTransaction Data: {transaction}"
    )
    
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = await chain.ainvoke({"transaction": json.dumps(transaction_data, indent=2)})
        return response
    except Exception as e:
        logger.error(f"LLM Analysis failed: {e}")
        return "Analysis failed"

async def run_agent():
    redis = aioredis.from_url(REDIS_URL)
    logger.info("Security Agent started. Monitoring suspicious transactions...")

    while True:
        try:
            # Blocking pop from Redis list
            # blpop returns a tuple (key, element)
            result = await redis.blpop("suspicious_transactions", timeout=1)
            
            if result:
                _, data = result
                transaction = json.loads(data)
                logger.info(f"Processing suspicious transaction: {transaction.get('transaction_id')}")
                
                analysis = await analyze_transaction(transaction)
                logger.info(f"Agent Report:\n{analysis}")
                
                # In a real system, we might store this report in Postgres or alert a human
                
        except Exception as e:
            logger.error(f"Error in agent loop: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_agent())
