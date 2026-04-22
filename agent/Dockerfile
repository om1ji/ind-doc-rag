FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    sse-starlette \
    langgraph \
    langchain \
    langchain-core \
    langchain-openai \
    langchain-qdrant \
    qdrant-client \
    "fastembed>=0.3"

COPY agent/ ./agent/
COPY ingestion/ ./ingestion/

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "8001"]
