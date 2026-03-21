import requests
from qdrant_client import QdrantClient

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "bge-m3:latest"

def get_embedding(text: str) -> list[float]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text}
    )
    return response.json()["embedding"]

client = QdrantClient(url="http://localhost:6333")

query = input("Запрос: ")
vector = get_embedding(query)

results = client.query_points(
    collection_name="law",
    query=vector,
    limit=3
).points

for r in results:
    print(f"Score: {r.score:.3f}")
    print(f"Heading: {r.payload['metadata']['heading']}")
    print(r.payload['page_content'][:200])
    print("---")