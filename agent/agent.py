import asyncio
import json
import logging
import os
import time
from redis import asyncio as aioredis
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "").strip().lower()  # openai | gemini
LLM_MODEL = os.getenv("LLM_MODEL")

AGENT_MIN_SECONDS_BETWEEN_LLM_CALLS = float(os.getenv("AGENT_MIN_SECONDS_BETWEEN_LLM_CALLS", "10"))
ANALYSIS_DEDUP_SET_KEY = os.getenv("ANALYSIS_DEDUP_SET_KEY", "analyzed_transactions")


def _build_llm():
    # Provider selection rules:
    # - Default is Gemini.
    # - OpenAI is only used if explicitly selected.
    provider = LLM_PROVIDER or "gemini"

    if provider == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
        model = LLM_MODEL or "gemini-3-flash-preview"
        return ChatGoogleGenerativeAI(google_api_key=GEMINI_API_KEY, model=model)

    if provider == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        model = LLM_MODEL or "gpt-4o-mini"
        return ChatOpenAI(api_key=OPENAI_API_KEY, model=model)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")

async def analyze_transaction(transaction_data: dict):
    try:
        llm = _build_llm()
    except Exception as e:
        logger.warning(f"LLM not configured. Skipping LLM analysis. ({e})")
        return "Analysis skipped (LLM not configured)"
    
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

    # Log which provider/model will be used (helps confirm Gemini is active).
    try:
        provider = (LLM_PROVIDER or "gemini").lower()
        model = LLM_MODEL or ("gemini-3-flash-preview" if provider == "gemini" else "gpt-4o-mini")
        logger.info(f"LLM configured: provider={provider}, model={model}")
    except Exception:
        pass

    last_llm_call_at = 0.0

    while True:
        try:
            # Blocking pop from Redis list
            # blpop returns a tuple (key, element)
            result = await redis.blpop("suspicious_transactions", timeout=1)
            
            if result:
                _, data = result
                transaction = json.loads(data)
                tx_id = transaction.get("transaction_id")
                logger.info(f"Processing suspicious transaction: {tx_id}")

                # Deduplicate so we don't re-analyze the same tx repeatedly.
                if tx_id:
                    already = await redis.sismember(ANALYSIS_DEDUP_SET_KEY, tx_id)
                    if already:
                        logger.info(f"Skipping LLM analysis (already analyzed): {tx_id}")
                        continue

                # Rate-limit LLM calls to avoid quota/rate bursts.
                now = time.time()
                wait_for = AGENT_MIN_SECONDS_BETWEEN_LLM_CALLS - (now - last_llm_call_at)
                if wait_for > 0:
                    await asyncio.sleep(wait_for)

                analysis = await analyze_transaction(transaction)
                last_llm_call_at = time.time()
                logger.info(f"Agent Report:\n{analysis}")

                if tx_id:
                    await redis.sadd(ANALYSIS_DEDUP_SET_KEY, tx_id)
                
                # In a real system, we might store this report in Postgres or alert a human
                
        except Exception as e:
            logger.error(f"Error in agent loop: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_agent())
