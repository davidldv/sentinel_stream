# SentinelStream

A Distributed, Real-Time Intelligent Event Processing System.

## Architecture

- **Ingestion Layer**: FastAPI + Kafka
- **Processing Engine**: Python Consumer + Scikit-Learn
- **Intelligence Layer**: LangChain Agent
- **Storage**: Redis + PostgreSQL
- **Infrastructure**: Docker + Kubernetes

## Setup

1. Set your OpenAI API Key (optional, for Agent):

   **Recommended (Docker Compose):**
   - Copy `.env.example` to `.env`
   - Set `OPENAI_API_KEY=your_key_here` in `.env`

   **Alternative (running without Compose):**
   - PowerShell:
     ```powershell
     $env:OPENAI_API_KEY = "your_key_here"
     ```
   - Bash:
     ```bash
     export OPENAI_API_KEY=your_key_here
     ```

   **Gemini (recommended if OpenAI quota is exceeded):**
   - Copy `.env.example` to `.env`
   - Set `GEMINI_API_KEY=your_key_here` in `.env`

   **By default, the agent prefers Gemini** (and will only use OpenAI if you set `LLM_PROVIDER=openai`).

   **To reduce LLM calls:** set `AGENT_MIN_SECONDS_BETWEEN_LLM_CALLS=10` (or higher) in `.env`.

2. Start infrastructure and services:
   ```bash
   docker-compose up --build -d
   ```

3. Send a test transaction:
   ```bash
   curl -X POST "http://localhost:8000/transactions/" \
        -H "Content-Type: application/json" \
        -d '{
              "transaction_id": "tx_123",
              "user_id": "user_456",
              "amount": 5000.0,
              "currency": "USD",
              "timestamp": "2023-10-27T10:00:00",
              "merchant_id": "merch_789",
              "location": "New York",
              "ip_address": "192.168.1.1"
            }'
   ```

4. Check logs to see the pipeline in action:
   ```bash
   docker-compose logs -f processing agent
   ```

